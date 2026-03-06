"""
Responsible for: rendering the sidebar and returning the analysis config dict.
"""

import streamlit as st
from datetime import datetime, timedelta

from config.settings import (
    DEFAULT_CLOUD_COVER, INDEX_CATEGORIES, AVAILABLE_PALETTES
)
from config.site_presets import SITE_PRESETS
from config.indices_config import INDICES_CONFIG, SENTINEL2_BANDS
from frontend.components.index_description import IndexDescription


class Sidebar:
    """
    Renders the full left sidebar and returns a config dict consumed by
    the rest of the app.

    Usage:
        sidebar = Sidebar()
        config = sidebar.render()   # call once per Streamlit rerun
    """

    def render(self) -> dict:
        with st.sidebar:
            st.header('Analysis Setup')
            st.markdown('---')

            self._render_site_section()
            st.markdown('---')
            start_date, end_date, cloud_cover = self._render_time_section()
            st.markdown('---')
            indices = self._render_indices_section()
            st.markdown('---')
            indices = self._render_custom_index_section(indices)
            st.markdown('---')
            change_threshold, sample_size = self._render_advanced_section()
            st.markdown('---')
            run_analysis = self._render_run_button()

        # Merge custom index names into indices list
        all_indices = list(indices)
        for ci in st.session_state.get('custom_indices', []):
            if ci['name'] not in all_indices:
                all_indices.append(ci['name'])

        return {
            'site_name':        st.session_state.site_name,
            'center_lat':       st.session_state.center_lat,
            'center_lon':       st.session_state.center_lon,
            'buffer_km':        st.session_state.buffer_km,
            'start_date':       start_date,
            'end_date':         end_date,
            'cloud_cover':      cloud_cover,
            'indices':          all_indices,
            'custom_indices':   st.session_state.get('custom_indices', []),
            'run_analysis':     run_analysis,
            'change_threshold': change_threshold,
            'sample_size':      sample_size,
        }

    # ── Section renderers (each renders one logical block) ──────────────────

    def _render_site_section(self) -> None:
        st.subheader('Site Selection')

        preset_name = st.selectbox(
            'Select Heritage Site',
            list(SITE_PRESETS.keys()),
        )

        # Update session state when preset changes
        if preset_name != st.session_state.get('current_preset'):
            st.session_state.current_preset = preset_name
            if preset_name != 'Custom Region':
                p = SITE_PRESETS[preset_name]
                st.session_state.site_name  = preset_name
                st.session_state.center_lat = p['lat']
                st.session_state.center_lon = p['lon']
                st.session_state.buffer_km  = p['buffer_km']
            else:
                st.session_state.site_name = 'Custom Region'

        if preset_name != 'Custom Region':
            site_name = st.text_input(
                'Site Name (Optional)',
                value=st.session_state.get('site_name', preset_name),
                key='site_name_input',
            )
            st.session_state.site_name = site_name
        else:
            if st.session_state.get('site_name', '') in (
                'Custom Region (Point)', 'Custom Region (Polygon)'
            ):
                st.success(f"""
                 **Region Selected**
                - Lat: {st.session_state.center_lat:.4f}°
                - Lon: {st.session_state.center_lon:.4f}°
                - Radius: {st.session_state.buffer_km} km
                """)

            site_name = st.text_input(
                'Site Name (Optional)',
                value=st.session_state.get('site_name', 'Custom Region'),
                key='site_name_input',
            )
            st.session_state.site_name = site_name

            with st.expander(' Manual Coordinates Entry'):
                col1, col2 = st.columns(2)
                with col1:
                    lat = st.number_input('Latitude', value=st.session_state.center_lat,
                                         format='%.4f', key='lat_input')
                with col2:
                    lon = st.number_input('Longitude', value=st.session_state.center_lon,
                                         format='%.4f', key='lon_input')
                st.session_state.center_lat = lat
                st.session_state.center_lon = lon

        buffer_km = st.slider(
            'Analysis Radius (km)', 0.5, 10.0,
            st.session_state.buffer_km, 0.5,
        )
        st.session_state.buffer_km = buffer_km

    def _render_time_section(self) -> tuple:
        st.subheader('Time Period')
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input('Start Date', datetime.now() - timedelta(days=730))
        with col2:
            end_date = st.date_input('End Date', datetime.now())
        cloud_cover = st.slider('Max Cloud Cover (%)', 0, 50, DEFAULT_CLOUD_COVER)
        return start_date, end_date, cloud_cover

    def _render_indices_section(self) -> list[str]:
        st.subheader('Spectral Indices')

        selected_category = st.selectbox(
            'Filter by Category',
            ['All'] + [c for c in INDEX_CATEGORIES if c != 'Custom'],
        )

        if selected_category == 'All':
            available = list(INDICES_CONFIG.keys())
        else:
            available = [
                k for k, v in INDICES_CONFIG.items()
                if v.get('category') == selected_category
            ]

        IndexDescription(available).render()

        indices = st.multiselect(
            'Select Indices to Calculate',
            available,
            default=[i for i in ['NDVI', 'NDBI'] if i in available],
        )
        return indices

    def _render_custom_index_section(self, indices: list[str]) -> list[str]:
        st.subheader('Custom Index Builder')

        with st.expander('Build Your Own Index', expanded=False):
            custom_name = st.text_input(
                'Index Name', value='CUSTOM1', max_chars=20,
            ).upper().replace(' ', '_')

            formula_type = st.selectbox('Formula Type', [
                'Normalized Difference: (A-B)/(A+B)',
                'Ratio: A/B',
                'Difference: A-B',
                'Custom Expression',
            ])

            band_options = list(SENTINEL2_BANDS.keys())
            band_labels  = {b: SENTINEL2_BANDS[b]['name'] for b in band_options}
            custom_def   = None

            if formula_type != 'Custom Expression':
                c1, c2 = st.columns(2)
                with c1:
                    band_a = st.selectbox('Band A', band_options,
                                          format_func=lambda x: band_labels[x],
                                          index=band_options.index('B8'))
                with c2:
                    band_b = st.selectbox('Band B', band_options,
                                          format_func=lambda x: band_labels[x],
                                          index=band_options.index('B4'))

                formula_map = {
                    'Normalized Difference: (A-B)/(A+B)': 'normalized_diff',
                    'Ratio: A/B':                         'ratio',
                    'Difference: A-B':                    'difference',
                }
                custom_def = {
                    'name':    custom_name,
                    'formula': formula_map[formula_type],
                    'band_a':  band_a,
                    'band_b':  band_b,
                }
            else:
                expr = st.text_area('Expression', value='(NIR - RED) / (NIR + RED)', height=80)
                num_vars = st.number_input('Number of variables', 1, 6, 2)
                expr_map = {}
                defaults = ['NIR', 'RED', 'GREEN', 'SWIR1', 'SWIR2', 'BLUE']
                for i in range(int(num_vars)):
                    c1, c2 = st.columns(2)
                    with c1:
                        vname = st.text_input(f'Variable {i+1}',
                                              value=defaults[i] if i < 6 else f'VAR{i}',
                                              key=f'var_name_{i}')
                    with c2:
                        vband = st.selectbox('→ Band', band_options,
                                             format_func=lambda x: band_labels[x],
                                             index=min(i, len(band_options)-1),
                                             key=f'var_band_{i}')
                    expr_map[vname] = vband

                custom_def = {
                    'name':             custom_name,
                    'formula':          'expression',
                    'expression':       expr,
                    'expression_bands': expr_map,
                }

            # Palette / min / max
            cp, cmin, cmax = st.columns(3)
            with cp:
                pal_name = st.selectbox('Palette', list(AVAILABLE_PALETTES.keys()),
                                        key='custom_palette')
            with cmin:
                c_min = st.number_input('Min', value=-1.0, step=0.1, key='custom_min')
            with cmax:
                c_max = st.number_input('Max', value=1.0, step=0.1, key='custom_max')

            if custom_def:
                custom_def.update({
                    'palette':      AVAILABLE_PALETTES[pal_name],
                    'min':          c_min,
                    'max':          c_max,
                    'category':     'Custom',
                    'description':  f'Custom index: {formula_type}',
                    'heritage_use': 'User-defined analysis',
                })

            if st.button('Add Custom Index to Analysis', use_container_width=True):
                if custom_name and custom_def:
                    if 'custom_indices' not in st.session_state:
                        st.session_state.custom_indices = []
                    st.session_state.custom_indices = [
                        c for c in st.session_state.custom_indices
                        if c['name'] != custom_name
                    ]
                    st.session_state.custom_indices.append(custom_def)
                    indices.append(custom_name)
                    st.success(f' {custom_name} added!')

            # List active custom indices with remove buttons
            if st.session_state.get('custom_indices'):
                st.markdown('**Active custom indices:**')
                for ci in st.session_state.custom_indices:
                    col_name, col_rm = st.columns([3, 1])
                    with col_name:
                        st.caption(f"**{ci['name']}** — {ci.get('formula', '')}")
                    with col_rm:
                        if st.button('✕', key=f"rm_{ci['name']}"):
                            st.session_state.custom_indices = [
                                c for c in st.session_state.custom_indices
                                if c['name'] != ci['name']
                            ]
                            st.rerun()

        return indices

    def _render_advanced_section(self) -> tuple[float, int]:
        with st.expander('Advanced Options'):
            threshold    = st.slider('Change Detection Threshold', 0.1, 1.0, 0.2, 0.05)
            sample_size  = st.slider('Time Series Sample Size', 5, 50, 20, 5)
        return threshold, sample_size

    def _render_run_button(self) -> bool:
        run = st.button('Run Analysis', type='primary', use_container_width=True)
        if run and st.session_state.get('site_name') == 'Custom Region':
            st.warning('Please select a region on the map first!')
            return False
        return run