"""
Interactive Maps Tab — Heritage Site Monitoring System
"""

import streamlit as st
import geemap.foliumap as geemap
from folium.plugins import Draw
import folium
from config.settings import INDICES_CONFIG
import ee
from datetime import datetime
from utils.db_utils import get_all_indices_for_date
import time

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None


def update_coordinates_callback():
    drawings = st.session_state.get('latest_drawings', [])
    if not drawings:
        st.session_state.coord_update_msg = {'type': 'warning', 'text': "No region drawn on map."}
        return
    try:
        feature  = drawings[-1]
        geometry = feature['geometry']
        if geometry['type'] == 'Point':
            coords = geometry['coordinates']
            st.session_state.center_lon = coords[0]
            st.session_state.center_lat = coords[1]
            st.session_state.site_name  = "Custom Region (Point)"
            st.session_state.lon_input  = coords[0]
            st.session_state.lat_input  = coords[1]
            st.session_state.site_name_input = "Custom Region (Point)"
            st.session_state.coord_update_msg = {'type': 'success', 'text': f"Updated: {coords[1]:.4f}°N, {coords[0]:.4f}°E"}
        elif geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]
            clat   = sum(c[1] for c in coords) / len(coords)
            clon   = sum(c[0] for c in coords) / len(coords)
            st.session_state.center_lat = clat
            st.session_state.center_lon = clon
            st.session_state.site_name  = "Custom Region (Polygon)"
            st.session_state.lat_input  = clat
            st.session_state.lon_input  = clon
            st.session_state.site_name_input = "Custom Region (Polygon)"
            st.session_state.coord_update_msg = {'type': 'success', 'text': f"Polygon center: {clat:.4f}°N, {clon:.4f}°E"}
    except Exception as e:
        st.session_state.coord_update_msg = {'type': 'error', 'text': str(e)}


def create_map(center_lat, center_lon, zoom=14):
    m = geemap.Map(center=[center_lat, center_lon], zoom=zoom, add_google_map=False)
    m.add_basemap('HYBRID')
    return m


def _get_image_dates(collection):
    timestamps = collection.aggregate_array('system:time_start').getInfo()
    dates = []
    for ts in timestamps:
        dt = datetime.fromtimestamp(ts / 1000)
        dates.append((ts, dt.strftime('%Y-%m-%d'), dt))
    return sorted(dates, key=lambda x: x[0])


def _add_index_layers(m, indices_image, config, default_visible=False):
    custom_map = {c['name']: c for c in config.get('custom_indices', [])}
    for idx in config['indices']:
        try:
            if idx in INDICES_CONFIG:
                idc = INDICES_CONFIG[idx]
                m.addLayer(indices_image.select(idx),
                           {'min': idc['min'], 'max': idc['max'], 'palette': idc['palette']},
                           idc['name'], default_visible)
            elif idx in custom_map:
                ci = custom_map[idx]
                m.addLayer(indices_image.select(idx),
                           {'min': ci.get('min', -1), 'max': ci.get('max', 1),
                            'palette': ci.get('palette', ['FFFFFF', '0000FF'])},
                           f"{idx} (custom)", default_visible)
        except Exception:
            pass


def _palette_css(idx_name, config):
    custom_map = {c['name']: c for c in config.get('custom_indices', [])}
    if idx_name in INDICES_CONFIG:
        idc = INDICES_CONFIG[idx_name]
        pal = ['#'+p if not p.startswith('#') else p for p in idc['palette']]
        return ', '.join(pal), idc['min'], idc['max']
    elif idx_name in custom_map:
        ci  = custom_map[idx_name]
        pal = ['#'+p if not p.startswith('#') else p for p in ci.get('palette', ['#FFFFFF', '#0000FF'])]
        return ', '.join(pal), ci.get('min', -1), ci.get('max', 1)
    return '#ccc, #ccc', 0, 1


GEE_MAX_PIXELS = 26_214_400


