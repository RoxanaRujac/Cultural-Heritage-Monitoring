"""
Responsible for: computing spectral indices on EE Images.
"""

import ee
from config.indices_config import INDICES_CONFIG


class IndexCalculator:
    """
    Adds spectral index bands to an EE Image.

    Supports all indices defined in config/indices_config.py plus
    arbitrary user-defined custom indices passed at runtime.

    Usage:
        calc = IndexCalculator()
        image_with_indices = calc.compute(image)
        image_with_all     = calc.compute(image, extra_indices=[custom_dict])
    """

    def compute(
        self,
        image: ee.Image,
        extra_indices: list[dict] | None = None,
    ) -> ee.Image:
        """
        Add all configured + custom index bands to *image*.

        Args:
            image:         Source Sentinel-2 ee.Image.
            extra_indices: List of custom index dicts from the UI builder.

        Returns:
            ee.Image with all index bands appended.
        """
        bands_to_add = []

        for name, cfg in INDICES_CONFIG.items():
            band = self._compute_predefined(image, name, cfg)
            if band is not None:
                bands_to_add.append(band)

        if extra_indices:
            for custom in extra_indices:
                band = self._compute_custom(image, custom)
                if band is not None:
                    bands_to_add.append(band)

        return image.addBands(bands_to_add) if bands_to_add else image

    # ── Predefined formulas ──────────────────────────────────────────────────

    def _compute_predefined(
        self, image: ee.Image, name: str, cfg: dict
    ) -> ee.Image | None:
        formula = cfg.get('formula', 'normalized_diff')
        bands   = cfg.get('bands', [])

        try:
            if formula == 'normalized_diff' and len(bands) >= 2:
                return image.normalizedDifference([bands[0], bands[1]]).rename(name)

            if formula == 'evi':
                return self._evi(image, name)

            if formula == 'savi':
                return self._savi(image, name)

            if formula == 'bsi':
                return self._bsi(image, name)

            if formula == 'ibi':
                return self._ibi(image, name)

        except Exception:
            pass  # Band may not exist in this image; silently skip.

        return None

    # ── Named formula implementations ───────────────────────────────────────

    def _evi(self, image: ee.Image, name: str) -> ee.Image:
        """EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)"""
        nir  = image.select('B8').divide(10000)
        red  = image.select('B4').divide(10000)
        blue = image.select('B2').divide(10000)
        return (
            nir.subtract(red).multiply(2.5)
            .divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1))
            .rename(name)
        )

    def _savi(self, image: ee.Image, name: str) -> ee.Image:
        """SAVI = (NIR - Red) / (NIR + Red + 0.5) * 1.5"""
        L   = 0.5
        nir = image.select('B8').divide(10000)
        red = image.select('B4').divide(10000)
        return (
            nir.subtract(red)
            .divide(nir.add(red).add(L))
            .multiply(1 + L)
            .rename(name)
        )

    def _bsi(self, image: ee.Image, name: str) -> ee.Image:
        """BSI = ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))"""
        swir = image.select('B11')
        red  = image.select('B4')
        nir  = image.select('B8')
        blue = image.select('B2')
        num  = swir.add(red).subtract(nir.add(blue))
        den  = swir.add(red).add(nir.add(blue))
        return num.divide(den).rename(name)

    def _ibi(self, image: ee.Image, name: str) -> ee.Image:
        """IBI = (NDBI - (SAVI + MNDWI)/2) / (NDBI + (SAVI + MNDWI)/2)"""
        ndbi  = image.normalizedDifference(['B11', 'B8'])
        mndwi = image.normalizedDifference(['B3', 'B11'])
        savi  = self._savi(image, 'savi_tmp')
        mean  = savi.add(mndwi).divide(2)
        return ndbi.subtract(mean).divide(ndbi.add(mean)).rename(name)

    # ── Custom index ─────────────────────────────────────────────────────────

    def _compute_custom(self, image: ee.Image, custom: dict) -> ee.Image | None:
        """
        Compute a user-defined index from the sidebar Custom Index Builder.

        Supported formulas: normalized_diff | ratio | difference | expression
        """
        name    = custom.get('name', 'CUSTOM')
        formula = custom.get('formula', 'normalized_diff')

        try:
            if formula == 'normalized_diff':
                return image.normalizedDifference(
                    [custom['band_a'], custom['band_b']]
                ).rename(name)

            if formula == 'ratio':
                return (
                    image.select(custom['band_a'])
                    .divide(image.select(custom['band_b']))
                    .rename(name)
                )

            if formula == 'difference':
                return (
                    image.select(custom['band_a'])
                    .subtract(image.select(custom['band_b']))
                    .rename(name)
                )

            if formula == 'expression':
                band_map = {
                    var: image.select(band)
                    for var, band in custom.get('expression_bands', {}).items()
                }
                return image.expression(custom['expression'], band_map).rename(name)

        except Exception:
            pass

        return None