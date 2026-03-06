"""
Responsible for: rendering the Comprehensive Report tab.
"""

import streamlit as st
from datetime import datetime

from backend.gee.index_calculator import IndexCalculator
from backend.gee.statistics_calculator import StatisticsCalculator
from backend.export.report_builder import ReportBuilder
from frontend.components.metric_cards import MetricCards
from config.indices_config import INDICES_CONFIG


class ReportTab:
    """
    Renders the full monitoring export tab:
    - Executive summary cards
    - Site + data parameters
    - Per-index analysis with interpretation
    - Data quality assessment
    - Methodology section
    - Download buttons (JSON / TXT / CSV)

    Usage:
        tab = ReportTab(results)
        tab.render()
    """

    def __init__(self, results: dict):
        self._config     = results['config']
        self._collection = results['collection']
        self._aoi        = results['aoi']
        self._count      = results['count']
        self._calc       = IndexCalculator()
        self._stats_calc = StatisticsCalculator()
        self._cards      = MetricCards()

    def render(self) -> None:
        st.subheader('Comprehensive Monitoring Report')

        self._render_summary_cards()
        st.markdown('---')
        self._render_site_info()
        st.markdown('---')

        indices_stats = self._compute_all_stats()
        if self._count > 0:
            self._render_indices_analysis(indices_stats)

        st.markdown('---')
        self._render_data_quality()
        st.markdown('---')
        self._render_methodology()
        st.markdown('---')
        self._render_downloads(indices_stats)

    # ── Sections ─────────────────────────────────────────────────────────────

    def _render_summary_cards(self) -> None:
        st.markdown('### Executive Summary')
        cols = st.columns(3)
        self._cards.render_in_column(cols[0], 'Site Information',
                                     self._config['site_name'], 'purple')
        self._cards.render_in_column(cols[1], 'Images Analysed',
                                     f"{self._count} Sentinel-2 scenes",  'pink')
        days = (self._config['end_date'] - self._config['start_date']).days
        self._cards.render_in_column(cols[2], 'Time Span',
                                     f'{days} days', 'blue')

    def _render_site_info(self) -> None:
        st.markdown('### Site Location & Parameters')
        col1, col2 = st.columns(2)
        cfg = self._config

        with col1:
            st.markdown("""
            <div style='background:#f8f9fa;padding:20px;border-radius:10px;border-left:4px solid #667eea;'>
                <h4 style='color:#2c3e50;margin-top:0;'>Geographic Information</h4>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - **Latitude:** {cfg['center_lat']:.6f}°
            - **Longitude:** {cfg['center_lon']:.6f}°
            - **Radius:** {cfg['buffer_km']} km
            - **Area:** ~{3.14159 * cfg['buffer_km']**2:.2f} km²
            """)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style='background:#f8f9fa;padding:20px;border-radius:10px;border-left:4px solid #764ba2;'>
                <h4 style='color:#2c3e50;margin-top:0;'>Acquisition Parameters</h4>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            - **Start Date:** {cfg['start_date'].strftime('%B %d, %Y')}
            - **End Date:** {cfg['end_date'].strftime('%B %d, %Y')}
            - **Max Cloud Cover:** {cfg['cloud_cover']}%
            - **Satellite:** Sentinel-2 MSI (10m)
            - **Indices:** {', '.join(cfg['indices'])}
            """)
            st.markdown('</div>', unsafe_allow_html=True)

    def _render_indices_analysis(self, indices_stats: dict) -> None:
        st.markdown('### Spectral Indices Analysis Results')

        for idx in self._config['indices']:
            with st.expander(f'**{idx}** — Detailed Analysis', expanded=True):
                stats = indices_stats.get(idx, {})
                self._cards.render_stats_row(stats, idx)

                st.markdown('**Interpretation:**')
                median_val = stats.get(f'{idx}_median', 0)
                self._interpret(idx, median_val)

    def _interpret(self, idx: str, median_val: float) -> None:
        """Simple rule-based interpretation (no AI — AI is in ChangeTab)."""
        rules = {
            'NDVI': [
                (0.2,  'warning', 'Low vegetation cover. May indicate bare soil, urban areas, or stress.'),
                (0.4,  'info',    'Moderate vegetation cover. Mix of vegetated and non-vegetated areas.'),
                (None, 'success', 'Healthy vegetation cover detected.'),
            ],
            'NDBI': [
                (0.3,  'warning', 'Significant built-up area. Monitor urban encroachment.'),
                (0.0,  'info',    'Some built-up structures present.'),
                (None, 'success', 'Predominantly natural landscape.'),
            ],
            'NDMI': [
                (-0.2, 'warning', 'Low moisture content. Increased erosion risk.'),
                (0.2,  'info',    'Moderate moisture levels. Normal conditions.'),
                (None, 'success', 'High moisture content.'),
            ],
            'NDWI': [
                (0.3,  'info', 'Significant water presence detected. Monitor for flooding risk.'),
                (0.0,  'info', 'Some water bodies present.'),
                (None, 'success', 'No significant water accumulation.'),
            ],
            'BSI': [
                (0.3,  'warning', 'High bare soil exposure. Increased erosion vulnerability.'),
                (0.0,  'info',    'Moderate soil exposure present.'),
                (None, 'success', 'Minimal bare soil.'),
            ],
        }
        for threshold, level, message in rules.get(idx, []):
            if threshold is None or median_val < threshold:
                getattr(st, level)(message)
                return
        st.info(f'**{idx}** median: {median_val:.4f}. Interpret in context of site conditions.')

    def _render_data_quality(self) -> None:
        st.markdown('### Data Quality Assessment')
        col1, col2 = st.columns(2)
        coverage = 'excellent' if self._count >= 20 else 'good' if self._count >= 10 else 'adequate'

        with col1:
            st.markdown(f"""
            <div style='background:#e8f5e9;padding:15px;border-radius:8px;border-left:4px solid #4caf50;'>
                <h4 style='color:#2e7d32;margin-top:0;'>Data Strengths</h4>
            </div>""", unsafe_allow_html=True)
            st.markdown(f"""
            - **Image Count:** {self._count} scenes — {coverage} temporal coverage
            - **Resolution:** 10-metre spatial resolution
            - **Multi-spectral:** 13 bands from visible to SWIR
            - **Cloud Filtering:** ≤ {self._config['cloud_cover']}% cloud cover
            - **Revisit Time:** 5-day satellite cycle
            """)

        with col2:
            st.markdown("""
            <div style='background:#fff3e0;padding:15px;border-radius:8px;border-left:4px solid #ff9800;'>
                <h4 style='color:#e65100;margin-top:0;'>Limitations</h4>
            </div>""", unsafe_allow_html=True)
            st.markdown("""
            - Residual clouds may affect local quality
            - Weather conditions may create temporal gaps
            - 10m resolution may miss fine architectural details
            - Surface-only observations (no subsurface)
            - Ground-truth validation recommended
            """)

    def _render_methodology(self) -> None:
        with st.expander('Methodology & Scientific Background', expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                #### Data Sources
                **Sentinel-2 Mission:**
                - ESA Earth observation program
                - Twin satellites (2A & 2B), launched 2015/2017
                - 13 spectral bands, 290 km swath
                - 5-day global revisit cycle

                **Processing Platform:**
                - Google Earth Engine cloud computing
                - Petabyte-scale imagery archive
                """)
            with col2:
                st.markdown("""
                #### Spectral Indices Formulas
                ```
                NDVI = (B8 - B4) / (B8 + B4)
                NDBI = (B11 - B8) / (B11 + B8)
                NDMI = (B8 - B11) / (B8 + B11)
                NDWI = (B3 - B8) / (B3 + B8)
                BSI  = ((B11+B4)-(B8+B2)) / ((B11+B4)+(B8+B2))
                ```
                """)

    def _render_downloads(self, indices_stats: dict) -> None:
        st.markdown('### Export Report & Data')

        builder = ReportBuilder(self._config, indices_stats, self._count)
        base    = builder.filename_base()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                'Download JSON Report',
                data=builder.as_json(),
                file_name=f'{base}.json',
                mime='application/json',
            )
        with col2:
            st.download_button(
                'Download Text Report',
                data=builder.as_text(),
                file_name=f'{base}.txt',
                mime='text/plain',
            )
        with col3:
            if indices_stats:
                st.download_button(
                    'Download Statistics CSV',
                    data=builder.as_csv(),
                    file_name=f'{base}.csv',
                    mime='text/csv',
                )

    # ── Private helpers ──────────────────────────────────────────────────────

    def _compute_all_stats(self) -> dict:
        if self._count == 0:
            return {}
        extra        = self._config.get('custom_indices', [])
        median_image = self._collection.median()
        indexed      = self._calc.compute(median_image, extra_indices=extra)
        return self._stats_calc.run_multiple(indexed, self._aoi, self._config['indices'])