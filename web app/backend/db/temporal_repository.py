"""
Responsible for: all SQL operations on the temporal_cache table.
"""

import pandas as pd
from backend.db.db_connection import DBConnection


class TemporalRepository:
    """
    Stores and retrieves per-date index values for incremental
    temporal analysis (avoids re-fetching GEE data already computed).

    Table schema expected:
        temporal_cache (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            site_name     VARCHAR(255),
            index_name    VARCHAR(50),
            analysis_date DATE,
            value         DOUBLE,
            UNIQUE KEY uq_site_index_date (site_name, index_name, analysis_date)
        )

    Usage:
        repo = TemporalRepository(db)
        repo.save_point('Alba Iulia', 'NDVI', date(2024, 6, 1), 0.45)
        df = repo.find_range('Alba Iulia', 'NDVI', start, end)
    """

    def __init__(self, db: DBConnection):
        self._db = db

    def save_point(
        self,
        site_name: str,
        index_name: str,
        analysis_date,   # datetime.date
        value: float,
    ) -> None:
        """
        Insert a single date/value data point.
        Silently ignores duplicates (INSERT IGNORE).
        """
        sql = """
            INSERT IGNORE INTO temporal_cache
                (site_name, index_name, analysis_date, value)
            VALUES (%s, %s, %s, %s)
        """
        with self._db.get() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (site_name, index_name, analysis_date, float(value)))
            conn.commit()
            cursor.close()

    def find_range(
        self,
        site_name: str,
        index_name: str,
        start_date,   # datetime.date or str
        end_date,     # datetime.date or str
    ) -> pd.DataFrame:
        """
        Return all stored data points for *site_name* / *index_name*
        within [start_date, end_date] ordered ascending.

        Returns:
            DataFrame with columns ['analysis_date', 'value'].
            Empty DataFrame if no data found.
        """
        sql = """
            SELECT analysis_date, value
            FROM temporal_cache
            WHERE site_name = %s
              AND index_name = %s
              AND analysis_date BETWEEN %s AND %s
            ORDER BY analysis_date ASC
        """
        with self._db.get() as conn:
            df = pd.read_sql(sql, conn, params=(site_name, index_name, start_date, end_date))
        return df

    def get_existing_dates(
        self,
        site_name: str,
        index_name: str,
        start_date,
        end_date,
    ) -> set[str]:
        """
        Return a set of ISO date strings already stored for the given
        site/index/range. Used to skip re-fetching from GEE.
        """
        df = self.find_range(site_name, index_name, start_date, end_date)
        if df.empty:
            return set()
        return set(df['analysis_date'].astype(str))