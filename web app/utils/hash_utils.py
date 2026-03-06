"""
Responsible for: generating deterministic hashes from analysis config dicts.
"""

import hashlib


class HashUtils:
    """
    Produces a SHA-256 hex string from the fields that uniquely identify
    an analysis run. Used as a cache key in the database.
    """

    @staticmethod
    def hash_config(config: dict) -> str:
        """
        Build a deterministic hash from the fields that define an analysis:
        site_name, coordinates, buffer, date range and cloud cover.

        Args:
            config: Analysis configuration dict.

        Returns:
            64-character hex SHA-256 string.
        """
        key = (
            f"{config['site_name']}_"
            f"{config['center_lat']}_"
            f"{config['center_lon']}_"
            f"{config['buffer_km']}_"
            f"{config['start_date']}_"
            f"{config['end_date']}_"
            f"{config['cloud_cover']}"
        )
        return hashlib.sha256(key.encode()).hexdigest()