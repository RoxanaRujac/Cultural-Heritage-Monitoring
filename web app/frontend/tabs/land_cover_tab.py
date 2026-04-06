"""
Land Cover Classification Tab — Heritage Site Monitoring System
Using geemap's Dynamic World timeseries (fix: uses 'label' band, not 'classification')
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import ee
import geemap.foliumap as geemap

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None


# ── Dynamic World class definitions ─────────────────────────────────────────
DW_CLASSES = {
    0: {'name': 'Water',           'hex': '419BDF', 'description': 'Open water bodies'},
    1: {'name': 'Trees',           'hex': '397D49', 'description': 'Forest and woody vegetation'},
    2: {'name': 'Grass',          'hex': '88B053', 'description': 'Grassland and herbaceous'},
    3: {'name': 'Flooded vegetation',     'hex': '7A87C6', 'description': 'Flooded vegetation'},
    4: {'name': 'Crops',           'hex': 'E49635', 'description': 'Agricultural crops'},
    5: {'name': 'Shrub & scrub',   'hex': 'DFC35A', 'description': 'Shrub and scrub'},
    6: {'name': 'Built',           'hex': 'C4281B', 'description': 'Urban structures'},
    7: {'name': 'Bare',            'hex': 'A59B8F', 'description': 'Exposed soil and rock'},
    8: {'name': 'Snow & ice',      'hex': 'B39FE1', 'description': 'Snow and ice'},
}

DW_PALETTE = [DW_CLASSES[i]['hex'] for i in range(9)]
DW_NAMES   = [DW_CLASSES[i]['name'] for i in range(9)]

VIS_PARAMS = {
    'min':     0,
    'max':     8,
    'palette': DW_PALETTE,
}


def render_land_cover_tab(results: dict) -> None:
    """
    Land Cover Classification using geemap's Dynamic World timeseries.

    Key fix: dynamic_world_timeseries(return_type='class') returns images
    whose classification band is named 'label', not 'classification'.
    We cast to Int32 before the histogram so values are clean integers 0-8.
    """
    config = results['config']
    aoi    = results['aoi']

    st.subheader(f"Land Cover Classification — {config['site_name']}")

    start_date = config['start_date'].strftime('%Y-%m-%d')
    end_date   = config['end_date'].strftime('%Y-%m-%d')

    # ── 1. Load Dynamic World timeseries ────────────────────────────────────
    with st.spinner('Fetching Dynamic World timeseries…'):
        try:
            dw_col = (
                ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
                .filterBounds(aoi)
                .filterDate(start_date, end_date)
            )
            count = dw_col.size().getInfo()
        except Exception as exc:
            st.error(f'Error loading Dynamic World data: {exc}')
            return

    if count == 0:
        st.warning('No Dynamic World images found. Try expanding the date range.')
        return

    st.info(f'Found **{count}** Dynamic World images for this period.')

  # ── 2. Compute mode composite ─────────────────────────────────────────────
    with st.spinner(f'Computing mode composite from {count} images…'):
        try:
            label_col = dw_col.select('label')
            composite = label_col.reduce(ee.Reducer.mode()).rename('label').toInt32()
        except Exception as exc:
            st.error(f'Error computing composite: {exc}')
            return

    # ── 3. Map ───────────────────────────────────────────────────────────────
    st.markdown('### Classification Map')
    st.caption(f'Mode composite · {count} images · {start_date} → {end_date}')

    try:
        Map = geemap.Map(
            center=[config['center_lat'], config['center_lon']],
            zoom=14,
            add_google_map=False,
        )
        Map.add_basemap('HYBRID')
        Map.addLayer(composite, VIS_PARAMS, 'Dynamic World Classification', opacity=0.8)

        aoi_style = ee.FeatureCollection(aoi).style(
            color='764ba2', fillColor='764ba200', width=2
        )
        Map.addLayer(aoi_style, {}, 'Area of Interest')

        legend_cols = st.columns(3)
        for i in range(9):
            with legend_cols[i % 3]:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
                    f'<div style="width:16px;height:16px;border-radius:3px;flex-shrink:0;'
                    f'background:#{DW_CLASSES[i]["hex"]};border:1px solid #ccc;"></div>'
                    f'<span style="font-size:13px;color:#ffffff;">{DW_CLASSES[i]["name"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        Map.centerObject(aoi, 14)
        Map.add_layer_control()

        if st_folium:
            st_folium(Map, height=500, width='100%', returned_objects=[])
        else:
            Map.to_streamlit(height=500)

    except Exception as exc:
        st.error(f'Map error: {exc}')

    # ── 4. Statistics ────────────────────────────────────────────────────────
    st.markdown('### Land Cover Statistics')

    with st.spinner('Computing pixel statistics…'):
        try:
            histogram = composite.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=aoi,
                scale=10,
                maxPixels=1e9,
            ).getInfo()

            # The band is named 'label' (from Dynamic World), not 'classification'
            raw_counts = histogram.get('label', {})

            if not raw_counts:
                st.error(
                    'No pixel counts returned. '
                    'The histogram band was not "label" — raw result: '
                    f'{list(histogram.keys())}'
                )
                return

            total_pixels = sum(raw_counts.values())
            stats_data   = []

            for class_id in range(9):
                # Keys may be ints or strings depending on GEE version
                pixels = raw_counts.get(class_id, raw_counts.get(str(class_id), 0))
                pct    = (pixels / total_pixels * 100) if total_pixels > 0 else 0
                area   = (pixels * 10 * 10) / 1e6   # 10 m resolution → km²

                stats_data.append({
                    'Class':      DW_CLASSES[class_id]['name'],
                    'Pixels':     int(pixels),
                    'Percentage': pct,
                    'Area (km²)': area,
                    'Hex':        DW_CLASSES[class_id]['hex'],
                })

            # Keep only classes that have pixels
            stats_data = [s for s in stats_data if s['Pixels'] > 0]

            if not stats_data:
                st.error('No land cover detected — check coordinates and date range.')
                return

            stats_data.sort(key=lambda x: x['Percentage'], reverse=True)

        except Exception as exc:
            st.error(f'Statistics error: {exc}')
            import traceback
            st.code(traceback.format_exc())
            return

    # ── Display statistics ───────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure(data=[go.Pie(
            labels=[s['Class']      for s in stats_data],
            values=[s['Percentage'] for s in stats_data],
            marker=dict(colors=['#' + s['Hex'] for s in stats_data]),
            hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>',
            textposition='inside',
            textinfo='label+percent',
        )])
        fig.update_layout(
            title='Land Cover Distribution',
            height=400,
            template='plotly_white',
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('#### Summary')
        st.metric('Total Pixels', f'{total_pixels:,}')
        st.metric('Total Area',   f'{(total_pixels * 100) / 1e6:.2f} km²')
        st.metric('Classes Detected', len(stats_data))
        st.markdown('---')

    # Detailed table
    st.markdown('#### Detailed Breakdown')
    df = pd.DataFrame([
        {
            'Class':       s['Class'],
            'Percentage':  f"{s['Percentage']:.2f}%",
            'Pixels':      f"{s['Pixels']:,}",
            'Area (km²)':  f"{s['Area (km²)']:.3f}",
        }
        for s in stats_data
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown('---')

    # ── 5. Temporal comparison (first vs last image) ─────────────────────────
    st.markdown('### Temporal Analysis')
    st.caption(
        f"Evolution of land cover over "
        f"{(config['end_date'] - config['start_date']).days} days"
    )

    with st.spinner('Computing temporal comparison…'):
        try:
            images_list = dw_col.select('label').toList(dw_col.size())
            first_img = ee.Image(images_list.get(0)).toInt32()
            last_img = ee.Image(images_list.get(count - 1)).toInt32()

            def get_class_percentages(img: ee.Image) -> dict:
                hist = img.reduceRegion(
                    reducer=ee.Reducer.frequencyHistogram(),
                    geometry=aoi,
                    scale=10,
                    maxPixels=1e9,
                ).getInfo()
                counts = hist.get('label', {})
                total  = sum(counts.values()) if counts else 1
                return {
                    class_id: (counts.get(class_id, counts.get(str(class_id), 0)) / total * 100)
                    for class_id in range(9)
                }

            first_pcts = get_class_percentages(first_img)
            last_pcts  = get_class_percentages(last_img)

            comparison = [
                {
                    'Class':  DW_CLASSES[i]['name'],
                    'Start':  first_pcts[i],
                    'End':    last_pcts[i],
                    'Change': last_pcts[i] - first_pcts[i],
                }
                for i in range(9)
            ]

            df_cmp = pd.DataFrame(comparison)

            fig_t = go.Figure()
            fig_t.add_trace(go.Bar(
                name='Start',
                x=df_cmp['Class'], y=df_cmp['Start'],
                marker_color='#9b6fc5', opacity=0.8,
            ))
            fig_t.add_trace(go.Bar(
                name='End',
                x=df_cmp['Class'], y=df_cmp['End'],
                marker_color='#f0c040', opacity=0.8,
            ))
            fig_t.update_layout(
                title=f'Land Cover Change: {start_date} → {end_date}',
                barmode='group',
                xaxis_title='Class',
                yaxis_title='Percentage (%)',
                height=400,
                template='plotly_white',
            )
            st.plotly_chart(fig_t, use_container_width=True)

        except Exception as exc:
            st.warning(f'Temporal analysis unavailable: {exc}')

    st.markdown('---')

    # ── 6. Legend ────────────────────────────────────────────────────────────
    with st.expander('Classification Legend', expanded=False):
        cols = st.columns(3)
        for i in range(9):
            with cols[i % 3]:
                st.markdown(
                    f'<div style="background:#f9f6fd;padding:8px;border-radius:6px;'
                    f'border-left:4px solid #{DW_CLASSES[i]["hex"]};margin:4px 0;">'
                    f'<strong style="color:#4a2d6b;">{DW_CLASSES[i]["name"]}</strong>'
                    f'<br><small style="color:#764ba2;">{DW_CLASSES[i]["description"]}</small></div>',
                    unsafe_allow_html=True,
                )