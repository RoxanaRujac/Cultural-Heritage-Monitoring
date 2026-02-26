"""
Interactive Maps Tab for Heritage Site Monitoring System
"""

import streamlit as st
import geemap.foliumap as geemap
from folium.plugins import Draw
from config.settings import INDICES_CONFIG
import ee

# Import for interactivity (st_folium)
try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None


def update_coordinates_callback():
    """
    Callback function for updating coordinates from map selection
    """
    drawings = st.session_state.get('latest_drawings', [])

    if not drawings:
        st.session_state.coord_update_msg = {
            'type': 'warning',
            'text': "No region drawn on map. Please draw a shape first."
        }
        return

    try:
        feature = drawings[-1]
        geometry = feature['geometry']

        if geometry['type'] == 'Point':
            coords = geometry['coordinates']

            st.session_state.center_lon = coords[0]
            st.session_state.center_lat = coords[1]
            st.session_state.site_name = "Custom Region (Point)"

            st.session_state.lon_input = coords[0]
            st.session_state.lat_input = coords[1]
            st.session_state.site_name_input = "Custom Region (Point)"

            st.session_state.coord_update_msg = {
                'type': 'success',
                'text': f" Updated to point: {coords[1]:.4f}°N, {coords[0]:.4f}°E"
            }

        elif geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            center_lon = sum(lons) / len(lons)
            center_lat = sum(lats) / len(lats)

            st.session_state.center_lon = center_lon
            st.session_state.center_lat = center_lat
            st.session_state.site_name = "Custom Region (Polygon)"

            st.session_state.lon_input = center_lon
            st.session_state.lat_input = center_lat
            st.session_state.site_name_input = "Custom Region (Polygon)"

            st.session_state.coord_update_msg = {
                'type': 'success',
                'text': f" Updated to polygon center: {center_lat:.4f}°N, {center_lon:.4f}°E"
            }

    except Exception as e:
        st.session_state.coord_update_msg = {
            'type': 'error',
            'text': f"Error extracting coordinates: {str(e)}"
        }


def create_interactive_map(center_lat, center_lon, zoom=12):
    """Create interactive map with geemap"""
    m = geemap.Map(center=[center_lat, center_lon], zoom=zoom, add_google_map=False)
    m.add_basemap('HYBRID')
    return m


def render_custom_region_map(config):
    """Render map for custom region selection (before analysis)"""
    st.subheader(" Select Your Custom Region")

    st.info(" Use the drawing tools below to select your region, then click 'Get Coordinates from Map Selection'")

    # Show empty map for selection
    m = create_interactive_map(config['center_lat'], config['center_lon'], 10)
    Draw(export=True).add_to(m)
    m.add_layer_control()

    if st_folium is not None:
        map_output = st_folium(m, height=430, width="100%", returned_objects=["all_drawings"])
        if map_output and 'all_drawings' in map_output:
            st.session_state.latest_drawings = map_output['all_drawings']
    else:
        m.to_streamlit(height=430)

    st.markdown("###  How to Select Your Region")

    col_inst1, col_inst2 = st.columns(2)

    with col_inst1:
        st.markdown("""
        **Step 1: Draw on the Map**
        - Click the **drawing tools** (top-left of map)
        - Select the **Marker tool**  for a point location
        - OR select the **Polygon tool**  to outline an area
        - Draw your region on the map
        """)

    with col_inst2:
        st.markdown("""
        **Step 2: Confirm Selection**
        - Click the button below to extract coordinates
        - Check the sidebar for updated coordinates
        - Adjust the analysis radius if needed
        - Click **'Run Analysis'** in the sidebar
        """)

    st.button(" Get Coordinates from Map Selection",
              on_click=update_coordinates_callback,
              type="primary",
              use_container_width=True)

    if 'coord_update_msg' in st.session_state:
        msg = st.session_state.coord_update_msg
        if msg['type'] == 'success':
            st.success(msg['text'])
        elif msg['type'] == 'warning':
            st.warning(msg['text'])
        elif msg['type'] == 'error':
            st.error(msg['text'])
        del st.session_state.coord_update_msg


