
import streamlit as st
import geemap.foliumap as geemap
import ee
from datetime import datetime
from utils.visualization import plot_change_detection
from utils.ai_utils import get_ai_interpretation
from config.settings import INDICES_CONFIG
import folium

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None

def _severity(delta):
    a = abs(delta)
    if a >= 0.3:
        return 'critical'
    if a >= 0.15:
        return 'high'
    if a >= 0.07:
        return 'moderate'
    return 'low'

SEVERITY_COLOR = {
    'critical': '#c0392b',
    'high':     '#e67e22',
    'moderate': '#f0c040',
    'low':      '#764ba2',
}
SEVERITY_LABEL = {
    'critical': '🔴 Critical',
    'high':     '🟠 High',
    'moderate': '🟡 Moderate',
    'low':      '🟣 Low',
}


def _sample_change_points(first_image, last_image, aoi, change_index, threshold, n_points=12):
    """
    Esantioneaza puncte din imaginea de diferenta unde |delta| > threshold.
    Returneaza lista de dict {lat, lon, value_before, value_after, delta, severity, label}.
    Foloseste ee.Image.sample() pentru eficienta.
    """
    diff = last_image.select(change_index).subtract(first_image.select(change_index))

    # Combinam before, after, diff intr-o singura imagine pentru sampling eficient
    combined = first_image.select(change_index).rename('before') \
        .addBands(last_image.select(change_index).rename('after')) \
        .addBands(diff.rename('delta'))

    change_mask = diff.abs().gt(threshold)
    combined_masked = combined.updateMask(change_mask)

    try:
        samples = combined_masked.sample(
            region=aoi,
            scale=30,           # 30m pentru sampling mai rar
            numPixels=n_points,
            seed=42,
            geometries=True
        ).getInfo()
    except Exception:
        return []

    events = []
    for feat in samples.get('features', []):
        props = feat.get('properties', {})
        coords = feat.get('geometry', {}).get('coordinates', [0, 0])
        delta  = props.get('delta', 0)
        sev    = _severity(delta)

        direction = "decrease" if delta < 0 else "increase"
        vb = props.get('before', 0)
        va = props.get('after',  0)

        events.append({
            'lat':          coords[1],
            'lon':          coords[0],
            'value_before': round(vb, 4),
            'value_after':  round(va, 4),
            'delta':        round(delta, 4),
            'severity':     sev,
            'label':        f"{change_index} {direction}: {vb:.3f} → {va:.3f} (Δ{delta:+.3f})"
        })

    # Sorteaza dupa |delta| descrescator
    events.sort(key=lambda e: abs(e['delta']), reverse=True)
    return events


