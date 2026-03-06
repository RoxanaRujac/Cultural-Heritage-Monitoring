"""
Responsible for: all SQL operations on the sites_history table.
"""

import json
from backend.db.db_connection import DBConnection
from utils.hash_utils import HashUtils


class AnalysisRepository:
    """
    Persists and retrieves completed analysis results keyed by a
    deterministic hash of the analysis parameters.

    Table schema expected:
        sites_history (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            site_name    VARCHAR(255),
            latitude     DOUBLE,
            longitude    DOUBLE,
            buffer_km    DOUBLE,
            start_date   DATE,
            end_date     DATE,
            cloud_cover  INT,
            stats_json   LONGTEXT,
            params_hash  VARCHAR(64) UNIQUE,
            analysis_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )

    Usage:
        repo = AnalysisRepository(db)
        repo.save(config, stats_dict)
        result = repo.find_by_config(config)   # returns dict or None
    """

    def __init__(self, db: DBConnection):
        self._db = db

    def save(self, config: dict, stats: dict) -> None:
        """
        Insert a new analysis result.
        If the same parameter hash already exists, update the timestamp only.
        """
        params_hash = HashUtils.hash_config(config)

        sql = """
            INSERT INTO sites_history
                (site_name, latitude, longitude, buffer_km,
                 start_date, end_date, cloud_cover, stats_json, params_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE analysis_date = CURRENT_TIMESTAMP
        """
        values = (
            config['site_name'],
            config['center_lat'],
            config['center_lon'],
            config['buffer_km'],
            config['start_date'],
            config['end_date'],
            config['cloud_cover'],
            json.dumps(stats),
            params_hash,
        )

        with self._db.get() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            conn.commit()
            cursor.close()

    def find_by_config(self, config: dict) -> dict | None:
        """
        Return the cached stats dict for *config*, or None if not cached.
        """
        params_hash = HashUtils.hash_config(config)

        sql = "SELECT stats_json FROM sites_history WHERE params_hash = %s"

        with self._db.get() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (params_hash,))
            row = cursor.fetchone()
            cursor.close()

        return json.loads(row['stats_json']) if row else None

    def find_all(self) -> list[dict]:
        """Return all rows from sites_history ordered by most recent first."""
        sql = """
            SELECT site_name, latitude, longitude, buffer_km,
                   start_date, end_date, cloud_cover, analysis_date
            FROM sites_history
            ORDER BY analysis_date DESC
        """
        with self._db.get() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()
        return rows