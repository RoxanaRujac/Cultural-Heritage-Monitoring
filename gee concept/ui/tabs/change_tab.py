import streamlit as st
import geemap.foliumap as geemap
import ee
from datetime import datetime
from utils.visualization import plot_change_detection
from utils.ai_utils import get_ai_interpretation
from config.settings import INDICES_CONFIG

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None


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

    # 1. Pregatirea imaginilor
    image_list = collection.toList(collection.size())
    dates = collection.aggregate_array('system:time_start').getInfo()

    extra_indices = config.get("custom_indices", [])
    first_image = monitor.calculate_indices(ee.Image(image_list.get(0)), extra_indices=extra_indices)
    last_image = monitor.calculate_indices(ee.Image(image_list.get(count - 1)), extra_indices=extra_indices)

    first_date = datetime.fromtimestamp(dates[0] / 1000).strftime('%Y-%m-%d')
    last_date = datetime.fromtimestamp(dates[-1] / 1000).strftime('%Y-%m-%d')

    st.info(f"Comparing: {first_date} -> {last_date}")

    # 2. Selectie Indice si Threshold
    col1, col2 = st.columns([3, 1])
    with col1:
        change_index = st.selectbox("Select Index for Change Detection", config['indices'])
    with col2:
        threshold = st.slider("Change Threshold", 0.05, 0.5, 0.20, 0.05)

    # Parametri vizualizare RGB
    vis_rgb = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4}

    # Parametri vizualizare pentru indicele selectat din config
    if change_index in INDICES_CONFIG:
        idx_cfg = INDICES_CONFIG[change_index]
        vis_index = {
            'min': idx_cfg['min'],
            'max': idx_cfg['max'],
            'palette': idx_cfg['palette']
        }
        palette = idx_cfg['palette']
        # Normalizeaza culorile (adauga # daca lipseste)
        hex_colors = ['#' + p if not p.startswith('#') else p for p in palette]
    else:
        vis_index = {'min': -1, 'max': 1, 'palette': ['red', 'white', 'green']}
        hex_colors = ['red', 'white', 'green']

    center = [config['center_lat'], config['center_lon']]

    # -------------------------------------------------------------------------
    # 3. SPLIT MAP — Before vs After cu indicele ca overlay blend pe RGB
    # Left = first_date cu indicele, Right = last_date cu indicele
    # -------------------------------------------------------------------------
    st.markdown("### Before vs After — Index Overlay (Split View)")
    st.caption(f"Left: **{first_date}** | Right: **{last_date}** | Overlay: **{change_index}**")

    try:
        # Vizualizam RGB si indicele ca imagini separate in EE
        before_rgb_vis = first_image.visualize(**vis_rgb)
        after_rgb_vis  = last_image.visualize(**vis_rgb)
        before_idx_vis = first_image.select(change_index).visualize(**vis_index)
        after_idx_vis  = last_image.select(change_index).visualize(**vis_index)

        # Blend: 55% RGB + 45% index overlay pentru a pastra contextul vizual
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

    # Legenda scala indice pentru split map
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

    # -------------------------------------------------------------------------
    # 4. CHANGE DETECTION MAP
    # RGB base (last image) + overlay colorat: rosu=scadere, albastru=crestere
    # Zonele fara schimbare semnificativa raman ca RGB curat
    # -------------------------------------------------------------------------
    st.markdown("### Change Detection Map")
    st.caption(f"RGB base ({last_date}) + **{change_index}** change overlay | threshold: ±{threshold}")

    try:
        diff = last_image.select(change_index).subtract(first_image.select(change_index))

        # Masti pentru cele 3 zone
        decrease_mask = diff.lt(-threshold)   # scadere semnificativa
        increase_mask = diff.gt(threshold)    # crestere semnificativa
        change_mask   = decrease_mask.Or(increase_mask)  # orice schimbare

        # Imagine colorata pentru change zones
        # Decrease = rosu (255, 0, 0), Increase = albastru (0, 0, 255)
        r_band = ee.Image(255).multiply(decrease_mask).add(ee.Image(0).multiply(increase_mask))
        g_band = ee.Image(0)
        b_band = ee.Image(0).multiply(decrease_mask).add(ee.Image(255).multiply(increase_mask))

        change_colored = ee.Image.cat([r_band, g_band, b_band]) \
                           .rename(['vis-red', 'vis-green', 'vis-blue']) \
                           .toUint8() \
                           .updateMask(change_mask)

        # Overlay final: unde exista change -> blend RGB 30% + culoare 70%
        #                unde nu exista change -> RGB curat 100%
        after_rgb_vis2 = last_image.visualize(**vis_rgb)

        # .where() pe fiecare canal
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

        # Contur AOI
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

    # -------------------------------------------------------------------------
    # 5. Statistici
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 6. Chart Comparativ
    # -------------------------------------------------------------------------
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