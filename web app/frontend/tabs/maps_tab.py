"""
Responsible for: rendering the Interactive Maps tab (Median / Browse / Timelapse GIF).
"""

import streamlit as st
import folium
import ee
from datetime import datetime

from config.indices_config import INDICES_CONFIG
from config.settings import GEE_MAX_PIXELS
from frontend.components.map_widget import MapWidget
from frontend.components.legend_widget import LegendWidget
from backend.gee.index_calculator import IndexCalculator
from backend.gee.gif_generator import GifGenerator
from backend.gee.statistics_calculator import StatisticsCalculator
from utils.date_utils import DateUtils

try:
    from streamlit_folium import st_folium
    _HAS_ST_FOLIUM = True
except ImportError:
    _HAS_ST_FOLIUM = False


class MapsTab:
    """
    Renders the Interactive Maps tab with three view modes:
      - Median  : median composite with layer selector
      - Browse  : slide through individual images
      - Timelapse GIF : animated GIF via GEE

    Usage:
        tab = MapsTab(results)
        tab.render()
    """

    VIEW_MODES = ['Median', 'Browse', 'Timelapse GIF']

    def __init__(self, results: dict):
        self._config     = results['config']
        self._collection = results['collection']
        self._aoi        = results['aoi']
        self._count      = results['count']
        self._calc       = IndexCalculator()
        self._stats_calc = StatisticsCalculator()
        self._gif_gen    = GifGenerator()
        self._widget     = MapWidget(self._config['center_lat'], self._config['center_lon'])

    def render(self) -> None:
        st.subheader(f"Interactive Maps — {self._config['site_name']}")

        if self._count == 0:
            st.warning('No images found. Try adjusting cloud cover or dates.')
            return

        selected_view = self._render_layer_selector()
        view_mode     = self._render_mode_buttons()
        st.markdown('---')

        if view_mode == 'Median':
            self._render_median(selected_view)
        elif view_mode == 'Browse':
            self._render_browse(selected_view)
        elif view_mode == 'Timelapse GIF':
            self._render_timelapse(selected_view)

        if view_mode != 'Timelapse GIF':
            LegendWidget(self._config).render()

    # ── Layer selector ───────────────────────────────────────────────────────

    def _render_layer_selector(self) -> str:
        available = ['Natural Color (RGB)'] + [
            i for i in self._config['indices']
            if i in INDICES_CONFIG or
            i in {c['name'] for c in self._config.get('custom_indices', [])}
        ]
        col_layer, col_meta = st.columns([4, 1])
        with col_layer:
            selected = st.selectbox('Layer to visualize', available, key='maps_selected_layer')
        with col_meta:
            st.metric('Images', self._count)
        return selected

    # ── Mode buttons ─────────────────────────────────────────────────────────

    def _render_mode_buttons(self) -> str:
        if 'maps_view_mode' not in st.session_state:
            st.session_state.maps_view_mode = 'Median'

        st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
            position: relative !important;
            opacity: 0 !important;
            height: 50px !important;
            margin-top: -54px !important;
            width: 100% !important;
            cursor: pointer !important;
            z-index: 10 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        btn_cols = st.columns(len(self.VIEW_MODES))
        for col, key in zip(btn_cols, self.VIEW_MODES):
            is_active = st.session_state.maps_view_mode == key
            bg     = 'linear-gradient(135deg,#4a2d6b,#764ba2)' if is_active else 'transparent'
            color  = 'white' if is_active else '#764ba2'
            weight = '700'   if is_active else '500'
            with col:
                st.markdown(f"""
                <div style="text-align:center;padding:10px 6px;background:{bg};
                            border:1.5px solid #764ba2;border-radius:8px;
                            font-size:13px;font-weight:{weight};color:{color};
                            margin-bottom:4px;min-height:50px;
                            display:flex;align-items:center;justify-content:center;">
                    {key}
                </div>""", unsafe_allow_html=True)
                if st.button(key, key=f'viewbtn_{key}', use_container_width=True):
                    st.session_state.maps_view_mode = key
                    st.rerun()

        return st.session_state.maps_view_mode

    # ── Median view ──────────────────────────────────────────────────────────

    def _render_median(self, selected_view: str) -> None:
        extra  = self._config.get('custom_indices', [])
        median = self._collection.median()
        m      = self._widget.create_base_map()

        if selected_view == 'Natural Color (RGB)':
            self._widget.add_ee_layer(
                m, median,
                {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4},
                'RGB Median',
            )
        else:
            img_idx = self._calc.compute(median, extra_indices=extra)
            self._add_index_layer(m, img_idx, selected_view, visible=True)

        self._widget.add_aoi_border(m, self._aoi)
        self._widget.add_draw_control(m)
        m.centerObject(self._aoi, 14)
        out = self._widget.render(m)
        if out and 'all_drawings' in out:
            st.session_state.latest_drawings = out['all_drawings']

    # ── Browse view ──────────────────────────────────────────────────────────

    def _render_browse(self, selected_view: str) -> None:
        extra      = self._config.get('custom_indices', [])
        cache_key  = f'img_dates_{id(self._collection)}'

        if cache_key not in st.session_state:
            with st.spinner('Loading image timeline...'):
                timestamps = self._collection.aggregate_array('system:time_start').getInfo()
                st.session_state[cache_key] = DateUtils.timestamps_to_date_list(timestamps)

        image_dates = st.session_state[cache_key]
        total       = len(image_dates)

        if 'browse_idx' not in st.session_state:
            st.session_state.browse_idx = 0
        st.session_state.browse_idx %= total

        st.session_state.browse_idx = st.select_slider(
            'Timeline',
            options=range(total),
            value=st.session_state.browse_idx,
            format_func=lambda x: image_dates[x][1],
            key='browse_slider',
        )

        cp, _, cn = st.columns([1, 8, 1])
        with cp:
            if st.button('◀', use_container_width=True,
                         disabled=st.session_state.browse_idx == 0):
                st.session_state.browse_idx -= 1
                st.rerun()
        with cn:
            if st.button('▶', use_container_width=True,
                         disabled=st.session_state.browse_idx == total - 1):
                st.session_state.browse_idx += 1
                st.rerun()

        cur_ts, cur_date_str, cur_dt = image_dates[st.session_state.browse_idx]
        image = ee.Image(
            self._collection
            .filterDate(cur_dt.strftime('%Y-%m-%d'), cur_dt.strftime('%Y-%m-%d') + 'T23:59:59')
            .first()
        )
        m = self._widget.create_base_map()

        if selected_view == 'Natural Color (RGB)':
            self._widget.add_ee_layer(
                m, image,
                {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4},
                f'RGB {cur_date_str}',
            )
        else:
            img_idx = self._calc.compute(image, extra_indices=extra)
            self._add_index_layer(m, img_idx, selected_view, visible=True)

        self._widget.add_aoi_border(m, self._aoi)
        self._widget.add_date_overlay(m, cur_date_str, st.session_state.browse_idx + 1, total)
        m.centerObject(self._aoi, 14)
        self._widget.render(m, key=f'browse_{st.session_state.browse_idx}_{selected_view}')

        # Per-date stats below the map
        if selected_view != 'Natural Color (RGB)':
            img_idx2 = self._calc.compute(image, extra_indices=extra)
            self._render_browse_stats(img_idx2, cur_date_str)

    def _render_browse_stats(self, image: ee.Image, date_str: str) -> None:
        indices = [
            i for i in self._config['indices']
            if i in INDICES_CONFIG or
            i in {c['name'] for c in self._config.get('custom_indices', [])}
        ]
        if not indices:
            return
        st.markdown(f'**Index values — {date_str}**')
        cols = st.columns(min(len(indices), 5))
        for i, idx in enumerate(indices):
            with cols[i % len(cols)]:
                stats = self._stats_calc.run(image, self._aoi, idx)
                val   = stats.get(f'{idx}_median')
                st.metric(idx, f'{val:.4f}' if val is not None else 'N/A')

    # ── Timelapse GIF ────────────────────────────────────────────────────────

    def _render_timelapse(self, selected_view: str) -> None:
        st.markdown('### Timelapse GIF')

        col_fps, col_res, col_btn = st.columns([2, 2, 2])
        with col_fps:
            fps = st.slider('Frames per second', 1, 8, 2)
        with col_res:
            dimensions = st.select_slider('Resolution', [400, 512, 600, 768, 900], value=600)
        with col_btn:
            st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
            generate = st.button('▶ Generate Timelapse', type='primary', use_container_width=True)

        gif_key         = f'gif_{selected_view}_{fps}_{dimensions}_{id(self._collection)}'
        date_range_days = max(1, (self._config['end_date'] - self._config['start_date']).days)
        max_frames      = max(1, GEE_MAX_PIXELS // (dimensions * dimensions))

        if self._count > max_frames:
            st.warning(
                f' {self._count} images exceed the GEE limit for {dimensions}px '
                f'({max_frames} max frames). Auto-sampling will be applied.'
            )
        else:
            st.info(f'✓ All {self._count} images fit within the GEE pixel limit at {dimensions}px.')

        if generate:
            vis_params = self._get_vis_params(selected_view)
            with st.spinner('GEE is rendering frames… (may take 15–60s)'):
                try:
                    url, n_frames, was_sampled = self._gif_gen.build_url(
                        self._collection, self._aoi, selected_view, vis_params,
                        fps=fps, dimensions=dimensions, date_range_days=date_range_days,
                    )
                    st.session_state[gif_key] = (url, n_frames, was_sampled)
                    label = f'✓ {n_frames} frames (sampled from {self._count}).' if was_sampled \
                            else f'✓ Timelapse generated — {n_frames} frames.'
                    st.success(label)
                except Exception as e:
                    st.error(f'GEE error: {e}')

        if gif_key in st.session_state:
            url, n_frames, was_sampled = st.session_state[gif_key]
            note = f' (sampled from {self._count})' if was_sampled else ''
            st.markdown(f"""
            <div style="border-radius:12px;overflow:hidden;
                        border:2px solid #764ba2;box-shadow:0 4px 20px rgba(118,75,162,0.3);">
                <img src="{url}" style="width:100%;display:block;" alt="Timelapse"/>
                <div style="position:absolute;top:10px;left:10px;
                            background:rgba(26,26,46,0.85);color:#f0c040;
                            font-family:monospace;font-size:13px;font-weight:700;
                            padding:5px 10px;border-radius:5px;border:1px solid #764ba2;">
                    {selected_view} · {n_frames} frames{note} · {fps} fps
                </div>
            </div>
            <div style="margin-top:8px;">
                <a href="{url}" download="timelapse.gif" target="_blank">
                    <button style="background:linear-gradient(135deg,#4a2d6b,#764ba2);
                                   color:white;border:none;padding:9px 20px;
                                   border-radius:8px;cursor:pointer;font-size:14px;font-weight:600;">
                        ⬇ Download GIF
                    </button>
                </a>
            </div>
            """, unsafe_allow_html=True)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _add_index_layer(
        self, m, image: ee.Image, idx: str, visible: bool = True
    ) -> None:
        custom_map = {c['name']: c for c in self._config.get('custom_indices', [])}
        if idx in INDICES_CONFIG:
            idc = INDICES_CONFIG[idx]
            self._widget.add_ee_layer(
                m, image.select(idx),
                {'min': idc['min'], 'max': idc['max'], 'palette': idc['palette']},
                idx, visible,
            )
        elif idx in custom_map:
            ci = custom_map[idx]
            self._widget.add_ee_layer(
                m, image.select(idx),
                {'min': ci.get('min', -1), 'max': ci.get('max', 1),
                 'palette': ci.get('palette', ['FFFFFF', '0000FF'])},
                f'{idx} (custom)', visible,
            )

    def _get_vis_params(self, selected_view: str) -> dict:
        if selected_view == 'Natural Color (RGB)':
            return {}
        custom_map = {c['name']: c for c in self._config.get('custom_indices', [])}
        if selected_view in INDICES_CONFIG:
            idc = INDICES_CONFIG[selected_view]
            return {'min': idc['min'], 'max': idc['max'], 'palette': idc['palette']}
        if selected_view in custom_map:
            ci = custom_map[selected_view]
            return {'min': ci.get('min', -1), 'max': ci.get('max', 1),
                    'palette': ci.get('palette', ['FFFFFF', '0000FF'])}
        return {}