def _render_annotated_map(first_image, last_image, aoi, config, change_index, threshold,
                          first_date, last_date, events):
    """
    Harta cu overlay RGB + change detection + markere adnotate pentru fiecare eveniment.
    """
    vis_rgb = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4}
    center  = [config['center_lat'], config['center_lon']]

    if change_index in INDICES_CONFIG:
        idx_cfg = INDICES_CONFIG[change_index]
        vis_index = {'min': idx_cfg['min'], 'max': idx_cfg['max'], 'palette': idx_cfg['palette']}
    else:
        vis_index = {'min': -1, 'max': 1, 'palette': ['FF0000', 'FFFFFF', '00AA00']}

    diff          = last_image.select(change_index).subtract(first_image.select(change_index))
    decrease_mask = diff.lt(-threshold)
    increase_mask = diff.gt(threshold)
    change_mask   = decrease_mask.Or(increase_mask)

    r = ee.Image(255).multiply(decrease_mask).add(ee.Image(0).multiply(increase_mask))
    g = ee.Image(0)
    b = ee.Image(0).multiply(decrease_mask).add(ee.Image(200).multiply(increase_mask))

    change_colored = ee.Image.cat([r, g, b]).rename(['vis-red','vis-green','vis-blue']).toUint8().updateMask(change_mask)
    after_rgb      = last_image.visualize(**vis_rgb)

    r_f = after_rgb.select('vis-red').where(change_mask,   after_rgb.select('vis-red').multiply(0.3).add(change_colored.select('vis-red').multiply(0.7)))
    g_f = after_rgb.select('vis-green').where(change_mask, after_rgb.select('vis-green').multiply(0.3).add(change_colored.select('vis-green').multiply(0.7)))
    b_f = after_rgb.select('vis-blue').where(change_mask,  after_rgb.select('vis-blue').multiply(0.3).add(change_colored.select('vis-blue').multiply(0.7)))

    change_overlay = ee.Image.cat([r_f, g_f, b_f]).rename(['vis-red','vis-green','vis-blue']).toUint8()

    m = geemap.Map(center=center, zoom=14, add_google_map=False)
    m.add_basemap('HYBRID')
    m.addLayer(change_overlay, {'bands': ['vis-red','vis-green','vis-blue'], 'min': 0, 'max': 255},
               f'RGB + {change_index} Changes')

    # AOI border
    aoi_style = ee.FeatureCollection(aoi).style(color='764ba2', fillColor='764ba200', width=2)
    m.addLayer(aoi_style, {}, 'AOI')

    # ── Adnotari: markere colorate pe harta ──────────────────
    for i, ev in enumerate(events):
        color  = SEVERITY_COLOR[ev['severity']].lstrip('#')
        popup_html = f"""
        <div style="font-family:Arial,sans-serif; min-width:200px; padding:4px;">
            <div style="font-weight:700; font-size:13px; color:#{color}; margin-bottom:4px;">
                {SEVERITY_LABEL[ev['severity']]} — {change_index}
            </div>
            <table style="font-size:12px; width:100%;">
                <tr><td style="color:#666;">Before ({first_date}):</td><td><b>{ev['value_before']:.4f}</b></td></tr>
                <tr><td style="color:#666;">After ({last_date}):</td><td><b>{ev['value_after']:.4f}</b></td></tr>
                <tr><td style="color:#666;">Change (Δ):</td>
                    <td><b style="color:{'#c0392b' if ev['delta'] < 0 else '#2d7a4f'}">{ev['delta']:+.4f}</b></td></tr>
                <tr><td style="color:#666;">Location:</td><td>{ev['lat']:.5f}°N, {ev['lon']:.5f}°E</td></tr>
            </table>
        </div>
        """
        folium.CircleMarker(
            location=[ev['lat'], ev['lon']],
            radius=10,
            color='#' + color,
            fill=True,
            fill_color='#' + color,
            fill_opacity=0.7,
            weight=2,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"#{i+1} Δ{ev['delta']:+.3f} — {ev['severity']}"
        ).add_to(m)

        # Numar pe marker
        folium.Marker(
            location=[ev['lat'], ev['lon']],
            icon=folium.DivIcon(
                html=f'<div style="font-size:10px;font-weight:700;color:white;'
                     f'background:#{color};border-radius:50%;width:18px;height:18px;'
                     f'display:flex;align-items:center;justify-content:center;'
                     f'margin-top:-9px;margin-left:-9px;">{i+1}</div>',
                icon_size=(18, 18)
            )
        ).add_to(m)

    m.add_layer_control()
    m.centerObject(aoi, 14)

    if st_folium:
        st_folium(m, height=540, width="100%", returned_objects=[])
    else:
        m.to_streamlit(height=540)


