"""
Responsible for: rendering the History tab.

Shows all past analysis sessions.  Clicking a session loads its saved
data from the DB and renders:
  - Median composite map (re-fetched from GEE, lightweight)
  - Spectral index stats cards
  - Change-detection snapshots with events table
  - AI interpretation text (stored)
  - Free-text notes (add / delete inline)
"""

from __future__ import annotations

import ee
import folium
import streamlit as st
import geemap.foliumap as geemap
from datetime import datetime, date

from backend.db.history_repository import HistoryRepository
from backend.db.db_connection import DBConnection
from backend.gee.collection_builder import CollectionBuilder
from backend.gee.index_calculator import IndexCalculator
from config.indices_config import INDICES_CONFIG
from backend.gee.change_detector import SEVERITY_COLOR, SEVERITY_LABEL

try:
    from streamlit_folium import st_folium
    _HAS_ST_FOLIUM = True
except ImportError:
    _HAS_ST_FOLIUM = False


# ── colour ────────────────────────────────────────────────────────────

_DELTA_BG = {
    'critical': '#fde8e8',
    'high':     '#fef3e2',
    'moderate': '#fefce8',
    'low':      '#f3edf9',
}
_DELTA_BORDER = {
    'critical': '#c0392b',
    'high':     '#e67e22',
    'moderate': '#d4a017',
    'low':      '#764ba2',
}


