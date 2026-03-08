"""
Heritage Site Monitoring System — Entry Point

Responsibilities:
  - Configure Streamlit page
  - Initialise GEE once
  - Initialise DB connection once
  - Render sidebar → get config
  - Orchestrate the analysis pipeline
  - Pass results to the correct tab

No business logic lives here. Every action is delegated to a dedicated class.
"""

import streamlit as st
import ee
from datetime import datetime

from config.settings import PAGE_CONFIG
from utils.hash_utils import HashUtils
from config.theme import THEME_CSS

# Backend
from backend.gee.gee_initializer import GEEInitializer
from backend.gee.collection_builder import CollectionBuilder
from backend.gee.index_calculator import IndexCalculator
from backend.gee.statistics_calculator import StatisticsCalculator
from backend.db.db_connection import DBConnection
from backend.db.analysis_repository import AnalysisRepository

# Frontend
from frontend.sidebar.sidebar import Sidebar
from frontend.tabs.maps_tab import MapsTab
from frontend.tabs.temporal_tab import TemporalTab
from frontend.tabs.change_tab import ChangeTab
from frontend.tabs.report_tab import ReportTab
from frontend.tabs.history_tab import HistoryTab
from backend.db.history_repository import HistoryRepository

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(**PAGE_CONFIG)
st.markdown(THEME_CSS, unsafe_allow_html=True)

TAB_NAMES = ['Interactive Maps', 'Temporal Analysis', 'Change Detection', 'Report', 'History']


