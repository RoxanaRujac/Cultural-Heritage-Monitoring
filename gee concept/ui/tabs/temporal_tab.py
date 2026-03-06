import streamlit as st
import pandas as pd
import numpy as np
import ee
from datetime import datetime, timedelta
from utils.db_utils import get_db_connection

def get_cached_temporal_data(site_name, index_name, start_date, end_date):
    """Retrieve existing data from MySQL for the requested time range"""
    conn = get_db_connection()
    query = """
        SELECT analysis_date, value FROM temporal_cache 
        WHERE site_name = %s AND index_name = %s 
        AND analysis_date BETWEEN %s AND %s
        ORDER BY analysis_date ASC
    """
    df = pd.read_sql(query, conn, params=(site_name, index_name, start_date, end_date))
    conn.close()
    return df

def save_temporal_point(site_name, index_name, date_obj, value):
    """Save a new data point to MySQL"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Using INSERT IGNORE to avoid errors if the date-site-index combo already exists
    query = "INSERT IGNORE INTO temporal_cache (site_name, index_name, analysis_date, value) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (site_name, index_name, date_obj, float(value)))
    conn.commit()
    cursor.close()
    conn.close()

def render_temporal_tab(results):
    """Render the temporal analysis tab using incremental logic from DB and GEE"""
    config = results['config']
    monitor = results['monitor']
    aoi = results['aoi']

    st.subheader("Incremental Temporal Analysis")

    # Iterate through each selected index (e.g., NDVI, NDBI)
    for idx_name in config['indices']:
        st.write(f"### {idx_name} Evolution")

        # 1. Fetch data already stored in MySQL
        existing_data = get_cached_temporal_data(
            config['site_name'], idx_name, config['start_date'], config['end_date']
        )

        # 2. Identify available images in Google Earth Engine
        collection = monitor.get_sentinel2_collection(
            aoi, config['start_date'].strftime('%Y-%m-%d'),
            config['end_date'].strftime('%Y-%m-%d'), config['cloud_cover']
        )

        # Get list of all timestamps available in GEE
        all_dates_gee = collection.aggregate_array('system:time_start').getInfo()
        dates_to_process = []

        # Filter: Only process GEE dates that do NOT exist in the database
        existing_dates_set = set(existing_data['analysis_date'].astype(str))

        for ts in all_dates_gee:
            d_str = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d')
            if d_str not in existing_dates_set:
                dates_to_process.append(ts)

        # 3. Process only the "gaps" (missing dates)
        if dates_to_process:
            progress_bar = st.progress(0)

            for i, ts in enumerate(dates_to_process):
                # Filter collection for the exact specific date
                curr_date = datetime.fromtimestamp(ts/1000)
                img = ee.Image(collection.filterDate(
                    curr_date.strftime('%Y-%m-%d'),
                    (curr_date + timedelta(days=1)).strftime('%Y-%m-%d')
                ).first())

                # Calculate indices and extract statistics
                extra_indices = config.get("custom_indices", [])
                img_with_idx = monitor.calculate_indices(img, extra_indices=extra_indices)
                stats = monitor.calculate_statistics(img_with_idx, aoi, idx_name)
                val = stats.get(f'{idx_name}_mean')

                # Save the new calculation to the database
                if val is not None:
                    save_temporal_point(config['site_name'], idx_name, curr_date.date(), val)

                progress_bar.progress((i + 1) / len(dates_to_process))

            progress_bar.empty()

        # 4. Reload everything from DB (now including the new dates) for the chart
        final_df = get_cached_temporal_data(
            config['site_name'], idx_name, config['start_date'], config['end_date']
        )

        if not final_df.empty:
            # Prepare data for the existing plot_time_series utility
            # Format: {index_name: {date_string: value}}
            chart_data = {idx_name: dict(zip(final_df['analysis_date'].astype(str), final_df['value']))}

            from utils.visualization import plot_time_series
            fig = plot_time_series(chart_data, f"{idx_name} - {config['site_name']}", "Value")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No temporal data available for {idx_name}.")