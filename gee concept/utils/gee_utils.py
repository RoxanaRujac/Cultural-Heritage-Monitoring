"""
Google Earth Engine utility functions for heritage site monitoring
Extended with custom index support and additional predefined indices.
"""

import ee
from config.settings import EE_PROJECT_ID, INDICES_CONFIG


class HeritageMonitor:
    """Class for monitoring historical sites using Google Earth Engine"""

    def __init__(self):
        try:
            ee.Initialize(project=EE_PROJECT_ID)
        except:
            raise Exception("Failed to initialize Google Earth Engine")

    def get_sentinel2_collection(self, geometry, start_date, end_date, cloud_cover=20):
        collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                      .filterBounds(geometry)
                      .filterDate(start_date, end_date)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)))
        return collection

    def calculate_indices(self, image, extra_indices=None):
        """
        Calculate spectral indices. Calculeaza toti indicii din INDICES_CONFIG
        plus orice indici custom definiti de utilizator.

        Args:
            image: Earth Engine Image
            extra_indices: lista de dicts cu indici custom:
                [{'name': 'CUSTOM1', 'formula': 'normalized_diff',
                  'band_a': 'B8', 'band_b': 'B4', ...}]
        Returns:
            Image with all index bands added
        """
        bands_to_add = []

        # --- Indici predefiniti din INDICES_CONFIG ---
        for idx_name, cfg in INDICES_CONFIG.items():
            try:
                band = self._compute_index(image, idx_name, cfg)
                if band is not None:
                    bands_to_add.append(band)
            except Exception:
                pass  # ignora daca banda nu exista in imagine

        # --- Indici custom definiti de utilizator ---
        if extra_indices:
            for custom in extra_indices:
                try:
                    band = self._compute_custom_index(image, custom)
                    if band is not None:
                        bands_to_add.append(band)
                except Exception:
                    pass

        if bands_to_add:
            return image.addBands(bands_to_add)
        return image

    def _compute_index(self, image, name, cfg):
        """Calculeaza un indice predefinit pe baza formulei din config."""
        formula = cfg.get('formula', 'normalized_diff')
        bands = cfg.get('bands', [])

        if formula == 'normalized_diff' and len(bands) >= 2:
            return image.normalizedDifference([bands[0], bands[1]]).rename(name)

        elif formula == 'evi':
            # EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
            nir  = image.select('B8').divide(10000)
            red  = image.select('B4').divide(10000)
            blue = image.select('B2').divide(10000)
            evi  = nir.subtract(red).multiply(2.5).divide(
                nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)
            )
            return evi.rename(name)

        elif formula == 'savi':
            # SAVI = (NIR - Red) / (NIR + Red + 0.5) * 1.5
            L = 0.5
            nir = image.select('B8').divide(10000)
            red = image.select('B4').divide(10000)
            savi = nir.subtract(red).divide(
                nir.add(red).add(L)
            ).multiply(1 + L)
            return savi.rename(name)

        elif formula == 'bsi':
            # BSI = (SWIR1 + Red) - (NIR + Blue) / (SWIR1 + Red) + (NIR + Blue)
            swir = image.select('B11')
            red  = image.select('B4')
            nir  = image.select('B8')
            blue = image.select('B2')
            bsi = (swir.add(red).subtract(nir.add(blue))).divide(
                   swir.add(red).add(nir.add(blue)))
            return bsi.rename(name)

        elif formula == 'ibi':
            # IBI = (NDBI - (SAVI + MNDWI)/2) / (NDBI + (SAVI + MNDWI)/2)
            ndbi  = image.normalizedDifference(['B11', 'B8'])
            mndwi = image.normalizedDifference(['B3', 'B11'])
            L = 0.5
            nir = image.select('B8').divide(10000)
            red = image.select('B4').divide(10000)
            savi = nir.subtract(red).divide(nir.add(red).add(L)).multiply(1 + L)
            mean_savi_mndwi = savi.add(mndwi).divide(2)
            ibi = ndbi.subtract(mean_savi_mndwi).divide(
                  ndbi.add(mean_savi_mndwi))
            return ibi.rename(name)

        return None

    def _compute_custom_index(self, image, custom):
        """
        Calculeaza un indice custom definit de utilizator.

        custom dict poate contine:
          - formula: 'normalized_diff' | 'ratio' | 'difference' | 'expression'
          - name: str
          - band_a, band_b: pentru normalized_diff / ratio / difference
          - expression: str cu expresie EE (ex: '(B8-B4)/(B8+B4)')
          - expression_bands: dict de mapare {var: band} pentru expression
        """
        name    = custom.get('name', 'CUSTOM')
        formula = custom.get('formula', 'normalized_diff')

        if formula == 'normalized_diff':
            band_a = custom['band_a']
            band_b = custom['band_b']
            return image.normalizedDifference([band_a, band_b]).rename(name)

        elif formula == 'ratio':
            band_a = custom['band_a']
            band_b = custom['band_b']
            return image.select(band_a).divide(image.select(band_b)).rename(name)

        elif formula == 'difference':
            band_a = custom['band_a']
            band_b = custom['band_b']
            return image.select(band_a).subtract(image.select(band_b)).rename(name)

        elif formula == 'expression':
            expr   = custom['expression']
            expr_map = custom.get('expression_bands', {})
            band_map = {k: image.select(v) for k, v in expr_map.items()}
            return image.expression(expr, band_map).rename(name)

        return None

    def detect_changes(self, image1, image2, index='NDVI', threshold=0.2):
        diff = image2.select(index).subtract(image1.select(index))
        change_mask = diff.abs().gt(threshold)
        return diff.updateMask(change_mask)

    def calculate_statistics(self, image, geometry, index='NDVI'):
        stats = image.select(index).reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.stdDev(),
                sharedInputs=True
            ).combine(
                reducer2=ee.Reducer.minMax(),
                sharedInputs=True
            ),
            geometry=geometry,
            scale=10,
            maxPixels=1e9
        )
        return stats.getInfo()

    def classify_land_cover(self, image, training_points=None):
        bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'NDVI', 'NDBI', 'NDMI']
        if training_points:
            training = image.select(bands).sampleRegions(
                collection=training_points,
                properties=['class'],
                scale=10
            )
            classifier = ee.Classifier.smileRandomForest(50).train(
                features=training,
                classProperty='class',
                inputProperties=bands
            )
            return image.select(bands).classify(classifier)
        return None