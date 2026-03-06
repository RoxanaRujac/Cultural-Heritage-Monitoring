"""
Responsible for: building filtered Sentinel-2 ImageCollections.
"""

import ee


class CollectionBuilder:
    """
    Builds and filters Sentinel-2 SR Harmonised image collections.

    Usage:
        builder = CollectionBuilder()
        collection = builder.build(aoi, '2023-01-01', '2024-01-01', cloud_cover=20)
        count = builder.count(collection)
    """

    COLLECTION_ID = 'COPERNICUS/S2_SR_HARMONIZED'

    def build(
        self,
        geometry: ee.Geometry,
        start_date: str,
        end_date: str,
        cloud_cover: int = 20,
    ) -> ee.ImageCollection:
        """
        Return a collection filtered by bounds, date range and cloud cover.

        Args:
            geometry:    EE geometry defining the area of interest.
            start_date:  ISO date string 'YYYY-MM-DD'.
            end_date:    ISO date string 'YYYY-MM-DD'.
            cloud_cover: Maximum allowed CLOUDY_PIXEL_PERCENTAGE (0-100).

        Returns:
            Filtered ee.ImageCollection.
        """
        return (
            ee.ImageCollection(self.COLLECTION_ID)
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover))
        )

    def count(self, collection: ee.ImageCollection) -> int:
        """Return the number of images in the collection (server-side call)."""
        return collection.size().getInfo()

    def get_timestamps(self, collection: ee.ImageCollection) -> list[int]:
        """Return list of Unix millisecond timestamps for all images."""
        return collection.aggregate_array('system:time_start').getInfo()

    def build_aoi(self, lat: float, lon: float, buffer_km: float) -> ee.Geometry:
        """
        Create a circular area of interest from a centre point.

        Args:
            lat:       Centre latitude.
            lon:       Centre longitude.
            buffer_km: Radius in kilometres.

        Returns:
            ee.Geometry (buffered point).
        """
        return ee.Geometry.Point([lon, lat]).buffer(buffer_km * 1000)