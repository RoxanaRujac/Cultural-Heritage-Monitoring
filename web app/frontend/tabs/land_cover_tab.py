"""
Land Cover Classification Tab — Heritage Site Monitoring System
Using geemap's optimized Dynamic World functions
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import ee
from datetime import datetime
import geemap.foliumap as geemap
import numpy as np

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None


# Dynamic World Classes
DW_CLASSES = {
    0: {'name': 'Water', 'hex': '419BDF', 'description': 'Open water bodies'},
    1: {'name': 'Trees', 'hex': '397D49', 'description': 'Forest and woody vegetation'},
    2: {'name': 'Grass', 'hex': '88B053', 'description': 'Grassland and herbaceous'},
    3: {'name': 'Cropland', 'hex': '7A87C6', 'description': 'Agricultural crops'},
    4: {'name': 'Built-up', 'hex': 'E49635', 'description': 'Urban structures'},
    5: {'name': 'Bare', 'hex': 'DFC35A', 'description': 'Exposed soil and rock'},
    6: {'name': 'Snow', 'hex': 'C4281B', 'description': 'Snow and ice'},
    7: {'name': 'Clouds', 'hex': 'A59B8F', 'description': 'Cloud cover'},
    8: {'name': 'Flooded', 'hex': 'B39FE1', 'description': 'Flooded vegetation'},
}

DW_PALETTE = [DW_CLASSES[i]['hex'] for i in range(9)]
DW_NAMES = [DW_CLASSES[i]['name'] for i in range(9)]

VIS_PARAMS = {
    "min": 0,
    "max": 8,
    "palette": DW_PALETTE,
}


def render_land_cover_tab(results):
    """
    Land Cover Classification using geemap's optimized Dynamic World functions
    """
    config = results['config']
    aoi = results['aoi']

    st.subheader(f"Land Cover Classification — {config['site_name']}")

    # ─────────────────────────────────────────────────────────────
    # 1. LOAD DYNAMIC WORLD TIMESERIES
    # ─────────────────────────────────────────────────────────────


    with st.spinner("Fetching Dynamic World timeseries..."):
        try:
            start_date = config['start_date'].strftime('%Y-%m-%d')
            end_date = config['end_date'].strftime('%Y-%m-%d')

            images = geemap.dynamic_world_timeseries(
                aoi,
                start_date,
                end_date,
                return_type="class"  # Get classification, not visualization
            )

            count = images.size().getInfo()

            if count == 0:
                st.info("Try expanding the date range or checking the location")
                return


        except Exception as e:
            st.error(f"Error loading data: {e}")
            import traceback
            st.error(traceback.format_exc())
            return

    # ─────────────────────────────────────────────────────────────
    # 2. COMPUTE COMPOSITE (MEDIAN/MODE)
    # ─────────────────────────────────────────────────────────────


    with st.spinner(f"Computing mode composite from {count} images..."):
        try:
            # Mode = most common class per pixel (better than median for classification)
            composite = images.mode()

            st.success(f"✅ Mode composite ready ({count} images medianized)")

        except Exception as e:
            st.error(f"Error processing composite: {e}")
            return

    # ─────────────────────────────────────────────────────────────
    # 3. DISPLAY MAP WITH CLASSIFICATION
    # ─────────────────────────────────────────────────────────────

    st.markdown("### Classification Map")
    st.caption(f"Mode composite from {count} daily Dynamic World classifications")

    try:
        Map = geemap.Map(
            center=[config['center_lat'], config['center_lon']],
            zoom=14,
            add_google_map=False
        )
        Map.add_basemap('HYBRID')

        # Add classification layer
        Map.addLayer(
            composite,
            VIS_PARAMS,
            "Dynamic World Classification",
            opacity=0.8
        )

        # Add AOI boundary
        aoi_style = ee.FeatureCollection(aoi).style(
            color='764ba2',
            fillColor='764ba200',
            width=2
        )
        Map.addLayer(aoi_style, {}, 'Area of Interest')

        # Add legend
        Map.add_legend(
            title="Land Cover Classes",
            labels=DW_NAMES,
            colors=['#' + DW_CLASSES[i]['hex'] for i in range(9)]
        )

        Map.centerObject(aoi, 14)
        Map.add_layer_control()

        if st_folium:
            st_folium(Map, height=500, width="100%", returned_objects=[])
        else:
            Map.to_streamlit(height=500)

    except Exception as e:
        st.error(f"Map error: {e}")

    # ─────────────────────────────────────────────────────────────
    # 4. CALCULATE STATISTICS
    # ─────────────────────────────────────────────────────────────

    st.markdown("### 📊 Land Cover Statistics")

    with st.spinner("Computing pixel statistics..."):
        try:
            # Calculate frequency histogram
            histogram = composite.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=aoi,
                scale=10,
                maxPixels=1e9
            ).getInfo()

            # Parse histogram
            class_counts = histogram.get('classification', {})

            if not class_counts:
                st.error("No classification data extracted")
                return

            # Convert to readable format
            total_pixels = sum(class_counts.values())
            stats_data = []

            for class_id in range(9):
                class_id_str = str(class_id)
                pixels = class_counts.get(class_id_str, 0)
                percentage = (pixels / total_pixels * 100) if total_pixels > 0 else 0
                area_km2 = (pixels * 10 * 10) / 1e6  # 10m resolution

                stats_data.append({
                    'Class': DW_CLASSES[class_id]['name'],
                    'Pixels': int(pixels),
                    'Percentage': percentage,
                    'Area (km²)': area_km2,
                    'Hex': DW_CLASSES[class_id]['hex']
                })

            # Filter out 0-pixel classes
            stats_data = [s for s in stats_data if s['Pixels'] > 0]

            if not stats_data:
                st.error("❌ No land cover detected. Check your coordinates and date range.")
                return

            # Sort by percentage
            stats_data.sort(key=lambda x: x['Percentage'], reverse=True)

        except Exception as e:
            st.error(f"Statistics error: {e}")
            import traceback
            st.error(traceback.format_exc())
            return

    # ── Display Stats ──────────────────────────────────────────
    col1, col2 = st.columns([2, 1])

    with col1:
        # Pie chart
        fig = go.Figure(data=[go.Pie(
            labels=[s['Class'] for s in stats_data],
            values=[s['Percentage'] for s in stats_data],
            marker=dict(colors=['#' + s['Hex'] for s in stats_data]),
            hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>',
            textposition='inside',
            textinfo='label+percent'
        )])

        fig.update_layout(
            title="Land Cover Distribution",
            height=400,
            template='plotly_white'
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Summary")
        st.metric("Total Pixels", f"{total_pixels:,}")
        st.metric("Total Area", f"{(total_pixels * 100) / 1e6:.2f} km²")
        st.metric("Classes Detected", len(stats_data))

        st.markdown("---")
        st.markdown("#### Top Classes")
        for i, stat in enumerate(stats_data[:3]):
            st.write(f"**{i+1}. {stat['Class']}** — {stat['Percentage']:.1f}%")

    # ── Detailed Table ────────────────────────────────────────
    st.markdown("#### Detailed Breakdown")

    df = pd.DataFrame([
        {
            'Class': s['Class'],
            'Percentage': f"{s['Percentage']:.2f}%",
            'Pixels': f"{s['Pixels']:,}",
            'Area (km²)': f"{s['Area (km²)']:.3f}"
        }
        for s in stats_data
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────
    # 5. TIMESERIES COMPARISON
    # ─────────────────────────────────────────────────────────────

    st.markdown("### 📈 Temporal Analysis")
    st.caption(f"Evolution of land cover over {(config['end_date'] - config['start_date']).days} days")

    with st.spinner("Computing temporal trends..."):
        try:
            # Get first and last image
            images_list = images.toList(images.size())
            first_img = ee.Image(images_list.get(0))
            last_img = ee.Image(images_list.get(count - 1))

            # Compute stats for both
            first_stats = first_img.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=aoi,
                scale=10,
                maxPixels=1e9
            ).getInfo()

            last_stats = last_img.reduceRegion(
                reducer=ee.Reducer.frequencyHistogram(),
                geometry=aoi,
                scale=10,
                maxPixels=1e9
            ).getInfo()

            # Build comparison data
            comparison = []
            first_counts = first_stats.get('classification', {})
            last_counts = last_stats.get('classification', {})
            total_first = sum(first_counts.values())
            total_last = sum(last_counts.values())

            for class_id in range(9):
                class_id_str = str(class_id)
                first_pct = (first_counts.get(class_id_str, 0) / total_first * 100) if total_first > 0 else 0
                last_pct = (last_counts.get(class_id_str, 0) / total_last * 100) if total_last > 0 else 0
                change = last_pct - first_pct

                comparison.append({
                    'Class': DW_CLASSES[class_id]['name'],
                    'Start': first_pct,
                    'End': last_pct,
                    'Change': change
                })

            df_comparison = pd.DataFrame(comparison)

            # Bar chart
            fig_temporal = go.Figure()

            fig_temporal.add_trace(go.Bar(
                name='Start',
                x=df_comparison['Class'],
                y=df_comparison['Start'],
                marker_color='#9b6fc5',
                opacity=0.7
            ))

            fig_temporal.add_trace(go.Bar(
                name='End',
                x=df_comparison['Class'],
                y=df_comparison['End'],
                marker_color='#f0c040',
                opacity=0.7
            ))

            fig_temporal.update_layout(
                title=f"Land Cover Change: {start_date} → {end_date}",
                barmode='group',
                xaxis_title='Class',
                yaxis_title='Percentage (%)',
                height=400,
                template='plotly_white'
            )

            st.plotly_chart(fig_temporal, use_container_width=True)

        except Exception as e:
            st.warning(f"Temporal analysis unavailable: {e}")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────
    # 6. LEGEND
    # ─────────────────────────────────────────────────────────────

    with st.expander("📋 Classification Legend", expanded=False):
        cols = st.columns(3)

        for i, class_id in enumerate(range(9)):
            with cols[i % 3]:
                st.markdown(f"""
                <div style="background:#f9f6fd; padding:8px; border-radius:6px; 
                           border-left:4px solid #{DW_CLASSES[class_id]['hex']}; margin:4px 0;">
                    <strong>{DW_CLASSES[class_id]['name']}</strong>
                    <br><small>{DW_CLASSES[class_id]['description']}</small>
                </div>
                """, unsafe_allow_html=True)