# ── Session state defaults ───────────────────────────────────────────────────
def _init_session_state() -> None:
    defaults = {
        'site_name':        'Alba Iulia Fortress',
        'center_lat':       46.0686,
        'center_lon':       23.5714,
        'buffer_km':        2.0,
        'analysis_results': None,
        'active_tab':       0,
        'custom_indices':   [],
        'latest_drawings':  [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Cached singletons ────────────────────────────────────────────────────────
@st.cache_resource
def _get_db() -> DBConnection:
    return DBConnection()


@st.cache_resource
def _get_collection_builder() -> CollectionBuilder:
    return CollectionBuilder()


@st.cache_resource
def _get_index_calculator() -> IndexCalculator:
    return IndexCalculator()


@st.cache_resource
def _get_stats_calculator() -> StatisticsCalculator:
    return StatisticsCalculator()


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    _init_session_state()

    st.markdown(
        '<h1 class="main-header">Heritage Site Monitoring System</h1>',
        unsafe_allow_html=True,
    )
    st.markdown('---')

    # Initialise GEE (no-op if already done)
    try:
        GEEInitializer.init()
    except RuntimeError as exc:
        st.error(str(exc))
        st.info('Please ensure you are authenticated with Earth Engine.')
        st.stop()

    # Shared singletons
    db              = _get_db()
    col_builder     = _get_collection_builder()
    idx_calc        = _get_index_calculator()
    stats_calc      = _get_stats_calculator()
    analysis_repo   = AnalysisRepository(db)
    history_repo    = HistoryRepository(db)

    # Sidebar → config dict
    config = Sidebar().render()

    # Custom-region map (shown above the tabs when no preset is selected)
    if config['site_name'] == 'Custom Region':
        _render_custom_region_map(config)
        return

    # Build AOI
    aoi = col_builder.build_aoi(
        config['center_lat'], config['center_lon'], config['buffer_km']
    )

    # Run analysis when requested
    if config['run_analysis']:
        _run_analysis(config, aoi, db, col_builder, idx_calc, stats_calc, analysis_repo, history_repo)

    # Propagate fresh custom indices into stored results
    if st.session_state.analysis_results:
        fresh_custom = st.session_state.get('custom_indices', [])
        if fresh_custom:
            st.session_state.analysis_results['config']['custom_indices'] = fresh_custom

    # Render tabs
    if st.session_state.analysis_results:
        _render_tabs(st.session_state.analysis_results, db, history_repo)
    else:
        # Still allow browsing history even before running a new analysis
        selected_tab = st.radio(
            label='tabs', options=['History'],
            horizontal=True, label_visibility='collapsed',
            key='tab_selector_empty',
        )
        if selected_tab == 'History':
            HistoryTab(db, _get_collection_builder(), _get_index_calculator()).render()
        else:
            st.info("Configure parameters in the sidebar and click 'Run Analysis' to begin.")

    st.markdown('---')
    st.markdown(
        "<div class='footer-text'>"
        "Powered by Google Earth Engine &nbsp;|&nbsp; Sentinel-2 &nbsp;|&nbsp; Streamlit"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Analysis pipeline ────────────────────────────────────────────────────────
def _run_analysis(
    config, aoi, db, col_builder, idx_calc, stats_calc, analysis_repo, history_repo
) -> None:
    with st.spinner('Connecting to satellite archive…'):
        collection = col_builder.build(
            aoi,
            config['start_date'].strftime('%Y-%m-%d'),
            config['end_date'].strftime('%Y-%m-%d'),
            config['cloud_cover'],
        )
        count = col_builder.count(collection)

    if count == 0:
        st.warning('No satellite images found for the selected period.')
        return

    # Try cache first
    cached = analysis_repo.find_by_config(config)
    if cached:
        st.session_state.analysis_results = _build_results(
            config, collection, count, aoi, cached, is_from_cache=True
        )
        return

    # Full computation
    with st.spinner('Calculating spectral indices…'):
        median      = collection.median()
        indexed     = idx_calc.compute(median, extra_indices=config.get('custom_indices', []))
        stats       = stats_calc.run_multiple(indexed, aoi, config['indices'])

    config['image_count'] = count
    analysis_repo.save(config, stats)

    # Store indices list and image count in history meta
    try:
        hid = history_repo.get_id_by_hash(HashUtils.hash_config(config))
        if hid:
            history_repo.update_indices_meta(hid, config['indices'], count)
    except Exception:
        pass

    st.session_state.analysis_results = _build_results(
        config, collection, count, aoi, stats, is_from_cache=False
    )


def _build_results(config, collection, count, aoi, stats, is_from_cache) -> dict:
    return {
        'config':        config,
        'collection':    collection,
        'count':         count,
        'aoi':           aoi,
        'stats':         stats,
        'is_from_cache': is_from_cache,
    }


# ── Tab rendering ─────────────────────────────────────────────────────────────
def _render_tabs(results: dict, db: DBConnection, history_repo) -> None:
    selected_tab = st.radio(
        label='tabs',
        options=TAB_NAMES,
        index=st.session_state.active_tab,
        horizontal=True,
        label_visibility='collapsed',
        key='tab_selector',
    )
    st.session_state.active_tab = TAB_NAMES.index(selected_tab)

    if selected_tab == TAB_NAMES[0]:
        MapsTab(results).render()
    elif selected_tab == TAB_NAMES[1]:
        TemporalTab(results, db).render()
    elif selected_tab == TAB_NAMES[2]:
        ChangeTab(results, history_repo=history_repo).render()
    elif selected_tab == TAB_NAMES[3]:
        ReportTab(results).render()
    elif selected_tab == TAB_NAMES[4]:
        HistoryTab(db, _get_collection_builder(), _get_index_calculator()).render()


# ── Custom region helper ──────────────────────────────────────────────────────
def _render_custom_region_map(config: dict) -> None:
    """Minimal draw-on-map UI for custom region selection."""
    from frontend.components.map_widget import MapWidget
    from folium.plugins import Draw

    st.subheader('Select Your Custom Region')
    st.info('Draw a point or polygon on the map, then click "Get Coordinates".')

    widget = MapWidget(config['center_lat'], config['center_lon'])
    m = widget.create_base_map(zoom=10)
    widget.add_draw_control(m)
    out = widget.render(m)

    if out and 'all_drawings' in out:
        st.session_state.latest_drawings = out['all_drawings']

    if st.button('Get Coordinates from Map', type='primary', use_container_width=True):
        _update_coordinates_from_drawing()


def _update_coordinates_from_drawing() -> None:
    drawings = st.session_state.get('latest_drawings', [])
    if not drawings:
        st.warning('No region drawn on map.')
        return
    try:
        geometry = drawings[-1]['geometry']
        if geometry['type'] == 'Point':
            lon, lat = geometry['coordinates']
            st.session_state.update(center_lat=lat, center_lon=lon,
                                    site_name='Custom Region (Point)')
            st.success(f'Updated: {lat:.4f}°N, {lon:.4f}°E')
        elif geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]
            lat = sum(c[1] for c in coords) / len(coords)
            lon = sum(c[0] for c in coords) / len(coords)
            st.session_state.update(center_lat=lat, center_lon=lon,
                                    site_name='Custom Region (Polygon)')
            st.success(f'Polygon centre: {lat:.4f}°N, {lon:.4f}°E')
    except Exception as exc:
        st.error(str(exc))


if __name__ == '__main__':
    main()