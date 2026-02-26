"""
Sidebar UI component for Heritage Site Monitoring System
Extended with custom index builder and category filtering.
"""

import streamlit as st
from datetime import datetime, timedelta
from config.settings import (
    SITE_PRESETS, DEFAULT_CLOUD_COVER, INDICES_CONFIG,
    INDEX_CATEGORIES, SENTINEL2_BANDS, AVAILABLE_PALETTES
)
from utils.db_utils import get_db_connection
import pandas as pd


def render_sidebar():
    with st.sidebar:
        st.header("Analysis Setup")
        st.markdown("---")

        # ---------------------------------------------------------------
        # 1. SITE SELECTION
        # ---------------------------------------------------------------
        st.subheader("🏛️ Site Selection")

        preset_name = st.selectbox(
            "Select Heritage Site",
            list(SITE_PRESETS.keys()),
            help="Choose a preset site or 'Custom Region' to define your own area"
        )

        if preset_name != st.session_state.get('current_preset', None):
            st.session_state.current_preset = preset_name
            if preset_name != 'Custom Region':
                preset = SITE_PRESETS[preset_name]
                st.session_state.site_name    = preset_name
                st.session_state.center_lat   = preset['lat']
                st.session_state.center_lon   = preset['lon']
                st.session_state.buffer_km    = preset['buffer_km']
                st.session_state.site_name_input = preset_name
                st.session_state.lat_input    = preset['lat']
                st.session_state.lon_input    = preset['lon']
            else:
                st.session_state.site_name = "Custom Region"
                st.session_state.site_name_input = "Custom Region"

        if preset_name != 'Custom Region':
            site_name = st.text_input(
                "Site Name (Optional)",
                value=st.session_state.get('site_name', preset_name),
                key='site_name_input'
            )
            st.session_state.site_name = site_name
        else:
            if st.session_state.get('site_name', '') in ('Custom Region (Point)', 'Custom Region (Polygon)'):
                st.success(f"""
                 **Region Selected**
                - Latitude: {st.session_state.center_lat:.4f}°
                - Longitude: {st.session_state.center_lon:.4f}°
                - Radius: {st.session_state.buffer_km} km
                """)
            site_name = st.text_input(
                "Site Name (Optional)",
                value=st.session_state.get('site_name', 'Custom Region'),
                key='site_name_input'
            )
            st.session_state.site_name = site_name

            with st.expander(" Manual Coordinates Entry"):
                col1, col2 = st.columns(2)
                with col1:
                    center_lat = st.number_input("Latitude",  value=st.session_state.center_lat, format="%.4f", key='lat_input')
                with col2:
                    center_lon = st.number_input("Longitude", value=st.session_state.center_lon, format="%.4f", key='lon_input')
                st.session_state.center_lat = center_lat
                st.session_state.center_lon = center_lon

        buffer_km = st.slider(
            "Analysis Radius (km)", 0.5, 10.0,
            st.session_state.buffer_km, 0.5
        )
        st.session_state.buffer_km = buffer_km

        st.markdown("---")

        # ---------------------------------------------------------------
        # 2. TIME PERIOD
        # ---------------------------------------------------------------
        st.subheader("Time Period")

        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=730))
        with col4:
            end_date = st.date_input("End Date", datetime.now())

        cloud_cover = st.slider("Max Cloud Cover (%)", 0, 50, DEFAULT_CLOUD_COVER)

        st.markdown("---")

        # ---------------------------------------------------------------
        # 3. SPECTRAL INDICES — cu filtrare pe categorie
        # ---------------------------------------------------------------
        st.subheader("Spectral Indices")

        # Filtrare pe categorie
        selected_category = st.selectbox(
            "Filter by Category",
            ["All"] + [c for c in INDEX_CATEGORIES if c != 'Custom'],
            help="Filter indices by analysis type"
        )

        # Indici disponibili din config filtrati pe categorie
        if selected_category == "All":
            available_indices = list(INDICES_CONFIG.keys())
        else:
            available_indices = [
                k for k, v in INDICES_CONFIG.items()
                if v.get('category') == selected_category
            ]

        # Arata descrierea fiecarui indice disponibil
        with st.expander("Index Descriptions", expanded=False):
            for idx in available_indices:
                cfg = INDICES_CONFIG[idx]
                st.markdown(f"**{idx}** — {cfg['name']}")
                st.caption(f"{cfg['description']}  \n *{cfg['heritage_use']}*")
                st.markdown("---")

        indices = st.multiselect(
            "Select Indices to Calculate",
            available_indices,
            default=[i for i in ["NDVI", "NDBI"] if i in available_indices],
            help="Choose which spectral indices to calculate and display"
        )

        st.markdown("---")

        # ---------------------------------------------------------------
        # 4. CUSTOM INDEX BUILDER
        # ---------------------------------------------------------------
        st.subheader("Custom Index Builder")

        with st.expander("Build Your Own Index", expanded=False):
            st.markdown("Create a custom spectral index using Sentinel-2 bands.")

            custom_name = st.text_input(
                "Index Name",
                value="CUSTOM1",
                max_chars=20,
                help="Short name, no spaces (e.g. MY_IDX)"
            ).upper().replace(' ', '_')

            formula_type = st.selectbox(
                "Formula Type",
                [
                    "Normalized Difference: (A-B)/(A+B)",
                    "Ratio: A/B",
                    "Difference: A-B",
                    "Custom Expression"
                ],
                help="Choose the mathematical formula"
            )

            band_options = list(SENTINEL2_BANDS.keys())
            band_labels  = {b: SENTINEL2_BANDS[b]['name'] for b in band_options}

            custom_index_def = None

            if formula_type != "Custom Expression":
                col_a, col_b = st.columns(2)
                with col_a:
                    band_a = st.selectbox(
                        "Band A (numerator)" if "Normalized" in formula_type else "Band A",
                        band_options,
                        format_func=lambda x: band_labels[x],
                        index=band_options.index('B8')
                    )
                with col_b:
                    band_b = st.selectbox(
                        "Band B (denominator)" if "Normalized" in formula_type else "Band B",
                        band_options,
                        format_func=lambda x: band_labels[x],
                        index=band_options.index('B4')
                    )

                formula_map = {
                    "Normalized Difference: (A-B)/(A+B)": "normalized_diff",
                    "Ratio: A/B": "ratio",
                    "Difference: A-B": "difference"
                }

                # Preview formula
                if "Normalized" in formula_type:
                    st.info(f"**Preview:** `({band_a} - {band_b}) / ({band_a} + {band_b})`")
                elif "Ratio" in formula_type:
                    st.info(f"**Preview:** `{band_a} / {band_b}`")
                else:
                    st.info(f"**Preview:** `{band_a} - {band_b}`")

                custom_index_def = {
                    'name': custom_name,
                    'formula': formula_map[formula_type],
                    'band_a': band_a,
                    'band_b': band_b,
                }

            else:
                st.markdown("Write an Earth Engine expression using band variables:")
                st.code("Example: (NIR - RED) / (NIR + RED + 0.5) * 1.5", language="text")

                expr = st.text_area(
                    "Expression",
                    value="(NIR - RED) / (NIR + RED)",
                    height=80,
                    help="Use variable names you define below"
                )

                st.markdown("**Map variable names to bands:**")
                num_vars = st.number_input("Number of variables", 1, 6, 2)
                expr_map = {}
                for i in range(int(num_vars)):
                    c1, c2 = st.columns(2)
                    with c1:
                        var_name = st.text_input(f"Variable {i+1} name", value=["NIR","RED","GREEN","SWIR1","SWIR2","BLUE"][i] if i < 6 else f"VAR{i+1}", key=f"var_name_{i}")
                    with c2:
                        var_band = st.selectbox(f"→ Band", band_options, format_func=lambda x: band_labels[x], index=min(i, len(band_options)-1), key=f"var_band_{i}")
                    expr_map[var_name] = var_band

                custom_index_def = {
                    'name': custom_name,
                    'formula': 'expression',
                    'expression': expr,
                    'expression_bands': expr_map,
                }

            # Vizualizare pentru indicele custom
            st.markdown("**Visualization:**")
            col_pal, col_min, col_max = st.columns(3)
            with col_pal:
                palette_name = st.selectbox("Palette", list(AVAILABLE_PALETTES.keys()), key="custom_palette")
            with col_min:
                custom_min = st.number_input("Min", value=-1.0, step=0.1, key="custom_min")
            with col_max:
                custom_max = st.number_input("Max", value=1.0,  step=0.1, key="custom_max")

            if custom_index_def:
                custom_index_def['palette'] = AVAILABLE_PALETTES[palette_name]
                custom_index_def['min'] = custom_min
                custom_index_def['max'] = custom_max
                custom_index_def['category'] = 'Custom'
                custom_index_def['description'] = f"Custom index: {formula_type}"
                custom_index_def['heritage_use'] = "User-defined analysis"

            # Buton pentru a adauga indicele custom la lista
            if st.button("Add Custom Index to Analysis", use_container_width=True):
                if custom_name and custom_index_def:
                    # Salveaza in session state
                    if 'custom_indices' not in st.session_state:
                        st.session_state.custom_indices = []
                    # Evita duplicate
                    st.session_state.custom_indices = [
                        c for c in st.session_state.custom_indices
                        if c['name'] != custom_name
                    ]
                    st.session_state.custom_indices.append(custom_index_def)
                    indices.append(custom_name)
                    st.success(f"{custom_name} added!")

            # Afiseaza indicii custom salvati
            if st.session_state.get('custom_indices'):
                st.markdown("**Active custom indices:**")
                for ci in st.session_state.custom_indices:
                    col_ci, col_rm = st.columns([3, 1])
                    with col_ci:
                        st.caption(f"🔹 **{ci['name']}** — {ci.get('formula','')}")
                    with col_rm:
                        if st.button("✕", key=f"rm_{ci['name']}", help=f"Remove {ci['name']}"):
                            st.session_state.custom_indices = [
                                c for c in st.session_state.custom_indices
                                if c['name'] != ci['name']
                            ]
                            st.rerun()

        st.markdown("---")

        # ---------------------------------------------------------------
        # 5. ADVANCED OPTIONS
        # ---------------------------------------------------------------
        with st.expander("Advanced Options"):
            change_threshold = st.slider("Change Detection Threshold", 0.1, 1.0, 0.2, 0.05)
            sample_size = st.slider("Time Series Sample Size", 5, 50, 20, 5)

        st.markdown("---")

        run_analysis = st.button(
            "Run Analysis",
            type="primary",
            use_container_width=True
        )

        if run_analysis and preset_name == 'Custom Region':
            if st.session_state.get('site_name') == 'Custom Region':
                st.warning("Please select a region on the map first!")
                run_analysis = False

    # Combina indicii predefiniti cu cei custom pentru a-i trimite inapoi in app
    all_indices = list(indices)
    custom_indices = st.session_state.get('custom_indices', [])
    for ci in custom_indices:
        if ci['name'] not in all_indices:
            all_indices.append(ci['name'])

    return {
        'analysis_type': "Comprehensive Analysis",
        'site_name':     st.session_state.site_name,
        'center_lat':    st.session_state.center_lat,
        'center_lon':    st.session_state.center_lon,
        'buffer_km':     buffer_km,
        'start_date':    start_date,
        'end_date':      end_date,
        'cloud_cover':   cloud_cover,
        'indices':       all_indices,
        'custom_indices': custom_indices,
        'run_analysis':  run_analysis,
        'change_threshold': change_threshold,
        'sample_size':   sample_size,
    }


def render_history_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.subheader("History")
    try:
        conn = get_db_connection()
        query = """
            SELECT site_name as 'Sit',
                   DATE_FORMAT(analysis_date, '%d-%m %H:%i') as 'Data'
            FROM sites_history
            ORDER BY analysis_date DESC
            LIMIT 5
        """
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            st.sidebar.table(df)
        else:
            st.sidebar.info("No previous analyses found.")
    except Exception as e:
        st.sidebar.error(f"DB error: {e}")