def render_maps_tab(results):
    """Render interactive maps tab with region selection"""
    config = results['config']
    monitor = results['monitor']
    aoi = results['aoi']
    collection = results['collection']
    count = results['count']

    st.subheader(f" Interactive Map - {config['site_name']}")

    # Check if this is a custom region without selection
    if config['site_name'] == 'Custom Region':
        st.info(" Use the drawing tools below to select your region, then click 'Get Coordinates from Map Selection'")

        # Show empty map for selection
        m = create_interactive_map(config['center_lat'], config['center_lon'], 10)
        Draw(export=True).add_to(m)
        m.add_layer_control()

        if st_folium is not None:
            map_output = st_folium(m, height=500, width="100%", returned_objects=["all_drawings"])
            if map_output and 'all_drawings' in map_output:
                st.session_state.latest_drawings = map_output['all_drawings']
        else:
            m.to_streamlit(height=500)

        st.markdown("###  How to Select Your Region")
        st.markdown("""
        1. **Draw a Marker** () for a point location, or **Draw a Polygon** (⬟) to outline an area
        2. Click the **'Get Coordinates from Map Selection'** button below
        3. Return to the sidebar and click **'Run Analysis'** to process your custom region
        """)

        st.button(" Get Coordinates from Map Selection",
                 on_click=update_coordinates_callback,
                 type="primary",
                 use_container_width=True)

        if 'coord_update_msg' in st.session_state:
            msg = st.session_state.coord_update_msg
            if msg['type'] == 'success':
                st.success(msg['text'])
            elif msg['type'] == 'warning':
                st.warning(msg['text'])
            elif msg['type'] == 'error':
                st.error(msg['text'])
            del st.session_state.coord_update_msg

        return

    st.info(f" Found {count} Sentinel-2 images for the selected period")

    if count > 0:
        # Calculate images and indices
        median_image = collection.median()
        indices_image = monitor.calculate_indices(median_image)

        # Initialize map
        m = create_interactive_map(config['center_lat'], config['center_lon'], 13)

        # Add RGB layer
        vis_params_rgb = {
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 3000,
            'gamma': 1.4
        }
        m.addLayer(median_image, vis_params_rgb, 'RGB Natural Color', False)

        custom_idx_layers = {c["name"]: c for c in config.get("custom_indices", [])}
        # Add spectral index layers
        for idx in config["indices"]:
            try:
                if idx in INDICES_CONFIG:
                    idc = INDICES_CONFIG[idx]
                    m.addLayer(indices_image.select(idx),
                               {"min": idc["min"], "max": idc["max"], "palette": idc["palette"]}, idc["name"], False)
                elif idx in custom_idx_layers:
                    ci = custom_idx_layers[idx]
                    m.addLayer(indices_image.select(idx), {"min": ci.get("min", -1), "max": ci.get("max", 1),
                                                           "palette": ci.get("palette", ["FFFFFF", "0000FF"])},
                               f"{idx} (custom)", False)
            except Exception:
                pass

        # Add AOI
        aoi_style = ee.FeatureCollection(aoi).style(**{
            'color': 'FF0000',
            'fillColor': 'FF00001A',
            'width': 2
        })

        m.addLayer(aoi_style, {}, 'Area of Interest')

        Draw(export=True).add_to(m)
        m.add_layer_control()
        m.centerObject(aoi, 14)


        # Display map
        if st_folium is not None:
            map_output = st_folium(m, height=430, width="100%", returned_objects=["all_drawings"])
            if map_output and 'all_drawings' in map_output:
                st.session_state.latest_drawings = map_output['all_drawings']
        else:
            m.to_streamlit(height=430)

        # Enhanced Legend
        st.markdown("---")
        st.markdown("###  Spectral Indices Guide")

        custom_idx_legend = {c["name"]: c for c in config.get("custom_indices", [])}
        for idx in config["indices"]:
            if idx in custom_idx_legend:
                ci = custom_idx_legend[idx]
                with st.expander(f"**{idx}** - Custom Index", expanded=False):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown("**Formula:**")
                        if ci.get("formula") in ("normalized_diff", "ratio", "difference"):
                            ops = {"normalized_diff": "(A-B)/(A+B)", "ratio": "A/B", "difference": "A-B"}
                            expr = ops[ci["formula"]].replace("A", ci.get("band_a", "")).replace("B",
                                                                                                 ci.get("band_b", ""))
                            st.code(expr)
                        elif ci.get("formula") == "expression":
                            st.code(ci.get("expression", ""))
                        st.caption(f"Range: {ci.get('min', -1)} to {ci.get('max', 1)}")
                    with col2:
                        st.markdown("**Description:**")
                        st.info(ci.get("description", "User-defined custom spectral index."))
                continue
            if idx not in INDICES_CONFIG:
                continue
            idc = INDICES_CONFIG[idx]

            with st.expander(f"**{idx}** - {idc['name']}", expanded=False):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown("**Color Scale:**")
                    palette = idc["palette"]
                    hex_pal = ["#" + p if not p.startswith("#") else p for p in palette]
                    grad = ", ".join(hex_pal)
                    st.markdown(
                        f'<div style="background:linear-gradient(to right,{grad});height:16px;border-radius:4px;border:1px solid #ccc;"></div><div style="display:flex;justify-content:space-between;font-size:11px;"><span>{idc["min"]}</span><span>{idc["max"]}</span></div>',
                        unsafe_allow_html=True)
                with col2:
                    st.markdown("**Interpretation:**")
                    st.markdown(idc.get("description", ""))
                    st.caption(idc.get("heritage_use", ""))

        else:
            st.warning(" No images found for the selected period. Try adjusting cloud cover or dates.")