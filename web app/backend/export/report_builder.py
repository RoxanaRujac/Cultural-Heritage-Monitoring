"""
Responsible for: assembling export data (JSON dict, plain text, CSV bytes).
The result is always a plain Python object ready for st.download_button.
"""

import json
import pandas as pd
from datetime import datetime
from io import BytesIO
from playwright.sync_api import sync_playwright
from fpdf import FPDF
import os


class ReportBuilder:
    """
    Builds exportable export artefacts from analysis results.

    Usage:
        builder = ReportBuilder(config, stats, count)
        json_str  = builder.as_json()
        txt_str   = builder.as_text()
        csv_bytes = builder.as_csv()
    """

    def __init__(self, config: dict, stats: dict, count: int):
        """
        Args:
            config: Analysis config dict (site_name, center_lat, …).
            stats:  Dict of {index_name: {metric_key: value}}.
            count:  Number of satellite images analysed.
        """
        self._config = config
        self._stats  = stats
        self._count  = count
        self._now    = datetime.now()

    # ── Public methods ───────────────────────────────────────────────────────

    def as_json(self) -> str:
        """Return a JSON string of the full structured export."""
        return json.dumps(self._build_dict(), indent=2)

    def as_text(self) -> str:
        """Return a human-readable plain-text export."""
        cfg = self._config
        sep = '=' * 100
        thin = '-' * 100
        duration = (cfg['end_date'] - cfg['start_date']).days
        area = 3.14159 * (cfg['buffer_km'] ** 2)

        lines = [
            sep,
            'HERITAGE SITE MONITORING REPORT',
            sep,
            '',
            'SITE INFORMATION',
            thin,
            f"Site Name:      {cfg['site_name']}",
            f"Location:       {cfg['center_lat']:.6f}°N, {cfg['center_lon']:.6f}°E",
            f"Radius:         {cfg['buffer_km']} km",
            f"Total Area:     {area:.2f} km²",
            '',
            'ANALYSIS PERIOD',
            thin,
            f"Start Date:     {cfg['start_date'].strftime('%B %d, %Y')}",
            f"End Date:       {cfg['end_date'].strftime('%B %d, %Y')}",
            f"Duration:       {duration} days",
            '',
            'DATA PROCESSING',
            thin,
            f"Images:         {self._count} Sentinel-2 scenes",
            f"Platform:       Google Earth Engine",
            f"Resolution:     10 metres",
            f"Cloud Cover:    ≤ {cfg['cloud_cover']}%",
            f"Indices:        {', '.join(cfg['indices'])}",
        ]

        if self._stats:
            lines += ['', 'SPECTRAL INDICES RESULTS', thin]
            for idx in cfg['indices']:
                s = self._stats.get(idx, {})
                lines += [
                    f"\n{idx}:",
                    f"  Median:      {s.get(f'{idx}_median', 0):.6f}",
                    f"  Std Dev:     {s.get(f'{idx}_stdDev', 0):.6f}",
                    f"  Min:         {s.get(f'{idx}_min', 0):.6f}",
                    f"  Max:         {s.get(f'{idx}_max', 0):.6f}",
                ]

        lines += [
            '',
            'REPORT GENERATION',
            thin,
            f"Generated:      {self._now.strftime('%B %d, %Y at %H:%M:%S')}",
            f"System:         Heritage Site Monitoring System v1.0",
            '',
            sep,
            'END OF REPORT',
            sep,
        ]
        return '\n'.join(lines)

    def as_csv(self) -> bytes:
        """Return CSV bytes of per-index statistics (for st.download_button)."""
        rows = []
        for idx in self._config['indices']:
            s = self._stats.get(idx, {})
            rows.append({
                'Index':         idx,
                'Median':        s.get(f'{idx}_median',   0),
                'Std_Deviation': s.get(f'{idx}_stdDev', 0),
                'Minimum':       s.get(f'{idx}_min',    0),
                'Maximum':       s.get(f'{idx}_max',    0),
            })
        buf = BytesIO()
        pd.DataFrame(rows).to_csv(buf, index=False)
        return buf.getvalue()


    def capture_map_image(html_path, output_image_path):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            page.goto(f"file://{os.path.abspath(html_path)}")

            page.wait_for_selector(".folium-map")

            page.screenshot(path=output_image_path, full_page=True)
            browser.close()

    def as_pdf(self, maps_html: list = None) -> bytes:
        """
        Generate a PDF report as bytes. Optionally include map screenshots (as HTML strings) in the report.
        """
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", 20)
        pdf.set_text_color(118, 75, 162)
        pdf.cell(0, 15, "Pdf Report", ln=True, align="C")

        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"Sit: {self._config['site_name']}", ln=True)

        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, (
            f"Location: {self._config['center_lat']:.6f}, {self._config['center_lon']:.6f}\n"
            f"Period: {self._config['start_date']} - {self._config['end_date']}\n"
            f"Analyzed images: {self._count} scene Sentinel-2"
        ))

        if image_paths:
            for img_path in image_paths:
                if os.path.exists(img_path):
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(0, 10, "Vizualizare Satelitară (Schimbări)", ln=True)
                    # Adăugăm imaginea (w=190 ocupă aproape toată lățimea A4)
                    pdf.image(img_path, x=10, y=30, w=190)
        return pdf.output()

    def filename_base(self) -> str:
        """Return a safe filename prefix (no extension)."""
        site = self._config['site_name'].replace(' ', '_')
        ts   = self._now.strftime('%Y%m%d_%H%M%S')
        return f"{site}_report_{ts}"

    # ── Private ──────────────────────────────────────────────────────────────

    def _build_dict(self) -> dict:
        cfg = self._config
        duration = (cfg['end_date'] - cfg['start_date']).days
        area     = round(3.14159 * (cfg['buffer_km'] ** 2), 2)

        data = {
            'metadata': {
                'report_title':    f"Heritage Site Monitoring Report — {cfg['site_name']}",
                'generation_date': self._now.strftime('%Y-%m-%d %H:%M:%S'),
                'version':         '1.0',
            },
            'site_information': {
                'name':        cfg['site_name'],
                'coordinates': {'latitude': cfg['center_lat'], 'longitude': cfg['center_lon']},
                'area':        {'radius_km': cfg['buffer_km'], 'area_km2': area},
            },
            'analysis_parameters': {
                'period': {
                    'start':         str(cfg['start_date']),
                    'end':           str(cfg['end_date']),
                    'duration_days': duration,
                },
                'data_quality': {
                    'max_cloud_cover_percent':    cfg['cloud_cover'],
                    'spatial_resolution_meters':  10,
                    'temporal_resolution_days':   5,
                },
                'spectral_indices': cfg['indices'],
            },
            'results': {
                'total_images_analyzed': self._count,
                'satellite_platform':    'Sentinel-2 MSI',
                'processing_platform':   'Google Earth Engine',
            },
        }

        if self._stats:
            data['spectral_analysis'] = {
                idx: {
                    'median':        self._stats[idx].get(f'{idx}_median',   0),
                    'std_deviation': self._stats[idx].get(f'{idx}_stdDev', 0),
                    'minimum':       self._stats[idx].get(f'{idx}_min',    0),
                    'maximum':       self._stats[idx].get(f'{idx}_max',    0),
                }
                for idx in self._config['indices']
                if idx in self._stats
            }

        return data