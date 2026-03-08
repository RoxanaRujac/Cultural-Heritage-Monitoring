"""
Responsible for: all SQL operations related to the history feature.
Tables: sites_history, change_snapshots, analysis_notes.
"""

import json
from datetime import date
from backend.db.db_connection import DBConnection


class HistoryRepository:
    """
    Provides read/write access to the three history-related tables.

    Usage:
        repo = HistoryRepository(db)

        # Save what indices were used and image count alongside existing stats
        repo.update_indices_meta(history_id, ['NDVI', 'NDBI'], image_count=34)

        # Persist a change-detection run
        repo.save_snapshot(history_id, snapshot_dict)

        # Notes
        repo.add_note(history_id, 'Vegetation increase near north wall.')
        repo.get_notes(history_id)

        # Full history list for the sidebar / tab
        repo.list_sessions()          # → list[dict]
        repo.get_session(history_id)  # → dict with stats, snapshots, notes
    """

    def __init__(self, db: DBConnection):
        self._db = db

    # ── sites_history helpers ─────────────────────────────────────────────────

    def get_id_by_hash(self, params_hash: str) -> int | None:
        """Return the primary-key id for a given params_hash."""
        sql = "SELECT id FROM sites_history WHERE params_hash = %s"
        with self._db.get() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (params_hash,))
            row = cur.fetchone()
            cur.close()
        return row['id'] if row else None

    def update_indices_meta(self, history_id: int,
                            indices: list[str], image_count: int) -> None:
        """Store the indices list and image count on an existing row."""
        sql = """
            UPDATE sites_history
               SET indices_json = %s,
                   image_count  = %s
             WHERE id = %s
        """
        with self._db.get() as conn:
            cur = conn.cursor()
            cur.execute(sql, (json.dumps(indices), image_count, history_id))
            conn.commit()
            cur.close()

    def list_sessions(self, limit: int = 50) -> list[dict]:
        """
        Return the most recent analysis sessions with a summary of their
        snapshots and note count.  All fields needed to populate the
        history sidebar are included.
        """
        sql = """
            SELECT
                h.id,
                h.site_name,
                h.latitude,
                h.longitude,
                h.buffer_km,
                h.start_date,
                h.end_date,
                h.cloud_cover,
                h.image_count,
                h.indices_json,
                h.stats_json,
                h.analysis_date,
                COUNT(DISTINCT s.id)  AS snapshot_count,
                COUNT(DISTINCT n.id)  AS note_count
            FROM sites_history h
            LEFT JOIN change_snapshots s ON s.history_id = h.id
            LEFT JOIN analysis_notes   n ON n.history_id = h.id
            GROUP BY h.id
            ORDER BY h.analysis_date DESC
            LIMIT %s
        """
        with self._db.get() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            cur.close()

        # Decode JSON columns
        for row in rows:
            row['indices']     = json.loads(row['indices_json'])  if row['indices_json'] else []
            row['stats']       = json.loads(row['stats_json'])    if row['stats_json']   else {}
        return rows

    def get_session(self, history_id: int) -> dict | None:
        """Return full detail for one session: meta + stats + snapshots + notes."""
        sql_meta = """
            SELECT id, site_name, latitude, longitude, buffer_km,
                   start_date, end_date, cloud_cover, image_count,
                   indices_json, stats_json, analysis_date
              FROM sites_history
             WHERE id = %s
        """
        with self._db.get() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql_meta, (history_id,))
            meta = cur.fetchone()
            cur.close()

        if not meta:
            return None

        meta['indices']  = json.loads(meta['indices_json'])  if meta['indices_json'] else []
        meta['stats']    = json.loads(meta['stats_json'])    if meta['stats_json']   else {}

        meta['snapshots'] = self.get_snapshots(history_id)
        meta['notes']     = self.get_notes(history_id)
        return meta

    # ── change_snapshots ──────────────────────────────────────────────────────

    def save_snapshot(self, history_id: int, snap: dict) -> int:
        """
        Upsert a change-detection snapshot.
        snap keys: index_name, first_date, last_date, threshold,
                   before_median, after_median, delta_median,
                   events (list), ai_text (str)
        Returns the new row id.
        """
        sql = """
            INSERT INTO change_snapshots
                (history_id, index_name, first_date, last_date, threshold,
                 before_median, after_median, delta_median, events_json, ai_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            history_id,
            snap['index_name'],
            snap['first_date'],
            snap['last_date'],
            snap.get('threshold', 0.2),
            snap.get('before_median'),
            snap.get('after_median'),
            snap.get('delta_median'),
            json.dumps(snap.get('events', [])),
            snap.get('ai_text', ''),
        )
        with self._db.get() as conn:
            cur = conn.cursor()
            cur.execute(sql, values)
            conn.commit()
            new_id = cur.lastrowid
            cur.close()
        return new_id

    def get_snapshots(self, history_id: int) -> list[dict]:
        sql = """
            SELECT id, index_name, first_date, last_date, threshold,
                   before_median, after_median, delta_median,
                   events_json, ai_text, created_at
              FROM change_snapshots
             WHERE history_id = %s
             ORDER BY created_at DESC
        """
        with self._db.get() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (history_id,))
            rows = cur.fetchall()
            cur.close()

        for row in rows:
            row['events'] = json.loads(row['events_json']) if row['events_json'] else []
        return rows

    # ── analysis_notes ────────────────────────────────────────────────────────

    def add_note(self, history_id: int, text: str, author: str = 'analyst') -> int:
        sql = """
            INSERT INTO analysis_notes (history_id, author, note_text)
            VALUES (%s, %s, %s)
        """
        with self._db.get() as conn:
            cur = conn.cursor()
            cur.execute(sql, (history_id, author, text))
            conn.commit()
            new_id = cur.lastrowid
            cur.close()
        return new_id

    def delete_note(self, note_id: int) -> None:
        sql = "DELETE FROM analysis_notes WHERE id = %s"
        with self._db.get() as conn:
            cur = conn.cursor()
            cur.execute(sql, (note_id,))
            conn.commit()
            cur.close()

    def get_notes(self, history_id: int) -> list[dict]:
        sql = """
            SELECT id, author, note_text, created_at
              FROM analysis_notes
             WHERE history_id = %s
             ORDER BY created_at ASC
        """
        with self._db.get() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (history_id,))
            rows = cur.fetchall()
            cur.close()
        return rows