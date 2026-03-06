"""
Responsible for: detecting and sampling spatial change between two EE Images.
"""

import ee
from datetime import datetime


SEVERITY_THRESHOLDS = {
    'critical': 0.30,
    'high':     0.15,
    'moderate': 0.07,
}

SEVERITY_COLOR = {
    'critical': '#c0392b',
    'high':     '#e67e22',
    'moderate': '#f0c040',
    'low':      '#764ba2',
}

SEVERITY_LABEL = {
    'critical': '🔴 Critical',
    'high':     '🟠 High',
    'moderate': '🟡 Moderate',
    'low':      '🟣 Low',
}


def _classify_severity(delta: float) -> str:
    abs_delta = abs(delta)
    if abs_delta >= SEVERITY_THRESHOLDS['critical']:
        return 'critical'
    if abs_delta >= SEVERITY_THRESHOLDS['high']:
        return 'high'
    if abs_delta >= SEVERITY_THRESHOLDS['moderate']:
        return 'moderate'
    return 'low'


class ChangeDetector:
    """
    Detects significant pixel-level changes between two EE Images for a
    given spectral index, and returns structured event records.

    Usage:
        detector = ChangeDetector()
        events = detector.sample_change_points(
            first_image, last_image, aoi, 'NDVI', threshold=0.20
        )
        overlay_image = detector.build_change_overlay(first_image, last_image, 'NDVI', threshold=0.20)
    """

    SAMPLE_SCALE    = 30    # metres — coarser grid for efficient sampling
    MAX_SAMPLE_PTS  = 15

    def sample_change_points(
        self,
        first_image: ee.Image,
        last_image: ee.Image,
        aoi: ee.Geometry,
        index: str,
        threshold: float = 0.20,
        n_points: int = MAX_SAMPLE_PTS,
    ) -> list[dict]:
        """
        Sample locations where |delta| > threshold.

        Returns:
            List of event dicts sorted by |delta| descending.
            Each dict contains: lat, lon, value_before, value_after,
            delta, severity, label.
        """
        diff = last_image.select(index).subtract(first_image.select(index))

        combined = (
            first_image.select(index).rename('before')
            .addBands(last_image.select(index).rename('after'))
            .addBands(diff.rename('delta'))
        )
        combined_masked = combined.updateMask(diff.abs().gt(threshold))

        try:
            samples = combined_masked.sample(
                region=aoi,
                scale=self.SAMPLE_SCALE,
                numPixels=n_points,
                seed=42,
                geometries=True,
            ).getInfo()
        except Exception:
            return []

        events = []
        for feat in samples.get('features', []):
            props  = feat.get('properties', {})
            coords = feat.get('geometry', {}).get('coordinates', [0, 0])
            delta  = props.get('delta', 0)
            vb     = props.get('before', 0)
            va     = props.get('after', 0)
            sev    = _classify_severity(delta)
            direction = "decrease" if delta < 0 else "increase"

            events.append({
                'lat':          coords[1],
                'lon':          coords[0],
                'value_before': round(vb, 4),
                'value_after':  round(va, 4),
                'delta':        round(delta, 4),
                'severity':     sev,
                'label':        f"{index} {direction}: {vb:.3f} → {va:.3f} (Δ{delta:+.3f})",
            })

        events.sort(key=lambda e: abs(e['delta']), reverse=True)
        return events

    def build_change_overlay(
        self,
        first_image: ee.Image,
        last_image: ee.Image,
        index: str,
        threshold: float = 0.20,
    ) -> ee.Image:
        """
        Build an RGB ee.Image overlay:
          - Decreases → red tint
          - Increases → blue tint
          - No significant change → transparent mask

        Returns:
            ee.Image with bands vis-red, vis-green, vis-blue (uint8).
        """
        vis_rgb = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4}

        diff          = last_image.select(index).subtract(first_image.select(index))
        decrease_mask = diff.lt(-threshold)
        increase_mask = diff.gt(threshold)
        change_mask   = decrease_mask.Or(increase_mask)

        r = ee.Image(255).multiply(decrease_mask).add(ee.Image(0).multiply(increase_mask))
        g = ee.Image(0)
        b = ee.Image(0).multiply(decrease_mask).add(ee.Image(200).multiply(increase_mask))

        change_colored = (
            ee.Image.cat([r, g, b])
            .rename(['vis-red', 'vis-green', 'vis-blue'])
            .toUint8()
            .updateMask(change_mask)
        )
        after_rgb = last_image.visualize(**vis_rgb)

        r_f = after_rgb.select('vis-red').where(
            change_mask,
            after_rgb.select('vis-red').multiply(0.3).add(change_colored.select('vis-red').multiply(0.7))
        )
        g_f = after_rgb.select('vis-green').where(
            change_mask,
            after_rgb.select('vis-green').multiply(0.3).add(change_colored.select('vis-green').multiply(0.7))
        )
        b_f = after_rgb.select('vis-blue').where(
            change_mask,
            after_rgb.select('vis-blue').multiply(0.3).add(change_colored.select('vis-blue').multiply(0.7))
        )

        return (
            ee.Image.cat([r_f, g_f, b_f])
            .rename(['vis-red', 'vis-green', 'vis-blue'])
            .toUint8()
        )