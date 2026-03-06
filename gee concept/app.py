"""
Heritage Site Monitoring System - Main Application
"""

import streamlit as st
import ee
from datetime import datetime, timedelta, date

from config.settings import PAGE_CONFIG, THEME_CSS
from utils.gee_utils import HeritageMonitor
from ui.sidebar import render_sidebar
from ui.tabs.maps_tab import render_maps_tab, render_custom_region_map
from ui.tabs.temporal_tab import render_temporal_tab
from ui.tabs.change_tab import render_change_tab
from ui.tabs.report_tab import render_report_tab
from utils.db_utils import (
    get_analysis_from_db, save_analysis_to_db
)

st.set_page_config(**PAGE_CONFIG)
st.markdown(THEME_CSS, unsafe_allow_html=True)


def initialize_session_state():
    defaults = {
        'selected_region': None,
        'site_name': "Alba Iulia Fortress",
        'center_lat': 46.0686,
        'center_lon': 23.5714,
        'buffer_km': 2.0,
        'analysis_results': None,
        'active_tab': 0,
        'change_index': None,
        'change_threshold': 0.20,
        'custom_indices': [],
        'restore_from_history': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


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

    if config['site_name'].startswith('Custom Region'):
        render_custom_region_map(config)

    if config['site_name'] != 'Custom Region':
        center_point = ee.Geometry.Point([config['center_lon'], config['center_lat']])
        aoi = center_point.buffer(config['buffer_km'] * 1000)

        if config['run_analysis']:
            with st.spinner("Connecting to satellite archive..."):
                collection = monitor.get_sentinel2_collection(
                    aoi,
                    config['start_date'].strftime('%Y-%m-%d'),
                    config['end_date'].strftime('%Y-%m-%d'),
                    config['cloud_cover']
                )
                count = collection.size().getInfo()

            cached_stats = get_analysis_from_db(config) if count > 0 else None

            if cached_stats:
                st.session_state.analysis_results = {
                    'collection':    collection,
                    'count':         count,
                    'stats':         cached_stats,
                    'is_from_cache': True,
                    'config':        config,
                    'monitor':       monitor,
                    'aoi':           aoi,
                }
            elif count > 0:
                with st.spinner("Calculating spectral indices..."):
                    median_image       = collection.median()
                    image_with_indices = monitor.calculate_indices(
                        median_image,
                        extra_indices=config.get('custom_indices', [])
                    )
                    results_to_save = {}
                    for idx in config['indices']:
                        stats = monitor.calculate_statistics(image_with_indices, aoi, idx)
                        results_to_save[idx] = stats

                    config['image_count'] = count
                    save_analysis_to_db(config, results_to_save)

                    st.session_state.analysis_results = {
                        'collection':    collection,
                        'count':         count,
                        'stats':         results_to_save,
                        'is_from_cache': False,
                        'config':        config,
                        'monitor':       monitor,
                        'aoi':           aoi,
                    }
            else:
                st.warning("No satellite images found for the selected period.")

    if st.session_state.analysis_results:
        results = st.session_state.analysis_results

        fresh_custom = st.session_state.get("custom_indices", [])
        if fresh_custom:
            results["config"]["custom_indices"] = fresh_custom

        if results.get('is_restored'):
            cfg = results['config']
            st.info(
                f" Restored: **{cfg['site_name']}** · "
                f"{cfg['start_date']} → {cfg['end_date']} · "
                f"{results['count']} images · "
                f"Indices: {', '.join(cfg['indices'])}"
            )

        TAB_NAMES = [
            "Interactive Maps",
            "Temporal Analysis",
            "Change Detection",
            "Report"
        ]

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
    st.markdown("<div class='footer-text'>Powered by Google Earth Engine &nbsp;|&nbsp; Sentinel-2 Data &nbsp;|&nbsp; Streamlit</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()