class HistoryTab:
    """
    Usage:
        HistoryTab(db, col_builder, idx_calc).render()
    """

    def __init__(self, db: DBConnection,
                 col_builder: CollectionBuilder,
                 idx_calc: IndexCalculator):
        self._repo        = HistoryRepository(db)
        self._col_builder = col_builder
        self._idx_calc    = idx_calc

    # ── entry point ───────────────────────────────────────────────────────────

    def render(self) -> None:
        st.subheader('Analysis History')

        sessions = self._repo.list_sessions(limit=60)
        if not sessions:
            st.info('No analysis sessions saved yet. Run an analysis first.')
            return

        if 'history_selected_id' not in st.session_state:
            st.session_state.history_selected_id = None

        # CSS: make st.button look like a styled info card (no split screen)
        st.markdown("""
        <style>
        [data-testid="stHorizontalBlock"] { gap: 0 !important; }
        div[data-testid="column"] > div > div > div > button {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            height: auto !important;
        }
        .hist-card {
            border: 1.5px solid #e0d6f0;
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 6px;
            background: #faf7fd;
            cursor: pointer;
            transition: border-color 0.15s;
        }
        .hist-card:hover { border-color: #764ba2; }
        .hist-card.active {
            background: linear-gradient(135deg,#4a2d6b,#764ba2);
            border-color: #764ba2;
        }
        .hist-card .title  { font-weight:700; font-size:14px; color:#2c2c3e; }
        .hist-card.active .title,
        .hist-card.active .sub,
        .hist-card.active .tiny { color: white !important; opacity: 1 !important; }
        .hist-card .sub    { font-size:11px; color:#6b6b8a; margin-top:3px; }
        .hist-card .tiny   { font-size:10px; color:#6b6b8a; margin-top:2px; opacity:0.8; }
        .badge-y { background:#f0c040; color:#2c2c3e; font-size:10px; font-weight:700;
                   padding:1px 7px; border-radius:10px; margin-left:6px; }
        .badge-p { background:#9b6fc5; color:white; font-size:10px; font-weight:700;
                   padding:1px 7px; border-radius:10px; margin-left:4px; }
        </style>
        """, unsafe_allow_html=True)

        search = st.text_input(' Filter by site', key='history_search',
                               placeholder='e.g. Alba Iulia').strip().lower()

        filtered = [s for s in sessions
                    if not search or search in s['site_name'].lower()]

        if not filtered:
            st.caption('No sessions match the filter.')

        # Render each session as a styled card (st.button only, no decorative markdown)
        for s in filtered:
            is_active   = st.session_state.history_selected_id == s['id']
            date_str    = s['analysis_date'].strftime('%d %b %Y, %H:%M') \
                          if isinstance(s['analysis_date'], datetime) else str(s['analysis_date'])
            indices_str = ', '.join(s['indices'][:4]) + \
                          (f' +{len(s["indices"])-4}' if len(s['indices']) > 4 else '')
            snap_txt  = f'{s["snapshot_count"]} changes' if s['snapshot_count'] else ''
            note_txt  = f'{s["note_count"]} notes'      if s['note_count']     else ''

            active_cls = 'active' if is_active else ''
            badge_html = (
                (f'<span class="badge-y">{snap_txt}</span>' if snap_txt else '') +
                (f'<span class="badge-p">{note_txt}</span>' if note_txt else '')
            )

            st.markdown(f"""
            <div class="hist-card {active_cls}">
                <div class="title"> {s['site_name']} {badge_html}</div>
                <div class="sub">
                    {str(s['start_date'])} → {str(s['end_date'])}
                    &nbsp;·&nbsp; {s['image_count'] or '?'} images
                </div>
                <div class="sub">Indices: {indices_str or '—'}</div>
                <div class="tiny">Saved: {date_str}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button('Select', key=f'load_{s["id"]}', use_container_width=True):
                st.session_state.history_selected_id = s['id']
                st.rerun()

        st.markdown('---')

        # Detail panel below the list
        selected_id = st.session_state.history_selected_id
        if selected_id:
            session = self._repo.get_session(selected_id)
            if session:
                self._render_session_detail(session)
        else:
            st.caption('Select a session above to view its details.')

    # ── detail panel ──────────────────────────────────────────────────────────

    def _render_session_detail(self, s: dict) -> None:
        # ── Header ───────────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#4a2d6b 0%,#764ba2 100%);
                    padding:18px 22px;border-radius:12px;color:white;margin-bottom:16px;">
            <div style="font-size:20px;font-weight:700;"> {s['site_name']}</div>
            <div style="font-size:13px;opacity:0.85;margin-top:4px;">
                 {s['latitude']:.5f}°N, {s['longitude']:.5f}°E
                &nbsp;·&nbsp; Radius: {s['buffer_km']} km
                &nbsp;·&nbsp;  ≤ {s['cloud_cover']}%
            </div>
            <div style="font-size:13px;opacity:0.85;">
                🗓 {str(s['start_date'])} → {str(s['end_date'])}
                &nbsp;·&nbsp; 🛰 {s['image_count'] or '?'} Sentinel-2 images
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Tabs inside the detail panel ──────────────────────────────────────
        inner_tabs = st.tabs(['Map', ' Statistics', ' Changes', ' Notes'])

        with inner_tabs[0]:
            self._render_map_panel(s)

        with inner_tabs[1]:
            self._render_stats_panel(s)

        with inner_tabs[2]:
            self._render_snapshots_panel(s)

        with inner_tabs[3]:
            self._render_notes_panel(s)

    # ── Map panel ─────────────────────────────────────────────────────────────

    def _render_map_panel(self, s: dict) -> None:
        st.caption('Median composite for the analysis period ')

        cache_key = f'hist_map_{s["id"]}'

        if cache_key not in st.session_state:
            with st.spinner('Fetching median composite from GEE…'):
                try:
                    aoi = self._col_builder.build_aoi(
                        s['latitude'], s['longitude'], s['buffer_km']
                    )
                    collection = self._col_builder.build(
                        aoi,
                        str(s['start_date']),
                        str(s['end_date']),
                        s['cloud_cover'],
                    )
                    count = self._col_builder.count(collection)

                    if count == 0:
                        st.warning('No images found for this session period.')
                        return

                    median = collection.median()
                    # Pick the first stored index for the overlay (fallback: RGB)
                    indices = s.get('indices', [])
                    overlay_idx = next(
                        (i for i in indices if i in INDICES_CONFIG), None
                    )

                    if overlay_idx:
                        indexed = self._idx_calc.compute(median)
                        idc     = INDICES_CONFIG[overlay_idx]
                        vis     = {'min': idc['min'], 'max': idc['max'],
                                   'palette': idc['palette']}
                        layer   = indexed.select(overlay_idx)
                        label   = overlay_idx
                    else:
                        layer = median
                        vis   = {'bands': ['B4', 'B3', 'B2'],
                                 'min': 0, 'max': 3000, 'gamma': 1.4}
                        label = 'RGB'

                    st.session_state[cache_key] = {
                        'layer': layer, 'vis': vis, 'label': label,
                        'aoi': aoi, 'lat': s['latitude'], 'lon': s['longitude'],
                        'overlay_idx': overlay_idx,
                        'indices': indices,
                    }
                except Exception as exc:
                    st.error(f'GEE error: {exc}')
                    return

        if cache_key in st.session_state:
            cached = st.session_state[cache_key]

            # Index selector (only indices stored for this session)
            if cached['indices']:
                available = ['Natural Color (RGB)'] + [
                    i for i in cached['indices'] if i in INDICES_CONFIG
                ]
                sel = st.selectbox('Layer', available,
                                   key=f'hist_layer_{s["id"]}')
            else:
                sel = 'Natural Color (RGB)'

            # Rebuild visualisation if user changed selector
            aoi    = cached['aoi']
            median = None  # lazy — only recompute if needed

            m = geemap.Map(
                center=[cached['lat'], cached['lon']],
                zoom=14, add_google_map=False,
            )
            m.add_basemap('HYBRID')

            if sel == 'Natural Color (RGB)':
                # We need the raw median image — re-fetch from GEE lazily
                with st.spinner('Rendering RGB…'):
                    aoi2 = self._col_builder.build_aoi(
                        s['latitude'], s['longitude'], s['buffer_km']
                    )
                    col2 = self._col_builder.build(
                        aoi2, str(s['start_date']), str(s['end_date']),
                        s['cloud_cover'],
                    )
                    med2 = col2.median()
                m.addLayer(med2,
                           {'bands': ['B4', 'B3', 'B2'],
                            'min': 0, 'max': 3000, 'gamma': 1.4},
                           'RGB Median')
            else:
                idc = INDICES_CONFIG[sel]
                m.addLayer(cached['layer'] if sel == cached['overlay_idx']
                           else cached['layer'],  # already the indexed image
                           {'min': idc['min'], 'max': idc['max'],
                            'palette': idc['palette']},
                           sel)

            # AOI border
            aoi_style = ee.FeatureCollection(aoi).style(
                color='764ba2', fillColor='764ba21A', width=2
            )
            m.addLayer(aoi_style, {}, 'AOI')
            m.add_layer_control()
            m.centerObject(aoi, 14)

            if _HAS_ST_FOLIUM:
                st_folium(m, height=480, width='100%',
                          key=f'hist_map_render_{s["id"]}_{sel}',
                          returned_objects=[])
            else:
                m.to_streamlit(height=480)

    # ── Statistics panel ──────────────────────────────────────────────────────

    def _render_stats_panel(self, s: dict) -> None:
        stats   = s.get('stats', {})
        indices = s.get('indices', [])

        if not stats:
            st.info('No statistics stored for this session.')
            return

        st.markdown('#### Spectral Index Summary')

        for idx in indices:
            if idx not in stats:
                continue
            idx_stats = stats[idx]
            median_v  = idx_stats.get(f'{idx}_median', idx_stats.get(f'{idx}_mean', None))
            std_v     = idx_stats.get(f'{idx}_stdDev')
            min_v     = idx_stats.get(f'{idx}_min')
            max_v     = idx_stats.get(f'{idx}_max')

            idc  = INDICES_CONFIG.get(idx, {})
            name = idc.get('name', idx)
            desc = idc.get('description', '')
            heritage = idc.get('heritage_use', '')

            # Colour bar
            palette   = idc.get('palette', [])
            hex_pal   = ['#'+p if not p.startswith('#') else p for p in palette]
            grad      = ', '.join(hex_pal) if hex_pal else '#ccc, #ccc'
            vmin, vmax = idc.get('min', 0), idc.get('max', 1)

            with st.expander(f'**{idx}** — {name}', expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric('Median', f'{median_v:.4f}' if median_v is not None else '—')
                c2.metric('Std Dev', f'{std_v:.4f}'  if std_v     is not None else '—')
                c3.metric('Min',     f'{min_v:.4f}'  if min_v     is not None else '—')
                c4.metric('Max',     f'{max_v:.4f}'  if max_v     is not None else '—')

                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;
                            padding:6px 0;font-size:12px;color:#6b6b8a;">
                    <span style="background:linear-gradient(to right,{grad});
                          width:160px;height:10px;display:inline-block;
                          border-radius:3px;border:1px solid #ccc;"></span>
                    <span>{vmin} → {vmax}</span>
                </div>
                """, unsafe_allow_html=True)

                if desc:
                    st.caption(f' {desc}')
                if heritage:
                    st.caption(f' {heritage}')

    # ── Change snapshots panel ────────────────────────────────────────────────

    def _render_snapshots_panel(self, s: dict) -> None:
        snapshots = s.get('snapshots', [])

        if not snapshots:
            st.info(
                'No change-detection snapshots saved yet for this session.  '
                'Run Change Detection and the results will be stored automatically.'
            )
            return

        st.markdown(f'#### {len(snapshots)} Change-Detection Run(s)')

        for snap in snapshots:
            delta   = snap.get('delta_median', 0) or 0
            d_color = '#c0392b' if delta < 0 else '#2d7a4f'
            created = snap['created_at'].strftime('%d %b %Y %H:%M') \
                      if isinstance(snap['created_at'], datetime) else str(snap['created_at'])

            title = (
                f"**{snap['index_name']}** &nbsp;·&nbsp; "
                f"{str(snap['first_date'])} → {str(snap['last_date'])} &nbsp;·&nbsp; "
                f"Δ <span style='color:{d_color};font-weight:700;'>{delta:+.4f}</span>"
            )
            with st.expander(
                f"{snap['index_name']}  {str(snap['first_date'])} → {str(snap['last_date'])}  "
                f"Δ {delta:+.4f}",
                expanded=False,
            ):
                # Summary metrics
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric('Index',    snap['index_name'])
                mc2.metric('Before',   f"{snap['before_median']:.4f}" if snap['before_median'] is not None else '—')
                mc3.metric('After',    f"{snap['after_median']:.4f}"  if snap['after_median']  is not None else '—')
                mc4.metric('Δ Median', f'{delta:+.4f}',
                           delta=f'{delta:+.4f}',
                           delta_color='inverse' if delta < 0 else 'normal')

                st.caption(
                    f"Threshold: ±{snap['threshold']} &nbsp;·&nbsp; Saved: {created}"
                )

                # Events table
                events = snap.get('events', [])
                if events:
                    st.markdown(f'**{len(events)} significant change locations:**')
                    self._render_compact_events(events, snap['index_name'])
                else:
                    st.caption('No individual change events recorded.')

                # AI interpretation
                if snap.get('ai_text'):
                    st.markdown('** AI Interpretation (saved):**')
                    st.info(snap['ai_text'])

    @staticmethod
    def _render_compact_events(events: list[dict], idx: str) -> None:
        """Compact events table — fits inside an expander."""
        hcols = st.columns([0.4, 1.4, 1.6, 1.1, 1.1, 1.1])
        for col, h in zip(hcols, ['#', 'Severity', 'Location',
                                   'Before', 'After', 'Δ']):
            col.markdown(f'<span style="font-size:11px;font-weight:700;">{h}</span>',
                         unsafe_allow_html=True)

        for i, ev in enumerate(events):
            sev   = ev.get('severity', 'low')
            s_col = SEVERITY_COLOR.get(sev, '#764ba2')
            d_col = '#c0392b' if ev['delta'] < 0 else '#2d7a4f'
            cols  = st.columns([0.4, 1.4, 1.6, 1.1, 1.1, 1.1])
            cols[0].markdown(
                f'<span style="color:#764ba2;font-weight:700;font-size:12px;">{i+1}</span>',
                unsafe_allow_html=True,
            )
            cols[1].markdown(
                f'<span style="color:{s_col};font-size:12px;font-weight:600;">'
                f'{SEVERITY_LABEL.get(sev, sev)}</span>',
                unsafe_allow_html=True,
            )
            cols[2].caption(f"{ev['lat']:.4f}°N\n{ev['lon']:.4f}°E")
            cols[3].markdown(f'`{ev["value_before"]:.3f}`')
            cols[4].markdown(f'`{ev["value_after"]:.3f}`')
            cols[5].markdown(
                f'<span style="color:{d_col};font-weight:700;">{ev["delta"]:+.3f}</span>',
                unsafe_allow_html=True,
            )

    # ── Notes panel ───────────────────────────────────────────────────────────

    def _render_notes_panel(self, s: dict) -> None:
        history_id = s['id']
        notes      = s.get('notes', [])

        st.markdown('#### Field Notes')
        st.caption(
            'Add observations, concerns, or action items for this analysis session.'
        )

        # ── Add note ─────────────────────────────────────────────────────────
        note_key  = f'new_note_{history_id}'
        note_text = st.text_area(
            'New note',
            key=note_key,
            placeholder='e.g. Vegetation increase detected near north wall. '
                        'Recommend ground inspection.',
            height=90,
            label_visibility='collapsed',
        )
        c_save, c_clear = st.columns([2, 1])
        with c_save:
            if st.button(' Save Note', key=f'save_note_{history_id}',
                         type='primary', use_container_width=True):
                if note_text.strip():
                    self._repo.add_note(history_id, note_text.strip())
                    st.success('Note saved.')
                    st.rerun()
                else:
                    st.warning('Note is empty.')

        st.markdown('---')

        # ── Existing notes ────────────────────────────────────────────────────
        if not notes:
            st.caption('No notes yet for this session.')
            return

        for note in reversed(notes):  # newest first
            created = note['created_at'].strftime('%d %b %Y, %H:%M') \
                      if isinstance(note['created_at'], datetime) \
                      else str(note['created_at'])

            nc1, nc2 = st.columns([9, 1])
            with nc1:
                st.markdown(f"""
                <div style="background:#f9f6fd;border-left:4px solid #764ba2;
                            border-radius:6px;padding:10px 14px;margin-bottom:6px;">
                    <div style="font-size:13px;color:#2c2c3e;">{note['note_text']}</div>
                    <div style="font-size:10px;color:#9b8db0;margin-top:4px;">
                         {note['author']} &nbsp;·&nbsp; {created}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with nc2:
                if st.button('🗑', key=f'del_note_{note["id"]}',
                             help='Delete this note'):
                    self._repo.delete_note(note['id'])
                    st.rerun()