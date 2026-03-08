"""
Responsible for: rendering the Change Detection tab.
"""

import streamlit as st
import folium
import ee
from datetime import datetime

import geemap.foliumap as geemap

from config.indices_config import INDICES_CONFIG
from backend.gee.index_calculator import IndexCalculator
from backend.gee.statistics_calculator import StatisticsCalculator
from backend.gee.change_detector import (
    ChangeDetector, SEVERITY_COLOR, SEVERITY_LABEL
)
from backend.ai.ai_interpreter import AIInterpreter
from utils.date_utils import DateUtils
from utils.visualization import ChartBuilder
from frontend.components.map_widget import MapWidget

try:
    from streamlit_folium import st_folium
    _HAS_ST_FOLIUM = True
except ImportError:
    _HAS_ST_FOLIUM = False


class ChangeTab:
    """
    Renders the Change Detection tab:
    - Split map (before / after index overlay)
    - Annotated change map with sampled event markers
    - Events table
    - Statistical comparison
    - AI interpretation

    Usage:
        tab = ChangeTab(results)
        tab.render()
    """

    def __init__(self, results: dict, history_repo=None):
        self._config       = results['config']
        self._collection   = results['collection']
        self._aoi          = results['aoi']
        self._count        = results['count']
        self._history_repo = history_repo          # HistoryRepository | None
        self._calc         = IndexCalculator()
        self._stats_calc   = StatisticsCalculator()
        self._detector     = ChangeDetector()
        self._ai           = AIInterpreter()
        self._charts       = ChartBuilder()
        self._widget       = MapWidget(self._config['center_lat'], self._config['center_lon'])

    def render(self) -> None:
        st.subheader('Change Detection & AI Insights')

        if self._count < 2:
            st.warning('At least 2 images required for change detection.')
            return

        first_image, last_image, first_date, last_date = self._load_boundary_images()
        st.info(f'Comparing: {first_date} → {last_date}')

        change_index, threshold = self._render_controls()
        vis_rgb   = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4}
        vis_index = self._get_vis_params(change_index)

        self._render_split_map(first_image, last_image, change_index, vis_rgb, vis_index,
                               first_date, last_date)
        self._render_palette_bar(change_index, vis_index)

        st.markdown('### Change Detection Map')
        st.caption(f'Click markers for details · Threshold: ±{threshold}')

        with st.spinner('Detecting significant change locations...'):
            events = self._detector.sample_change_points(
                first_image, last_image, self._aoi, change_index, threshold
            )

        self._render_annotated_map(first_image, last_image, change_index, threshold,
                                   first_date, last_date, events)
        self._render_change_legend()
        st.markdown('---')
        self._render_events_table(events, change_index, first_date, last_date)
        before_stats, after_stats = self._render_stats_comparison(
            first_image, last_image, change_index, first_date, last_date
        )
        ai_text = self._render_ai_section(first_image, last_image, change_index,
                                          before_stats, after_stats)
        self._auto_save_snapshot(
            change_index, threshold, first_date, last_date,
            before_stats, after_stats, events, ai_text,
        )

    # ── Data loading ─────────────────────────────────────────────────────────

    def _load_boundary_images(self):
        extra      = self._config.get('custom_indices', [])
        image_list = self._collection.toList(self._collection.size())
        dates      = self._collection.aggregate_array('system:time_start').getInfo()

        first_image = self._calc.compute(ee.Image(image_list.get(0)), extra_indices=extra)
        last_image  = self._calc.compute(ee.Image(image_list.get(self._count - 1)), extra_indices=extra)
        first_date  = DateUtils.from_timestamp_ms(dates[0]).strftime('%Y-%m-%d')
        last_date   = DateUtils.from_timestamp_ms(dates[-1]).strftime('%Y-%m-%d')

        return first_image, last_image, first_date, last_date

    # ── Controls ─────────────────────────────────────────────────────────────

    def _render_controls(self) -> tuple[str, float]:
        col1, col2 = st.columns([3, 1])
        with col1:
            change_index = st.selectbox('Select Index for Change Detection', self._config['indices'])
        with col2:
            threshold = st.slider('Change Threshold', 0.05, 0.5, 0.20, 0.05)
        return change_index, threshold

    # ── Split map ─────────────────────────────────────────────────────────────

    def _render_split_map(self, first_image, last_image, idx, vis_rgb, vis_index,
                          first_date, last_date) -> None:
        st.markdown('### Before vs After — Index Overlay (Split View)')
        st.caption(f'Left: **{first_date}** | Right: **{last_date}** | Overlay: **{idx}**')

        try:
            blend_params = {'bands': ['vis-red', 'vis-green', 'vis-blue'], 'min': 0, 'max': 255}

            def blend(img):
                rgb_vis = img.visualize(**vis_rgb)
                idx_vis = img.select(idx).visualize(**vis_index)
                return rgb_vis.multiply(0.55).add(idx_vis.multiply(0.45)).toUint8()

            before_blend = blend(first_image)
            after_blend  = blend(last_image)

            center = [self._config['center_lat'], self._config['center_lon']]
            m = geemap.Map(center=center, zoom=14, add_google_map=False)
            m.add_basemap('HYBRID')
            left  = geemap.ee_tile_layer(before_blend, blend_params, f'Before {idx}: {first_date}')
            right = geemap.ee_tile_layer(after_blend,  blend_params, f'After {idx}: {last_date}')
            m.split_map(left_layer=left, right_layer=right)
            m.centerObject(self._aoi, 14)

            if _HAS_ST_FOLIUM:
                st_folium(m, height=520, width='100%', returned_objects=[])
            else:
                m.to_streamlit(height=520)
        except Exception as e:
            st.error(f'Split map error: {e}')

    def _render_palette_bar(self, idx: str, vis_index: dict) -> None:
        palette = vis_index.get('palette', [])
        if not palette:
            return
        hex_colors = ['#' + p if not p.startswith('#') else p for p in palette]
        grad = ', '.join(hex_colors)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;padding:6px 0 16px 0;font-size:13px;">
            <strong>{idx} scale:</strong>
            <span style="background:linear-gradient(to right,{grad});width:180px;height:14px;
                  display:inline-block;border-radius:3px;vertical-align:middle;border:1px solid #555;">
            </span>
            <span>{vis_index.get('min', '')}</span>
            <span style="margin:0 4px;">→</span>
            <span>{vis_index.get('max', '')}</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Annotated change map ─────────────────────────────────────────────────

    def _render_annotated_map(self, first_image, last_image, idx, threshold,
                              first_date, last_date, events) -> None:
        overlay = self._detector.build_change_overlay(first_image, last_image, idx, threshold)
        center  = [self._config['center_lat'], self._config['center_lon']]

        m = geemap.Map(center=center, zoom=14, add_google_map=False)
        m.add_basemap('HYBRID')
        m.addLayer(overlay, {'bands': ['vis-red', 'vis-green', 'vis-blue'], 'min': 0, 'max': 255},
                   f'RGB + {idx} Changes')

        aoi_style = ee.FeatureCollection(self._aoi).style(
            color='764ba2', fillColor='764ba200', width=2
        )
        m.addLayer(aoi_style, {}, 'AOI')

        for i, ev in enumerate(events):
            color      = SEVERITY_COLOR[ev['severity']].lstrip('#')
            popup_html = self._event_popup_html(ev, color, idx, first_date, last_date)
            folium.CircleMarker(
                location=[ev['lat'], ev['lon']],
                radius=10,
                color='#' + color, fill=True, fill_color='#' + color,
                fill_opacity=0.7, weight=2,
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f'#{i+1} Δ{ev["delta"]:+.3f} — {ev["severity"]}',
            ).add_to(m)
            folium.Marker(
                location=[ev['lat'], ev['lon']],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:10px;font-weight:700;color:white;'
                         f'background:#{color};border-radius:50%;width:18px;height:18px;'
                         f'display:flex;align-items:center;justify-content:center;'
                         f'margin-top:-9px;margin-left:-9px;">{i+1}</div>',
                    icon_size=(18, 18),
                ),
            ).add_to(m)

        m.add_layer_control()
        m.centerObject(self._aoi, 14)

        if _HAS_ST_FOLIUM:
            st_folium(m, height=540, width='100%', returned_objects=[])
        else:
            m.to_streamlit(height=540)

    @staticmethod
    def _event_popup_html(ev, color, idx, first_date, last_date) -> str:
        sev_label = SEVERITY_LABEL[ev['severity']]
        delta_color = '#c0392b' if ev['delta'] < 0 else '#2d7a4f'
        return f"""
        <div style="font-family:Arial,sans-serif;min-width:200px;padding:4px;">
            <div style="font-weight:700;font-size:13px;color:#{color};margin-bottom:4px;">
                {sev_label} — {idx}
            </div>
            <table style="font-size:12px;width:100%;">
                <tr><td style="color:#666;">Before ({first_date}):</td><td><b>{ev['value_before']:.4f}</b></td></tr>
                <tr><td style="color:#666;">After ({last_date}):</td><td><b>{ev['value_after']:.4f}</b></td></tr>
                <tr><td style="color:#666;">Change (Δ):</td>
                    <td><b style="color:{delta_color}">{ev['delta']:+.4f}</b></td></tr>
                <tr><td style="color:#666;">Location:</td><td>{ev['lat']:.5f}°N, {ev['lon']:.5f}°E</td></tr>
            </table>
        </div>
        """

    @staticmethod
    def _render_change_legend() -> None:
        st.markdown("""
        <div style="display:flex;gap:24px;padding:8px 0 16px 0;font-size:14px;align-items:center;">
            <strong>Legend:</strong>
            <span><span style="display:inline-block;width:16px;height:16px;background:#FF0000;
                  border-radius:3px;margin-right:6px;vertical-align:middle;"></span>Decrease</span>
            <span><span style="display:inline-block;width:16px;height:16px;background:#AAAAAA;
                  border:1px solid #999;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>No change</span>
            <span><span style="display:inline-block;width:16px;height:16px;background:#0000FF;
                  border-radius:3px;margin-right:6px;vertical-align:middle;"></span>Increase</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Events table ─────────────────────────────────────────────────────────

    def _render_events_table(self, events, idx, first_date, last_date) -> None:
        if not events:
            st.info('No significant change events detected above the threshold.')
            return

        st.markdown('### Significant Change Events')
        st.caption(f'Detected changes in **{idx}** between {first_date} and {last_date}')

        headers = ['#', 'Severity', 'Location', f'{idx} Before', f'{idx} After', 'Δ Change', 'Direction', 'Summary']
        header_cols = st.columns([0.5, 1.5, 1.5, 1.2, 1.2, 1.2, 1.2, 2])
        for col, h in zip(header_cols, headers):
            col.markdown(f'**{h}**')
        st.markdown('<hr style="margin:4px 0;border-color:#c5c5d8;">', unsafe_allow_html=True)

        for i, ev in enumerate(events):
            sev_color   = SEVERITY_COLOR[ev['severity']]
            direction   = 'Decrease' if ev['delta'] < 0 else 'Increase'
            delta_color = '#c0392b'  if ev['delta'] < 0 else '#2d7a4f'

            cols = st.columns([0.5, 1.5, 1.5, 1.2, 1.2, 1.2, 1.2, 2])
            cols[0].markdown(f"<span style='font-weight:700;color:#764ba2;'>{i+1}</span>", unsafe_allow_html=True)
            cols[1].markdown(f"<span style='color:{sev_color};font-weight:600;'>{SEVERITY_LABEL[ev['severity']]}</span>", unsafe_allow_html=True)
            cols[2].caption(f"{ev['lat']:.4f}°N\n{ev['lon']:.4f}°E")
            cols[3].markdown(f'`{ev["value_before"]:.4f}`')
            cols[4].markdown(f'`{ev["value_after"]:.4f}`')
            cols[5].markdown(f"<span style='color:{delta_color};font-weight:700;'>{ev['delta']:+.4f}</span>", unsafe_allow_html=True)
            cols[6].markdown(direction)
            cols[7].caption(ev['label'])

            if i < len(events) - 1:
                st.markdown('<hr style="margin:2px 0;border-color:#f0f0f5;">', unsafe_allow_html=True)

    # ── Stats comparison ─────────────────────────────────────────────────────

    def _render_stats_comparison(self, first_image, last_image, idx,
                                 first_date, last_date) -> None:
        st.markdown('### Statistical Comparison')

        before_stats = self._stats_calc.run(first_image, self._aoi, idx)
        after_stats  = self._stats_calc.run(last_image,  self._aoi, idx)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'#### Before — {first_date}')
            st.metric('Median',  f"{before_stats.get(f'{idx}_median', 0):.4f}")
            st.metric('Std Dev', f"{before_stats.get(f'{idx}_stdDev', 0):.4f}")
            st.metric('Min',     f"{before_stats.get(f'{idx}_min',    0):.4f}")
            st.metric('Max',     f"{before_stats.get(f'{idx}_max',    0):.4f}")

        with c2:
            st.markdown(f'#### After — {last_date}')
            median_before = before_stats.get(f'{idx}_median', 0)
            median_after  = after_stats.get(f'{idx}_median', 0)
            st.metric('Median',  f"{median_after:.4f}", delta=f'{median_after - median_before:+.4f}')
            st.metric('Std Dev', f"{after_stats.get(f'{idx}_stdDev', 0):.4f}")
            st.metric('Min',     f"{after_stats.get(f'{idx}_min',    0):.4f}")
            st.metric('Max',     f"{after_stats.get(f'{idx}_max',    0):.4f}")

        st.markdown('### Comparative Trends')
        before_vals = [before_stats.get(f'{idx}_{k}', 0) for k in ('median', 'stdDev', 'min', 'max')]
        after_vals  = [after_stats.get(f'{idx}_{k}',  0) for k in ('median', 'stdDev', 'min', 'max')]
        fig = self._charts.before_after_bars(before_vals, after_vals, idx)
        st.plotly_chart(fig, use_container_width=True)

        return before_stats, after_stats

    # ── AI section ───────────────────────────────────────────────────────────

    def _render_ai_section(self, first_image, last_image, idx,
                            before_stats=None, after_stats=None) -> str:
        st.markdown('---')
        st.markdown('### AI Interpretation')

        if before_stats is None:
            before_stats = self._stats_calc.run(first_image, self._aoi, idx)
        if after_stats is None:
            after_stats  = self._stats_calc.run(last_image,  self._aoi, idx)

        with st.spinner('AI is analysing the satellite trends...'):
            text = self._ai.interpret(
                index_name=idx,
                before_mean=before_stats.get(f'{idx}_median', 0),
                after_mean=after_stats.get(f'{idx}_median',  0),
                context=self._config['site_name'],
            )
        st.info(text)
        return text


    # ── Auto-save snapshot ────────────────────────────────────────────────────

    def _auto_save_snapshot(self, idx, threshold, first_date, last_date,
                             before_stats, after_stats, events, ai_text) -> None:
        """Persist the change-detection run to history DB (silent, best-effort)."""
        if not self._history_repo:
            return
        from utils.hash_utils import HashUtils
        history_id = self._history_repo.get_id_by_hash(
            HashUtils.hash_config(self._config)
        )
        if not history_id:
            return  # session not yet saved — skip

        snap_key = f'snap_saved_{history_id}_{idx}_{first_date}_{last_date}'
        if st.session_state.get(snap_key):
            return  # already saved this run

        try:
            self._history_repo.save_snapshot(history_id, {
                'index_name':    idx,
                'first_date':    first_date,
                'last_date':     last_date,
                'threshold':     threshold,
                'before_median': before_stats.get(f'{idx}_median', 0),
                'after_median':  after_stats.get(f'{idx}_median',  0),
                'delta_median':  (after_stats.get(f'{idx}_median', 0)
                                  - before_stats.get(f'{idx}_median', 0)),
                'events':        events,
                'ai_text':       ai_text or '',
            })
            st.session_state[snap_key] = True
        except Exception:
            pass  # never break the UI over a save failure

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_vis_params(self, idx: str) -> dict:
        custom_map = {c['name']: c for c in self._config.get('custom_indices', [])}
        if idx in INDICES_CONFIG:
            idc = INDICES_CONFIG[idx]
            return {'min': idc['min'], 'max': idc['max'], 'palette': idc['palette']}
        if idx in custom_map:
            ci = custom_map[idx]
            return {'min': ci.get('min', -1), 'max': ci.get('max', 1),
                    'palette': ci.get('palette', ['FF0000', 'FFFFFF', '00AA00'])}
        return {'min': -1, 'max': 1, 'palette': ['FF0000', 'FFFFFF', '00AA00']}