"""
Sentinel-2 band definitions and spectral indices catalogue.
"""

SENTINEL2_BANDS = {
    'B1':  {'name': 'B1 - Coastal Aerosol (443nm)',  'wavelength': 443,  'resolution': 60},
    'B2':  {'name': 'B2 - Blue (490nm)',              'wavelength': 490,  'resolution': 10},
    'B3':  {'name': 'B3 - Green (560nm)',             'wavelength': 560,  'resolution': 10},
    'B4':  {'name': 'B4 - Red (665nm)',               'wavelength': 665,  'resolution': 10},
    'B5':  {'name': 'B5 - Red Edge 1 (705nm)',        'wavelength': 705,  'resolution': 20},
    'B6':  {'name': 'B6 - Red Edge 2 (740nm)',        'wavelength': 740,  'resolution': 20},
    'B7':  {'name': 'B7 - Red Edge 3 (783nm)',        'wavelength': 783,  'resolution': 20},
    'B8':  {'name': 'B8 - NIR (842nm)',               'wavelength': 842,  'resolution': 10},
    'B8A': {'name': 'B8A - Narrow NIR (865nm)',       'wavelength': 865,  'resolution': 20},
    'B9':  {'name': 'B9 - Water Vapour (945nm)',      'wavelength': 945,  'resolution': 60},
    'B11': {'name': 'B11 - SWIR 1 (1610nm)',          'wavelength': 1610, 'resolution': 20},
    'B12': {'name': 'B12 - SWIR 2 (2190nm)',          'wavelength': 2190, 'resolution': 20},
}

# Each entry defines everything needed to compute + visualize + describe an index.
INDICES_CONFIG = {

    # ── Vegetation ──────────────────────────────────────────────────────────
    'NDVI': {
        'name': 'Vegetation Index',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B4'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.2, 'max': 0.8,
        'category': 'Vegetation',
        'description': 'Vegetation health. High = dense healthy vegetation.',
        'heritage_use': 'Monitor vegetation encroachment and landscape change around structures.',
    },
    'EVI': {
        'name': 'Enhanced Vegetation Index',
        'formula': 'evi',
        'bands': ['B8', 'B4', 'B2'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.2, 'max': 0.8,
        'category': 'Vegetation',
        'description': 'Improved vegetation index reducing atmospheric and soil background noise.',
        'heritage_use': 'More accurate vegetation monitoring in areas with dense canopy or high aerosols.',
    },
    'SAVI': {
        'name': 'Soil-Adjusted Vegetation Index',
        'formula': 'savi',
        'bands': ['B8', 'B4'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.5, 'max': 1.0,
        'category': 'Vegetation',
        'description': 'Vegetation index corrected for soil brightness effect.',
        'heritage_use': 'Better vegetation detection in arid or semi-arid sites with exposed soil.',
    },
    'NDRE': {
        'name': 'Red Edge Vegetation Index',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B5'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.2, 'max': 0.8,
        'category': 'Vegetation',
        'description': 'Sensitive to chlorophyll content using Red Edge band.',
        'heritage_use': 'Detect early vegetation stress before it becomes visible in NDVI.',
    },

    # ── Urban ────────────────────────────────────────────────────────────────
    'NDBI': {
        'name': 'Built-up Index',
        'formula': 'normalized_diff',
        'bands': ['B11', 'B8'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -0.5, 'max': 0.5,
        'category': 'Urban',
        'description': 'Highlights built-up and urban areas. High = urban.',
        'heritage_use': 'Monitor urban expansion and new construction in the buffer zone.',
    },
    'UI': {
        'name': 'Urban Index',
        'formula': 'normalized_diff',
        'bands': ['B12', 'B8A'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -0.5, 'max': 0.5,
        'category': 'Urban',
        'description': 'Alternative urban index using SWIR2 and Narrow NIR.',
        'heritage_use': 'Cross-validate NDBI for urban encroachment detection.',
    },
    'IBI': {
        'name': 'Index-Based Built-up Index',
        'formula': 'ibi',
        'bands': ['B11', 'B8', 'B3', 'B4'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -1.0, 'max': 1.0,
        'category': 'Urban',
        'description': 'Combined built-up index using NDBI, MNDWI and NDVI.',
        'heritage_use': 'High accuracy urban detection combining multiple spectral signals.',
    },

    # ── Moisture / Water ─────────────────────────────────────────────────────
    'NDMI': {
        'name': 'Moisture Index',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B11'],
        'palette': ['8B4513', 'FFFFFF', '0000FF'],
        'min': -0.5, 'max': 0.5,
        'category': 'Moisture',
        'description': 'Soil and vegetation moisture. High = wet.',
        'heritage_use': 'Assess waterlogging risk and moisture-related structural damage.',
    },
    'NDWI': {
        'name': 'Water Index',
        'formula': 'normalized_diff',
        'bands': ['B3', 'B8'],
        'palette': ['FFFFFF', '0000FF'],
        'min': -0.5, 'max': 0.5,
        'category': 'Moisture',
        'description': 'Surface water detection. Positive values = open water.',
        'heritage_use': 'Monitor flooding risk and proximity to water bodies.',
    },
    'MNDWI': {
        'name': 'Modified Water Index',
        'formula': 'normalized_diff',
        'bands': ['B3', 'B11'],
        'palette': ['FFFFFF', '0000FF'],
        'min': -0.5, 'max': 0.5,
        'category': 'Moisture',
        'description': 'Improved water index suppressing built-up noise.',
        'heritage_use': 'More accurate water detection in urban heritage contexts.',
    },

    # ── Soil ─────────────────────────────────────────────────────────────────
    'BSI': {
        'name': 'Bare Soil Index',
        'formula': 'bsi',
        'bands': ['B11', 'B4', 'B8', 'B2'],
        'palette': ['00AA00', 'FFFFFF', '8B4513'],
        'min': -1, 'max': 1,
        'category': 'Soil',
        'description': 'Bare soil exposure. High = exposed bare soil.',
        'heritage_use': 'Identify erosion-prone areas and soil disturbance near structures.',
    },
    'RI': {
        'name': 'Redness Index',
        'formula': 'normalized_diff',
        'bands': ['B4', 'B3'],
        'palette': ['00AA00', 'FFFFFF', 'FF4500'],
        'min': -0.5, 'max': 0.5,
        'category': 'Soil',
        'description': 'Iron oxide content in exposed soils.',
        'heritage_use': 'Detect soil type changes and archaeological features in bare soil areas.',
    },

    # ── Fire ─────────────────────────────────────────────────────────────────
    'NBR': {
        'name': 'Normalized Burn Ratio',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B12'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -1, 'max': 1,
        'category': 'Fire',
        'description': 'Fire damage assessment. Low = burned area.',
        'heritage_use': 'Assess wildfire impact on landscape surrounding heritage sites.',
    },
    'BAI': {
        'name': 'Burned Area Index',
        'formula': 'normalized_diff',
        'bands': ['B12', 'B8A'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -0.5, 'max': 0.5,
        'category': 'Fire',
        'description': 'Highlights recently burned areas.',
        'heritage_use': 'Post-fire damage mapping around heritage sites.',
    },
}