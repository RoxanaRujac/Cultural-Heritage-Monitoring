"""
Responsible for: generating timelapse GIF URLs from EE ImageCollections.
"""

import ee
from config.settings import GEE_MAX_PIXELS
from backend.gee.index_calculator import IndexCalculator


class GifGenerator:
    """
    Generates animated GIF URLs from Sentinel-2 collections via
    ee.ImageCollection.getVideoThumbURL().

    Automatically down-samples the collection when the total pixel count
    would exceed GEE's limit (26 214 400 px).

    Usage:
        gen = GifGenerator()
        url, n_frames, was_sampled = gen.build_url(
            collection, aoi, selected_view='NDVI',
            vis_params={...}, fps=2, dimensions=600, date_range_days=730
        )
    """

    def build_url(
        self,
        collection: ee.ImageCollection,
        aoi: ee.Geometry,
        selected_view: str,
        vis_params: dict,
        fps: int = 2,
        dimensions: int = 600,
        date_range_days: int = 365,
    ) -> tuple[str, int, bool]:
        """
        Build and return a GEE video thumbnail URL.

        Args:
            collection:       Source image collection.
            aoi:              Area of interest geometry.
            selected_view:    'Natural Color (RGB)' or an index name.
            vis_params:       Dict with min/max/palette (ignored for RGB).
            fps:              Frames per second for the animation.
            dimensions:       GIF width in pixels.
            date_range_days:  Date span — used to pick sampling interval.

        Returns:
            Tuple of (gif_url, n_frames_used, was_down_sampled).
        """
        sampled_col, n_frames = self._sample_collection(
            collection, dimensions, date_range_days
        )
        total = collection.size().getInfo()
        was_sampled = n_frames < total

        if selected_view == 'Natural Color (RGB)':
            video_col = sampled_col.map(self._prep_rgb)
        else:
            calc = IndexCalculator()
            def prep_index(img):
                idx_img = calc.compute(img).select(selected_view)
                return idx_img.visualize(
                    min=vis_params['min'],
                    max=vis_params['max'],
                    palette=vis_params['palette'],
                )
            video_col = sampled_col.map(prep_index)

        url = video_col.getVideoThumbURL({
            'dimensions':      dimensions,
            'region':          aoi,
            'framesPerSecond': fps,
            'crs':             'EPSG:3857',
        })
        return url, n_frames, was_sampled

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _prep_rgb(img: ee.Image) -> ee.Image:
        return img.visualize(bands=['B4', 'B3', 'B2'], min=0, max=3000, gamma=1.4)

    def _sample_collection(
        self,
        collection: ee.ImageCollection,
        dimensions: int,
        date_range_days: int,
    ) -> tuple[ee.ImageCollection, int]:
        """
        Reduce the collection to stay within GEE_MAX_PIXELS.
        Returns (filtered_collection, n_frames).
        """
        max_frames = max(1, GEE_MAX_PIXELS // (dimensions * dimensions))
        total      = collection.size().getInfo()

        if total <= max_frames:
            return collection, total

        interval_days = self._pick_interval(date_range_days)
        millis_interval = interval_days * 24 * 60 * 60 * 1000

        timestamps = sorted(collection.aggregate_array('system:time_start').getInfo())
        selected, last_kept = [], None

        for ts in timestamps:
            if last_kept is None or (ts - last_kept) >= millis_interval:
                selected.append(ts)
                last_kept = ts
                if len(selected) >= max_frames:
                    break

        filtered = collection.filter(
            ee.Filter.inList('system:time_start', selected)
        )
        return filtered, len(selected)

    @staticmethod
    def _pick_interval(date_range_days: int) -> int:
        """Map date-range length → sampling interval in days."""
        if date_range_days <= 180:
            return 5
        if date_range_days <= 730:
            return 30
        if date_range_days <= 1825:
            return 60
        return 90