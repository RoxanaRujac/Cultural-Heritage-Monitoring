"""
Utilități pentru export date, hărți și generare rapoarte
Pentru Heritage Site Monitoring System
"""

import ee
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import base64
from io import BytesIO
import plotly.graph_objects as go
import plotly.express as px


class DataExporter:
    """Export date GEE în diverse formate"""

    @staticmethod
    def export_image_to_drive(image: ee.Image,
                              geometry: ee.Geometry,
                              description: str,
                              folder: str = 'GEE_Exports',
                              scale: int = 10) -> ee.batch.Task:
        """
        Export imagine GEE către Google Drive

        Args:
            image: Imagine de exportat
            geometry: Zona de interes
            description: Nume fișier
            folder: Folder Drive
            scale: Rezoluție în metri

        Returns:
            Task pentru monitoring
        """

        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            folder=folder,
            region=geometry,
            scale=scale,
            crs='EPSG:4326',
            maxPixels=1e13,
            fileFormat='GeoTIFF'
        )

        task.start()
        return task

    @staticmethod
    def export_table_to_drive(features: ee.FeatureCollection,
                              description: str,
                              folder: str = 'GEE_Exports',
                              file_format: str = 'CSV') -> ee.batch.Task:
        """Export tabel/statistici către Drive"""

        task = ee.batch.Export.table.toDrive(
            collection=features,
            description=description,
            folder=folder,
            fileFormat=file_format
        )

        task.start()
        return task

    @staticmethod
    def export_to_cloud_storage(image: ee.Image,
                                bucket: str,
                                file_prefix: str,
                                geometry: ee.Geometry,
                                scale: int = 10) -> ee.batch.Task:
        """Export către Google Cloud Storage"""

        task = ee.batch.Export.image.toCloudStorage(
            image=image,
            description=file_prefix,
            bucket=bucket,
            fileNamePrefix=file_prefix,
            region=geometry,
            scale=scale,
            maxPixels=1e13
        )

        task.start()
        return task

    @staticmethod
    def download_statistics_as_csv(stats_dict: Dict,
                                   filename: str = 'statistics.csv') -> bytes:
        """
        Convertește dicționar statistici în CSV pentru download

        Returns:
            Bytes CSV pentru download în Streamlit
        """

        # Flatten nested dict
        flat_data = []
        for key, values in stats_dict.items():
            if isinstance(values, dict):
                for sub_key, value in values.items():
                    flat_data.append({
                        'Index': key,
                        'Metric': sub_key,
                        'Value': value
                    })
            else:
                flat_data.append({
                    'Index': key,
                    'Metric': 'value',
                    'Value': values
                })

        df = pd.DataFrame(flat_data)

        # Convert to CSV bytes
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_bytes = csv_buffer.getvalue()

        return csv_bytes

    @staticmethod
    def create_geojson_from_geometry(geometry: ee.Geometry,
                                     properties: Optional[Dict] = None) -> str:
        """Convertește geometrie EE în GeoJSON string"""

        geojson = geometry.getInfo()

        if properties:
            geojson['properties'] = properties

        return json.dumps(geojson, indent=2)


class ReportGenerator:
    """Generare rapoarte comprehensive HTML și PDF"""

    def __init__(self, site_name: str, coordinates: Tuple[float, float]):
        self.site_name = site_name
        self.coordinates = coordinates
        self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def generate_html_report(self,
                             statistics: Dict,
                             time_series_data: Dict,
                             change_detection: Optional[Dict] = None,
                             images: Optional[Dict] = None) -> str:
        """
        Generează raport HTML complet cu grafice interactive

        Args:
            statistics: Statistici indici
            time_series_data: Date serie temporală
            change_detection: Rezultate detectare schimbări
            images: Dict cu imagini base64 encoded

        Returns:
            HTML string
        """

        html = f"""
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raport Monitorizare - {self.site_name}</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        h2 {{
            color: #34495e;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-top: 40px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 30px;
        }}
        .header-info {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 40px;
            font-size: 1.1em;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 10px;
            color: white;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            transition: transform 0.3s;
        }}
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
        }}
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .stats-table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }}
        .stats-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .stats-table tr:hover {{
            background: #f8f9fa;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        .alert {{
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 5px solid;
        }}
        .alert-info {{
            background: #e3f2fd;
            border-color: #2196f3;
            color: #1976d2;
        }}
        .alert-warning {{
            background: #fff3e0;
            border-color: #ff9800;
            color: #f57c00;
        }}
        .alert-success {{
            background: #e8f5e9;
            border-color: #4caf50;
            color: #388e3c;
        }}
        .image-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .image-card {{
            border: 2px solid #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }}
        .image-card img {{
            width: 100%;
            height: auto;
        }}
        .image-label {{
            padding: 15px;
            background: #34495e;
            color: white;
            text-align: center;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            color: #7f8c8d;
        }}
        .recommendation {{
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #667eea;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏛️ Raport Monitorizare Sit Istoric</h1>
        <div class="header-info">
            <p><strong>{self.site_name}</strong></p>
            <p>📍 Coordonate: {self.coordinates[0]:.4f}°N, {self.coordinates[1]:.4f}°E</p>
            <p>📅 Data generare: {self.timestamp}</p>
        </div>

        <div class="alert alert-info">
            <strong>ℹ️ Informație:</strong> Acest raport a fost generat automat folosind date satelitare Sentinel-2 
            procesate prin Google Earth Engine. Metodologia se bazează pe studii științifice recente în 
            monitorizarea patrimoniului cultural.
        </div>
"""

        # Add statistics section
        if statistics:
            html += self._generate_statistics_section(statistics)

        # Add time series charts
        if time_series_data:
            html += self._generate_time_series_section(time_series_data)

        # Add change detection section
        if change_detection:
            html += self._generate_change_detection_section(change_detection)

        # Add images
        if images:
            html += self._generate_images_section(images)

        # Add recommendations
        html += self._generate_recommendations_section(statistics, change_detection)

        # Footer
        html += """
        <div class="footer">
            <p>🛰️ Powered by Google Earth Engine & Sentinel-2</p>
            <p>📚 Metodologii bazate pe: Moise et al., Monna et al., Agapiou et al., Kopec et al.</p>
            <p><em>Heritage Site Monitoring System v1.0</em></p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def _generate_statistics_section(self, statistics: Dict) -> str:
        """Generează secțiune statistici"""

        html = """
        <h2>📊 Statistici Indici Spectrali</h2>
        <div class="metric-grid">
