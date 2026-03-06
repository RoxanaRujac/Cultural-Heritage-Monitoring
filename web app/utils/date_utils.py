"""
Responsible for: date parsing, formatting and range operations.
"""

from datetime import datetime, timedelta, date


class DateUtils:
    """
    Centralises all date/time manipulations used across the app so that
    format strings and conversion logic live in one place.
    """

    ISO_FORMAT   = '%Y-%m-%d'
    HUMAN_FORMAT = '%B %d, %Y'

    @staticmethod
    def to_iso(d) -> str:
        """Convert a date / datetime / string to 'YYYY-MM-DD'."""
        if isinstance(d, str):
            return d
        return d.strftime(DateUtils.ISO_FORMAT)

    @staticmethod
    def to_human(d) -> str:
        """Convert a date / datetime to e.g. 'January 01, 2024'."""
        if isinstance(d, str):
            d = datetime.strptime(d, DateUtils.ISO_FORMAT)
        return d.strftime(DateUtils.HUMAN_FORMAT)

    @staticmethod
    def from_timestamp_ms(ts_ms: int) -> datetime:
        """Convert a Unix millisecond timestamp to a naive datetime."""
        return datetime.fromtimestamp(ts_ms / 1000)

    @staticmethod
    def timestamps_to_date_list(timestamps: list[int]) -> list[tuple[int, str, datetime]]:
        """
        Convert a list of ms timestamps to sorted (ts, date_str, datetime) tuples.
        Used by the browse-images slider in the maps tab.
        """
        result = []
        for ts in timestamps:
            dt = DateUtils.from_timestamp_ms(ts)
            result.append((ts, dt.strftime(DateUtils.ISO_FORMAT), dt))
        return sorted(result, key=lambda x: x[0])

    @staticmethod
    def day_after(d) -> str:
        """Return the ISO string for the day after *d*."""
        if isinstance(d, str):
            d = datetime.strptime(d, DateUtils.ISO_FORMAT)
        return (d + timedelta(days=1)).strftime(DateUtils.ISO_FORMAT)

    @staticmethod
    def duration_days(start, end) -> int:
        """Return number of days between start and end (accepts date or str)."""
        if isinstance(start, str):
            start = datetime.strptime(start, DateUtils.ISO_FORMAT).date()
        if isinstance(end, str):
            end = datetime.strptime(end, DateUtils.ISO_FORMAT).date()
        return (end - start).days