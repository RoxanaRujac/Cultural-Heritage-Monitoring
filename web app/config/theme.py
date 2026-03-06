"""
Application theme — CSS only
"""

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

.stApp { background-color: #22222e; }

.main-header {
  font-size: 2.2rem; font-weight: 700; text-align: center;
  padding: 1rem 0 0.5rem;
  background: linear-gradient(135deg, var(--purple) 80%, var(--purple-light) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; letter-spacing: -0.5px;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #1a1a2e 0%, #2c2040 100%) !important;
}
[data-testid="stSidebar"] * { color: #e8e0f0 !important; }
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] header {
  color: var(--yellow) !important;
  border-bottom: 1px solid rgba(240,192,64,0.3); padding-bottom: 4px;
}
[data-testid="stSidebar"] hr { border-color: rgba(118,75,162,0.4) !important; }

[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stNumberInput > div > div > input {
  background-color: rgba(118,75,162,0.15) !important;
  border: 1px solid rgba(118,75,162,0.5) !important;
  color: #e8e0f0 !important; border-radius: 6px !important;
}

[data-testid="stSidebar"] .stMultiSelect span[data-baseweb="tag"] {
  background-color: var(--purple) !important; color: white !important; border-radius: 4px !important;
}
[data-testid="stSidebar"] .streamlit-expanderHeader {
  background: rgba(118,75,162,0.2) !important;
  border: 1px solid rgba(118,75,162,0.4) !important;
  border-radius: 6px !important; color: #e8e0f0 !important;
}
[data-testid="stSidebar"] .streamlit-expanderHeader:hover {
  background: rgba(118,75,162,0.35) !important; border-color: var(--yellow) !important;
}
[data-testid="stSidebar"] .streamlit-expanderContent {
  background: rgba(26,26,46,0.6) !important;
  border: 1px solid rgba(118,75,162,0.3) !important;
  border-top: none !important; border-radius: 0 0 6px 6px !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--purple-dark) 0%, var(--purple) 100%) !important;
  color: white !important; border: none !important; border-radius: 8px !important;
  font-weight: 600 !important; transition: all 0.2s !important;
  box-shadow: 0 2px 8px rgba(118,75,162,0.4) !important;
}
.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, var(--purple) 0%, var(--purple-light) 100%) !important;
  box-shadow: 0 4px 14px rgba(118,75,162,0.55) !important; transform: translateY(-1px) !important;
}
.stButton > button:not([kind="primary"]) {
  background: transparent !important; color: var(--purple) !important;
  border: 1px solid var(--purple) !important; border-radius: 6px !important;
  font-weight: 500 !important; transition: all 0.2s !important;
}
.stDownloadButton > button {
  background: linear-gradient(135deg, #2c2040 0%, var(--purple-dark) 100%) !important;
  color: var(--yellow) !important; border: 1px solid rgba(240,192,64,0.4) !important;
  border-radius: 8px !important; font-weight: 600 !important;
}

div[role="radiogroup"] {
  display: flex !important; flex-direction: row !important; gap: 3px !important;
  border-bottom: 2px solid var(--purple) !important; padding-bottom: 0 !important;
  margin-bottom: 24px !important;
}
div[role="radiogroup"] label {
  padding: 9px 22px !important; border-radius: 8px 8px 0 0 !important;
  border: 1px solid var(--grey-300) !important; border-bottom: none !important;
  font-weight: 500 !important; font-size: 0.9rem !important;
  background: var(--purple) !important; color: var(--grey-700) !important;
  margin-bottom: -2px !important;
}
div[role="radiogroup"] label:has(input:checked) {
  background: var(--purple) !important; color: white !important;
  border-color: var(--purple) !important; font-weight: 700 !important;
}
div[role="radiogroup"] input { display: none !important; }

[data-testid="stMetricValue"] { color: var(--purple-dark) !important; font-weight: 700 !important; }
[data-testid="stMetricDeltaIcon-Up"]   { color: var(--success) !important; }
[data-testid="stMetricDeltaIcon-Down"] { color: #c0392b !important; }

.stProgress > div > div > div > div {
  background: linear-gradient(90deg, var(--purple) 0%, var(--yellow) 100%) !important;
  border-radius: 4px !important;
}

[data-testid="stAlert"][kind="info"]    { background-color: var(--info-bg) !important; border-left-color: var(--purple) !important; border-radius: 8px !important; }
[data-testid="stAlert"][kind="success"] { background-color: var(--success-bg) !important; border-left-color: var(--success) !important; border-radius: 8px !important; }
[data-testid="stAlert"][kind="warning"] { background-color: var(--warning-bg) !important; border-left-color: var(--yellow) !important; border-radius: 8px !important; }
[data-testid="stAlert"][kind="error"]   { background-color: #f9edf3 !important; border-left-color: var(--purple-dark) !important; border-radius: 8px !important; }

code, pre { background: #2c2040 !important; color: var(--yellow) !important; border-radius: 5px !important; }

::-webkit-scrollbar { width: 7px; }
::-webkit-scrollbar-track { background: var(--grey-100); }
::-webkit-scrollbar-thumb { background: var(--purple); border-radius: 4px; }

.footer-text { text-align: center; color: var(--grey-500); font-size: 0.85rem; margin-top: 8px; }
.metric-card {
  background: linear-gradient(135deg, var(--purple-dark) 0%, var(--purple) 100%);
  padding: 1rem; border-radius: 10px; color: white;
  box-shadow: 0 4px 12px rgba(118,75,162,0.3);
}
.legend-box {
  background: var(--purple-faint); padding: 15px; border-radius: 8px;
  border-left: 4px solid var(--purple); margin: 10px 0;
}

</style>
"""