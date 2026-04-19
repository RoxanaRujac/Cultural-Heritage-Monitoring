"""
Responsible for: assembling export data (JSON dict, plain text, CSV bytes, PDF bytes).
"""

import json
import urllib.request
import pandas as pd
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image as RLImage,
)

_PURPLE       = colors.HexColor('#764ba2')
_PURPLE_DARK  = colors.HexColor('#4a2d6b')
_PURPLE_LIGHT = colors.HexColor('#9b6fc5')
_YELLOW       = colors.HexColor('#f0c040')
_DARK         = colors.HexColor('#1a1a2e')
_GREY_900     = colors.HexColor('#2c2c3e')
_GREY_700     = colors.HexColor('#4a4a6a')
_GREY_300     = colors.HexColor('#c5c5d8')
_INFO_BG      = colors.HexColor('#f3edf9')
_WHITE        = colors.white
_SUCCESS_BG   = colors.HexColor('#eaf5ef')
_SUCCESS_GRN  = colors.HexColor('#2d7a4f')
_WARN_RED     = colors.HexColor('#c0392b')
_WARN_BG      = colors.HexColor('#fde8e8')

W, H = A4


class ReportBuilder:
    """
    Usage:
        builder = ReportBuilder(config, stats, count)

        # Simple (no maps):
        pdf = builder.as_pdf(ai_texts={'NDVI': '...'})

        # With real GEE map thumbnails:
        pdf = builder.as_pdf(
            ai_texts   = {'NDVI': '...'},
            collection = ee_collection,
            aoi        = ee_geometry,
        )
    """

    def __init__(self, config: dict, stats: dict, count: int):
        self._config = config
        self._stats  = stats
        self._count  = count
        self._now    = datetime.now()

    # ── Public API ─────────────────────────────────────────────────────────────

    def as_json(self) -> str:
        return json.dumps(self._build_dict(), indent=2)

    def as_text(self) -> str:
        cfg  = self._config
        sep  = '=' * 100
        thin = '-' * 100
        dur  = (cfg['end_date'] - cfg['start_date']).days
        area = 3.14159 * cfg['buffer_km'] ** 2
        lines = [
            sep, 'HERITAGE SITE MONITORING REPORT', sep, '',
            'SITE INFORMATION', thin,
            f"Site Name:      {cfg['site_name']}",
            f"Location:       {cfg['center_lat']:.6f}N, {cfg['center_lon']:.6f}E",
            f"Radius:         {cfg['buffer_km']} km",
            f"Total Area:     {area:.2f} km2", '',
            'ANALYSIS PERIOD', thin,
            f"Start Date:     {cfg['start_date'].strftime('%B %d, %Y')}",
            f"End Date:       {cfg['end_date'].strftime('%B %d, %Y')}",
            f"Duration:       {dur} days", '',
            'DATA PROCESSING', thin,
            f"Images:         {self._count} Sentinel-2 scenes",
            f"Platform:       Google Earth Engine",
            f"Resolution:     10 metres",
            f"Cloud Cover:    <= {cfg['cloud_cover']}%",
            f"Indices:        {', '.join(cfg['indices'])}",
        ]
        if self._stats:
            lines += ['', 'SPECTRAL INDICES RESULTS', thin]
            for idx in cfg['indices']:
                s = self._stats.get(idx, {})
                lines += [f"\n{idx}:",
                          f"  Median:  {s.get(f'{idx}_median', 0):.6f}",
                          f"  Std Dev: {s.get(f'{idx}_stdDev', 0):.6f}",
                          f"  Min:     {s.get(f'{idx}_min', 0):.6f}",
                          f"  Max:     {s.get(f'{idx}_max', 0):.6f}"]
        lines += ['', 'GENERATED', thin,
                  f"Date: {self._now.strftime('%B %d, %Y at %H:%M:%S')}",
                  '', sep, 'END OF REPORT', sep]
        return '\n'.join(lines)

    def as_csv(self) -> bytes:
        rows = []
        for idx in self._config['indices']:
            s = self._stats.get(idx, {})
            rows.append({'Index': idx,
                         'Median':        s.get(f'{idx}_median',   0),
                         'Std_Deviation': s.get(f'{idx}_stdDev', 0),
                         'Minimum':       s.get(f'{idx}_min',    0),
                         'Maximum':       s.get(f'{idx}_max',    0)})
        buf = BytesIO()
        pd.DataFrame(rows).to_csv(buf, index=False)
        return buf.getvalue()

    def as_pdf(self, ai_texts: dict | None = None,
               collection=None, aoi=None) -> bytes:
        """
        Args:
            ai_texts:   {index_name: interpretation_string}
            collection: ee.ImageCollection  (optional — enables real map images)
            aoi:        ee.Geometry         (required when collection is given)
        """
        map_images = {}
        if collection is not None and aoi is not None:
            map_images = self._fetch_gee_thumbnails(collection, aoi)

        return _PDFRenderer(
            config=self._config, stats=self._stats,
            count=self._count, now=self._now,
            ai_texts=ai_texts or {}, map_images=map_images,
        ).build()

    def filename_base(self) -> str:
        site = self._config['site_name'].replace(' ', '_')
        return f"{site}_report_{self._now.strftime('%Y%m%d_%H%M%S')}"

    # ── GEE thumbnail fetcher ──────────────────────────────────────────────────

    def _fetch_gee_thumbnails(self, collection, aoi) -> dict:
        """
        Call ee.Image.getThumbURL() for RGB + every selected index.
        Returns {label: BytesIO} with the PNG bytes ready to embed.
        """
        from backend.gee.index_calculator import IndexCalculator
        from config.indices_config import INDICES_CONFIG

        calc    = IndexCalculator()
        extra   = self._config.get('custom_indices', [])
        median  = collection.median()
        indexed = calc.compute(median, extra_indices=extra)

        base_params = {'region': aoi, 'dimensions': 600, 'format': 'png'}
        images = {}

        # RGB natural colour
        try:
            url = median.visualize(
                bands=['B4', 'B3', 'B2'], min=0, max=3000, gamma=1.4
            ).getThumbURL(base_params)
            buf = self._download(url)
            if buf:
                images['Natural Color (RGB)'] = buf
        except Exception:
            pass

        # Each spectral index
        for idx in self._config['indices']:
            try:
                if idx in INDICES_CONFIG:
                    idc = INDICES_CONFIG[idx]
                    vis = indexed.select(idx).visualize(
                        min=idc['min'], max=idc['max'], palette=idc['palette'])
                else:
                    vis = indexed.select(idx).visualize(min=-1, max=1)
                url = vis.getThumbURL(base_params)
                buf = self._download(url)
                if buf:
                    images[idx] = buf
            except Exception:
                pass

        return images

    @staticmethod
    def _download(url: str) -> BytesIO | None:
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
            buf = BytesIO(data)
            buf.seek(0)
            return buf
        except Exception:
            return None

    def _build_dict(self) -> dict:
        cfg  = self._config
        dur  = (cfg['end_date'] - cfg['start_date']).days
        area = round(3.14159 * cfg['buffer_km'] ** 2, 2)
        d = {
            'metadata': {'report_title': f"Heritage Site Monitoring Report — {cfg['site_name']}",
                         'generation_date': self._now.strftime('%Y-%m-%d %H:%M:%S'),
                         'version': '1.0'},
            'site_information': {'name': cfg['site_name'],
                                 'coordinates': {'latitude': cfg['center_lat'],
                                                 'longitude': cfg['center_lon']},
                                 'area': {'radius_km': cfg['buffer_km'], 'area_km2': area}},
            'analysis_parameters': {
                'period': {'start': str(cfg['start_date']), 'end': str(cfg['end_date']),
                           'duration_days': dur},
                'data_quality': {'max_cloud_cover_percent': cfg['cloud_cover'],
                                 'spatial_resolution_meters': 10},
                'spectral_indices': cfg['indices']},
            'results': {'total_images_analyzed': self._count,
                        'satellite_platform': 'Sentinel-2 MSI',
                        'processing_platform': 'Google Earth Engine'},
        }
        if self._stats:
            d['spectral_analysis'] = {
                idx: {'median':        self._stats[idx].get(f'{idx}_median',   0),
                      'std_deviation': self._stats[idx].get(f'{idx}_stdDev', 0),
                      'minimum':       self._stats[idx].get(f'{idx}_min',    0),
                      'maximum':       self._stats[idx].get(f'{idx}_max',    0)}
                for idx in cfg['indices'] if idx in self._stats}
        return d


