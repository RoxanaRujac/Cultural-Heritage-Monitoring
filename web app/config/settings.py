"""
Global application settings — only constants and default values.
"""

PAGE_CONFIG = {
    'page_title': "Heritage Site Monitor",
    'page_icon': "🏛️",
    'layout': "wide",
    'initial_sidebar_state': "expanded"
}

# Earth Engine
EE_PROJECT_ID = "first-project-481215"

# Data acquisition defaults
DEFAULT_CLOUD_COVER = 20
DEFAULT_BUFFER_KM = 2.0
DEFAULT_DAYS_BACK = 730

# Export
EXPORT_FOLDER = 'Heritage_Site_Exports'

# GEE pixel limit for GIF generation
GEE_MAX_PIXELS = 26_214_400

# Available color palettes for custom index builder
AVAILABLE_PALETTES = {
    'Red → Yellow → Green':     ['FF0000', 'FFFF00', '00AA00'],
    'Green → Yellow → Red':     ['00AA00', 'FFFF00', 'FF0000'],
    'Brown → White → Blue':     ['8B4513', 'FFFFFF', '0000FF'],
    'Blue → White → Red':       ['0000FF', 'FFFFFF', 'FF0000'],
    'White → Blue':             ['FFFFFF', '0000FF'],
    'Green → White → Red':      ['00AA00', 'FFFFFF', 'FF0000'],
    'Black → White':            ['000000', 'FFFFFF'],
    'Green → White → Brown':    ['00AA00', 'FFFFFF', '8B4513'],
    'Purple → White → Orange':  ['800080', 'FFFFFF', 'FFA500'],
}

# Index categories used in sidebar filter
INDEX_CATEGORIES = ['Vegetation', 'Urban', 'Moisture', 'Soil', 'Fire', 'Custom']