"""
Heritage Site Monitoring System - Main Application
"""

import streamlit as st
import ee
from datetime import datetime, timedelta

from config.settings import PAGE_CONFIG, CUSTOM_CSS
from utils.gee_utils import HeritageMonitor
from ui.sidebar import render_sidebar, render_history_sidebar
from ui.tabs.maps_tab import render_maps_tab, render_custom_region_map
from ui.tabs.temporal_tab import render_temporal_tab
from ui.tabs.change_tab import render_change_tab
from ui.tabs.report_tab import render_report_tab
from utils.db_utils import get_analysis_from_db, save_analysis_to_db

st.set_page_config(**PAGE_CONFIG)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def initialize_session_state():
    if 'selected_region' not in st.session_state:
        st.session_state.selected_region = None
    if 'site_name' not in st.session_state:
        st.session_state.site_name = "Alba Iulia Fortress"
    if 'center_lat' not in st.session_state:
        st.session_state.center_lat = 46.0686
    if 'center_lon' not in st.session_state:
        st.session_state.center_lon = 23.5714
    if 'buffer_km' not in st.session_state:
        st.session_state.buffer_km = 2.0
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0
    if 'change_index' not in st.session_state:
        st.session_state.change_index = None
    if 'change_threshold' not in st.session_state:
        st.session_state.change_threshold = 0.20


def main():
    initialize_session_state()

    st.markdown(
        '<h1 class="main-header">Heritage Site Monitoring System</h1>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    try:
        monitor = HeritageMonitor()
    except Exception as e:
        st.error(f"Error initializing Google Earth Engine: {str(e)}")
        st.info("Please ensure you are authenticated with Earth Engine.")
        st.stop()

    config = render_sidebar()
    render_history_sidebar()

    if config['site_name'].startswith('Custom Region'):
        render_custom_region_map(config)

    if config['site_name'] != 'Custom Region':
        center_point = ee.Geometry.Point([config['center_lon'], config['center_lat']])
        aoi = center_point.buffer(config['buffer_km'] * 1000)

        if config['run_analysis']:
            cached_stats = get_analysis_from_db(config)

            with st.spinner("Checking for cached data..."):
                collection = monitor.get_sentinel2_collection(
                    aoi,
                    config['start_date'].strftime('%Y-%m-%d'),
                    config['end_date'].strftime('%Y-%m-%d'),
                    config['cloud_cover']
                )
                count = collection.size().getInfo()

            if cached_stats:
                st.session_state.analysis_results = {
                    'collection': collection,
                    'count': count,
                    'stats': cached_stats,
                    'is_from_cache': True,
                    'config': config,
                    'monitor': monitor,
                    'aoi': aoi
                }
            else:
                if count > 0:
                    with st.spinner("Gathering data and calculating statistics..."):
                        median_image = collection.median()
                        image_with_indices = monitor.calculate_indices(median_image, extra_indices = config.get('custom_indices', []))

                        results_to_save = {}
                        for idx in config['indices']:
                            stats = monitor.calculate_statistics(image_with_indices, aoi, idx)
                            results_to_save[idx] = stats

                        save_analysis_to_db(config, results_to_save)

                        st.session_state.analysis_results = {
                            'collection': collection,
                            'count': count,
                            'stats': results_to_save,
                            'is_from_cache': False,
                            'config': config,
                            'monitor': monitor,
                            'aoi': aoi
                        }
                else:
                    st.warning("No images were found for the selected time period.")

    if st.session_state.analysis_results:
        results = st.session_state.analysis_results


        TAB_NAMES = [
            " Interactive Maps",
            " Temporal Analysis",
            " Change Detection",
            " Report"
        ]

        st.markdown("""
        <style>
        div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            gap: 4px;
            border-bottom: 2px solid black;
            padding-bottom: 0;
            margin-bottom: 20px;
        }
        div[role="radiogroup"] label {
            padding: 8px 20px;
            border-radius: 6px 6px 0 0;
            border: 1px solid #764ba2;
            border-bottom: none;
            cursor: pointer;
            font-weight: 500;
            background: #f8f9fa;
            foreground: black;
            color: #555;
            transition: all 0.15s;
            margin-bottom: -2px;
        }
        div[role="radiogroup"] label:has(input:checked) {
            background: #764ba2;
            foreground: black;
            color: #1f77b4;
            border-color: #764ba2;
            border-bottom: #1f77b4;
            font-weight: 600;
        }
        div[role="radiogroup"] input {
            display: none;
            color: #bdbd3a
        }
        </style>
        """, unsafe_allow_html=True)

        selected_tab = st.radio(
            label="tabs",
            options=TAB_NAMES,
            index=st.session_state.active_tab,
            horizontal=True,
            label_visibility="collapsed",
            key="tab_selector"
        )

        st.session_state.active_tab = TAB_NAMES.index(selected_tab)

        if selected_tab == TAB_NAMES[0]:
            render_maps_tab(results)
        elif selected_tab == TAB_NAMES[1]:
            render_temporal_tab(results)
        elif selected_tab == TAB_NAMES[2]:
            render_change_tab(results)
        elif selected_tab == TAB_NAMES[3]:
            render_report_tab(results)

    else:
        st.info("Configure parameters in the sidebar and click 'Run Analysis' to begin.")

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #7f8c8d;'>
        <p>Powered by Google Earth Engine | Sentinel-2 Data | Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()