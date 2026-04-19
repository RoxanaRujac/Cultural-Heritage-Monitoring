"""
Responsible for: rendering the Comprehensive Report tab.
"""

import streamlit as st
from datetime import datetime

from backend.gee.index_calculator import IndexCalculator
from backend.gee.statistics_calculator import StatisticsCalculator
from backend.export.report_builder import ReportBuilder
from frontend.components.metric_cards import MetricCards
from backend.ai.ai_interpreter import AIInterpreter
from config.indices_config import INDICES_CONFIG
import tempfile
import os
import io


class ReportTab:
    """
    Renders the full monitoring export tab:
    - Executive summary cards
    - Site + data parameters
    - Per-index analysis with AI interpretation
    - Data quality assessment
    - Methodology section
    - Download buttons (JSON / TXT / CSV / PDF)

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
        self.ai          = AIInterpreter()

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
                                     self._config['site_name'])
        self._cards.render_in_column(cols[1], 'Images Analysed',
                                     f"{self._count} Sentinel-2 scenes")
        days = (self._config['end_date'] - self._config['start_date']).days
        self._cards.render_in_column(cols[2], 'Time Span',
                                     f'{days} days')

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

                st.markdown('**AI Interpretation:**')
                median_val = stats.get(f'{idx}_median', 0)
                self._interpret_with_ai(idx, median_val)

    def _interpret_with_ai(self, idx: str, median_val: float) -> None:
        """Generate AI interpretation for a single index based on its median value."""
        cache_key = f'report_ai_{idx}_{self._config["site_name"]}_{median_val:.4f}'

        if cache_key not in st.session_state:
            idc = INDICES_CONFIG.get(idx, {})
            index_desc   = idc.get('description', '')
            heritage_use = idc.get('heritage_use', '')
            vmin         = idc.get('min', -1)
            vmax         = idc.get('max', 1)

            prompt = (
                f"You are an expert in satellite remote sensing and cultural heritage conservation.\n\n"
                f"A spectral index analysis for **{self._config['site_name']}** produced the following result:\n"
                f"- Index: {idx}\n"
                f"- Description: {index_desc}\n"
                f"- Heritage relevance: {heritage_use}\n"
                f"- Typical value range: {vmin} to {vmax}\n"
                f"- Observed median value: {median_val:.4f}\n\n"
                f"Provide a concise professional interpretation (4-5 sentences) covering:\n"
                f"1. What this observed value physically represents for this site.\n"
                f"2. Whether the value is concerning, normal, or positive relative to typical ranges.\n"
                f"3. Any specific risks or opportunities for heritage conservation.\n"
                f"4. One concrete recommended action for conservators.\n\n"
                f"Write clearly and professionally for heritage conservation specialists. "
                f"Respond in English only. Do not use bullet points — write in flowing prose."
            )

            with st.spinner(f'AI is analysing {idx}…'):
                text = self.ai.FALLBACK_MSG
                with st.spinner(f'AI is analysing {idx}…'):
                    text = self.ai.interpret(
                        index_name=idx,
                        before_mean=median_val,
                        after_mean=median_val,
                        context=self._config['site_name'],
                    )

            st.session_state[cache_key] = text

        ai_text = st.session_state[cache_key]

        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #1a1a2e 0%, #2c2040 100%);
                border: 1px solid rgba(118,75,162,0.5);
                border-left: 4px solid #764ba2;
                border-radius: 8px;
                padding: 14px 18px;
                margin-top: 10px;
                color: #e8e0f0;
                font-size: 14px;
                line-height: 1.75;
            ">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                    <span style="
                        font-size:11px;
                        font-weight:700;
                        color:#f0c040;
                        letter-spacing:1px;
                        text-transform:uppercase;
                    ">AI Analysis · {idx}</span>
                </div>
                <div style="color:#ddd8f0;">{ai_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

        # ── Collect AI texts already generated in the session ─────────────────
        ai_texts = {}
        for idx in self._config['indices']:
            stats = indices_stats.get(idx, {})
            med   = stats.get(f'{idx}_median', 0)
            ck    = f'report_ai_{idx}_{self._config["site_name"]}_{med:.4f}'
            if ck in st.session_state:
                ai_texts[idx] = st.session_state[ck]

        # ── Pre-generate PDF bytes and cache them ─────────────────────────────
        pdf_cache_key = f'pdf_bytes_{base}'
        if pdf_cache_key not in st.session_state:
            with st.spinner('Fetching satellite map thumbnails from GEE and building PDF… (20–60 s)'):
                try:
                    pdf_bytes = builder.as_pdf(
                        ai_texts=ai_texts,
                        collection=self._collection,
                        aoi=self._aoi,
                    )
                    st.session_state[pdf_cache_key] = pdf_bytes
                except Exception as exc:
                    st.error(f'PDF generation failed: {exc}')
                    import traceback
                    st.code(traceback.format_exc())
                    st.session_state[pdf_cache_key] = None

        pdf_bytes = st.session_state.get(pdf_cache_key)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.download_button(
                '⬇ JSON Report',
                data=builder.as_json(),
                file_name=f'{base}.json',
                mime='application/json',
            )
        with col2:
            st.download_button(
                '⬇ Text Report',
                data=builder.as_text(),
                file_name=f'{base}.txt',
                mime='text/plain',
            )
        with col3:
            if indices_stats:
                st.download_button(
                    '⬇ CSV Report',
                    data=builder.as_csv(),
                    file_name=f'{base}.csv',
                    mime='text/csv',
                )
        with col4:
            if pdf_bytes:
                st.download_button(
                    '⬇ PDF Report',
                    data=pdf_bytes,
                    file_name=f'{base}.pdf',
                    mime='application/pdf',
                    type='primary',
                )
            else:
                if st.button('⬇ PDF Report', type='primary', use_container_width=True,
                             key='pdf_retry'):
                    # Clear cache so next render re-tries generation
                    if pdf_cache_key in st.session_state:
                        del st.session_state[pdf_cache_key]
                    st.rerun()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _compute_all_stats(self) -> dict:
        if self._count == 0:
            return {}
        extra        = self._config.get('custom_indices', [])
        median_image = self._collection.median()
        indexed      = self._calc.compute(median_image, extra_indices=extra)
        return self._stats_calc.run_multiple(indexed, self._aoi, self._config['indices'])