"""

        for index, stats in statistics.items():
            mean_val = stats.get(f'{index}_mean', 0)
            html += f"""
            <div class="metric-card">
                <div class="metric-label">{index}</div>
                <div class="metric-value">{mean_val:.3f}</div>
            </div>
"""

        html += "</div>"

        # Detailed table
        html += """
        <table class="stats-table">
            <thead>
                <tr>
                    <th>Indice</th>
                    <th>Medie</th>
                    <th>Std Dev</th>
                    <th>Min</th>
                    <th>Max</th>
                </tr>
            </thead>
            <tbody>
"""

        for index, stats in statistics.items():
            html += f"""
                <tr>
                    <td><strong>{index}</strong></td>
                    <td>{stats.get(f'{index}_mean', 0):.4f}</td>
                    <td>{stats.get(f'{index}_stdDev', 0):.4f}</td>
                    <td>{stats.get(f'{index}_min', 0):.4f}</td>
                    <td>{stats.get(f'{index}_max', 0):.4f}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>
"""

        return html

    def _generate_time_series_section(self, time_series_data: Dict) -> str:
        """Generează secțiune time series cu Plotly"""

        html = """
        <h2>📈 Analiză Serie Temporală</h2>
        <div class="chart-container">
            <div id="timeSeriesChart"></div>
        </div>

        <script>
"""

        # Prepare data for Plotly
        traces = []
        for index, data_points in time_series_data.items():
            dates = list(data_points.keys())
            values = list(data_points.values())

            traces.append(f"""
            {{
                x: {json.dumps(dates)},
                y: {json.dumps(values)},
                mode: 'lines+markers',
                name: '{index}',
                line: {{width: 3}},
                marker: {{size: 8}}
            }}
""")

        html += f"""
            var data = [{','.join(traces)}];

            var layout = {{
                title: 'Evoluție Indici Spectrali',
                xaxis: {{title: 'Dată'}},
                yaxis: {{title: 'Valoare Indice'}},
                hovermode: 'x unified',
                template: 'plotly_white',
                height: 500
            }};

            Plotly.newPlot('timeSeriesChart', data, layout);
        </script>
"""

        return html

    def _generate_change_detection_section(self, change_detection: Dict) -> str:
        """Generează secțiune detectare schimbări"""

        html = """
        <h2>🔍 Detectare Schimbări</h2>
"""

        if change_detection.get('significant', False):
            html += """
        <div class="alert alert-warning">
            <strong>⚠️ Atenție:</strong> Au fost detectate schimbări semnificative în zona analizată!
        </div>
"""
        else:
            html += """
        <div class="alert alert-success">
            <strong>✅ Rezultat:</strong> Nu au fost detectate schimbări semnificative în perioada analizată.
        </div>
"""

        # Change statistics
        html += """
        <table class="stats-table">
            <thead>
                <tr>
                    <th>Parametru</th>
                    <th>Valoare Before</th>
                    <th>Valoare After</th>
                    <th>Diferență</th>
                </tr>
            </thead>
            <tbody>
"""

        before = change_detection.get('before_stats', {})
        after = change_detection.get('after_stats', {})

        for key in before.keys():
            before_val = before.get(key, 0)
            after_val = after.get(key, 0)
            diff = after_val - before_val

            html += f"""
                <tr>
                    <td><strong>{key}</strong></td>
                    <td>{before_val:.4f}</td>
                    <td>{after_val:.4f}</td>
                    <td style="color: {'red' if diff < 0 else 'green'};">{diff:+.4f}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>
"""

        return html

    def _generate_images_section(self, images: Dict) -> str:
        """Generează galerie imagini"""

        html = """
        <h2>🗺️ Hărți Satelitare</h2>
        <div class="image-gallery">
