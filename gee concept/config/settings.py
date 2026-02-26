"""
Configuration settings for Heritage Site Monitoring System
"""

# Page configuration
PAGE_CONFIG = {
    'page_title': "Heritage Site Monitor",
    'page_icon': "🏛️",
    'layout': "wide",
    'initial_sidebar_state': "expanded"
}

# Custom CSS
CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        padding: 1rem;
        background: #764ba2;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card {
        background: #764ba2;
        padding: 1rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stAlert {
        background-color: #f0f2f6;
        border-left: 4px solid #667eea;
    }
    .legend-box {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 10px 0;
    }
</style>
"""

# Default site presets
SITE_PRESETS = {
    'Alba Iulia Fortress (Romania)': {
        'lat': 46.0686,
        'lon': 23.5714,
        'buffer_km': 2.0
    },
    'Sagrada Familia (Spain)': {
        'lat': 41.4036,
        'lon': 2.1744,
        'buffer_km': 1.0
    },
    'Pyramids of Giza (Egypt)': {
        'lat': 29.9792,
        'lon': 31.1342,
        'buffer_km': 2.5
    },
    'Machu Picchu (Peru)': {
        'lat': -13.1631,
        'lon': -72.5450,
        'buffer_km': 1.5
    },
    'Colosseum Rome (Italy)': {
        'lat': 41.8902,
        'lon': 12.4922,
        'buffer_km': 0.8
    },
    'Taj Mahal (India)': {
        'lat': 27.1751,
        'lon': 78.0421,
        'buffer_km': 1.2
    },
    'Acropolis of Athens (Greece)': {
        'lat': 37.9715,
        'lon': 23.7257,
        'buffer_km': 1.0
    },
    'Custom Region': {
        'lat': 46.0686,
        'lon': 23.5714,
        'buffer_km': 2.0
    }
}


# ---------------------------------------------------------------------------
# Sentinel-2 bands - custom index construction
# ---------------------------------------------------------------------------
SENTINEL2_BANDS = {
    'B1':  {'name': 'B1 - Coastal Aerosol (443nm)',   'wavelength': 443,  'resolution': 60},
    'B2':  {'name': 'B2 - Blue (490nm)',               'wavelength': 490,  'resolution': 10},
    'B3':  {'name': 'B3 - Green (560nm)',              'wavelength': 560,  'resolution': 10},
    'B4':  {'name': 'B4 - Red (665nm)',                'wavelength': 665,  'resolution': 10},
    'B5':  {'name': 'B5 - Red Edge 1 (705nm)',         'wavelength': 705,  'resolution': 20},
    'B6':  {'name': 'B6 - Red Edge 2 (740nm)',         'wavelength': 740,  'resolution': 20},
    'B7':  {'name': 'B7 - Red Edge 3 (783nm)',         'wavelength': 783,  'resolution': 20},
    'B8':  {'name': 'B8 - NIR (842nm)',                'wavelength': 842,  'resolution': 10},
    'B8A': {'name': 'B8A - Narrow NIR (865nm)',        'wavelength': 865,  'resolution': 20},
    'B9':  {'name': 'B9 - Water Vapour (945nm)',       'wavelength': 945,  'resolution': 60},
    'B11': {'name': 'B11 - SWIR 1 (1610nm)',           'wavelength': 1610, 'resolution': 20},
    'B12': {'name': 'B12 - SWIR 2 (2190nm)',           'wavelength': 2190, 'resolution': 20},
}

# ----------------------------------------------------
# Palettes
# ----------------------------------------------------
AVAILABLE_PALETTES = {
    'Red → Yellow → Green': ['FF0000', 'FFFF00', '00AA00'],
    'Green → Yellow → Red': ['00AA00', 'FFFF00', 'FF0000'],
    'Brown → White → Blue': ['8B4513', 'FFFFFF', '0000FF'],
    'Blue → White → Red':   ['0000FF', 'FFFFFF', 'FF0000'],
    'White → Blue':         ['FFFFFF', '0000FF'],
    'Green → White → Red':  ['00AA00', 'FFFFFF', 'FF0000'],
    'Black → White':        ['000000', 'FFFFFF'],
    'Green → White → Brown':['00AA00', 'FFFFFF', '8B4513'],
    'Purple → White → Orange': ['800080', 'FFFFFF', 'FFA500'],
}

# ----------------------------------------------------
# Spectral indices
# ----------------------------------------------------
INDICES_CONFIG = {
     # --- Vegetation ---
    'NDVI': {
        'name': 'Vegetation Index',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B4'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.2, 'max': 0.8,
        'category': 'Vegetation',
        'description': 'Vegetation health. High = dense healthy vegetation.',
        'heritage_use': 'Monitor vegetation encroachment and landscape change around structures.'
    },
    'EVI': {
        'name': 'Enhanced Vegetation Index',
        'formula': 'evi',
        'bands': ['B8', 'B4', 'B2'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.2, 'max': 0.8,
        'category': 'Vegetation',
        'description': 'Improved vegetation index reducing atmospheric and soil background noise.',
        'heritage_use': 'More accurate vegetation monitoring in areas with dense canopy or high aerosols.'
    },
    'SAVI': {
        'name': 'Soil-Adjusted Vegetation Index',
        'formula': 'savi',
        'bands': ['B8', 'B4'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.5, 'max': 1.0,
        'category': 'Vegetation',
        'description': 'Vegetation index corrected for soil brightness effect.',
        'heritage_use': 'Better vegetation detection in arid or semi-arid sites with exposed soil.'
    },
    'NDRE': {
        'name': 'Red Edge Vegetation Index',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B5'],
        'palette': ['FF0000', 'FFFF00', '00AA00'],
        'min': -0.2, 'max': 0.8,
        'category': 'Vegetation',
        'description': 'Sensitive to chlorophyll content using Red Edge band.',
        'heritage_use': 'Detect early vegetation stress before it becomes visible in NDVI.'
    },


    # --- Urban ---
    'NDBI': {
        'name': 'Built-up Index',
        'formula': 'normalized_diff',
        'bands': ['B11', 'B8'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -0.5, 'max': 0.5,
        'category': 'Urban',
        'description': 'Highlights built-up and urban areas. High = urban.',
        'heritage_use': 'Monitor urban expansion and new construction in the buffer zone.'
    },
    'UI': {
        'name': 'Urban Index',
        'formula': 'normalized_diff',
        'bands': ['B12', 'B8A'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -0.5, 'max': 0.5,
        'category': 'Urban',
        'description': 'Alternative urban index using SWIR2 and Narrow NIR.',
        'heritage_use': 'Cross-validate NDBI for urban encroachment detection.'
    },
    'IBI': {
        'name': 'Index-Based Built-up Index',
        'formula': 'ibi',
        'bands': ['B11', 'B8', 'B3', 'B4'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -1.0, 'max': 1.0,
        'category': 'Urban',
        'description': 'Combined built-up index using NDBI, MNDWI and NDVI.',
        'heritage_use': 'High accuracy urban detection combining multiple spectral signals.'
    },


    # --- Moisture/Water ---
    'NDMI': {
        'name': 'Moisture Index',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B11'],
        'palette': ['8B4513', 'FFFFFF', '0000FF'],
        'min': -0.5, 'max': 0.5,
        'category': 'Moisture',
        'description': 'Soil and vegetation moisture. High = wet.',
        'heritage_use': 'Assess waterlogging risk and moisture-related structural damage.'
    },
    'NDWI': {
        'name': 'Water Index',
        'formula': 'normalized_diff',
        'bands': ['B3', 'B8'],
        'palette': ['FFFFFF', '0000FF'],
        'min': -0.5, 'max': 0.5,
        'category': 'Moisture',
        'description': 'Surface water detection. Positive values = open water.',
        'heritage_use': 'Monitor flooding risk and proximity to water bodies.'
    },
    'MNDWI': {
        'name': 'Modified Water Index',
        'formula': 'normalized_diff',
        'bands': ['B3', 'B11'],
        'palette': ['FFFFFF', '0000FF'],
        'min': -0.5, 'max': 0.5,
        'category': 'Moisture',
        'description': 'Improved water index suppressing built-up noise.',
        'heritage_use': 'More accurate water detection in urban heritage contexts.'
    },


    # --- Soil ---
    'BSI': {
        'name': 'Bare Soil Index',
        'formula': 'bsi',
        'bands': ['B11', 'B4', 'B8', 'B2'],
        'palette': ['00AA00', 'FFFFFF', '8B4513'],
        'min': -1, 'max': 1,
        'category': 'Soil',
        'description': 'Bare soil exposure. High = exposed bare soil.',
        'heritage_use': 'Identify erosion-prone areas and soil disturbance near structures.'
    },
    'RI': {
        'name': 'Redness Index',
        'formula': 'normalized_diff',
        'bands': ['B4', 'B3'],
        'palette': ['00AA00', 'FFFFFF', 'FF4500'],
        'min': -0.5, 'max': 0.5,
        'category': 'Soil',
        'description': 'Iron oxide content in exposed soils.',
        'heritage_use': 'Detect soil type changes and archaeological features in bare soil areas.'
    },

    # --- Fire ---
    'NBR': {
        'name': 'Normalized Burn Ratio',
        'formula': 'normalized_diff',
        'bands': ['B8', 'B12'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -1, 'max': 1,
        'category': 'Fire',
        'description': 'Fire damage assessment. Low = burned area.',
        'heritage_use': 'Assess wildfire impact on landscape surrounding heritage sites.'
    },
    'BAI': {
        'name': 'Burned Area Index',
        'formula': 'normalized_diff',
        'bands': ['B12', 'B8A'],
        'palette': ['00AA00', 'FFFFFF', 'FF0000'],
        'min': -0.5, 'max': 0.5,
        'category': 'Fire',
        'description': 'Highlights recently burned areas.',
        'heritage_use': 'Post-fire damage mapping around heritage sites.'
    },
}

INDEX_CATEGORIES = ['Vegetation', 'Urban', 'Moisture', 'Soil', 'Fire', 'Custom']

# Analysis types
ANALYSIS_TYPES = [
    "Temporal Monitoring",
    "Change Detection",
    "Land Cover Classification",
    "Comprehensive Report"
]

# Earth Engine project ID
EE_PROJECT_ID = "first-project-481215"

# Default parameters
DEFAULT_CLOUD_COVER = 20
DEFAULT_BUFFER_KM = 2.0
DEFAULT_DAYS_BACK = 730  # 2 years

# Export settings
EXPORT_FOLDER = 'Heritage_Site_Exports'