# ─────────────────────────────────────────────────────────────────────────────
class _PDFRenderer:
    """Builds the ReportLab document — no decorative cover page."""

    def __init__(self, config, stats, count, now, ai_texts, map_images):
        self.cfg   = config
        self.stats = stats
        self.count = count
        self.now   = now
        self.ai    = ai_texts
        self.imgs  = map_images   # {label: BytesIO}
        self.S     = self._styles()

    def build(self) -> bytes:
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=28*mm, bottomMargin=24*mm,
            title=f"Heritage Report — {self.cfg['site_name']}",
            author='Heritage Site Monitoring System',
        )
        story = (
            self._title_section()       # simple title on first page
            + self._exec_summary()
            + [PageBreak()]
            + self._site_params()
            + self._rgb_overview()
            + self._indices()
            + [PageBreak()]
            + self._quality()
            + self._methodology()
            + self._sign_off()
        )
        # Same header/footer on ALL pages (including first)
        doc.build(story, onFirstPage=self._bg_inner, onLaterPages=self._bg_inner)
        return buf.getvalue()

    # ── Page background / header / footer (shared by every page) ────────────

    def _bg_inner(self, c, doc):
        c.saveState()
        # Header bar
        c.setFillColor(_PURPLE_DARK)
        c.rect(0, H - 15*mm, W, 15*mm, fill=1, stroke=0)
        c.setFillColor(_YELLOW)
        c.rect(0, H - 16.5*mm, W, 1.5*mm, fill=1, stroke=0)
        c.setFillColor(_WHITE)
        c.setFont('Helvetica-Bold', 8)
        c.drawString(20*mm, H - 10*mm, 'HERITAGE SITE MONITORING SYSTEM')
        c.setFont('Helvetica', 8)
        c.drawRightString(W - 20*mm, H - 10*mm, self.cfg['site_name'])
        # Footer bar
        c.setFillColor(_GREY_900)
        c.rect(0, 0, W, 13*mm, fill=1, stroke=0)
        c.setFillColor(_YELLOW)
        c.rect(0, 13*mm, W, 1*mm, fill=1, stroke=0)
        c.setFillColor(_WHITE)
        c.setFont('Helvetica', 7.5)
        c.drawString(
            20*mm, 4.5*mm,
            f'Generated {self.now.strftime("%d %B %Y")}  |  '
            f'Sentinel-2 MSI  |  Google Earth Engine',
        )
        c.setFont('Helvetica-Bold', 8)
        c.drawRightString(W - 20*mm, 4.5*mm, f'Page {doc.page}')
        c.restoreState()

    # ── Simple title section (replaces decorative cover) ────────────────────

    def _title_section(self):
        S   = self.S
        cfg = self.cfg
        dur  = (cfg['end_date'] - cfg['start_date']).days
        area = round(3.14159 * cfg['buffer_km'] ** 2, 2)
        return [
            Spacer(1, 6*mm),
            Paragraph('Heritage Site Monitoring Report', S['report_title']),
            Spacer(1, 3*mm),
            Paragraph(cfg['site_name'], S['site_title']),
            Spacer(1, 2*mm),
            Paragraph(
                f"Lat {cfg['center_lat']:.5f}N  ·  Lon {cfg['center_lon']:.5f}E  ·  "
                f"Radius {cfg['buffer_km']} km  ·  "
                f"{cfg['start_date'].strftime('%d %b %Y')} – "
                f"{cfg['end_date'].strftime('%d %b %Y')}  ·  "
                f"{self.count} images  ·  {dur} days",
                S['subtitle'],
            ),
            Spacer(1, 4*mm),
            self._rule(),
            Spacer(1, 4*mm),
        ]

    # ── Executive summary ────────────────────────────────────────────────────

    def _exec_summary(self):
        S   = self.S
        cfg = self.cfg
        dur  = (cfg['end_date'] - cfg['start_date']).days
        area = round(3.14159 * cfg['buffer_km'] ** 2, 2)
        return [
            Paragraph('Executive Summary', S['h1']),
            self._rule(),
            Spacer(1, 4*mm),
            Table([[
                self._kpi('Site',    cfg['site_name'],       '#764ba2'),
                self._kpi('Images',  f"{self.count} scenes", '#4a2d6b'),
                self._kpi('Period',  f'{dur} days',           '#2d7a4f'),
                self._kpi('Area',    f'{area:.1f} km2',        '#c0392b'),
            ]], colWidths=[(W - 40*mm) / 4] * 4,
                style=TableStyle([
                    ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                    ('TOPPADDING',    (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
                ])),
            Spacer(1, 5*mm),
            Paragraph(
                f"This report presents the results of a comprehensive satellite-based monitoring "
                f"analysis for <b>{cfg['site_name']}</b>. The analysis covers {dur} days "
                f"({cfg['start_date'].strftime('%d %B %Y')} to "
                f"{cfg['end_date'].strftime('%d %B %Y')}), using {self.count} cloud-filtered "
                f"Sentinel-2 MSI images (max {cfg['cloud_cover']}% cloud cover). "
                f"{len(cfg['indices'])} spectral indices were computed at 10-metre resolution "
                f"within a {cfg['buffer_km']}-km radius ({area:.1f} km2) centred at "
                f"{cfg['center_lat']:.5f}N, {cfg['center_lon']:.5f}E.",
                S['body'],
            ),
        ]

    # ── Site parameters ──────────────────────────────────────────────────────

    def _site_params(self):
        S   = self.S
        cfg = self.cfg
        rows = [
            ['Parameter', 'Value'],
            ['Site Name',       cfg['site_name']],
            ['Latitude',        f"{cfg['center_lat']:.6f} N"],
            ['Longitude',       f"{cfg['center_lon']:.6f} E"],
            ['Analysis Radius', f"{cfg['buffer_km']} km"],
            ['Area Covered',    f"{3.14159 * cfg['buffer_km']**2:.2f} km2"],
            ['Start Date',      cfg['start_date'].strftime('%d %B %Y')],
            ['End Date',        cfg['end_date'].strftime('%d %B %Y')],
            ['Duration',        f"{(cfg['end_date'] - cfg['start_date']).days} days"],
            ['Satellite',       'Sentinel-2 MSI (ESA Copernicus)'],
            ['Max Cloud Cover', f"{cfg['cloud_cover']}%"],
            ['Images Used',     f"{self.count} scenes"],
            ['Platform',        'Google Earth Engine'],
            ['Indices',         ', '.join(cfg['indices'])],
        ]
        cw = W - 40*mm
        tbl = Table(
            rows, colWidths=[cw * 0.38, cw * 0.62],
            style=TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0),  _PURPLE_DARK),
                ('TEXTCOLOR',     (0, 0), (-1, 0),  _YELLOW),
                ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0), (-1, -1), 8.5),
                ('ROWBACKGROUNDS',(0, 1), (-1, -1), [_WHITE, _INFO_BG]),
                ('TEXTCOLOR',     (0, 1), (0, -1),  _GREY_700),
                ('FONTNAME',      (0, 1), (0, -1),  'Helvetica-Bold'),
                ('GRID',          (0, 0), (-1, -1), 0.4, _GREY_300),
                ('TOPPADDING',    (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ]),
        )
        return [
            Paragraph('Site Location & Analysis Parameters', S['h1']),
            self._rule(), Spacer(1, 4*mm), tbl, Spacer(1, 6*mm),
        ]

    # ── RGB overview map ────────────────────────────────────────────────────

    def _rgb_overview(self):
        buf = self.imgs.get('Natural Color (RGB)')
        if not buf:
            return []
        S = self.S
        buf.seek(0)
        img = RLImage(buf, width=W - 40*mm, height=95*mm)
        img.hAlign = 'CENTER'
        return [
            Paragraph('Satellite Overview — Natural Color (RGB)', S['h1']),
            self._rule(), Spacer(1, 2*mm),
            Paragraph(
                f"Sentinel-2 B4/B3/B2 median composite  ·  {self.count} scenes  ·  "
                f"{self.cfg['start_date'].strftime('%d %b %Y')} – "
                f"{self.cfg['end_date'].strftime('%d %b %Y')}",
                S['map_cap'],
            ),
            Spacer(1, 2*mm),
            img,
            Spacer(1, 5*mm),
        ]

    # ── Indices section (with map per index) ────────────────────────────────

    def _indices(self):
        S   = self.S
        cfg = self.cfg
        out = [
            Paragraph('Spectral Indices Analysis', S['h1']),
            self._rule(), Spacer(1, 4*mm),
        ]

        from config.indices_config import INDICES_CONFIG

        for idx in cfg['indices']:
            idc      = INDICES_CONFIG.get(idx, {})
            s        = self.stats.get(idx, {})
            median_v = s.get(f'{idx}_median')
            std_v    = s.get(f'{idx}_stdDev')
            min_v    = s.get(f'{idx}_min')
            max_v    = s.get(f'{idx}_max')
            ai_text  = self.ai.get(idx, '')

            def fmt(v): return f'{v:.4f}' if v is not None else '-'

            block = []

            # ── Index header banner ──────────────────────────────────────────
            block.append(Table(
                [[Paragraph(
                    f"<font color='#ffffff'><b>{idx}</b></font>  "
                    f"<font color='#c5c5d8'>— {idc.get('name', '')}</font>",
                    S['idx_hdr'],
                )]],
                colWidths=[W - 40*mm],
                style=TableStyle([
                    ('BACKGROUND',    (0, 0), (-1, -1), _PURPLE_DARK),
                    ('TOPPADDING',    (0, 0), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 10),
                ]),
            ))
            block.append(Spacer(1, 3*mm))

            # ── Stats table ──────────────────────────────────────────────────
            block.append(Table(
                [['Median', 'Std Dev', 'Min', 'Max'],
                 [fmt(median_v), fmt(std_v), fmt(min_v), fmt(max_v)]],
                colWidths=[(W - 40*mm) / 4] * 4,
                style=TableStyle([
                    ('BACKGROUND',    (0, 0), (-1, 0),  _PURPLE),
                    ('TEXTCOLOR',     (0, 0), (-1, 0),  _WHITE),
                    ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
                    ('FONTSIZE',      (0, 0), (-1, -1), 9),
                    ('BACKGROUND',    (0, 1), (-1, -1), _INFO_BG),
                    ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica-Bold'),
                    ('TEXTCOLOR',     (0, 1), (-1, -1), _DARK),
                    ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                    ('GRID',          (0, 0), (-1, -1), 0.4, _GREY_300),
                    ('TOPPADDING',    (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ]),
            ))
            block.append(Spacer(1, 3*mm))

            if idc.get('description'):
                block.append(Paragraph(f"<b>Description:</b> {idc['description']}", S['caption']))
            if idc.get('heritage_use'):
                block.append(Paragraph(f"<b>Heritage Use:</b> {idc['heritage_use']}", S['caption']))
            block.append(Spacer(1, 3*mm))

            # ── Real GEE map thumbnail for this index ────────────────────────
            thumb = self.imgs.get(idx)
            if thumb:
                thumb.seek(0)
                map_img = RLImage(thumb, width=W - 40*mm, height=88*mm)
                map_img.hAlign = 'CENTER'

                # Build colour-scale label from palette if available
                palette = idc.get('palette', [])
                vmin    = idc.get('min', '')
                vmax    = idc.get('max', '')
                scale_note = f"  |  Scale: {vmin} → {vmax}" if (vmin != '' and vmax != '') else ''

                block.append(Paragraph(
                    f"<font color='#764ba2'><b>Satellite Map — {idx}</b></font>  "
                    f"<font color='#6b6b8a'>(median composite, "
                    f"{cfg['start_date'].strftime('%d %b %Y')} – "
                    f"{cfg['end_date'].strftime('%d %b %Y')}"
                    f"{scale_note})</font>",
                    S['map_cap'],
                ))
                block.append(Spacer(1, 1*mm))
                block.append(map_img)
                block.append(Spacer(1, 3*mm))

            # ── AI interpretation card ───────────────────────────────────────
            if ai_text:
                block.append(Table(
                    [[Paragraph('<font color="#f0c040"><b>AI</b></font>', S['ai_badge']),
                      Paragraph(f'<font color="#ddd8f0">{ai_text}</font>', S['ai_body'])]],
                    colWidths=[12*mm, W - 40*mm - 16*mm],
                    style=TableStyle([
                        ('BACKGROUND',    (0, 0), (-1, -1), _DARK),
                        ('LEFTPADDING',   (0, 0), (0, -1),  8),
                        ('LEFTPADDING',   (1, 0), (1, -1),  8),
                        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
                        ('TOPPADDING',    (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('LINEAFTER',     (0, 0), (0, -1),  3, _PURPLE),
                        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                    ]),
                ))

            block.append(Spacer(1, 7*mm))
            out.append(KeepTogether(block[:4]))   # header + stats always together
            out.extend(block[4:])                 # rest can flow naturally

        return out

    # ── Data quality ────────────────────────────────────────────────────────

    def _quality(self):
        S   = self.S
        cfg = self.cfg
        cov = ('excellent' if self.count >= 20 else
               'good'      if self.count >= 10 else 'adequate')

        def _bullet_tbl(items, bg, border):
            rows = [[Paragraph(f'• {t}', S['bullet'])] for t in items]
            return Table(
                rows, colWidths=[W - 40*mm],
                style=TableStyle([
                    ('BACKGROUND',   (0, 0), (-1, -1), bg),
                    ('LEFTPADDING',  (0, 0), (-1, -1), 10),
                    ('TOPPADDING',   (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
                    ('LINEBEFORE',   (0, 0), (0, -1),  4, border),
                ]),
            )

        strengths = [
            f'Image Count: {self.count} scenes — {cov} temporal coverage',
            'Spatial Resolution: 10 metres (Sentinel-2 native)',
            'Multi-spectral: 13 bands from visible to SWIR',
            f'Cloud Filtering: max {cfg["cloud_cover"]}% applied',
            'Revisit Time: 5-day global Sentinel-2 cycle',
        ]
        limits = [
            'Residual clouds may affect localised pixel quality',
            'Weather patterns may create temporal data gaps',
            '10 m resolution may miss fine architectural details',
            'Surface-only observations (no subsurface)',
            'Ground-truth field validation recommended',
        ]
        cw = (W - 40*mm - 5*mm) / 2
        tbl = Table([[
            [Paragraph('<font color="#2d7a4f"><b>Data Strengths</b></font>', S['h2']),
             Spacer(1, 2*mm),
             _bullet_tbl(strengths, _SUCCESS_BG, _SUCCESS_GRN)],
            Spacer(5*mm, 1),
            [Paragraph('<font color="#c0392b"><b>Known Limitations</b></font>', S['h2']),
             Spacer(1, 2*mm),
             _bullet_tbl(limits, _WARN_BG, _WARN_RED)],
        ]], colWidths=[cw, 5*mm, cw],
            style=TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ]))
        return [
            Paragraph('Data Quality Assessment', S['h1']),
            self._rule(), Spacer(1, 4*mm), tbl, Spacer(1, 6*mm),
        ]

    # ── Methodology ──────────────────────────────────────────────────────────

    def _methodology(self):
        S = self.S
        known = {
            'NDVI':  ('Normalized Difference Vegetation Index', '(B8-B4)/(B8+B4)'),
            'NDBI':  ('Normalized Difference Built-up Index',   '(B11-B8)/(B11+B8)'),
            'NDMI':  ('Normalized Difference Moisture Index',   '(B8-B11)/(B8+B11)'),
            'NDWI':  ('Normalized Difference Water Index',      '(B3-B8)/(B3+B8)'),
            'MNDWI': ('Modified Normalized Diff Water Index',   '(B3-B11)/(B3+B11)'),
            'BSI':   ('Bare Soil Index',                        '((B11+B4)-(B8+B2))/((B11+B4)+(B8+B2))'),
            'EVI':   ('Enhanced Vegetation Index',              '2.5*(B8-B4)/(B8+6*B4-7.5*B2+1)'),
            'SAVI':  ('Soil-Adjusted Vegetation Index',         '1.5*(B8-B4)/(B8+B4+0.5)'),
            'NBR':   ('Normalized Burn Ratio',                  '(B8-B12)/(B8+B12)'),
            'NDRE':  ('Red Edge Vegetation Index',              '(B8-B5)/(B8+B5)'),
        }
        rows = [['Index', 'Full Name', 'Formula']]
        for idx in self.cfg['indices']:
            if idx in known:
                rows.append([idx, known[idx][0], known[idx][1]])
            else:
                rows.append([idx, 'Custom index', 'See sidebar configuration'])

        cw = W - 40*mm
        tbl = Table(
            rows, colWidths=[cw * 0.10, cw * 0.40, cw * 0.50],
            style=TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0),  _PURPLE_DARK),
                ('TEXTCOLOR',     (0, 0), (-1, 0),  _YELLOW),
                ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS',(0, 1), (-1, -1), [_WHITE, _INFO_BG]),
                ('FONTNAME',      (0, 1), (0, -1),  'Helvetica-Bold'),
                ('TEXTCOLOR',     (0, 1), (0, -1),  _PURPLE),
                ('GRID',          (0, 0), (-1, -1), 0.4, _GREY_300),
                ('TOPPADDING',    (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING',   (0, 0), (-1, -1), 6),
                ('FONT',          (2, 1), (-1, -1), 'Courier', 7.5),
            ]),
        )
        return [
            Paragraph('Methodology & Scientific Background', S['h1']),
            self._rule(), Spacer(1, 3*mm),
            Paragraph(
                'All analyses use the <b>Sentinel-2 MSI SR Harmonised</b> collection '
                '(COPERNICUS/S2_SR_HARMONIZED) processed through <b>Google Earth Engine</b>. '
                'Spectral indices are computed on the cloud-filtered median composite. '
                'Statistics are derived via <i>reduceRegion</i> at 10-metre resolution '
                'over the circular AOI buffer.',
                S['body'],
            ),
            Spacer(1, 4*mm), tbl, Spacer(1, 6*mm),
        ]

    def _sign_off(self):
        S = self.S
        return [
            self._rule(), Spacer(1, 3*mm),
            Paragraph(
                f"Report generated on <b>{self.now.strftime('%d %B %Y at %H:%M')} UTC</b> "
                f"by the Heritage Site Monitoring System v1.0.  "
                f"All satellite data copyright ESA Copernicus Programme.",
                S['caption'],
            ),
            Spacer(1, 2*mm),
            Paragraph(
                'AI interpretations are generated by the Groq LLaMA-3 model and should be '
                'reviewed by a qualified heritage conservation professional before use in '
                'official assessments.',
                S['caption'],
            ),
        ]

    def _rule(self):
        return HRFlowable(width='100%', thickness=1.5, color=_PURPLE, spaceAfter=2*mm)

    def _kpi(self, label, value, hex_color):
        S  = self.S
        bg = colors.HexColor(hex_color)
        return Table(
            [[Paragraph(f"<font color='#ffffff'><b>{value}</b></font>", S['kpi_val'])],
             [Paragraph(f"<font color='#dddddd'>{label}</font>",        S['kpi_lbl'])]],
            style=TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), bg),
                ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING',    (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]),
        )

    def _styles(self):
        def P(**kw): return ParagraphStyle('_', **kw)
        return {
            # ── New title styles (replaces cover) ──────────────────────────
            'report_title': P(fontSize=18, fontName='Helvetica-Bold',
                              textColor=_PURPLE_DARK, alignment=TA_CENTER,
                              spaceAfter=2*mm),
            'site_title':   P(fontSize=14, fontName='Helvetica-Bold',
                              textColor=_PURPLE, alignment=TA_CENTER,
                              spaceAfter=1*mm),
            'subtitle':     P(fontSize=8.5, fontName='Helvetica',
                              textColor=_GREY_700, alignment=TA_CENTER,
                              spaceAfter=1*mm),
            # ── Existing styles ────────────────────────────────────────────
            'h1':         P(fontSize=14, fontName='Helvetica-Bold',
                            textColor=_PURPLE_DARK, spaceAfter=2*mm),
            'h2':         P(fontSize=11, fontName='Helvetica-Bold',
                            textColor=_PURPLE, spaceAfter=1*mm),
            'body':       P(fontSize=9,  fontName='Helvetica', leading=14,
                            textColor=_GREY_900, alignment=TA_JUSTIFY),
            'caption':    P(fontSize=8,  fontName='Helvetica', leading=12,
                            textColor=_GREY_700),
            'bullet':     P(fontSize=8.5, fontName='Helvetica', leading=13,
                            textColor=_GREY_900),
            'map_cap':    P(fontSize=8,  fontName='Helvetica-Bold',
                            textColor=_PURPLE, alignment=TA_CENTER),
            'idx_hdr':    P(fontSize=11, fontName='Helvetica-Bold', textColor=_WHITE),
            'ai_badge':   P(fontSize=9,  fontName='Helvetica-Bold',
                            textColor=_YELLOW, alignment=TA_CENTER),
            'ai_body':    P(fontSize=8.5, fontName='Helvetica', leading=13,
                            textColor=colors.HexColor('#ddd8f0')),
            'kpi_val':    P(fontSize=11, fontName='Helvetica-Bold',
                            textColor=_WHITE, alignment=TA_CENTER),
            'kpi_lbl':    P(fontSize=7.5, fontName='Helvetica',
                            textColor=colors.HexColor('#dddddd'), alignment=TA_CENTER),
        }