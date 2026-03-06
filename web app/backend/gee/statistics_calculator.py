"""
Responsible for: computing spatial statistics over an AOI via reduceRegion.
"""

import ee


class StatisticsCalculator:
    """
    Extracts median / stdDev / min / max statistics for a single index band
    from an EE Image over a given geometry.

    Usage:
        stats_calc = StatisticsCalculator()
        stats = stats_calc.run(image_with_indices, aoi, 'NDVI')
        median = stats.get('NDVI_median')
    """

    DEFAULT_SCALE     = 10      # metres — Sentinel-2 native resolution
    DEFAULT_MAX_PIXELS = 1e9

    def run(
        self,
        image: ee.Image,
        geometry: ee.Geometry,
        index: str,
        scale: int = DEFAULT_SCALE,
    ) -> dict:
        """
        Compute median, stdDev, min and max for *index* band over *geometry*.

        Args:
            image:    EE Image that already contains the index band.
            geometry: Area of interest.
            index:    Band name to summarise (e.g. 'NDVI').
            scale:    Spatial resolution in metres for reduceRegion.

        Returns:
            Dict with keys like 'NDVI_mean', 'NDVI_stdDev', 'NDVI_min', 'NDVI_max'.
            Returns empty dict if the band is missing or the call fails.
        """
        try:
            stats = image.select(index).reduceRegion(
                reducer=(
                    ee.Reducer.median()
                    .combine(reducer2=ee.Reducer.stdDev(), sharedInputs=True)
                    .combine(reducer2=ee.Reducer.minMax(),  sharedInputs=True)
                ),
                geometry=geometry,
                scale=scale,
                maxPixels=self.DEFAULT_MAX_PIXELS,
            )
            return stats.getInfo()
        except Exception:
            return {}

    def run_multiple(
        self,
        image: ee.Image,
        geometry: ee.Geometry,
        indices: list[str],
    ) -> dict[str, dict]:
        """
        Convenience wrapper: run stats for every index in *indices*.

        Returns:
            Dict keyed by index name, each value is the stats dict from run().
        """
        return {idx: self.run(image, geometry, idx) for idx in indices}