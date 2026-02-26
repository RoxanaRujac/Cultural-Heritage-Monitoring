"""
Comprehensive Report Tab for Heritage Site Monitoring System
"""

import streamlit as st
import json
from datetime import datetime
import pandas as pd


def render_report_tab(results):
    """
    Render comprehensive report tab

    Args:
        results: Dictionary with analysis results
    """
    config = results['config']
    monitor = results['monitor']
    aoi = results['aoi']
    collection = results['collection']
    count = results['count']

    st.subheader(" Comprehensive Monitoring Report")

    # Executive Summary Section
    st.markdown("###  Executive Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 10px; color: white;'>
            <h4 style='margin:0; color: white;'> Site Information</h4>
            <p style='margin: 10px 0 0 0; font-size: 18px;'><strong>{config['site_name']}</strong></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 20px; border-radius: 10px; color: white;'>
            <h4 style='margin:0; color: white;'> Images Analyzed</h4>
            <p style='margin: 10px 0 0 0; font-size: 18px;'><strong>{count} Sentinel-2 scenes</strong></p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        days = (config['end_date'] - config['start_date']).days
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                    padding: 20px; border-radius: 10px; color: white;'>
            <h4 style='margin:0; color: white;'> Time Span</h4>
            <p style='margin: 10px 0 0 0; font-size: 18px;'><strong>{days} days</strong></p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Detailed Site Information
    st.markdown("###  Site Location & Parameters")

    site_info_col1, site_info_col2 = st.columns(2)

    with site_info_col1:
        st.markdown("""
        <div style='background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea;'>
            <h4 style='color: #2c3e50; margin-top: 0;'> Geographic Information</h4>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        - **Latitude:** {config['center_lat']:.6f}°
        - **Longitude:** {config['center_lon']:.6f}°
        - **Analysis Radius:** {config['buffer_km']} km
        - **Total Area:** ~{3.14159 * (config['buffer_km'] ** 2):.2f} km²
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    with site_info_col2:
        st.markdown("""
        <div style='background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #764ba2;'>
            <h4 style='color: #2c3e50; margin-top: 0;'> Data Acquisition Parameters</h4>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        - **Start Date:** {config['start_date'].strftime('%B %d, %Y')}
        - **End Date:** {config['end_date'].strftime('%B %d, %Y')}
        - **Max Cloud Cover:** {config['cloud_cover']}%
        - **Satellite:** Sentinel-2 MSI (10m resolution)
        - **Spectral Indices:** {', '.join(config['indices'])}
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Spectral Indices Analysis
    if count > 0:
        st.markdown("###  Spectral Indices Analysis Results")

        # Calculate current statistics
        median_image = collection.median()
        extra_indices = st.session_state.get("custom_indices", []) or config.get("custom_indices", [])
        indices_image = monitor.calculate_indices(median_image, extra_indices=extra_indices)

        indices_stats = {}
        for idx in config['indices']:
            try:
                stats = monitor.calculate_statistics(indices_image, aoi, idx)
                indices_stats[idx] = stats
            except Exception:
                indices_stats[idx] = {}

        # Display as expandable cards
        for idx in config['indices']:
            with st.expander(f"**{idx}** - Detailed Analysis", expanded=True):
                stats = indices_stats.get(idx, {})

                metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

                with metric_col1:
                    mean_val = stats.get(f'{idx}_mean', 0)
                    st.metric("Mean Value", f"{mean_val:.4f}")

                with metric_col2:
                    std_val = stats.get(f'{idx}_stdDev', 0)
                    st.metric("Std Deviation", f"{std_val:.4f}")

                with metric_col3:
                    min_val = stats.get(f'{idx}_min', 0)
                    st.metric("Minimum", f"{min_val:.4f}")

                with metric_col4:
                    max_val = stats.get(f'{idx}_max', 0)
                    st.metric("Maximum", f"{max_val:.4f}")

                # Interpretation
                st.markdown("** Interpretation:**")

                if idx == 'NDVI':
                    if mean_val < 0.2:
                        st.warning(" Low vegetation cover detected. This may indicate bare soil, urban areas, or vegetation stress.")
                    elif mean_val < 0.4:
                        st.info(" Moderate vegetation cover. Mix of vegetated and non-vegetated areas.")
                    else:
                        st.success(" Healthy vegetation cover detected, which may provide natural protection for the site.")

                elif idx == 'NDBI':
                    if mean_val > 0.3:
                        st.warning(" Significant built-up area detected. Monitor urban encroachment near heritage site.")
                    elif mean_val > 0:
                        st.info(" Some built-up structures present in the analysis area.")
                    else:
                        st.success(" Predominantly natural landscape with minimal urban development.")

                elif idx == 'NDMI':
                    if mean_val < -0.2:
                        st.warning(" Low moisture content. Increased erosion risk due to dry conditions.")
                    elif mean_val < 0.2:
                        st.info(" Moderate moisture levels. Normal conditions.")
                    else:
                        st.success(" High moisture content. Adequate water availability, but monitor for excess water accumulation.")

                elif idx == 'NDWI':
                    if mean_val > 0.3:
                        st.info(" Significant water presence detected. Monitor for flooding risk.")
                    elif mean_val > 0:
                        st.info(" Some water bodies present in the area.")
                    else:
                        st.success(" No significant water accumulation detected.")

                elif idx == 'BSI':
                    if mean_val > 0.3:
                        st.warning(" High bare soil exposure. Increased vulnerability to erosion.")
                    elif mean_val > 0:
                        st.info(" Moderate soil exposure present.")
                    else:
                        st.success(" Minimal bare soil, good vegetation or surface cover.")
                else:
                    st.info(f"**{idx}** mean value: {mean_val:.4f}. Interpret in context of site-specific conditions.")

    st.markdown("---")

    # Data Quality Assessment
    st.markdown("###  Data Quality Assessment")

    quality_col1, quality_col2 = st.columns(2)

    with quality_col1:
        st.markdown("""
        <div style='background: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 4px solid #4caf50;'>
            <h4 style='color: #2e7d32; margin-top: 0;'> Data Strengths</h4>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        - **Image Count:** {count} scenes provide {'excellent' if count >= 20 else 'good' if count >= 10 else 'adequate'} temporal coverage
        - **Resolution:** 10-meter spatial resolution for detailed analysis
        - **Multi-spectral:** 13 spectral bands from visible to SWIR
        - **Cloud Filtering:** Images limited to {config['cloud_cover']}% cloud cover
        - **Revisit Time:** 5-day satellite revisit cycle
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    with quality_col2:
        st.markdown("""
        <div style='background: #fff3e0; padding: 15px; border-radius: 8px; border-left: 4px solid #ff9800;'>
            <h4 style='color: #e65100; margin-top: 0;'> Limitations</h4>
        """, unsafe_allow_html=True)

        st.markdown("""
        - **Cloud Cover:** Some residual clouds may affect data quality
        - **Temporal Gaps:** Weather conditions may create gaps in coverage
        - **Resolution Limit:** 10m resolution may not capture fine details
        - **Satellite View:** Only surface features visible from above
        - **Validation Needed:** Ground-truth data required for confirmation
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Methodology section
    with st.expander(" Methodology & Scientific Background", expanded=False):
        method_col1, method_col2 = st.columns(2)

        with method_col1:
            st.markdown("""
            ####  Data Sources
            
            **Sentinel-2 Mission:**
            - European Space Agency's Earth observation program
            - Twin satellites (Sentinel-2A & 2B) launched 2015/2017
            - Multi-Spectral Instrument (MSI) with 13 spectral bands
            - Spatial resolution: 10m (visible/NIR), 20m (red edge/SWIR), 60m (atmospheric)
            - Swath width: 290 km
            - Global coverage every 5 days
            
            **Processing Platform:**
            - Google Earth Engine cloud computing platform
            - Petabyte-scale satellite imagery archive
            - Advanced geospatial analysis capabilities
            - Real-time processing and visualization
            """)

        with method_col2:
            st.markdown("""
            ####  Spectral Indices Formulas
            
            **NDVI** - Normalized Difference Vegetation Index
            ```
            (NIR - Red) / (NIR + Red)
            (B8 - B4) / (B8 + B4)
            ```
            
            **NDBI** - Normalized Difference Built-up Index
            ```
            (SWIR - NIR) / (SWIR + NIR)
            (B11 - B8) / (B11 + B8)
            ```
            
            **NDMI** - Normalized Difference Moisture Index
            ```
            (NIR - SWIR) / (NIR + SWIR)
            (B8 - B11) / (B8 + B11)
            ```
            
            **NDWI** - Normalized Difference Water Index
            ```
            (Green - NIR) / (Green + NIR)
            (B3 - B8) / (B3 + B8)
            ```
            
            **BSI** - Bare Soil Index
            ```
            ((SWIR + Red) - (NIR + Blue)) / ((SWIR + Red) + (NIR + Blue))
            ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))
            ```
            """)

        st.markdown("---")

        st.markdown("""
        ####  Scientific References
        
        This system implements methodologies from peer-reviewed research in heritage site monitoring:
        
        1. **Moise et al.** - "Archaeological site detection using remote sensing"
           - Multi-temporal analysis techniques for site identification
           - Spectral signature analysis of archaeological features
        
        2. **Monna et al.** - "Deep learning for heritage monitoring"
           - Machine learning approaches for automated feature detection
           - Integration of multi-source remote sensing data
        
        3. **Agapiou et al.** - "Remote sensing for cultural heritage management"
           - Best practices for satellite-based heritage monitoring
           - Change detection methodologies for conservation
        
        4. **Kopec et al.** - "Multi-temporal analysis of heritage sites"
           - Long-term monitoring strategies
           - Temporal pattern analysis techniques
        
        These studies demonstrate that satellite remote sensing provides:
        - Cost-effective monitoring over large areas
        - Regular temporal coverage for change detection
        - Non-invasive assessment of site conditions
        - Early warning system for threats to heritage sites
        """)

    st.markdown("---")

    # Export section
    st.markdown("###  Export Report & Data")

    # Prepare comprehensive report data
    report_data = {
        'metadata': {
            'report_title': f'Heritage Site Monitoring Report - {config["site_name"]}',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analyst': 'Heritage Site Monitoring System',
            'version': '1.0'
        },
        'site_information': {
            'name': config['site_name'],
            'coordinates': {
                'latitude': config['center_lat'],
                'longitude': config['center_lon']
            },
            'analysis_area': {
                'radius_km': config['buffer_km'],
                'area_km2': round(3.14159 * (config['buffer_km'] ** 2), 2)
            }
        },
        'analysis_parameters': {
            'period': {
                'start': str(config['start_date']),
                'end': str(config['end_date']),
                'duration_days': (config['end_date'] - config['start_date']).days
            },
            'data_quality': {
                'max_cloud_cover_percent': config['cloud_cover'],
                'spatial_resolution_meters': 10,
                'temporal_resolution_days': 5
            },
            'spectral_indices': config['indices']
        },
        'results': {
            'total_images_analyzed': count,
            'satellite_platform': 'Sentinel-2 MSI',
            'processing_platform': 'Google Earth Engine'
        }
    }

    if count > 0 and indices_stats:
        report_data['spectral_analysis'] = {}
        for idx in config['indices']:
            stats = indices_stats.get(idx, {})
            report_data['spectral_analysis'][idx] = {
                'mean': stats.get(f'{idx}_mean', 0),
                'std_deviation': stats.get(f'{idx}_stdDev', 0),
                'minimum': stats.get(f'{idx}_min', 0),
                'maximum': stats.get(f'{idx}_max', 0)
            }

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            label=" Download JSON Report",
            data=json.dumps(report_data, indent=2),
            file_name=f"{config['site_name'].replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            help="Machine-readable format for further analysis"
        )

    with col2:
        # Create detailed text report
        text_report = f"""
{'='*100}
HERITAGE SITE MONITORING REPORT
{'='*100}

SITE INFORMATION
{'-'*100}
Site Name: {config['site_name']}
Location: {config['center_lat']:.6f}°N, {config['center_lon']:.6f}°E
Analysis Radius: {config['buffer_km']} km
Total Area: {3.14159 * (config['buffer_km'] ** 2):.2f} km²

ANALYSIS PERIOD
{'-'*100}
Start Date: {config['start_date'].strftime('%B %d, %Y')}
End Date: {config['end_date'].strftime('%B %d, %Y')}
Duration: {(config['end_date'] - config['start_date']).days} days

DATA PROCESSING
{'-'*100}
Total Images Analyzed: {count} Sentinel-2 scenes
Satellite Platform: Sentinel-2 MSI (Multi-Spectral Instrument)
Processing Platform: Google Earth Engine
Spatial Resolution: 10 meters
Maximum Cloud Cover: {config['cloud_cover']}%
Spectral Indices: {', '.join(config['indices'])}

"""

        if count > 0 and indices_stats:
            text_report += f"""
SPECTRAL INDICES RESULTS
{'-'*100}
"""
            for idx in config['indices']:
                stats = indices_stats.get(idx, {})
                text_report += f"""
{idx} - Analysis:
  Mean:           {stats.get(f'{idx}_mean', 0):.6f}
  Std Deviation:  {stats.get(f'{idx}_stdDev', 0):.6f}
  Minimum:        {stats.get(f'{idx}_min', 0):.6f}
  Maximum:        {stats.get(f'{idx}_max', 0):.6f}

"""

        text_report += f"""
DATA QUALITY ASSESSMENT
{'-'*100}
✓ Image Count: {count} scenes provide {'excellent' if count >= 20 else 'good' if count >= 10 else 'adequate'} temporal coverage
✓ Resolution: 10-meter spatial resolution for detailed analysis
✓ Multi-spectral: 13 spectral bands from visible to SWIR wavelengths
✓ Cloud Filtering: All images filtered to {config['cloud_cover']}% maximum cloud cover
✓ Revisit Time: 5-day satellite revisit cycle ensures regular monitoring

 Limitations:
  - Some residual clouds may affect local data quality
  - Weather conditions may create temporal gaps in coverage
  - 10m resolution may not capture fine architectural details
  - Surface-only observations; subsurface features not visible
  - Ground-truth validation recommended for final interpretation

METHODOLOGY
{'-'*100}
This analysis employs satellite remote sensing techniques based on peer-reviewed research
in cultural heritage monitoring (Moise et al., Monna et al., Agapiou et al., Kopec et al.).

Spectral indices are calculated from Sentinel-2 multi-spectral bands to assess:
- Vegetation health and coverage (NDVI)
- Urban development and built-up areas (NDBI)
- Soil and vegetation moisture (NDMI)
- Water body presence and extent (NDWI)
- Bare soil exposure and erosion risk (BSI)

These indicators provide insights into environmental conditions affecting heritage site
preservation, including vegetation encroachment, urban pressure, erosion risk, water
threats, and landscape changes.

REPORT GENERATION
{'-'*100}
Report Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}
System Version: Heritage Site Monitoring System v1.0
Processing Engine: Google Earth Engine
Data Source: European Space Agency Sentinel-2 Mission

{'='*100}
END OF REPORT
{'='*100}
"""

        st.download_button(
            label=" Download Text Report",
            data=text_report,
            file_name=f"{config['site_name'].replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            help="Human-readable detailed report"
        )

    with col3:
        # Create CSV of statistics
        if count > 0 and indices_stats:
            csv_data = []
            for idx in config['indices']:
                stats = indices_stats.get(idx, {})
                csv_data.append({
                    'Index': idx,
                    'Mean': stats.get(f'{idx}_mean', 0),
                    'Std_Deviation': stats.get(f'{idx}_stdDev', 0),
                    'Minimum': stats.get(f'{idx}_min', 0),
                    'Maximum': stats.get(f'{idx}_max', 0)
                })

            df = pd.DataFrame(csv_data)
            csv = df.to_csv(index=False)

            st.download_button(
                label=" Download Statistics CSV",
                data=csv,
                file_name=f"{config['site_name'].replace(' ', '_')}_statistics_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                help="Spreadsheet format for data analysis"
            )