def _render_events_table(events, change_index, first_date, last_date):
    """
    Tabel cu toate evenimentele semnificative detectate.
    Acelasi tabel apare si in report_tab.
    """
    if not events:
        st.info("No significant change events detected above the threshold.")
        return

    st.markdown("###Significant Change Events")
    st.caption(f"Detected changes in **{change_index}** between {first_date} and {last_date}")

    # Header tabel
    header_cols = st.columns([0.5, 1.5, 1.5, 1.2, 1.2, 1.2, 1.2, 2])
    headers     = ["#", "Severity", "Location", f"{change_index} Before", f"{change_index} After", "Δ Change", "Direction", "Summary"]
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    st.markdown('<hr style="margin:4px 0; border-color:#c5c5d8;">', unsafe_allow_html=True)

    for i, ev in enumerate(events):
        sev_color = SEVERITY_COLOR[ev['severity']]
        direction = "Decrease" if ev['delta'] < 0 else "Increase"
        delta_color = "#c0392b" if ev['delta'] < 0 else "#2d7a4f"

        cols = st.columns([0.5, 1.5, 1.5, 1.2, 1.2, 1.2, 1.2, 2])
        with cols[0]:
            st.markdown(f"<span style='font-weight:700;color:#764ba2;'>{i+1}</span>", unsafe_allow_html=True)
        with cols[1]:
            st.markdown(f"<span style='color:{sev_color};font-weight:600;'>{SEVERITY_LABEL[ev['severity']]}</span>", unsafe_allow_html=True)
        with cols[2]:
            st.caption(f"{ev['lat']:.4f}°N\n{ev['lon']:.4f}°E")
        with cols[3]:
            st.markdown(f"`{ev['value_before']:.4f}`")
        with cols[4]:
            st.markdown(f"`{ev['value_after']:.4f}`")
        with cols[5]:
            st.markdown(f"<span style='color:{delta_color};font-weight:700;'>{ev['delta']:+.4f}</span>", unsafe_allow_html=True)
        with cols[6]:
            st.markdown(direction)
        with cols[7]:
            st.caption(ev['label'])

        if i < len(events) - 1:
            st.markdown('<hr style="margin:2px 0; border-color:#f0f0f5;">', unsafe_allow_html=True)