"""

        for label, img_data in images.items():
            html += f"""
            <div class="image-card">
                <img src="data:image/png;base64,{img_data}" alt="{label}">
                <div class="image-label">{label}</div>
            </div>
"""

        html += "</div>"

        return html

    def _generate_recommendations_section(self,
                                          statistics: Dict,
                                          change_detection: Optional[Dict]) -> str:
        """Generează secțiune recomandări"""

        html = """
        <h2>💡 Recomandări și Acțiuni</h2>
"""

        recommendations = []

        # Based on NDVI
        if statistics:
            for index, stats in statistics.items():
                mean_val = stats.get(f'{index}_mean', 0)

                if index == 'NDVI':
                    if mean_val < 0.2:
                        recommendations.append(
                            "⚠️ Vegetație scăzută detectată - evaluare risc eroziune"
                        )
                    elif mean_val > 0.6:
                        recommendations.append(
                            "🌿 Vegetație abundentă - planificare întreținere regulată"
                        )

                elif index == 'NDBI':
                    if mean_val > 0.3:
                        recommendations.append(
                            "🏗️ Zonă urbană densă - monitorizare impactul construcții"
                        )

                elif index == 'NDMI':
                    if mean_val < 0:
                        recommendations.append(
                            "💧 Umiditate sol scăzută - atenție la risc degradare"
                        )

        # Based on change detection
        if change_detection and change_detection.get('significant'):
            recommendations.append(
                "🔍 Schimbări semnificative detectate - investigație in-situ recomandată"
            )

        # General recommendations
        recommendations.extend([
            "📅 Continuare monitorizare lunară pentru tracking long-term",
            "📸 Colectare date UAV pentru validare înaltă rezoluție",
            "📋 Documentare fotografică periodică pentru arhivă",
            "👥 Consultare experți conservare pentru interpretare detaliată"
        ])

        for rec in recommendations:
            html += f"""
        <div class="recommendation">
            {rec}
        </div>
"""

        return html

    def save_to_file(self, html_content: str, filename: str):
        """Salvează raportul HTML în fișier"""

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)


class VisualizationExporter:
    """Export vizualizări și grafice"""

    @staticmethod
    def create_comparison_plot(before_data: Dict,
                               after_data: Dict,
                               index_name: str) -> go.Figure:
        """Creează grafic comparativ before/after"""

        categories = list(before_data.keys())
        before_values = list(before_data.values())
        after_values = list(after_data.values())

        fig = go.Figure(data=[
            go.Bar(name='Before', x=categories, y=before_values,
                   marker_color='lightblue'),
            go.Bar(name='After', x=categories, y=after_values,
                   marker_color='coral')
        ])

        fig.update_layout(
            title=f'Comparație {index_name}: Before vs After',
            barmode='group',
            template='plotly_white',
            height=500,
            font=dict(size=12)
        )

        return fig

    @staticmethod
    def create_multi_index_plot(data_dict: Dict,
                                title: str = 'Evoluție Indici') -> go.Figure:
        """Creează grafic cu multiple serii temporale"""

        fig = go.Figure()

        colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b']

        for i, (index, values) in enumerate(data_dict.items()):
            dates = list(values.keys())
            vals = list(values.values())

            fig.add_trace(go.Scatter(
                x=dates,
                y=vals,
                mode='lines+markers',
                name=index,
                line=dict(width=3, color=colors[i % len(colors)]),
                marker=dict(size=8)
            ))

        fig.update_layout(
            title=title,
            xaxis_title='Dată',
            yaxis_title='Valoare Indice',
            hovermode='x unified',
            template='plotly_white',
            height=500,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig

    @staticmethod
    def export_figure_as_html(fig: go.Figure, filename: str):
        """Export figura Plotly ca HTML standalone"""
        fig.write_html(filename)

    @staticmethod
    def export_figure_as_image(fig: go.Figure,
                               filename: str,
                               format: str = 'png'):
        """Export figura ca imagine"""
        fig.write_image(filename, format=format, width=1200, height=800)


# Utility functions
def create_download_link(content: bytes,
                         filename: str,
                         link_text: str) -> str:
    """Creează link download pentru Streamlit"""

    b64 = base64.b64encode(content).decode()
    return f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'


def batch_export_images(image_collection: ee.ImageCollection,
                        geometry: ee.Geometry,
                        indices: List[str],
                        folder: str = 'Heritage_Exports') -> List[ee.batch.Task]:
    """Export batch pentru toate imaginile dintr-o colecție"""

    tasks = []
    image_list = image_collection.toList(image_collection.size())
    size = image_collection.size().getInfo()

    for i in range(size):
        img = ee.Image(image_list.get(i))
        date = datetime.fromtimestamp(
            img.get('system:time_start').getInfo() / 1000
        ).strftime('%Y%m%d')

        for index in indices:
            description = f"{index}_{date}"

            task = ee.batch.Export.image.toDrive(
                image=img.select(index),
                description=description,
                folder=folder,
                region=geometry,
                scale=10,
                maxPixels=1e13
            )

            task.start()
            tasks.append(task)

    return tasks