def _smart_sample_collection(collection, dimensions, date_range_days):
    """
    Selecteaza automat un subset de imagini din colectie
    pentru a nu depasi limita GEE de pixeli.

    Strategia:
      - < 180 zile  : toate imaginile (max ~26 imagini Sentinel-2)
      - 180-730 zile : o imagine pe luna (reprezentativa)
      - > 730 zile   : o imagine la 2 luni
      - > 1825 zile  : o imagine la 3 luni (5+ ani)

    Intoarce colectia filtrata + numarul de frame-uri.
    """
    max_frames = max(1, GEE_MAX_PIXELS // (dimensions * dimensions))

    total = collection.size().getInfo()
    if total <= max_frames:
        return collection, total

    # Calculeaza intervalul de sampling in zile
    if date_range_days <= 180:
        interval_days = 5
    elif date_range_days <= 730:
        interval_days = 30      # ~1 imagine/luna
    elif date_range_days <= 1825:
        interval_days = 60      # ~1 imagine/2 luni
    else:
        interval_days = 90      # ~1 imagine/3 luni

    # Filtreaza pastrând o imagine per interval
    # GEE nu are un .every(n) nativ, asa ca folosim millis
    millis_per_interval = interval_days * 24 * 60 * 60 * 1000

    timestamps = collection.aggregate_array('system:time_start').getInfo()
    timestamps.sort()

    selected_ts = []
    last_kept   = None
    for ts in timestamps:
        if last_kept is None or (ts - last_kept) >= millis_per_interval:
            selected_ts.append(ts)
            last_kept = ts
            if len(selected_ts) >= max_frames:
                break

    # Ricostruieste colectia doar cu timestamp-urile selectate
    # Folosim un filtru bazat pe lista de date
    import ee as _ee
    filtered = collection.filter(
        _ee.Filter.inList('system:time_start', selected_ts)
    )
    return filtered, len(selected_ts)


def get_gee_gif_url(collection, aoi, selected_view, vis_params, fps=2, dimensions=512,
                    date_range_days=365):
    """
    Genereaza URL-ul unui GIF animat direct din GEE cu smart sampling.

    Parametri:
      selected_view    : 'Natural Color (RGB)' sau numele unui indice
      vis_params       : dict cu min/max/palette (ignorat pentru RGB)
      fps              : cadre per secunda
      dimensions       : rezolutia GIF (latimea in pixeli)
      date_range_days  : durata intervalului selectat — folosit pentru sampling

    Limita GEE: 26,214,400 pixeli total (frames x width x height).
    Functia reduce automat numarul de frame-uri daca e nevoie.
    Returneaza (url, n_frames, was_sampled).
    """
    # Calculeaza cate frame-uri incap
    max_frames = max(1, GEE_MAX_PIXELS // (dimensions * dimensions))

    sampled_col, n_frames = _smart_sample_collection(
        collection, dimensions, date_range_days
    )
    was_sampled = (n_frames < collection.size().getInfo())

    def prep_rgb(img):
        return img.visualize(bands=['B4', 'B3', 'B2'], min=0, max=3000, gamma=1.4)

    def prep_index(img):
        from utils.gee_utils import HeritageMonitor
        monitor = HeritageMonitor()
        idx_img = monitor.calculate_indices(img).select(selected_view)
        return idx_img.visualize(
            min=vis_params['min'],
            max=vis_params['max'],
            palette=vis_params['palette']
        )

    if selected_view == "Natural Color (RGB)":
        video_col = sampled_col.map(prep_rgb)
    else:
        video_col = sampled_col.map(prep_index)

    video_args = {
        'dimensions':      dimensions,
        'region':          aoi,
        'framesPerSecond': fps,
        'crs':             'EPSG:3857',
    }

    url = video_col.getVideoThumbURL(video_args)
    return url, n_frames, was_sampled


def _render_slideshow_stats(config, date_str, monitor, indices_image, aoi):
    site = config['site_name']
    cached_vals = {}
    try:
        cached_vals = get_all_indices_for_date(site, date_str)
    except Exception:
        pass

    indices_to_show = [idx for idx in config['indices']
                       if idx in INDICES_CONFIG or
                       idx in {c['name'] for c in config.get('custom_indices', [])}]
    if not indices_to_show:
        return

    st.markdown(f"**Index values — {date_str}**")
    cols = st.columns(min(len(indices_to_show), 5))
    for i, idx in enumerate(indices_to_show):
        with cols[i % len(cols)]:
            if idx in cached_vals:
                val, src = cached_vals[idx], "cached"
            else:
                try:
                    stats = monitor.calculate_statistics(indices_image, aoi, idx)
                    val   = stats.get(f'{idx}_mean')
                    src   = "live"
                except Exception:
                    val, src = None, "N/A"
            st.metric(idx, f"{val:.4f}" if val is not None else "N/A", help=src)


# ─────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────

def render_custom_region_map(config):
    st.subheader("Select Your Custom Region")
    st.info("Draw a point or polygon, then click 'Get Coordinates'.")
    m = create_map(config['center_lat'], config['center_lon'], 10)
    Draw(export=True).add_to(m)
    m.add_layer_control()
    if st_folium:
        out = st_folium(m, height=430, width="100%", returned_objects=["all_drawings"])
        if out and 'all_drawings' in out:
            st.session_state.latest_drawings = out['all_drawings']
    else:
        m.to_streamlit(height=430)
    st.button("Get Coordinates from Map", on_click=update_coordinates_callback,
              type="primary", use_container_width=True)
    if 'coord_update_msg' in st.session_state:
        msg = st.session_state.coord_update_msg
        getattr(st, msg['type'])(msg['text'])
        del st.session_state.coord_update_msg


def render_maps_tab(results):
    config     = results['config']
    monitor    = results['monitor']
    aoi        = results['aoi']
    collection = results['collection']
    count      = results['count']

    st.subheader(f"Interactive Maps — {config['site_name']}")

    if config['site_name'] == 'Custom Region':
        m = create_map(config['center_lat'], config['center_lon'], 10)
        Draw(export=True).add_to(m)
        m.add_layer_control()
        if st_folium:
            out = st_folium(m, height=500, width="100%", returned_objects=["all_drawings"])
            if out and 'all_drawings' in out:
                st.session_state.latest_drawings = out['all_drawings']
        else:
            m.to_streamlit(height=500)
        st.button("Get Coordinates from Map", on_click=update_coordinates_callback,
                  type="primary", use_container_width=True)
        return

    if count == 0:
        st.warning("No images found. Try adjusting cloud cover or dates.")
        return

    # ── Configurare comuna ───────────────────────────────────
    col_layer, col_meta = st.columns([4, 1])

    with col_layer:
        available_layers = ["Natural Color (RGB)"] + [
            i for i in config['indices']
            if i in INDICES_CONFIG or
            i in {c['name'] for c in config.get('custom_indices', [])}
        ]
        selected_view = st.selectbox(
            "Layer to visualize",
            available_layers,
            key="maps_selected_layer",
            help="Applied to all three view modes below"
        )

    with col_meta:
        st.metric("Images", count)

    # ── Selector mod — butoane inline, NU radio ──────────────
    if 'maps_view_mode' not in st.session_state:
        st.session_state.maps_view_mode = "Median"

    VIEW_MODES = {
        "Median": ("Median", ''),
        "Browse": ("Browse images", ''),
        "Timelapse GIF": ("Timelapse GIF", ''),
    }

    st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] button[kind="secondary"] p { visibility: hidden; height: 0; }
    [data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin-top: -56px !important;
        height: 56px !important;
        width: 100% !important;
        cursor: pointer !important;
    }
    </style>
    """, unsafe_allow_html=True)

    btn_cols = st.columns(len(VIEW_MODES))
    for col, (key, (label, desc)) in zip(btn_cols, VIEW_MODES.items()):
        is_active = st.session_state.maps_view_mode == key
        with col:
            bg    = "linear-gradient(135deg,#4a2d6b,#764ba2)" if is_active else "transparent"
            color = "white" if is_active else "#764ba2"
            weight = "700" if is_active else "500"
            st.markdown(f"""
            <div style="text-align:center; padding:10px 6px; background:{bg};
                        border:1.5px solid #764ba2; border-radius:8px;
                        font-size:13px; font-weight:{weight};
                        color:{color}; pointer-events:none; margin-bottom:4px;
                        min-height:50px; display:flex; flex-direction:column;
                        align-items:center; justify-content:center;">
                {label}
                <div style="font-size:10px; opacity:0.8; margin-top:3px;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(label, key=f"viewbtn_{key}", use_container_width=True):
                st.session_state.maps_view_mode = key
                st.rerun()

    view_mode = st.session_state.maps_view_mode
    st.markdown("---")

    # ── Modul 1: Median ──────────────────────────────────────
    if view_mode == "Median":
        extra        = st.session_state.get('custom_indices', []) or config.get('custom_indices', [])
        median_image = collection.median()

        m = create_map(config['center_lat'], config['center_lon'], 14)

        if selected_view == "Natural Color (RGB)":
            m.addLayer(median_image,
                       {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4},
                       'RGB Median', True)
        else:
            indices_image = monitor.calculate_indices(median_image, extra_indices=extra)
            _add_index_layers(m, indices_image, config, default_visible=False)
            # Activeaza direct layer-ul selectat
            if selected_view in INDICES_CONFIG:
                idc = INDICES_CONFIG[selected_view]
                m.addLayer(indices_image.select(selected_view),
                           {'min': idc['min'], 'max': idc['max'], 'palette': idc['palette']},
                           f"{selected_view} (active)", True)

        aoi_style = ee.FeatureCollection(aoi).style(color='764ba2', fillColor='764ba21A', width=2)
        m.addLayer(aoi_style, {}, 'AOI')
        Draw(export=True).add_to(m)
        m.add_layer_control()
        m.centerObject(aoi, 14)

        if st_folium:
            out = st_folium(m, height=540, width="100%", returned_objects=["all_drawings"])
            if out and 'all_drawings' in out:
                st.session_state.latest_drawings = out['all_drawings']
        else:
            m.to_streamlit(height=540)


    # ── Modul 2: Browse Images ───────────────────────────────
    elif view_mode == "Browse":
        extra = st.session_state.get('custom_indices', []) or config.get('custom_indices', [])

        cache_key = f"img_dates_{id(collection)}"
        if cache_key not in st.session_state:
            with st.spinner("Loading image timeline..."):
                st.session_state[cache_key] = _get_image_dates(collection)
        image_dates = st.session_state[cache_key]
        total = len(image_dates)

        if 'browse_idx' not in st.session_state:
            st.session_state.browse_idx = 0
        st.session_state.browse_idx = st.session_state.browse_idx % total

        # Timeline slider
        st.session_state.browse_idx = st.select_slider(
            "Timeline",
            options=range(total),
            value=st.session_state.browse_idx,
            format_func=lambda x: image_dates[x][1],
            key="browse_slider"
        )

        # Prev / Next
        cp, _, cn = st.columns([1, 8, 1])
        with cp:
            if st.button("◀", use_container_width=True,
                         disabled=st.session_state.browse_idx == 0):
                st.session_state.browse_idx -= 1
                st.rerun()
        with cn:
            if st.button("▶", use_container_width=True,
                         disabled=st.session_state.browse_idx == total - 1):
                st.session_state.browse_idx += 1
                st.rerun()

        cur_ts, cur_date_str, cur_dt = image_dates[st.session_state.browse_idx]

        image = ee.Image(collection.filterDate(
            cur_dt.strftime('%Y-%m-%d'),
            cur_dt.strftime('%Y-%m-%d') + 'T23:59:59'
        ).first())

        m = create_map(config['center_lat'], config['center_lon'], 14)

        if selected_view == "Natural Color (RGB)":
            m.addLayer(image,
                       {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4},
                       f'RGB {cur_date_str}', True)
        else:
            indices_image = monitor.calculate_indices(image, extra_indices=extra)
            if selected_view in INDICES_CONFIG:
                idc = INDICES_CONFIG[selected_view]
                m.addLayer(indices_image.select(selected_view),
                           {'min': idc['min'], 'max': idc['max'], 'palette': idc['palette']},
                           selected_view, True)

        aoi_style = ee.FeatureCollection(aoi).style(color='764ba2', fillColor='764ba210', width=2)
        m.addLayer(aoi_style, {}, 'AOI')
        m.add_layer_control()
        m.centerObject(aoi, 14)

        # Overlay data pe harta
        date_overlay = f"""
        <div style="position:absolute; top:12px; left:12px; z-index:1000;
                    background:rgba(26,26,46,0.82); color:#f0c040;
                    font-family:monospace; font-size:14px; font-weight:700;
                    padding:6px 12px; border-radius:6px; border:1px solid #764ba2;
                    pointer-events:none; letter-spacing:1px;">
            📅 {cur_date_str} &nbsp; [{st.session_state.browse_idx + 1}/{total}]
        </div>
        """
        m.get_root().html.add_child(folium.Element(date_overlay))

        if st_folium:
            st_folium(m, height=540, width="100%",
                      key=f"browse_{st.session_state.browse_idx}_{selected_view}",
                      returned_objects=[])
        else:
            m.to_streamlit(height=540)

        # Stats sub harta
        if selected_view != "Natural Color (RGB)":
            extra2 = st.session_state.get('custom_indices', []) or config.get('custom_indices', [])
            indices_image2 = monitor.calculate_indices(image, extra_indices=extra2)
            _render_slideshow_stats(config, cur_date_str, monitor, indices_image2, aoi)

    # ── Modul 3: Timelapse GIF ───────────────────────────────
    elif view_mode == "Timelapse GIF":
        st.markdown("### Timelapse GIF")

        col_fps, col_res, col_btn = st.columns([2, 2, 2])
        with col_fps:
            fps = st.slider("Frames per second", min_value=1, max_value=8, value=2,
                            help="Higher = faster animation")
        with col_res:
            dimensions = st.select_slider(
                "Resolution",
                options=[400, 512, 600, 768, 900],
                value=600,
                help="Width of the GIF in pixels. Higher = slower to generate."
            )
        with col_btn:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            generate = st.button("▶ Generate Timelapse", type="primary", use_container_width=True)

        gif_cache_key = f"gif_{selected_view}_{fps}_{dimensions}_{id(collection)}"

        # Calculeaza durata intervalului pentru smart sampling
        date_range_days = max(1, (config['end_date'] - config['start_date']).days)

        # Previzualizeaza cate frame-uri vor fi trimise inainte de generate
        max_frames_preview = max(1, GEE_MAX_PIXELS // (dimensions * dimensions))
        if count > max_frames_preview:
            if date_range_days <= 180:
                interval_str = "every 5 days"
            elif date_range_days <= 730:
                interval_str = "one per month"
            elif date_range_days <= 1825:
                interval_str = "one per 2 months"
            else:
                interval_str = "one per 3 months"
            st.warning(
                f"⚠️ {count} images exceed the GEE limit for {dimensions}px resolution "
                f"({max_frames_preview} max frames). "
                f"Will auto-sample to **~{max_frames_preview} frames** ({interval_str}) "
                f"to stay within limits."
            )
        else:
            st.info(f"✓ All {count} images fit within the GEE pixel limit at {dimensions}px.")

        if generate:
            with st.spinner(f"GEE is rendering frames at {fps} fps… (may take 15–60s)"):
                try:
                    if selected_view == "Natural Color (RGB)":
                        vis_params = {}
                    elif selected_view in INDICES_CONFIG:
                        idc = INDICES_CONFIG[selected_view]
                        vis_params = {
                            'min':     idc['min'],
                            'max':     idc['max'],
                            'palette': idc['palette'],
                        }
                    else:
                        custom_map = {c['name']: c for c in config.get('custom_indices', [])}
                        ci = custom_map.get(selected_view, {})
                        vis_params = {
                            'min':     ci.get('min', -1),
                            'max':     ci.get('max', 1),
                            'palette': ci.get('palette', ['FFFFFF', '0000FF']),
                        }

                    gif_url, n_frames, was_sampled = get_gee_gif_url(
                        collection, aoi, selected_view, vis_params,
                        fps=fps, dimensions=dimensions,
                        date_range_days=date_range_days
                    )
                    st.session_state[gif_cache_key] = (gif_url, n_frames, was_sampled)
                    if was_sampled:
                        st.success(f"✓ Timelapse generated — {n_frames} frames (sampled from {count}).")
                    else:
                        st.success(f"✓ Timelapse generated — {n_frames} frames.")

                except Exception as e:
                    st.error(f"GEE error: {e}")
                    st.info(
                        "Try reducing resolution (e.g. 400px) or shortening the date range."
                    )

        if gif_cache_key in st.session_state:
            gif_url, n_frames, was_sampled = st.session_state[gif_cache_key]
            sampled_note = f" (sampled from {count})" if was_sampled else ""

            st.markdown(f"""
            <div style="position:relative; border-radius:12px; overflow:hidden;
                        border:2px solid #764ba2; box-shadow:0 4px 20px rgba(118,75,162,0.3);">
                <img src="{gif_url}" style="width:100%; display:block;"
                     alt="Timelapse {selected_view}"/>
                <div style="position:absolute; top:10px; left:10px;
                            background:rgba(26,26,46,0.85); color:#f0c040;
                            font-family:monospace; font-size:13px; font-weight:700;
                            padding:5px 10px; border-radius:5px; border:1px solid #764ba2;
                            pointer-events:none;">
                     {selected_view} &nbsp;·&nbsp; {n_frames} frames{sampled_note} &nbsp;·&nbsp; {fps} fps
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Legenda indice sub GIF
            if selected_view != "Natural Color (RGB)":
                grad, vmin, vmax = _palette_css(selected_view, config)
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:10px; padding:8px 14px;
                            background:#f3edf9; border-radius:8px; border-left:4px solid #764ba2;
                            margin:8px 0; font-size:13px;">
                    <span style="font-weight:700; color:#4a2d6b;">{selected_view}</span>
                    <span style="background:linear-gradient(to right,{grad}); width:200px; height:12px;
                          display:inline-block; border-radius:3px; vertical-align:middle;
                          border:1px solid #c5c5d8;"></span>
                    <span style="color:#6b6b8a;">{vmin} → {vmax}</span>
                </div>
                """, unsafe_allow_html=True)

            # Buton download
            st.markdown(f"""
            <div style="margin-top:8px;">
                <a href="{gif_url}" download="timelapse_{selected_view}.gif" target="_blank">
                    <button style="background:linear-gradient(135deg,#4a2d6b,#764ba2);
                                   color:white; border:none; padding:9px 20px;
                                   border-radius:8px; cursor:pointer; font-size:14px;
                                   font-weight:600; letter-spacing:0.5px;">
                        ⬇ Download GIF
                    </button>
                </a>
                <span style="color:#9b8db0; font-size:12px; margin-left:12px;">
                    Right-click → Save image as... if button doesn't trigger download
                </span>
            </div>
            """, unsafe_allow_html=True)

        elif not generate:
            # Placeholder inainte de generate
            st.markdown(f"""
            <div style="border:2px dashed #c5b8d8; border-radius:12px; padding:60px 20px;
                        text-align:center; background:#f9f6fd; color:#764ba2;">
                <div style="font-size:48px; margin-bottom:12px;"></div>
                <div style="font-size:18px; font-weight:700; margin-bottom:8px;">
                    Ready to generate timelapse
                </div>
                <div style="font-size:14px; color:#9b8db0;">
                    {count} images · Layer: <b>{selected_view}</b> · {fps} fps · {dimensions}px
                    <br>Click <b>Generate Timelapse</b> above to start rendering.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Legenda indici (Median + Browse) ────────────────────
    if view_mode != "Timelapse GIF":
        _render_legend(config)


# ─────────────────────────────────────────────────────────────
# LEGENDA
# ─────────────────────────────────────────────────────────────

def _render_legend(config):
    st.markdown("---")
    st.markdown("### Spectral Indices Guide")
    custom_map = {c['name']: c for c in config.get('custom_indices', [])}
    for idx in config['indices']:
        if idx in custom_map:
            ci = custom_map[idx]
            with st.expander(f"**{idx}** — Custom Index", expanded=False):
                c1, c2 = st.columns([1, 2])
                with c1:
                    if ci.get('formula') in ('normalized_diff', 'ratio', 'difference'):
                        ops  = {'normalized_diff': '(A-B)/(A+B)', 'ratio': 'A/B', 'difference': 'A-B'}
                        expr = ops[ci['formula']].replace('A', ci.get('band_a', '')).replace('B', ci.get('band_b', ''))
                        st.code(expr)
                    elif ci.get('formula') == 'expression':
                        st.code(ci.get('expression', ''))
                    st.caption(f"Range: {ci.get('min', -1)} to {ci.get('max', 1)}")
                with c2:
                    st.info(ci.get('description', 'User-defined custom spectral index.'))
            continue
        if idx not in INDICES_CONFIG:
            continue
        idc = INDICES_CONFIG[idx]
        with st.expander(f"**{idx}** — {idc['name']}", expanded=False):
            c1, c2 = st.columns([1, 2])
            with c1:
                hex_pal = ['#'+p if not p.startswith('#') else p for p in idc['palette']]
                grad    = ', '.join(hex_pal)
                st.markdown(
                    f'<div style="background:linear-gradient(to right,{grad});height:16px;'
                    f'border-radius:4px;border:1px solid #ccc;"></div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:11px;">'
                    f'<span>{idc["min"]}</span><span>{idc["max"]}</span></div>',
                    unsafe_allow_html=True)
            with c2:
                st.markdown(idc.get('description', ''))
                st.caption(idc.get('heritage_use', ''))