def render_change_tab(results):
    config = results['config']
    monitor = results['monitor']
    aoi = results['aoi']
    collection = results['collection']
    count = results['count']

    st.subheader("Change Detection & AI Insights")

    if count < 2:
        st.warning("At least 2 images required for change detection.")
        return

    image_list = collection.toList(collection.size())
    dates = collection.aggregate_array('system:time_start').getInfo()

    extra_indices = config.get("custom_indices", [])
    first_image = monitor.calculate_indices(ee.Image(image_list.get(0)), extra_indices=extra_indices)
    last_image = monitor.calculate_indices(ee.Image(image_list.get(count - 1)), extra_indices=extra_indices)

    first_date = datetime.fromtimestamp(dates[0] / 1000).strftime('%Y-%m-%d')
    last_date = datetime.fromtimestamp(dates[-1] / 1000).strftime('%Y-%m-%d')

    st.info(f"Comparing: {first_date} -> {last_date}")

    col1, col2 = st.columns([3, 1])
    with col1:
        change_index = st.selectbox("Select Index for Change Detection", config['indices'])
    with col2:
        threshold = st.slider("Change Threshold", 0.05, 0.5, 0.20, 0.05)

    vis_rgb = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4}

    if change_index in INDICES_CONFIG:
        idx_cfg = INDICES_CONFIG[change_index]
        vis_index = {
            'min': idx_cfg['min'],
            'max': idx_cfg['max'],
            'palette': idx_cfg['palette']
        }
        palette = idx_cfg['palette']

        hex_colors = ['#' + p if not p.startswith('#') else p for p in palette]
    else:
        vis_index = {'min': -1, 'max': 1, 'palette': ['red', 'white', 'green']}
        hex_colors = ['red', 'white', 'green']

    center = [config['center_lat'], config['center_lon']]

    st.markdown("### Before vs After — Index Overlay (Split View)")
    st.caption(f"Left: **{first_date}** | Right: **{last_date}** | Overlay: **{change_index}**")

    try:
        before_rgb_vis = first_image.visualize(**vis_rgb)
        after_rgb_vis  = last_image.visualize(**vis_rgb)
        before_idx_vis = first_image.select(change_index).visualize(**vis_index)
        after_idx_vis  = last_image.select(change_index).visualize(**vis_index)

        vis_blend_params = {'bands': ['vis-red', 'vis-green', 'vis-blue'], 'min': 0, 'max': 255}
        before_blend = before_rgb_vis.multiply(0.55).add(before_idx_vis.multiply(0.45)).toUint8()
        after_blend  = after_rgb_vis.multiply(0.55).add(after_idx_vis.multiply(0.45)).toUint8()

        m_split = geemap.Map(center=center, zoom=14, add_google_map=False)
        m_split.add_basemap('HYBRID')

        left_layer  = geemap.ee_tile_layer(before_blend, vis_blend_params, f'Before {change_index}: {first_date}')
        right_layer = geemap.ee_tile_layer(after_blend,  vis_blend_params, f'After {change_index}: {last_date}')

        m_split.split_map(left_layer=left_layer, right_layer=right_layer)
        m_split.centerObject(aoi, 14)

        if st_folium is not None:
            st_folium(m_split, height=520, width="100%", returned_objects=[])
        else:
            m_split.to_streamlit(height=520)

    except Exception as e:
        st.error(f"Split map error: {e}")
        st.exception(e)

    grad_colors = ', '.join(hex_colors)
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:8px; padding:6px 0 16px 0; font-size:13px;">
        <strong>{change_index} scale:</strong>
        <span style="background:linear-gradient(to right, {grad_colors});
              width:180px; height:14px; display:inline-block; border-radius:3px;
              vertical-align:middle; border:1px solid #555;"></span>
        <span>{vis_index['min']}</span>
        <span style="margin:0 4px;">→</span>
        <span>{vis_index['max']}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Change Detection Map")
    st.caption(f"Click markers for details · Threshold: ±{threshold}")

    with st.spinner("Detecting significant change locations..."):
        events = _sample_change_points(first_image, last_image, aoi, change_index, threshold, n_points=15)

    _render_annotated_map(first_image, last_image, aoi, config, change_index, threshold,
                          first_date, last_date, events)

    try:
        diff = last_image.select(change_index).subtract(first_image.select(change_index))

        decrease_mask = diff.lt(-threshold)   # scadere semnificativa
        increase_mask = diff.gt(threshold)    # crestere semnificativa
        change_mask   = decrease_mask.Or(increase_mask)  # orice schimbare

        r_band = ee.Image(255).multiply(decrease_mask).add(ee.Image(0).multiply(increase_mask))
        g_band = ee.Image(0)
        b_band = ee.Image(0).multiply(decrease_mask).add(ee.Image(255).multiply(increase_mask))

        change_colored = ee.Image.cat([r_band, g_band, b_band]) \
                           .rename(['vis-red', 'vis-green', 'vis-blue']) \
                           .toUint8() \
                           .updateMask(change_mask)

        after_rgb_vis2 = last_image.visualize(**vis_rgb)

        r_final = after_rgb_vis2.select('vis-red').where(
            change_mask,
            after_rgb_vis2.select('vis-red').multiply(0.3)
                .add(change_colored.select('vis-red').multiply(0.7))
        )
        g_final = after_rgb_vis2.select('vis-green').where(
            change_mask,
            after_rgb_vis2.select('vis-green').multiply(0.3)
                .add(change_colored.select('vis-green').multiply(0.7))
        )
        b_final = after_rgb_vis2.select('vis-blue').where(
            change_mask,
            after_rgb_vis2.select('vis-blue').multiply(0.3)
                .add(change_colored.select('vis-blue').multiply(0.7))
        )

        change_overlay = ee.Image.cat([r_final, g_final, b_final]) \
                           .rename(['vis-red', 'vis-green', 'vis-blue']) \
                           .toUint8()

        vis_final = {'bands': ['vis-red', 'vis-green', 'vis-blue'], 'min': 0, 'max': 255}

        m_change = geemap.Map(center=center, zoom=14, add_google_map=False)
        m_change.add_basemap('HYBRID')
        m_change.addLayer(change_overlay, vis_final, f'RGB + {change_index} Changes')

        aoi_style = ee.FeatureCollection(aoi).style(**{
            'color': 'FF0000',
            'fillColor': 'FF000000',
            'width': 2
        })
        m_change.addLayer(aoi_style, {}, 'Area of Interest')
        m_change.centerObject(aoi, 14)
        m_change.add_layer_control()

        if st_folium is not None:
            st_folium(m_change, height=520, width="100%", returned_objects=[])
        else:
            m_change.to_streamlit(height=520)

    except Exception as e:
        st.error(f"Change map error: {e}")
        st.exception(e)

    st.markdown("""
    <div style="display:flex; gap:24px; padding:8px 0 16px 0; font-size:14px; align-items:center;">
        <strong>Legend:</strong>
        <span><span style="display:inline-block;width:16px;height:16px;background:#FF0000;
              border-radius:3px;margin-right:6px;vertical-align:middle;"></span>Decrease (loss)</span>
        <span><span style="display:inline-block;width:16px;height:16px;background:#AAAAAA;
              border:1px solid #999;border-radius:3px;margin-right:6px;vertical-align:middle;"></span>No significant change</span>
        <span><span style="display:inline-block;width:16px;height:16px;background:#0000FF;
              border-radius:3px;margin-right:6px;vertical-align:middle;"></span>Increase (gain)</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    _render_events_table(events, change_index, first_date, last_date)

    st.markdown("### Statistical Comparison")

    before_stats = monitor.calculate_statistics(first_image, aoi, change_index)
    after_stats  = monitor.calculate_statistics(last_image,  aoi, change_index)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"#### Before — {first_date}")
        if before_stats:
            st.metric("Mean",    f"{before_stats.get(f'{change_index}_mean', 0):.4f}")
            st.metric("Std Dev", f"{before_stats.get(f'{change_index}_stdDev', 0):.4f}")
            st.metric("Min",     f"{before_stats.get(f'{change_index}_min', 0):.4f}")
            st.metric("Max",     f"{before_stats.get(f'{change_index}_max', 0):.4f}")

    with c2:
        st.markdown(f"#### After — {last_date}")
        if after_stats:
            mean_before = before_stats.get(f'{change_index}_mean', 0)
            mean_after  = after_stats.get(f'{change_index}_mean', 0)
            mean_change = mean_after - mean_before
            st.metric("Mean",    f"{mean_after:.4f}", delta=f"{mean_change:+.4f}")
            st.metric("Std Dev", f"{after_stats.get(f'{change_index}_stdDev', 0):.4f}")
            st.metric("Min",     f"{after_stats.get(f'{change_index}_min', 0):.4f}")
            st.metric("Max",     f"{after_stats.get(f'{change_index}_max', 0):.4f}")

    st.markdown("### Comparative Trends")

    before_vals = [
        before_stats.get(f'{change_index}_mean', 0),
        before_stats.get(f'{change_index}_stdDev', 0),
        before_stats.get(f'{change_index}_min', 0),
        before_stats.get(f'{change_index}_max', 0),
    ]
    after_vals = [
        after_stats.get(f'{change_index}_mean', 0),
        after_stats.get(f'{change_index}_stdDev', 0),
        after_stats.get(f'{change_index}_min', 0),
        after_stats.get(f'{change_index}_max', 0),
    ]

    fig_change = plot_change_detection(before_vals, after_vals, change_index)
    st.plotly_chart(fig_change, use_container_width=True)

    # -------------------------------------------------------------------------
    # 7. AI Interpretation
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### AI Interpretation")

    s_before = {'mean': before_stats.get(f'{change_index}_mean', 0)}
    s_after  = {'mean': after_stats.get(f'{change_index}_mean', 0)}

    with st.spinner("AI is analyzing the satellite trends..."):
        interpretation = get_ai_interpretation(
            index_name=change_index,
            stats_before=s_before,
            stats_after=s_after,
            context=config['site_name']
        )
        st.info(interpretation)