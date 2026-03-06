"""
Configuration settings for Heritage Site Monitoring System
"""

PAGE_CONFIG = {
    'page_title': "Heritage Site Monitor",
    'page_icon': "🏛️",
    'layout': "wide",
    'initial_sidebar_state': "expanded"
}

THEME_CSS = """
<style>

/* ── VARIABLES ───────────────────────────────────────────── */
:root {
  --purple:        #764ba2;
  --purple-dark:   #4a2d6b;
  --purple-light:  #9b6fc5;
  --purple-faint:  #f3edf9;
  --yellow:        #f0c040;
  --yellow-light:  #fef9e7;
  --dark:          #1a1a2e;
  --grey-900:      #2c2c3e;
  --grey-700:      #4a4a6a;
  --grey-500:      #6b6b8a;
  --grey-300:      #c5c5d8;
  --grey-100:      #f0f0f5;
  --white:         #ffffff;
  --success:       #2d7a4f;
  --success-bg:    #eaf5ef;
  --warning-bg:    #fef9e7;
  --info-bg:       #f3edf9;
}

/* ── APP BACKGROUND ──────────────────────────────────────── */
.stApp {
  background-color: #22222e;
}

/* ── MAIN HEADER ─────────────────────────────────────────── */
.main-header {
  font-size: 2.2rem;
  font-weight: 700;
  text-align: center;
  padding: 1rem 0 0.5rem;
  background: linear-gradient(135deg, var(--purple) 80%, var(--purple-light) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.5px;
}

/* ── SIDEBAR ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1a1a2e 0%, #2c2040 100%) !important;
}
[data-testid="stSidebar"] * {
  color: #e8e0f0 !important;
}
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] header {
  color: var(--yellow) !important;
  border-bottom: 1px solid rgba(240,192,64,0.3);
  padding-bottom: 4px;
}
[data-testid="stSidebar"] hr {
  border-color: rgba(118,75,162,0.4) !important;
}
/* Sidebar inputs */
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stNumberInput > div > div > input {
  background-color: rgba(118,75,162,0.15) !important;
  border: 1px solid rgba(118,75,162,0.5) !important;
  color: #e8e0f0 !important;
  border-radius: 6px !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div:focus-within,
[data-testid="stSidebar"] .stTextInput > div > div > input:focus {
  border-color: var(--yellow) !important;
  box-shadow: 0 0 0 2px rgba(240,192,64,0.25) !important;
}
/* Slider track */
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] [role="progressbar"] {
  background: linear-gradient(to right, var(--purple), var(--purple-light)) !important;
}
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] [role="slider"] {
  background: var(--yellow) !important;
  border-color: var(--yellow-dark, #d4a017) !important;
}
/* Multiselect tags */
[data-testid="stSidebar"] .stMultiSelect span[data-baseweb="tag"] {
  background-color: var(--purple) !important;
  color: white !important;
  border-radius: 4px !important;
}
/* Expander */
[data-testid="stSidebar"] .streamlit-expanderHeader {
  background: rgba(118,75,162,0.2) !important;
  border: 1px solid rgba(118,75,162,0.4) !important;
  border-radius: 6px !important;
  color: #e8e0f0 !important;
}
[data-testid="stSidebar"] .streamlit-expanderHeader:hover {
  background: rgba(118,75,162,0.35) !important;
  border-color: var(--yellow) !important;
}
[data-testid="stSidebar"] .streamlit-expanderContent {
  background: rgba(26,26,46,0.6) !important;
  border: 1px solid rgba(118,75,162,0.3) !important;
  border-top: none !important;
  border-radius: 0 0 6px 6px !important;
}

/* ── PRIMARY BUTTON (Run Analysis, Add Index etc.) ───────── */
.stButton > button[kind="primary"],
button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--purple-dark) 0%, var(--purple) 100%) !important;
  color: white !important;
  border: none !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  letter-spacing: 0.3px !important;
  transition: all 0.2s !important;
  box-shadow: 0 2px 8px rgba(118,75,162,0.4) !important;
}
.stButton > button[kind="primary"]:hover,
button[kind="primary"]:hover {
  background: linear-gradient(135deg, var(--purple) 0%, var(--purple-light) 100%) !important;
  box-shadow: 0 4px 14px rgba(118,75,162,0.55) !important;
  transform: translateY(-1px) !important;
}
/* Secondary / normal button */
.stButton > button:not([kind="primary"]),
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
  background: transparent !important;
  color: var(--purple) !important;
  border: 1px solid var(--purple) !important;
  border-radius: 6px !important;
  font-weight: 500 !important;
  transition: all 0.2s !important;
}
.stButton > button:not([kind="primary"]):hover {
  background: var(--purple-faint) !important;
  border-color: var(--purple-light) !important;
  color: var(--purple-dark) !important;
}
/* Download button */
.stDownloadButton > button {
  background: linear-gradient(135deg, #2c2040 0%, var(--purple-dark) 100%) !important;
  color: var(--yellow) !important;
  border: 1px solid rgba(240,192,64,0.4) !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
  background: var(--purple-dark) !important;
  border-color: var(--yellow) !important;
  box-shadow: 0 0 12px rgba(240,192,64,0.3) !important;
}

/* ── TAB RADIO (custom tabs in app.py) ───────────────────── */
div[role="radiogroup"] {
  display: flex !important;
  flex-direction: row !important;
  gap: 3px !important;
  border-bottom: 2px solid var(--purple) !important;
  padding-bottom: 0 !important;
  margin-bottom: 24px !important;
  background: transparent !important;
}
div[role="radiogroup"] label {
  padding: 9px 22px !important;
  border-radius: 8px 8px 0 0 !important;
  border: 1px solid var(--grey-300) !important;
  border-bottom: none !important;
  cursor: pointer !important;
  font-weight: 500 !important;
  font-size: 0.9rem !important;
  background: var(--purple) !important;
  color: var(--grey-700) !important;
  transition: all 0.15s !important;
  margin-bottom: -2px !important;
}
div[role="radiogroup"] label:hover {
  background: var(--purple-faint) !important;
  color: var(--purple) !important;
  border-color: var(--purple-light) !important;
}
div[role="radiogroup"] label:has(input:checked) {
  background: var(--purple) !important;
  color: white !important;
  border-color: var(--purple) !important;
  font-weight: 700 !important;
  box-shadow: 0 -2px 6px rgba(118,75,162,0.25) !important;
}
div[role="radiogroup"] label:has(input:checked)::after {
  content: '' !important;
  display: block !important;
  height: 2px !important;
  background: var(--yellow) !important;
  position: absolute !important;
  bottom: -1px !important;
  left: 0 !important;
  right: 0 !important;
}
div[role="radiogroup"] input {
  display: none !important;
}

/* ── METRICS ─────────────────────────────────────────────── */
[data-testid="stMetricValue"] {
  color: var(--purple-dark) !important;
  font-weight: 700 !important;
}
[data-testid="stMetricDelta"] {
  font-weight: 600 !important;
}
[data-testid="stMetricDeltaIcon-Up"] { color: var(--success) !important; }
[data-testid="stMetricDeltaIcon-Down"] { color: #c0392b !important; }

/* ── EXPANDERS (main content) ────────────────────────────── */
.streamlit-expanderHeader {
  background: var(--purple-faint) !important;
  border: 1px solid var(--grey-300) !important;
  border-radius: 8px !important;
  color: var(--grey-900) !important;
  font-weight: 600 !important;
}
.streamlit-expanderHeader:hover {
  background: #e8ddf5 !important;
  border-color: var(--purple) !important;
}
.streamlit-expanderContent {
  border: 1px solid var(--grey-300) !important;
  border-top: none !important;
  border-radius: 0 0 8px 8px !important;
  background: white !important;
}

/* ── ALERTS / INFO / SUCCESS / WARNING ───────────────────── */
/* st.info → purple tones */
[data-testid="stAlert"][kind="info"],
div[data-testid="stAlert"] > div[data-baseweb="notification"][kind="info"] {
  background-color: var(--info-bg) !important;
  border-left-color: var(--purple) !important;
  color: var(--grey-900) !important;
  border-radius: 8px !important;
}
/* st.success → green (keep readable, just tweak border) */
[data-testid="stAlert"][kind="success"],
div[data-baseweb="notification"][kind="positive"] {
  background-color: var(--success-bg) !important;
  border-left-color: var(--success) !important;
  border-radius: 8px !important;
}
/* st.warning → yellow tones */
[data-testid="stAlert"][kind="warning"],
div[data-baseweb="notification"][kind="warning"] {
  background-color: var(--warning-bg) !important;
  border-left-color: var(--yellow) !important;
  border-radius: 8px !important;
  color: var(--grey-900) !important;
}
/* st.error → dark purple-red */
[data-testid="stAlert"][kind="error"],
div[data-baseweb="notification"][kind="negative"] {
  background-color: #f9edf3 !important;
  border-left-color: var(--purple-dark) !important;
  border-radius: 8px !important;
}

/* ── PROGRESS BAR ────────────────────────────────────────── */
.stProgress > div > div > div > div {
  background: linear-gradient(90deg, var(--purple) 0%, var(--yellow) 100%) !important;
  border-radius: 4px !important;
}

/* ── SPINNER ─────────────────────────────────────────────── */
.stSpinner > div > div {
  border-top-color: var(--purple) !important;
}

/* ── HORIZONTAL DIVIDER ──────────────────────────────────── */
hr {
  border-color: var(--grey-300) !important;
}

/* ── SELECTBOX / MULTISELECT (main area) ─────────────────── */
.stSelectbox > div > div,
.stMultiSelect > div > div {
  border-color: var(--grey-300) !important;
  border-radius: 6px !important;
}
.stSelectbox > div > div:focus-within,
.stMultiSelect > div > div:focus-within {
  border-color: var(--purple) !important;
  box-shadow: 0 0 0 2px rgba(118,75,162,0.2) !important;
}
.stMultiSelect span[data-baseweb="tag"] {
  background-color: var(--purple) !important;
  color: white !important;
  border-radius: 4px !important;
}

/* ── TABLES (st.table, history) ──────────────────────────── */
[data-testid="stTable"] table thead tr th {
  background: var(--purple) !important;
  color: white !important;
  font-weight: 600 !important;
}
[data-testid="stTable"] table tbody tr:nth-child(even) {
  background: var(--purple) !important;
}
[data-testid="stTable"] table tbody tr:hover {
  background: #e8ddf5 !important;
}

/* ── PLOTLY CHARTS — force consistent style via wrapper ──── */
.js-plotly-plot .plotly .modebar-btn path {
  fill: var(--purple) !important;
}

/* ── FOOTER ──────────────────────────────────────────────── */
.footer-text {
  text-align: center;
  color: var(--grey-500);
  font-size: 0.85rem;
  margin-top: 8px;
}

/* ── LEGEND BOX ──────────────────────────────────────────── */
.legend-box {
  background: var(--purple-faint);
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid var(--purple);
  margin: 10px 0;
}

/* ── METRIC CARD (custom HTML cards) ────────────────────── */
.metric-card {
  background: linear-gradient(135deg, var(--purple-dark) 0%, var(--purple) 100%);
  padding: 1rem;
  border-radius: 10px;
  color: white;
  box-shadow: 0 4px 12px rgba(118,75,162,0.3);
}

/* ── CODE BLOCKS ─────────────────────────────────────────── */
code, pre {
  background: #2c2040 !important;
  color: var(--yellow) !important;
  border-radius: 5px !important;
}

/* ── SCROLLBAR ───────────────────────────────────────────── */
::-webkit-scrollbar { width: 7px; }
::-webkit-scrollbar-track { background: var(--grey-100); }
::-webkit-scrollbar-thumb { background: var(--purple); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--purple-dark); }

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