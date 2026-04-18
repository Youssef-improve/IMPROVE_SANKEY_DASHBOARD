
from __future__ import annotations

# ============================================================
# IMPORTS
# ============================================================
from pathlib import Path
import os, sqlite3, hashlib, secrets, io, logging, html as _html
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    _mpl_ok = True
except ImportError:
    _mpl_ok = False

LOCAL_TZ_NAME = "Europe/Madrid"
LOCAL_TZ      = ZoneInfo(LOCAL_TZ_NAME) if ZoneInfo else None

_log = logging.getLogger("improve_sankey")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

st.set_page_config(
    page_title="Improve Sankey — Sistema de Monitorización",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# DESIGN SYSTEM — SCADA INDUSTRIAL v3
# ============================================================
DESIGN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@300;400;500;600&display=swap');

:root {
  --bg-base:        #060606;
  --bg-surface:     #0b0b0b;
  --bg-raised:      #101010;
  --bg-panel:       #080808;
  --bg-inset:       #030303;
  --border-faint:   rgba(255,255,255,0.04);
  --border-dim:     rgba(255,255,255,0.07);
  --border-default: rgba(255,255,255,0.11);
  --border-strong:  rgba(255,255,255,0.20);
  --accent:         #00b386;
  --accent-hi:      #00d4a0;
  --accent-dim:     rgba(0,179,134,0.08);
  --accent-border:  rgba(0,179,134,0.36);
  --warn:           #c49a0a;
  --warn-dim:       rgba(196,154,10,0.10);
  --warn-border:    rgba(196,154,10,0.38);
  --danger:         #b03030;
  --danger-dim:     rgba(176,48,48,0.10);
  --danger-border:  rgba(176,48,48,0.38);
  --info:           #3d6fa8;
  --text-100: #d0d0d0;
  --text-70:  #787878;
  --text-40:  #404040;
  --text-20:  #222222;
  --font-ui:   'IBM Plex Sans',  sans-serif;
  --font-data: 'IBM Plex Mono',  monospace;
  --r-xs:2px; --r-sm:3px; --r-md:4px; --r-lg:6px;
}

html,body,.stApp { background-color:var(--bg-base)!important; font-family:var(--font-ui)!important; color:var(--text-100)!important; }
.block-container { max-width:1700px!important; padding:0.4rem 1.6rem 3rem!important; }

[data-testid="stSidebar"] { background:var(--bg-panel)!important; border-right:1px solid var(--border-default)!important; box-shadow:none!important; }
[data-testid="stSidebar"] .block-container { padding:0.9rem 0.8rem!important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,[data-testid="stSidebar"] label { color:var(--text-100)!important; font-family:var(--font-ui)!important; }
[data-testid="stSidebar"] [data-testid="stExpander"] { border-radius:var(--r-md)!important; border:1px solid var(--border-dim)!important; background:var(--bg-raised)!important; }
[data-testid="stSidebar"] [data-testid="stExpander"] summary { font-family:var(--font-ui)!important; font-size:10px!important; font-weight:600!important; letter-spacing:.10em; text-transform:uppercase; color:var(--text-70)!important; }

div[data-testid="stSelectbox"] > div > div { background:var(--bg-raised)!important; border:1px solid var(--border-default)!important; border-radius:var(--r-sm)!important; color:var(--text-100)!important; font-family:var(--font-data)!important; font-size:12px!important; }
div[data-testid="stSelectbox"] label,div[data-testid="stDateInput"] label,div[data-testid="stTimeInput"] label,div[data-testid="stNumberInput"] label { font-size:9px!important; font-weight:600!important; letter-spacing:.12em; text-transform:uppercase; color:var(--text-40)!important; font-family:var(--font-ui)!important; }
div[data-testid="stDateInput"] input,div[data-testid="stTimeInput"] input { background:var(--bg-raised)!important; border:1px solid var(--border-default)!important; border-radius:var(--r-sm)!important; color:var(--text-100)!important; font-family:var(--font-data)!important; font-size:12px!important; }
div[data-testid="stTextInput"] label { font-size:9px!important; font-weight:600!important; letter-spacing:.12em; text-transform:uppercase; color:var(--text-40)!important; font-family:var(--font-ui)!important; }
div[data-testid="stTextInput"] input { background:var(--bg-inset)!important; border:1px solid var(--border-default)!important; border-radius:var(--r-sm)!important; color:var(--text-100)!important; font-family:var(--font-data)!important; font-size:13px!important; padding:9px 12px!important; transition:border-color 150ms!important; }
div[data-testid="stTextInput"] input:focus { border-color:var(--accent-border)!important; }
div[data-testid="stCheckbox"] label { font-size:11px!important; color:var(--text-70)!important; font-family:var(--font-ui)!important; }

.stButton > button { border-radius:var(--r-sm)!important; border:1px solid var(--border-default)!important; background:var(--bg-raised)!important; color:var(--text-70)!important; font-family:var(--font-ui)!important; font-size:11px!important; font-weight:600!important; letter-spacing:.08em; text-transform:uppercase; padding:7px 14px!important; transition:border-color 120ms,color 120ms,background 120ms!important; }
.stButton > button:hover { border-color:var(--accent-border)!important; color:var(--accent)!important; background:var(--accent-dim)!important; }
[data-testid="stDownloadButton"] > button { border-radius:var(--r-sm)!important; border:1px solid var(--border-default)!important; background:var(--bg-raised)!important; color:var(--text-70)!important; font-family:var(--font-ui)!important; font-size:11px!important; font-weight:600!important; letter-spacing:.07em; transition:border-color 120ms,color 120ms!important; }
[data-testid="stDownloadButton"] > button:hover { border-color:var(--accent-border)!important; color:var(--accent)!important; background:var(--accent-dim)!important; }
div[data-testid="stFormSubmitButton"] > button { width:100%!important; height:42px!important; border-radius:var(--r-md)!important; background:var(--accent-dim)!important; border:1px solid var(--accent-border)!important; color:var(--accent-hi)!important; font-family:var(--font-ui)!important; font-weight:600!important; font-size:12px!important; letter-spacing:.12em; text-transform:uppercase; margin-top:14px!important; transition:background 150ms,color 150ms!important; }
div[data-testid="stFormSubmitButton"] > button:hover { background:rgba(0,179,134,0.18)!important; color:#fff!important; }

[data-testid="stMetric"] { background:var(--bg-raised)!important; border:1px solid var(--border-dim)!important; border-radius:var(--r-md)!important; padding:10px 12px!important; }
[data-testid="stMetricLabel"] { font-size:9px!important; font-weight:600!important; letter-spacing:.12em; text-transform:uppercase; color:var(--text-40)!important; font-family:var(--font-ui)!important; }
[data-testid="stMetricValue"] { color:var(--text-100)!important; font-weight:500!important; font-size:1.28rem!important; font-family:var(--font-data)!important; }

.stTabs [data-baseweb="tab-list"] { gap:0; background:var(--bg-panel); border-bottom:1px solid var(--border-default); padding:0; margin-bottom:16px; }
.stTabs [data-baseweb="tab"] { border-radius:0!important; padding:10px 22px!important; background:transparent!important; border:none!important; border-bottom:2px solid transparent!important; color:var(--text-40)!important; font-family:var(--font-ui)!important; font-size:12px!important; font-weight:500!important; letter-spacing:.04em; transition:color 120ms,border-color 120ms!important; margin-bottom:-1px; }
.stTabs [data-baseweb="tab"]:hover { color:var(--text-70)!important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { background:transparent!important; border-bottom:2px solid var(--accent)!important; color:var(--accent)!important; }

.stAlert { border-radius:var(--r-sm)!important; border:1px solid var(--border-dim)!important; background:var(--bg-raised)!important; font-family:var(--font-ui)!important; font-size:12px!important; }
[data-testid="stDataFrame"] { border-radius:var(--r-md)!important; overflow:hidden; }

.js-plotly-plot .plotly .modebar { display:none!important; }
.js-plotly-plot .plotly,.js-plotly-plot .main-svg { background:transparent!important; }
div[data-testid="stPlotlyChart"] { border-radius:var(--r-md)!important; border:1px solid var(--border-faint)!important; background:var(--bg-panel)!important; overflow:hidden; }

/* ── COMPONENTS ── */
.is-card { background:var(--bg-surface); border:1px solid var(--border-dim); border-radius:var(--r-lg); padding:14px 16px 12px; margin:6px 0 14px; box-shadow:0 1px 2px rgba(0,0,0,.70); }
.is-section-title { display:flex; align-items:center; gap:9px; font-family:var(--font-ui); font-size:9px; font-weight:700; letter-spacing:.18em; text-transform:uppercase; color:var(--text-70); margin:22px 0 10px; }
.is-section-title .is-mark { width:3px; height:14px; border-radius:1px; background:var(--accent); flex-shrink:0; }
.is-section-title .is-rule { flex:1; height:1px; background:var(--border-faint); }

.is-val-badge { margin-bottom:5px; padding:7px 10px; background:var(--bg-raised); border:1px solid var(--border-faint); border-radius:var(--r-sm); }
.is-val-badge .vb-label { font-size:9px; font-weight:600; letter-spacing:.12em; text-transform:uppercase; color:var(--text-40); font-family:var(--font-ui); margin-bottom:2px; }
.is-val-badge .vb-value { font-family:var(--font-data); font-weight:500; font-size:14px; color:var(--text-100); }
.is-val-badge .vb-unit { font-family:var(--font-data); font-size:10px; color:var(--text-70); margin-left:3px; }

.kpi-strip { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:6px; margin-bottom:16px; }
.kpi-cell { background:var(--bg-raised); border:1px solid var(--border-dim); border-radius:var(--r-md); padding:10px 12px; position:relative; overflow:hidden; }
.kpi-cell::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; background:var(--kpi-accent,var(--accent)); }
.kpi-cell .kpi-label { font-family:var(--font-ui); font-size:8px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--text-40); margin-bottom:4px; }
.kpi-cell .kpi-value { font-family:var(--font-data); font-size:19px; font-weight:500; color:var(--text-100); line-height:1; }
.kpi-cell .kpi-unit { font-family:var(--font-data); font-size:10px; color:var(--text-70); margin-left:3px; }
.kpi-cell .kpi-sub { font-family:var(--font-ui); font-size:9px; color:var(--text-40); margin-top:4px; }

.stat-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:6px; margin:10px 0; }
.stat-cell { background:var(--bg-raised); border:1px solid var(--border-faint); border-radius:var(--r-sm); padding:8px 12px; }
.stat-cell .sc-label { font-size:8px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--text-40); font-family:var(--font-ui); margin-bottom:6px; }
.stat-row { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:3px; }
.stat-row .sr-key { font-size:9px; color:var(--text-40); font-family:var(--font-ui); }
.stat-row .sr-val { font-family:var(--font-data); font-size:11px; color:var(--text-100); }

.alarm-row { display:flex; align-items:center; gap:10px; padding:8px 12px; border-radius:var(--r-sm); border:1px solid; margin-bottom:5px; font-family:var(--font-ui); font-size:11px; }
.alarm-row.crit { border-color:var(--danger-border); background:var(--danger-dim); color:#e07070; }
.alarm-row.warn { border-color:var(--warn-border); background:var(--warn-dim); color:#c8a040; }
.alarm-row.info { border-color:rgba(0,179,134,0.25); background:var(--accent-dim); color:var(--accent); }
.alarm-dot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.alarm-dot.crit { background:#b03030; animation:led-blink 1.2s ease-in-out infinite; }
.alarm-dot.warn { background:#c49a0a; animation:led-blink 2.0s ease-in-out infinite; }
.alarm-dot.info { background:var(--accent); }
.alarm-ts { font-family:var(--font-data); font-size:9px; color:var(--text-40); margin-left:auto; white-space:nowrap; }

.is-client-card { padding:11px 13px; border:1px solid var(--border-default); border-left:2px solid var(--accent); border-radius:var(--r-md); background:var(--bg-raised); margin-bottom:12px; }
.is-client-card .cc-label { font-size:8px; font-weight:700; letter-spacing:.16em; text-transform:uppercase; color:var(--text-40); font-family:var(--font-ui); margin-bottom:3px; }
.is-client-card .cc-name { font-family:var(--font-data); font-size:15px; font-weight:500; color:var(--text-100); }
.is-client-card .cc-sub { display:flex; align-items:center; gap:5px; font-size:10px; color:var(--text-40); margin-top:6px; font-family:var(--font-ui); }
.is-led { display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--accent); flex-shrink:0; animation:led-blink 3.2s ease-in-out infinite; }
@keyframes led-blink { 0%,85%,100%{opacity:1} 92%{opacity:.20} }

.is-header { padding:8px 0 11px; border-bottom:1px solid var(--border-default); margin-bottom:8px; display:flex; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:8px; }
.is-header-left .brand { font-family:var(--font-data); font-size:16px; font-weight:600; letter-spacing:.10em; text-transform:uppercase; color:var(--text-100); line-height:1.1; }
.is-header-left .sub { font-family:var(--font-ui); font-size:9px; font-weight:500; color:var(--text-40); letter-spacing:.12em; text-transform:uppercase; margin-top:3px; }
.is-header-right { display:flex; align-items:center; gap:5px; flex-wrap:wrap; }
.is-tag { display:inline-flex; align-items:center; gap:5px; padding:3px 8px; border:1px solid var(--border-dim); border-radius:var(--r-xs); background:var(--bg-raised); font-family:var(--font-data); font-size:10px; color:var(--text-70); white-space:nowrap; }
.is-tag.ok  { border-color:rgba(0,179,134,0.28); color:var(--accent); }
.is-tag.err { border-color:rgba(176,48,48,0.35); color:#c06060; }
.is-tag.wrn { border-color:rgba(196,154,10,0.35); color:#c49a0a; }

.norm-row { display:flex; align-items:center; justify-content:space-between; padding:6px 10px; margin-bottom:4px; border-radius:var(--r-sm); border:1px solid var(--border-faint); background:var(--bg-raised); font-family:var(--font-ui); font-size:11px; }
.norm-ok   { border-left:2px solid var(--accent)!important; }
.norm-warn { border-left:2px solid var(--warn)!important; }
.norm-fail { border-left:2px solid var(--danger)!important; }
.norm-badge { font-family:var(--font-data); font-size:10px; padding:2px 6px; border-radius:2px; }
.norm-badge.ok   { background:rgba(0,179,134,0.12); color:var(--accent); }
.norm-badge.warn { background:rgba(196,154,10,0.12); color:var(--warn); }
.norm-badge.fail { background:rgba(176,48,48,0.12); color:var(--danger); }

::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:var(--border-default); border-radius:2px; }
/* ── ANTI-FLASH en auto-refresh ─────────────────────────── */
/* Elimina el oscurecimiento de graficas durante el refresco */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.block-container,
iframe,
div[data-testid="stPlotlyChart"],
div[data-testid="stPlotlyChart"] > div,
.js-plotly-plot,
.js-plotly-plot .plotly,
.js-plotly-plot .main-svg {
  transition: none !important;
  animation: none !important;
}

/* Spinner oculto — evita el overlay oscuro */
div[data-testid="stSpinner"] > div {
  display: none !important;
}

/* Mantiene opacidad durante rerender */
div[data-stale="true"],
div[data-stale="true"] * {
  opacity: 1 !important;
  filter: none !important;
  transition: none !important;
}

/* Streamlit aplica un backdrop oscuro durante reruns — lo eliminamos */
.stApp::after {
  display: none !important;
}

</style>
"""
st.markdown(DESIGN_CSS, unsafe_allow_html=True)


LOGIN_CSS = """
<style>
[data-testid="stSidebar"] { display:none!important; }
.block-container { max-width:100%!important; padding-top:0!important; }
div[data-testid="stForm"] { width:420px!important; margin:110px auto 0 auto!important; padding:24px 26px 20px!important; background:var(--bg-surface)!important; border:1px solid var(--border-default)!important; border-top:2px solid var(--accent)!important; border-radius:var(--r-md)!important; box-shadow:0 2px 4px rgba(0,0,0,.80),0 12px 40px rgba(0,0,0,.60)!important; }
.lg-brand { font-family:'IBM Plex Mono',monospace; font-size:15px; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:#d0d0d0; margin-bottom:2px; }
.lg-sub { font-family:'IBM Plex Sans',sans-serif; font-size:10px; color:#3a3a3a; letter-spacing:.10em; text-transform:uppercase; margin-bottom:20px; }
.lg-rule { height:1px; background:rgba(255,255,255,0.07); margin:0 0 18px; }
.lg-footer { margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.04); display:flex; align-items:center; justify-content:space-between; }
.lg-copy { font-family:'IBM Plex Mono',monospace; font-size:9px; color:#3a3a3a; letter-spacing:.08em; }
.lg-link { font-size:10px; font-family:'IBM Plex Sans',sans-serif; color:#606060; text-decoration:none; padding:4px 9px; border:1px solid rgba(255,255,255,0.07); border-radius:2px; background:#111; transition:border-color 120ms,color 120ms; }
.lg-link:hover { border-color:rgba(0,179,134,0.38); color:#00b386; }
</style>
"""

# ============================================================
# CONFIG
# ============================================================
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

DEFAULT_CLIENT_ID = 10

def _get_cid():
    return int(st.session_state.get("client_id", DEFAULT_CLIENT_ID))

ENV_DB_PATH       = os.getenv("IMPROVE_DB_PATH")

CLIENTS_CONFIG = {10:"Munskjö TRF", 11:"Munskjö TRE", 12:"Papelera Oria"}

USERS_CONFIG = [
    {"username":"munskjo","password": os.environ.get("PASSWORD_MUNSKJO", "1234"),         "role":"admin",  "client_ids":[10,11]},
    {"username":"rafa",   "password": os.environ.get("PASSWORD_RAFA",    "Rafa2026"),     "role":"viewer", "client_ids":[10,11]},
    {"username":"josu",   "password": os.environ.get("PASSWORD_JOSU",    "Josu2026"),     "role":"viewer", "client_ids":[10,11]},
    {"username":"oria",   "password": os.environ.get("PASSWORD_ORIA",    "Oria_2026"),    "role":"admin",  "client_ids":[12]},
    {"username":"alfredo","password": os.environ.get("PASSWORD_ALFREDO", "Alfredo2026"),  "role":"admin",  "client_ids":[10,11,12]},
    {"username":"juan",   "password": os.environ.get("PASSWORD_JUAN",    "Juan2026"),     "role":"admin",  "client_ids":[10,11,12]},
    {"username":"arturo", "password": os.environ.get("PASSWORD_ARTURO",  "Arturo2026"),   "role":"admin",  "client_ids":[10,11,12]},
    {"username":"youssef","password": os.environ.get("PASSWORD_YOUSSEF", "Youssef2026"),  "role":"admin",  "client_ids":[10,11,12]},
    {"username":"borja",  "password": os.environ.get("PASSWORD_BORJA",   "Borja2026"),    "role":"viewer", "client_ids":[12]},
    {"username":"aitor",  "password": os.environ.get("PASSWORD_AITOR",   "Aitor2026"),    "role":"viewer", "client_ids":[12]},
]
_using_defaults = [u["username"] for u in USERS_CONFIG
                   if not os.environ.get(f"PASSWORD_{u['username'].upper()}")]
if _using_defaults:
    _log.warning(
        "Using hardcoded default passwords for users: %s. "
        "Set PASSWORD_<USERNAME> environment variables before deploying to production.",
        _using_defaults,
    )

BASE_DIR        = Path(__file__).parent
ASSETS_DIR      = BASE_DIR / "assets"
DATA_DIR        = BASE_DIR / "data"
LOCAL_DB_PATH   = DATA_DIR / "improve_sankey.db"
POLLERS_DB_PATH = Path("/opt/improve_sankey/app/data/improve_sankey.db")

if ENV_DB_PATH:               DB_PATH = Path(ENV_DB_PATH)
elif POLLERS_DB_PATH.exists(): DB_PATH = POLLERS_DB_PATH
else:                          DB_PATH = LOCAL_DB_PATH

IS_GREEN="#00b386"; IS_CYAN="#3d6fa8"; IS_AMBER="#c49a0a"
IS_RED="#b03030";   IS_TEXT="#d0d0d0"; IS_VIOLET="#7c5cbf"

PHASE_COLORS = {"L1":"#2a2a2a","L2":"#7a4a28","L3":"#b0b0b0","N":"#3d6fa8"}

ALARM_CFG = {
    "THD_V":{"warn":5.0,"crit":8.0},
    "THD_I":{"warn":10.0,"crit":20.0},
    "PF":{"warn":0.92,"crit":0.85,"low_is_bad":True},
    "TEMP":{"warn":60.0,"crit":75.0},
    "FREQ":{"warn_lo":49.5,"warn_hi":50.5,"crit_lo":49.0,"crit_hi":51.0},
    "IMBALANCE_V":{"warn":1.0,"crit":2.0},
    "IMBALANCE_I":{"warn":10.0,"crit":15.0},
}

# EN 50160 limits
EN50160 = {
    "THD_V_limit":8.0,
    "freq_lo":49.5,"freq_hi":50.5,
    "voltage_variation":0.10,
    "imbalance_limit":2.0,
}

px.defaults.template = "plotly_dark"

MEAS_RENAME: dict[str,str] = {
    "VL1N":"V_L1N","VL2N":"V_L2N","VL3N":"V_L3N",
    "VL1L2":"V_L1L2","VL2L3":"V_L2L3","VL3L1":"V_L3L1",
    "IA1":"I_L1","IA2":"I_L2","IA3":"I_L3","IN":"I_N",
    "KW":"P_kW","KVAr":"Q_kVAr","KVA":"S_kVA","FP":"PF","Frecuencia":"Freq_Hz",
    "THDVL1N":"THD_V_L1","THDVL2N":"THD_V_L2","THDVL3N":"THD_V_L3",
    "THDL1":"THD_I_L1","THDL2":"THD_I_L2","THDL3":"THD_I_L3",
}
ORDERS = [3,5,7,9,11,13]
for _n in ORDERS:
    for _ph in ["L1","L2","L3"]:
        MEAS_RENAME[f"Thd_{_n}_I_{_ph}"] = f"H{_n}_I_{_ph}"
        MEAS_RENAME[f"Thd_{_n}_V_{_ph}"] = f"H{_n}_V_{_ph}"

# ============================================================
# AUTH
# ============================================================
def _make_hash(p: str) -> str:
    """Genera 'salt_hex:hash_hex'. Salt aleatorio embebido en el campo password_hash, sin columna extra."""
    salt = secrets.token_bytes(32)
    h = hashlib.pbkdf2_hmac("sha256", p.encode(), salt, 100_000).hex()
    return salt.hex() + ":" + h

def _verify_hash(p: str, stored: str) -> bool:
    """Verifica contraseña. Retrocompatible con hashes antiguos (sin salt embebido)."""
    if ":" in stored:
        salt_hex, hash_hex = stored.split(":", 1)
        h = hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt_hex), 100_000).hex()
        return h == hash_hex
    else:
        # Legado: salt estático para hashes anteriores a esta versión
        h = hashlib.pbkdf2_hmac("sha256", p.encode(), b"improve_sankey_v1", 100_000).hex()
        return h == stored

def ensure_auth_schema(con):
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(users)")
        ci = cur.fetchall(); cols = [r[1] for r in ci]
        if "client_id" in cols:
            cur.execute("ALTER TABLE users RENAME TO users_old")
            cur.execute("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT DEFAULT 'viewer',is_active INTEGER DEFAULT 1)")
            if all(c in cols for c in ["username","password_hash"]):
                re_=("role" if "role" in cols else "'viewer'"); ae_=("is_active" if "is_active" in cols else "1")
                cur.execute(f"INSERT OR IGNORE INTO users(username,password_hash,role,is_active) SELECT username,password_hash,{re_},{ae_} FROM users_old")
            cur.execute("DROP TABLE users_old")
    cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT DEFAULT 'viewer',is_active INTEGER DEFAULT 1)")
    cur.execute("CREATE TABLE IF NOT EXISTS user_clients(username TEXT NOT NULL,client_id INTEGER NOT NULL,PRIMARY KEY(username,client_id))")
    def _t(n):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",(n,)); return cur.fetchone() is not None
    if _t("measurements"):
        cur.execute("PRAGMA table_info(measurements)")
        if "client_id" not in [r[1] for r in cur.fetchall()]: cur.execute("ALTER TABLE measurements ADD COLUMN client_id INTEGER")
    if _t("states"):
        cur.execute("PRAGMA table_info(states)")
        if "client_id" not in [r[1] for r in cur.fetchall()]: cur.execute("ALTER TABLE states ADD COLUMN client_id INTEGER")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_clients_username ON user_clients(username)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_meas_ts_client   ON measurements(ts, client_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_meas_client      ON measurements(client_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_meas_client_ts   ON measurements(client_id, ts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_states_ts_client ON states(ts, client_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_states_client    ON states(client_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_states_client_ts ON states(client_id, ts)")
    con.commit()

def seed_users(con):
    cur = con.cursor()
    for item in USERS_CONFIG:
        u,pw,r,cids = item["username"].strip(),item["password"],item.get("role","viewer").strip(),item.get("client_ids",[])
        h = _make_hash(pw)
        cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role,is_active) VALUES(?,?,?,1)",(u,h,r))
        cur.execute("UPDATE users SET password_hash=?,role=?,is_active=1 WHERE username=?",(h,r,u))
        cur.execute("DELETE FROM user_clients WHERE username=?",(u,))
        for cid in cids: cur.execute("INSERT OR IGNORE INTO user_clients(username,client_id) VALUES(?,?)",(u,int(cid)))
    con.commit()

def get_allowed_clients(con,username):
    rows = con.execute("SELECT client_id FROM user_clients WHERE username=? ORDER BY client_id",(username,)).fetchall()
    return [int(r[0]) for r in rows] if rows else []

def auth_user(con,username,password):
    row = con.execute("SELECT id,role,password_hash FROM users WHERE username=? AND is_active=1 LIMIT 1",(username,)).fetchone()
    if not row: return None
    uid,role,stored = row
    if not _verify_hash(password, stored): return None
    _log.info("Login OK user=%s role=%s", username, role)
    return int(uid),get_allowed_clients(con,username) or [DEFAULT_CLIENT_ID],str(role)

# ============================================================
# LOGIN
# ============================================================
def login_ui(con):
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    LOGO = "data:image/png;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAQABAADASIAAhEBAxEB/8QAHQABAQEAAgMBAQAAAAAAAAAAAAECAwUEBgcICf/EAF4QAAIBAgQDBAUGBwoJCQgCAwABEQIhAwQxQQVRYQYScYEHEyKRoRQyUrHB0QgVI0KT0vAzU1RiY3KCkpThFhckNENzotPxGCU1NkRVdIOERUZWZGWFlcKysyY34v/EABsBAQEAAwEBAQAAAAAAAAAAAAABAgMEBQYH/8QAPREBAAEDAQUDCAkEAgIDAAAAAAECAxEEBRIhMVETQZEGFCJSYXGhsRUWU2KBwdHh8DJCkqIj4iQzQ2Oy/9oADAMBAAIRAxEAPwD8hgAzYgIAKAyABuAUCgEAnmAUUiKQAUD6iACAopAUggAKBSACghQABNyAUgKKQpEAAAAAEAAACkAFIClEAAFIAQNgAAAAApAAAQKG4AAAFAgAIAAKABQIAABSAgApCgAAKTcqAEABAAKBCkBQABAABRQCAB1AIAA8yiogKBAAACAAAAACkAFIUgAgAFICgUgAAAAACCkBSiAAC7ggIKQoAhSDcoFICAB0BQKQAPMFBAIEUoAAghSFAAm5QIACgAAAKEBACgQAIAAgAKCAUAEEYGgKABQIACAACgGUiAAAAACBuAAAAAABAEACgAAGrAgEAAFAAAAAAAAAAACkBAAADcAAACgQAIoAAAACAACgAEQAwCgB1AAAEAAFDcBAAPMAAACAACgAABQQAAUCAAAAAABQIF0AAFIUCAoAgAAAACkKAIAAKQAAUgAAFYAAAQrBCCjYBgCAbgUgKBAClEABABQUQAoCAAwA3BAAKQgblICgNwAAAAAoIINykAABgAAAABQKQEAAFAAEAAIoDcAgAAoAAAAACAAAAMAEAA2AAAAAAAQAAA8AAAABQG48wAAABAAgAAoAAABYABuAQACyUQBFIIACgACAANwDAKBAClEAKBACkEBQUQMAAAAKQAAUgAFDIQEC9QigQFAm4KQgAAAUhSgCAgoAAE3KQAAEBQCFFIwAAAAoi5AQUEKUQAAUhSAAUm4FBCgQAAAAAAKBAPMACkBAABQABBSAMoAAgApAAAKACBAACApACgACAUgKKQaggAFAgAApACikAIAAAAAoAAAAwBSFIA0uAADAAAAEFRCkKABQABCAUEKABSCAAACkArBCgQpBuUANygQAAUEBAAAAAMoFIAABSCAAANykKKQoIAIAKCAooICACkAFBAKCAANwADABQA3AFIAQUgBRQCAXYhSAAGABSACghQIAABUQAUgAF3IAQAWxCgCkIAAKAAIAAKAGwAAAAACAAwAABQAADYAEFRAChoACAAAAAKAAAADcgDcAoAAgAAoAAgAAoAAAAAAKQAACAAABSAooIUggAKAAArsQdQQUEG4CwKQoAAAAAAA3AFIEQUgAFBClAEAAvmAQQpCgCAANwAUCkKBAUgAAAUMEAAdQAAAAAAPMAEApClEK/EgIKQAoFIUACeYAAACkBQIACAAUohWQoEAAAAEFIAAAAAMFAgAAABAAAUNwAQAAUBuAA8QgUggG4KAAAABgNQAQAAUAPiCAACgACAACgAAA0AAAMEADcFAFIAAABAAAACAANygAAAAArIAAABAABQAAAAABqwCAAAABQG4AAAEKD5AAgFIwUAAACKQgFfiQFFIykAAqAAgC1AAAAECgQdQAAKQAAUACFAhQCCCCkKABQIUACFAAgKQAAAABdQIAAAAYAAoEAAAAEAbAFAAqIIACgCgggKQoDQAgAAAAAAA3AAAoAAABsAAYYAAAAAAAAAAAABuAAAIAAKKQAAAVkAhSFDcAAAAQAAUB5gACkBABUCiAu5CAAAA3AAAAoAAgpAUCFIAAKQoAFIIPMAoAIAAAAKQeZBUQpAAAKKQAAAAAKQAwAABQBACkEABQAKBAAQCgFEKAQR6gpCgCggEAKAAAApCAACgAwgACAApAQAUjKABSCAAooIUCBgAAABSApBAgCgAAAAAAMEAAFDcBgABuAAKQAAUCAAAAAAAAAFAgG4IBQQAACgACAAAAAKAAIABSieJQQgAAoAFAEAAAbAAAAAA2AAAACkAAFAgAAoINwABQIAUAAAIAGAGxSQAAABlIAAAAAAAAAKH4kKQCAACkGxQA2KQQpClERQAAAIIUAogBQIAAKQAAACAUAomwYAAAAANwQAAACAKAAIABQIACi7EBQIAAKyBAACkAAu5AAAAAAAAAAAAAAACggjKCFAAAAAAABAAAAdACgUjBAAGwAAAAC7gQpNilEKQpBAgAAKQoAAgAAopCggEBdgIEABdCApRCggAAACkQAAoIIACgNigggKCiAAgAFAgAKABdyCAAouw2ICAACgACAACiixCgAAQQAAAAUACgQMAgDcpGUNgAQAAUABuALuQAAAQAAUAAQUgBQABAABQACAMAAEACAAAAAAAAoAAAAwAAABjcAAAAABQIAAKQDUANwCAAACGwAAAFAeYAAAEAAFApAABSACkAApAAAAApBtqABSEFIUhQABABSAEGAAABQ3AAApAAD6AAAAQCghQKQbEAAoEABQAAAAAACgTcuxAABSEAAoAQiFKIVhACAAgBgFAoIAAQ3AAFAgAAAAAOgAAAbgANwBSAAUgDAAAAAAAAIKQCxQARQIAAAKyAUgAAAAAAAAG4AAAAAAAAACAAAGwAFIAAAAAEDQdACgAAAGwAAAAAAKCAAAAG4AAADzAAABuACCkA8wAAKAAAAAAG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gAAABAKADBAAYAABAABuAQBQIFoAUANwQACgQFBRAAAAKBCkKQQDxBQACAu5ACAACgAUCAAAACAACgAEQAgABSFAgKAIJKQoApAAAAAbgABuCAAilAhSEAAFDYo3IQAAUUgG4AAAECgggBSgCFIIVkBQAKBACkAhQBCghQABAAKUCMAgAAoAAgAFKIUgAAAgAAAXcgApC6gCAoAgAKAAIAAAABlAAEAAFAAEADcAAUgAQUhQBQQQAAAAUCkAFIAQGAAKQAopAAAAIKCFKIAGAAAAAAAAA2ABABQBAAAABQAAAAAAykAAFIAAAEKQoFBAKQFIIUEKBSFAgKCCFBCgCkIAAQApAUAAiC7EBSieABQIACAAUogQAAAAUEAAAupBBsAAABQAKQQAAAAUNwAwAAAAACkAAApNwAAAMpCkEABQYAIAAApACgAPMgAAoAAAAAG4AAAAgbgAAACgBuAAA3AAAAAAKRAEBBAFFIUgAFIQAAADAKCA3BBSFIBSBgAACgAUggAKAAAAAAACA9AikAAFKICkIABQIACgAABSFIIAygQAFFIAQAAUEAAAAIAAKAAAFZAwAAAAAAAAAYAAIAgAAoAAAAAAAAAABoBuAACAAbgAAAQAAUNGAAAAADcAAACAAAAAKAHkAAAAAAAAAAAIAAKAAALmAAAG4AAAAAAAAAMFIAA3ABjceIAAFIIACgACANAAAAAAAAACgAAAQBAAYAAAAUhSiADoAsAAAAAAAgAMFAAEDcpAABSACkBQEAEAMAoBAEAAFADcAUgBAABRSAAAAAKQoEKTwKQCApRBAAAAAAECAAAAAKAAAADzApCgCAFAgDAAAAUmxSEAAFAAEAAIANgCgACAACgANAAAAAAgAAAACgAAA3AAABgAAAAAADqCAAwUAUEEABQAAADcEAAFFIAQChgCFICgUgAAAgABlAAAUgAApAAAKQEQAACkKAAAAAAAAAKQAAUCAvkQgAbgoApAAAIAA3AFBAKCAoAFAEAAAAAUheoEABBSWKQoABkAAFAAAANwAABAABRSFJuQABuUAAQAABSFAEABQYH1DcAAEQAAAADAAAAACgACAACgCkIABSiAAAACAACgAAAAApACANgGBQCAEACgAVkEABQABADDBQBSEAAAAUgFIUhQAQIBSAAACikKAICkAoIACAAAAACkKBCsgAFAIJuACgANgAAAAAAAAKTcpAGhSACkAIAG4KKCAAAAAAAFINAAA2AAAgFICgB1BAHmAUAAAAAAApA2ICsohSACkBQHiQpGQAAUAAAABAYAKAAIAAepQABAABQAAAAAUg3D1AAFAgAAApEAAAAAAAAA0AAAAEAPQAopAAAAAAACggAoRCgAQqAgAAAAgIAFAAAACvUCFIAABQBCk3AAMACggAAEAApQJuAADBQBAUAQFAm5SFAhSAAAwABSEApAAAKUQAAACgQpCkEBSMoABEApAUAAQAAAABQgoIAACAAFAEKQgAAooICCkAKAA3IAKQAAAAAKAAAAAAACAACgAAAKQAggCAUgKAAAAAgAAoAAAACAAAKyAAAEAAKQAAAAAKABSCIoAAhSAAAUAAQAECgAABSFAgKCAAQoFAIBCgogHmAAAAFARBAVkKAAIAAKAAIAKQoAFAgAIABQIAAABSiACSBsAUohSaAAAAAAIAAYAApRAUjIAKRFABlAgKAICkIAAKAKTYACkIAAKBChEAAFAAEABAoAAAAAAAAAAgAAoAAAACAACgACAACgwAAAAAAAAAQUgAAApRACgQAAAAAABAG5SAAUgAAAAUFE0ABAAAFBClAEBBSFIUC7kKBAUbgQAEAAACgAQAIoAAACkQApNwQAAUAAAABAABQBSAAwUCAAAAJIAAKA3CBAADKABWBACgQAAAAQGACgACAACgAAAAABAAAAQAAUAAAAABAAgbgAoAAABAIG4AKABQIAAAAAADYAAAGwDAASAA2AADcAAAAAABAAKUQAEAAAAAAAAAAFAAANwAA3AAACxQIAAAAApGCgQAAAUgAFIAA3BAABQKQpBAAUCkKBCggAAEApAUAAABSEAAFDcFAE3AKBAAAAHmQCkBQG4AAAAACkEBSeZQAG4AAEAAAAAUAAAAAAAAAAAABAAAAAFDcAAAAAHiAAA3ACACgQAEAAFAAAAAQAAAAAAFIUAAAAAAAEApAUABuQAClEAAABABcAoEAAAFYAgKQAACB4gpNigAgAFtAAALcgAoYIIAUog3BQIGUgAApBNwUgAoAEAYAAFKIAAAAAF2INwAHkCAAChIAAAFIBAUogAAAFAhSF2AgAAAAgB9ACgAAAAIAAAFIUCMFIUAUhAABQCAIAAKAAAAAgAAAAAAAKGgAIAAKAAIAAKDCKQgAAoAAgAAoDYAgBjzAAFIA3ABQAYIG4AAAAAACgAwAABAAAAAblAFIBSF8yANwAAQKCCAAoAAgAAACkKBQAAJoVgACEAAABuAUAUgAAAAAA3BSIB5hlAEKQAAgAAKQAAAAAAAAAAAAAAblICAUEKG4AAAAAAUggAKAG4AAAAAAAAYAAAAAAAAApAQAAUAAAAAAAAAAADAIAG4KAAAAbggAAoAAANwXYCAAAAAAAAAAAACAACgEAQAAUCkBABSFAAAAAAAAApAAAAAFIAABAABQAZQABABQQgpC+ZCgCk3AAIAWCAEAApR//2Q=="
    mail = os.getenv("IMPROVE_SUPPORT_EMAIL","soporte@improvesankey.com").strip()

    with st.form("login_form", clear_on_submit=False):
        # Top header
        st.markdown(
            f'<div style="padding:28px 28px 24px;border-bottom:1px solid #1a1a1e;">'+
            f'<div style="display:flex;align-items:center;gap:14px;">'+
            f'<img src="{LOGO}" style="width:40px;height:40px;border-radius:10px;"/>'+
            f'<div>'+
            f'<div style="font-family:Inter,sans-serif;font-size:15px;font-weight:600;'+
            f'color:#e8e8f0;letter-spacing:-.01em;">Improve Sankey</div>'+
            f'<div style="font-family:Inter,sans-serif;font-size:11px;font-weight:400;'+
            f'color:#38383e;margin-top:1px;">Energy Monitoring</div>'+
            f'</div></div></div>',
            unsafe_allow_html=True)

        # Form fields
        st.markdown('<div style="padding:24px 28px 8px;">', unsafe_allow_html=True)
        username  = st.text_input("Correo o usuario", key="login_user", placeholder="usuario")
        password  = st.text_input("Contraseña",       type="password",  key="login_pass", placeholder="••••••••")
        submitted = st.form_submit_button("Iniciar sesión")
        st.markdown('</div>', unsafe_allow_html=True)

        if submitted:
            _ukey = (username or "").strip().lower()
            _attempts_key = f"_login_attempts_{_ukey}"
            _lockout_key  = f"_login_lockout_{_ukey}"
            _now_ts = datetime.now(timezone.utc)
            _lockout_until = st.session_state.get(_lockout_key)
            if _lockout_until and _now_ts < _lockout_until:
                _remaining = int((_lockout_until - _now_ts).total_seconds())
                st.error(f"Demasiados intentos fallidos. Espera {_remaining} segundos.")
            else:
                row = auth_user(con, (username or "").strip(), password)
                if row:
                    st.session_state.pop(_attempts_key, None)
                    st.session_state.pop(_lockout_key, None)
                    uid, allowed, role = row
                    st.session_state.update({
                        "logged_in": True, "user_id": uid, "role": role,
                        "username": (username or "").strip(),
                        "allowed_client_ids": allowed,
                        "client_id": int(allowed[0]) if allowed else DEFAULT_CLIENT_ID,
                        "client_name": f"Client_{allowed[0] if allowed else DEFAULT_CLIENT_ID}",
                    })
                    st.rerun()
                else:
                    _new_attempts = st.session_state.get(_attempts_key, 0) + 1
                    st.session_state[_attempts_key] = _new_attempts
                    _log.warning("Login fallido user=%s intento=%d", _ukey, _new_attempts)
                    if _new_attempts >= 5:
                        st.session_state[_lockout_key] = _now_ts + timedelta(minutes=5)
                        st.session_state[_attempts_key] = 0
                        _log.warning("Cuenta bloqueada 5 min user=%s", _ukey)
                        st.error("Demasiados intentos fallidos. Cuenta bloqueada 5 minutos.")
                    else:
                        st.error(f"Usuario o contraseña incorrectos. ({_new_attempts}/5 intentos)")

        # Footer
        st.markdown(
            f'<div style="padding:16px 28px;border-top:1px solid #1a1a1e;'+
            f'display:flex;align-items:center;justify-content:space-between;">'+
            f'<span style="font-family:Inter,sans-serif;font-size:11px;color:#28282e;">'+
            f'&copy; 2026 Improve Sankey</span>'+
            f'<a href="mailto:{mail}" style="font-family:Inter,sans-serif;font-size:11px;'+
            f'color:#38383e;text-decoration:none;transition:color 120ms;"'+
            f' onmouseover="this.style.color='#00b386'" '+
            f' onmouseout="this.style.color='#38383e'">'+
            f'Contacto</a></div>',
            unsafe_allow_html=True)


def get_conn():
    if DB_PATH.parent == DATA_DIR: DATA_DIR.mkdir(parents=True,exist_ok=True)
    con = sqlite3.connect(DB_PATH,check_same_thread=False,timeout=30)
    con.execute("PRAGMA journal_mode=WAL;"); con.execute("PRAGMA synchronous=NORMAL;"); con.execute("PRAGMA busy_timeout=5000;")
    con.execute("PRAGMA cache_size=-32000;"); con.execute("PRAGMA temp_store=MEMORY;")
    con.execute("PRAGMA mmap_size=268435456;"); con.execute("PRAGMA wal_autocheckpoint=500;")
    return con

@st.cache_resource
def init_auth_db():
    con = get_conn(); ensure_auth_schema(con); seed_users(con); return True

init_auth_db(); conn = get_conn()

CLIENT_LABEL_BY_ID = dict(CLIENTS_CONFIG)
CLIENT_ID_BY_LABEL = {v:k for k,v in CLIENT_LABEL_BY_ID.items()}

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if os.getenv("IMPROVE_SKIP_LOGIN","").strip()=="1":
    if os.getenv("IMPROVE_ENV","").strip().lower() == "production":
        raise EnvironmentError(
            "IMPROVE_SKIP_LOGIN=1 is not allowed when IMPROVE_ENV=production."
        )
    _log.warning("IMPROVE_SKIP_LOGIN is active — authentication is bypassed. "
                 "Do NOT use in production.")
    st.session_state["logged_in"]=True
    st.session_state.setdefault("role","service")
    st.session_state.setdefault("allowed_client_ids",list(CLIENT_LABEL_BY_ID.keys()))
    st.session_state.setdefault("client_id",DEFAULT_CLIENT_ID)
    st.session_state.setdefault("client_name",CLIENT_LABEL_BY_ID.get(DEFAULT_CLIENT_ID,f"Client_{DEFAULT_CLIENT_ID}"))
if not st.session_state["logged_in"]: login_ui(conn); st.stop()
st.session_state.setdefault("client_id",DEFAULT_CLIENT_ID)
st.session_state.setdefault("allowed_client_ids",list(CLIENT_LABEL_BY_ID.keys()))
st.session_state.setdefault("client_name",CLIENT_LABEL_BY_ID.get(int(st.session_state["client_id"]),"—"))

# ============================================================
# AUTO-REFRESH
# ============================================================
def _refresh_seconds(mode):
    return {"Cada 1 s (rápido)":1,"Cada 5 s (normal)":5,"Cada 10 s (ahorro)":10,"Manual":None}.get(mode)

def enable_refresh(seconds):
    if seconds and seconds>0 and st_autorefresh is not None:
        st_autorefresh(interval=int(seconds*1000),key="auto_refresh")

# ============================================================
# DATA HELPERS
# ============================================================
def _to_local_ts(s):
    dt = pd.to_datetime(s,errors="coerce",utc=True)
    if LOCAL_TZ:
        try:
            return dt.dt.tz_convert(LOCAL_TZ)
        except Exception:
            _log.debug("_to_local_ts: tz_convert failed, returning UTC series")
    return dt

_ALLOWED_TABLES = {"measurements","states","users","user_clients","alarm_history","annotations","daily_summary","motor_starts","voltage_dips"}
def _get_table_cols(con,table):
    if table not in _ALLOWED_TABLES: return []
    try:
        return [c[1] for c in con.execute(f"PRAGMA table_info({table})").fetchall()]
    except sqlite3.OperationalError:
        _log.debug("_get_table_cols: table '%s' not found in DB", table)
        return []

def _local_to_utc_iso(dt_local):
    if dt_local.tzinfo is None and LOCAL_TZ: dt_local = dt_local.replace(tzinfo=LOCAL_TZ)
    return (dt_local.astimezone(timezone.utc) if dt_local.tzinfo else dt_local).isoformat()

def read_table_between(con,table,dt_from,dt_to,limit=200_000):
    cols = _get_table_cols(con,table)
    if not cols: return pd.DataFrame()
    cid = int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
    q,p = f"SELECT * FROM {table} WHERE 1=1",[]
    if "client_id" in cols: q+=" AND client_id=?"; p.append(cid)
    if "ts" in cols:
        q+=" AND ts>=? AND ts<=?"; p+=[_local_to_utc_iso(dt_from),_local_to_utc_iso(dt_to)]
    sf=(st.session_state.get("source_filter","") or "").strip()
    if sf and "source" in cols: q+=" AND source LIKE ?"; p.append(f"%{sf}%")
    q+=" ORDER BY ts DESC LIMIT ?"; p.append(int(limit))
    df=pd.read_sql_query(q,con,params=p)
    if "ts" in df.columns:
        df["ts"]=_to_local_ts(df["ts"]); df=df.dropna(subset=["ts"]).sort_values("ts")
    return df

def read_table_between_agg(con,table,dt_from,dt_to,bucket_seconds,limit=500_000):
    """Muestreo por cubos de tiempo usando ROWID: devuelve una fila representativa por bucket.
    4x más rápido que MAX() por bucket y devuelve TODAS las columnas (incluidos armónicos).
    Para datos long-format (sin columnas wide) usa MAX(value) por bucket."""
    cols=_get_table_cols(con,table)
    if not cols: return pd.DataFrame()
    cid=int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
    bs=max(1,int(bucket_seconds))
    skip={"ts","client_id","id","source","tag","value"}
    wide_cols=[c for c in cols if c not in skip]
    is_long="tag" in cols and "value" in cols and not wide_cols
    p_inner=[]
    if is_long:
        # Long format: MAX(value) por bucket y tag
        epoch_expr=f"CAST(strftime('%s',ts) AS INTEGER)/{bs}"
        ts_expr=f"datetime(CAST(strftime('%s',ts) AS INTEGER)/{bs}*{bs},'unixepoch')"
        inner=f"SELECT {ts_expr} as ts, tag, MAX(CAST(value as REAL)) as value FROM {table} WHERE 1=1"
        if "client_id" in cols: inner+=" AND client_id=?"; p_inner.append(cid)
        inner+=" AND ts>=? AND ts<=?"; p_inner+=[_local_to_utc_iso(dt_from),_local_to_utc_iso(dt_to)]
        sf=(st.session_state.get("source_filter","") or "").strip()
        if sf and "source" in cols: inner+=" AND source LIKE ?"; p_inner.append(f"%{sf}%")
        inner+=f" GROUP BY {epoch_expr}, tag"
        q=inner+" ORDER BY ts LIMIT ?"; p_inner.append(int(limit))
        params=p_inner
    else:
        # Wide format: ROWID sampling — una fila representativa por bucket (MIN rowid en cada cubo)
        inner=f"SELECT MIN(rowid) as rid FROM {table} WHERE 1=1"
        if "client_id" in cols: inner+=" AND client_id=?"; p_inner.append(cid)
        inner+=" AND ts>=? AND ts<=?"; p_inner+=[_local_to_utc_iso(dt_from),_local_to_utc_iso(dt_to)]
        sf=(st.session_state.get("source_filter","") or "").strip()
        if sf and "source" in cols: inner+=" AND source LIKE ?"; p_inner.append(f"%{sf}%")
        inner+=f" GROUP BY CAST(strftime('%s',ts) AS INTEGER)/{bs}"
        q=f"SELECT * FROM {table} WHERE rowid IN ({inner}) ORDER BY ts LIMIT ?"
        params=p_inner+[int(limit)]
    try:
        df=pd.read_sql_query(q,con,params=params)
        if df.empty:
            raise ValueError("empty rowid sample")
    except Exception as _e:
        _log.warning("read_table_between_agg failed (%s), falling back",_e)
        return read_table_between(con,table,dt_from,dt_to,limit=min(limit,2_000_000))
    if "ts" in df.columns:
        df["ts"]=_to_local_ts(df["ts"]); df=df.dropna(subset=["ts"]).sort_values("ts")
    if df.empty or ("ts" in df.columns and df["ts"].isna().all()):
        return read_table_between(con,table,dt_from,dt_to,limit=min(limit,2_000_000))
    return df

def _pivot_if_long(df):
    if df is None or df.empty: return df
    if {"ts","tag","value"}.issubset(set(df.columns)):
        if df["tag"].isna().all() or (df["tag"].astype(str).str.strip()=="").all(): return df
        d=df.copy(); d["tag"]=d["tag"].astype(str).str.strip()
        d=d[(d["tag"].notna())&(d["tag"]!="")]; d["value"]=pd.to_numeric(d["value"],errors="coerce")
        d=d.dropna(subset=["ts","value"])
        if d.empty: return pd.DataFrame()
        wide=d.pivot_table(index="ts",columns="tag",values="value",aggfunc="last").reset_index()
        wide.columns.name=None; return wide.sort_values("ts")
    return df

_RANGE_TD = {
    "Últimos 5 min":timedelta(minutes=5),"Últimos 15 min":timedelta(minutes=15),
    "Últimos 30 min":timedelta(minutes=30),"Última 1 h":timedelta(hours=1),
    "Últimas 6 h":timedelta(hours=6),"Últimas 12 h":timedelta(hours=12),
    "Últimas 24 h":timedelta(hours=24),"Últimos 2 días":timedelta(days=2),
    "Última semana":timedelta(days=7),"Último mes":timedelta(days=30),
    "Últimos 6 meses":timedelta(days=182),"Último año":timedelta(days=365),"Últimos 2 años":timedelta(days=730),
}
def _range_to_td(rng):
    return _RANGE_TD.get(rng,timedelta(hours=1))

def _downsample(df_in,seconds,how="max"):
    if df_in is None or df_in.empty or "ts" not in df_in.columns: return df_in
    d=df_in.copy(); d["ts"]=pd.to_datetime(d["ts"],errors="coerce")
    d=d.dropna(subset=["ts"]).sort_values("ts").set_index("ts")
    d=d.apply(pd.to_numeric,errors="coerce")
    rule=f"{int(seconds)}s"
    rs=d.resample(rule)
    if how=="last": return rs.last().reset_index()
    if how=="mean": return rs.mean().reset_index()
    return rs.max().reset_index()

def coerce_numeric(df,cols):
    if df is None or df.empty: return df
    out=df.copy()
    for c in cols:
        if c in out.columns: out[c]=pd.to_numeric(out[c],errors="coerce")
    return out

def _dedup_cols(df):
    """Combina columnas duplicadas (pueden aparecer tras rename cuando la DB tiene nombres viejos y nuevos)."""
    if df is None or df.empty or not df.columns.duplicated().any(): return df
    result={}
    for nm in df.columns.unique():
        group=df.loc[:,df.columns==nm]
        if group.shape[1]==1:
            result[nm]=group.iloc[:,0]
        else:
            s=group.iloc[:,0]
            for i in range(1,group.shape[1]):
                s=s.combine_first(group.iloc[:,i])
            result[nm]=s
    return pd.DataFrame(result)

def _last_num(df,col,mode="last",tail=200):
    if df is None or df.empty or col not in df.columns: return None
    s=pd.to_numeric(df[col],errors="coerce").tail(int(tail)).dropna()
    if s.empty: return None
    return float(s.max()) if mode=="max_tail" else float(s.iloc[-1])

def _ck():
    """Auto-increment chart key."""
    st.session_state["_ck"] = st.session_state.get("_ck",0) + 1
    return f"chart_{st.session_state['_ck']}"

# ============================================================
# ALARM ENGINE
# ============================================================
def compute_alarms(df):
    alarms=[]
    if df is None or df.empty: return alarms
    now_ts=df["ts"].iloc[-1] if "ts" in df.columns else None
    try:
        ts_str=now_ts.strftime("%H:%M:%S") if (now_ts is not None and not pd.isnull(now_ts)) else "—"
    except (AttributeError, ValueError):
        ts_str="—"

    def _chk(col,val,cfg_key,label,unit=""):
        cfg=ALARM_CFG.get(cfg_key,{})
        if val is None: return
        low_bad=cfg.get("low_is_bad",False)
        _fmt=".3f" if cfg_key in ("THD_V","THD_I","PF") else ".0f"
        if low_bad:
            if val<cfg.get("crit",-999): alarms.append({"level":"crit","msg":f"{label} bajo: {val:{_fmt}}{unit}","ts":ts_str})
            elif val<cfg.get("warn",-999): alarms.append({"level":"warn","msg":f"{label} bajo: {val:{_fmt}}{unit}","ts":ts_str})
        else:
            if val>cfg.get("crit",999): alarms.append({"level":"crit","msg":f"{label} alto: {val:{_fmt}}{unit}","ts":ts_str})
            elif val>cfg.get("warn",999): alarms.append({"level":"warn","msg":f"{label} alto: {val:{_fmt}}{unit}","ts":ts_str})

    for ph in ["L1","L2","L3"]:
        _chk(f"THD_V_{ph}",_last_num(df,f"THD_V_{ph}"),"THD_V",f"THD-V {ph}","%")
        _chk(f"THD_I_{ph}",_last_num(df,f"THD_I_{ph}"),"THD_I",f"THD-I {ph}","%")
    _chk("PF",_last_num(df,"PF"),"PF","Factor de potencia","")
    freq=_last_num(df,"Freq_Hz")
    if freq is not None:
        cfg=ALARM_CFG["FREQ"]
        if freq<cfg["crit_lo"] or freq>cfg["crit_hi"]: alarms.append({"level":"crit","msg":f"Frecuencia fuera de rango: {freq:.0f} Hz","ts":ts_str})
        elif freq<cfg["warn_lo"] or freq>cfg["warn_hi"]: alarms.append({"level":"warn","msg":f"Frecuencia anómala: {freq:.0f} Hz","ts":ts_str})
    for col in ["T_Nucleo","T_Tiristor_R","T_Tiristor_S","T_Tiristor_T"]:
        _chk(col,_last_num(df,col),"TEMP",col.replace("_"," ")," °C")

    # Voltage imbalance
    vvals=[_last_num(df,f"V_L{i}N") for i in [1,2,3]]
    vvals=[v for v in vvals if v is not None]
    if len(vvals)==3:
        vmean=np.mean(vvals); vimb=max(abs(v-vmean) for v in vvals)/vmean*100 if vmean>0 else 0
        _chk("V_imb",vimb,"IMBALANCE_V","Desequilibrio tensión","%")
    # Current imbalance
    ivals=[_last_num(df,f"I_L{i}") for i in [1,2,3]]
    ivals=[v for v in ivals if v is not None]
    if len(ivals)==3:
        imean=np.mean(ivals); iimb=max(abs(v-imean) for v in ivals)/imean*100 if imean>0 else 0
        _chk("I_imb",iimb,"IMBALANCE_I","Desequilibrio corriente","%")

    if not alarms: alarms.append({"level":"info","msg":"Sin alarmas activas","ts":ts_str})
    return alarms

# ============================================================
# EMAIL ALERT
# ============================================================

# ============================================================
# PLOTLY THEME
# ============================================================
def _pth(fig,title=None,height=None):
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#090909",
        margin=dict(l=32,r=16,t=44 if title else 22,b=34),
        font=dict(size=11,color="#555",family="IBM Plex Mono,monospace"),
        legend=dict(orientation="h",yanchor="bottom",y=1.04,xanchor="right",x=1,
                    bgcolor="rgba(0,0,0,0)",font=dict(size=10,color="#505050"),itemsizing="constant"))
    if title: fig.update_layout(title=dict(text=title,x=0.01,font=dict(size=12,color="#888",family="IBM Plex Sans,sans-serif")))
    if height: fig.update_layout(height=height)
    ax=dict(showgrid=True,gridcolor="rgba(255,255,255,0.04)",zeroline=False,showline=False,
            tickfont=dict(color="#404040",size=10,family="IBM Plex Mono,monospace"),
            title_font=dict(color="#363636",size=10))
    fig.update_xaxes(**ax); fig.update_yaxes(**ax)
    return fig

def _color_sig(name):
    u=(name or "").upper()
    if "L1" in u: return PHASE_COLORS["L1"]
    if "L2" in u: return PHASE_COLORS["L2"]
    if "L3" in u: return PHASE_COLORS["L3"]
    if "NEUT" in u or "_N" in u or u.endswith("_N"): return PHASE_COLORS["N"]
    return IS_GREEN

# ============================================================
# CHARTS
# ============================================================
def line_hud(df,cols,unit="",colors=None,title_text="",height=260,x_window_seconds=None,ref_line=None):
    if df is None or df.empty: st.write("Sin datos todavía…"); return
    if "ts" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["ts"]):
        df=df.copy(); df["ts"]=pd.to_datetime(df["ts"],errors="coerce")
    df=df.dropna(subset=["ts"]).sort_values("ts")
    cols_ok=[c for c in cols if c in df.columns]
    if not cols_ok: st.info("No encuentro esas señales en la DB para este rango."); return
    if colors is None: colors=[_color_sig(c) for c in cols_ok]
    fig=go.Figure()
    for i,col in enumerate(cols_ok):
        raw=df[col]
        if isinstance(raw,pd.DataFrame): raw=raw.iloc[:,0]
        serie=pd.to_numeric(raw,errors="coerce"); lw=1.8 if "L1" in col.upper() else 1.4
        fig.add_trace(go.Scatter(x=df["ts"],y=serie,mode="lines",name=col,
            line=dict(width=lw,color=colors[i%len(colors)]),line_shape="linear",connectgaps=True,
            hovertemplate=f"<b>%{{y:.1f}} {unit}</b><br>%{{x|%Y-%m-%d %H:%M:%S}}<br><span style='color:#505050;font-size:10px;'>{col}</span><extra></extra>"))
    # Reference line (e.g. EN50160 limit)
    if ref_line is not None:
        fig.add_hline(y=ref_line,line_dash="dash",line_color="rgba(196,154,10,0.55)",line_width=1,
                      annotation_text=f"Límite {ref_line}{unit}",
                      annotation_font=dict(size=9,color="rgba(196,154,10,0.70)"),
                      annotation_position="top right")
    if x_window_seconds and len(df)>2:
        xe=df["ts"].iloc[-1]; xs=max(df["ts"].iloc[0],xe-pd.Timedelta(seconds=int(x_window_seconds)))
        fig.update_xaxes(range=[xs,xe])
    _pth(fig,title=title_text,height=height)
    fig.update_layout(xaxis_title="Tiempo",yaxis_title=unit)
    st.plotly_chart(fig,use_container_width=True,key=_ck())

def render_chart_with_values(df,cols,unit,colors,title_text,x_window_seconds=None,value_mode="last",tail=30,ref_line=None):
    df=coerce_numeric(df,cols)
    if not colors: colors=[_color_sig(c) for c in cols]
    col_chart,col_vals=st.columns([0.80,0.20])
    with col_chart:
        line_hud(df,cols,unit,colors,title_text=title_text,x_window_seconds=x_window_seconds,ref_line=ref_line)
    with col_vals:
        st.markdown(f"<div style='font-family:IBM Plex Sans,sans-serif;font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#3a3a3a;margin-bottom:9px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.04);'>{title_text}</div>",unsafe_allow_html=True)
        for i,col in enumerate(cols):
            val=_last_num(df,col,mode=value_mode,tail=tail)
            if val is None: continue
            cc=colors[i%len(colors)]
            _vfmt=".3f" if ("THD" in col or col=="PF") else ".0f"
            st.markdown(f'<div class="is-val-badge" style="border-left:2px solid {cc};"><div class="vb-label">{col}</div><div class="vb-value">{val:{_vfmt}}<span class="vb-unit">{unit}</span></div></div>',unsafe_allow_html=True)

def render_kpi_strip(df):
    if df is None or df.empty: return
    kpis=[("V_L1N","V L1-N","V","#2a2a2a"),("V_L2N","V L2-N","V","#7a4a28"),("V_L3N","V L3-N","V","#b0b0b0"),
          ("I_L1","I L1","A","#2a2a2a"),("I_L2","I L2","A","#7a4a28"),("I_L3","I L3","A","#b0b0b0"),
          ("P_kW","Potencia","kW",IS_GREEN),("Q_kVAr","Reactiva","kVAr",IS_AMBER),
          ("PF","Factor P","",IS_CYAN),("Freq_Hz","Frecuencia","Hz","#888")]
    cells=""
    for col,label,unit,color in kpis:
        val=_last_num(df,col)
        if val is None: continue
        if col=="PF": val_str=f"{val:.3f}"
        elif "THD" in col: val_str=f"{val:.2f}"
        else: val_str=f"{val:.0f}"
        cells+=(f'<div class="kpi-cell" style="--kpi-accent:{color};">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{val_str}<span class="kpi-unit">{unit}</span></div>'
                f'</div>')
    if cells: st.markdown(f'<div class="kpi-strip">{cells}</div>',unsafe_allow_html=True)

def render_stats_panel(df):
    """Min/Max/Mean/Std for main signals."""
    if df is None or df.empty: return
    sig_groups=[
        ("Tensiones (V)",["V_L1N","V_L2N","V_L3N"]),
        ("Corrientes (A)",["I_L1","I_L2","I_L3"]),
        ("Potencias",["P_kW","Q_kVAr","S_kVA"]),
        ("Calidad",["PF","Freq_Hz","THD_V_L1","THD_I_L1"]),
    ]
    cells=[]
    for group_label,cols in sig_groups:
        found=[(c,pd.to_numeric(df[c],errors="coerce").dropna()) for c in cols if c in df.columns]
        if not found: continue
        rows_html=[]
        for col,s in found:
            if s.empty: continue
            _sf=".2f" if ("THD" in col or col=="PF") else ".0f"
            rows_html.append(f'<div class="stat-row"><span class="sr-key">{col}</span>'
                        f'<span class="sr-val">{s.min():{_sf}} / {s.mean():{_sf}} / {s.max():{_sf}}'
                        f'<span style="color:#3a3a3a;font-size:9px;margin-left:4px;">σ={s.std():{_sf}}</span></span></div>')
        if rows_html:
            cells.append(f'<div class="stat-cell"><div class="sc-label">{group_label}</div>'
                    f'<div style="font-size:8px;color:#2a2a2a;margin-bottom:4px;font-family:IBM Plex Sans,sans-serif;">min / media / max</div>'
                    f'{"".join(rows_html)}</div>')
    if cells: st.markdown(f'<div class="stat-grid">{"".join(cells)}</div>',unsafe_allow_html=True)

def render_alarm_panel(df):
    alarms=compute_alarms(df)
    section("Estado de Alarmas")
    crits=[a for a in alarms if a["level"]=="crit"]
    html="".join(
        f'<div class="alarm-row {a["level"]}"><span class="alarm-dot {a["level"]}"></span>'
        f'<span>{a["msg"]}</span><span class="alarm-ts">{a["ts"]}</span></div>'
        for a in alarms
    )
    st.markdown(html,unsafe_allow_html=True)

def render_harmonic_bar(df,prefix,title):
    if df is None or df.empty: return
    bars=[]
    for o in ORDERS:
        for ph,color in [("L1",PHASE_COLORS["L1"]),("L2",PHASE_COLORS["L2"]),("L3",PHASE_COLORS["L3"])]:
            col=f"H{o}_{prefix}_{ph}"; val=_last_num(df,col,mode="max_tail",tail=30)
            if val is not None: bars.append({"Orden":f"H{o}","Fase":ph,"Valor":val,"Color":color})
    if not bars: st.info(f"Sin datos de armónicos de {prefix}."); return
    bdf=pd.DataFrame(bars); fig=go.Figure()
    for ph,color in [("L1",PHASE_COLORS["L1"]),("L2",PHASE_COLORS["L2"]),("L3",PHASE_COLORS["L3"])]:
        sub=bdf[bdf["Fase"]==ph]
        if sub.empty: continue
        fig.add_trace(go.Bar(x=sub["Orden"],y=sub["Valor"],name=f"{ph}",marker_color=color,
            hovertemplate=f"<b>%{{y:.3f}}%</b><br>Orden: %{{x}}<extra>{ph}</extra>"))
    # EN50160 reference
    fig.add_hline(y=EN50160["THD_V_limit"],line_dash="dash",line_color="rgba(196,154,10,0.50)",line_width=1,
                  annotation_text="EN 50160",annotation_font=dict(size=9,color="rgba(196,154,10,0.70)"),
                  annotation_position="top right")
    fig.update_layout(barmode="group",bargap=0.22,bargroupgap=0.08)
    _pth(fig,title=title,height=270)
    fig.update_layout(yaxis_title="%",xaxis_title="Orden armónico")
    st.plotly_chart(fig,use_container_width=True,key=_ck())

def render_phasor(df):
    """
    Phasor diagram. Voltages and currents drawn on SEPARATE axes
    so both are always visible regardless of magnitude difference.
    """
    if df is None or df.empty: return

    v1=_last_num(df,"V_L1N"); v2=_last_num(df,"V_L2N"); v3=_last_num(df,"V_L3N")
    i1=_last_num(df,"I_L1");  i2=_last_num(df,"I_L2");  i3=_last_num(df,"I_L3")
    pf=_last_num(df,"PF")

    if v1 is None: st.info("Sin datos de tensión para el diagrama fasorial."); return

    phi   = float(np.degrees(np.arccos(np.clip(pf,-1,1)))) if pf is not None else 0.0
    V1,V2,V3 = v1 or 230.0, v2 or 230.0, v3 or 230.0
    I1,I2,I3 = i1 or 0.0,   i2 or 0.0,   i3 or 0.0
    i_max = max(I1,I2,I3,0.001)
    v_max = max(V1,V2,V3,1.0)

    # Normalise both to unit circle so both fit perfectly
    vn = [V1/v_max, V2/v_max, V3/v_max]
    # Scale currents to same unit circle
    in_ = [I1/i_max, I2/i_max, I3/i_max]

    v_angs = [90, -30, -150]  # standard 3-phase: L1=90°, L2=-30°, L3=-150°
    i_angs = [a-phi for a in v_angs]
    colors = [PHASE_COLORS["L1"], PHASE_COLORS["L2"], PHASE_COLORS["L3"]]
    names  = ["L1","L2","L3"]

    fig = go.Figure()

    # Reference circle
    t = np.linspace(0,2*np.pi,120)
    fig.add_trace(go.Scatter(x=np.cos(t),y=np.sin(t),mode="lines",
        showlegend=False,line=dict(color="rgba(255,255,255,0.06)",width=1,dash="dot")))
    fig.add_trace(go.Scatter(x=0.5*np.cos(t),y=0.5*np.sin(t),mode="lines",
        showlegend=False,line=dict(color="rgba(255,255,255,0.04)",width=1,dash="dot")))

    # Voltage phasors (solid, full length)
    for k in range(3):
        ang=np.radians(v_angs[k])
        xe,ye = vn[k]*np.cos(ang), vn[k]*np.sin(ang)
        fig.add_trace(go.Scatter(x=[0,xe],y=[0,ye],mode="lines",
            name=f"V {names[k]} ({[V1,V2,V3][k]:.0f}V)",
            line=dict(color=colors[k],width=2.8),
            hovertemplate=f"<b>V{names[k]}={[V1,V2,V3][k]:.0f}V</b><br>Ángulo: {v_angs[k]}°<extra></extra>"))
        fig.add_trace(go.Scatter(x=[xe],y=[ye],mode="markers",showlegend=False,
            marker=dict(color=colors[k],size=9,symbol="circle")))
        # Label
        fig.add_annotation(x=xe*1.12,y=ye*1.12,
            text=f"<b>{names[k]}</b><br>{[V1,V2,V3][k]:.0f}V",
            showarrow=False,font=dict(size=9,color=colors[k],family="IBM Plex Mono"),
            xanchor="center")

    # Current phasors (dashed, scaled to 0.72 of circle so slightly shorter)
    if i_max > 0.01:
        I_SCALE = 0.72
        for k in range(3):
            ang=np.radians(i_angs[k])
            xe,ye = in_[k]*I_SCALE*np.cos(ang), in_[k]*I_SCALE*np.sin(ang)
            fig.add_trace(go.Scatter(x=[0,xe],y=[0,ye],mode="lines",
                name=f"I {names[k]} ({[I1,I2,I3][k]:.0f}A)",
                line=dict(color=colors[k],width=1.8,dash="dash"),
                hovertemplate=f"<b>I{names[k]}={[I1,I2,I3][k]:.0f}A</b><br>φ={phi:.0f}°<extra></extra>"))

    # Origin
    fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",showlegend=False,
        marker=dict(color="rgba(255,255,255,0.35)",size=8,symbol="cross")))

    pf_txt = f"{pf:.3f}" if pf else "—"
    _pth(fig,title=f"Diagrama Fasorial  —  PF={pf_txt}  φ={phi:.1f}°  "
         f"(V normalizado a {v_max:.1f}V, I a {i_max:.1f}A)",height=420)
    fig.update_layout(
        xaxis=dict(scaleanchor="y",scaleratio=1,range=[-1.35,1.35],
                   zeroline=True,zerolinecolor="rgba(255,255,255,0.10)",
                   zerolinewidth=1,showgrid=False,showticklabels=False),
        yaxis=dict(range=[-1.35,1.35],zeroline=True,
                   zerolinecolor="rgba(255,255,255,0.10)",
                   zerolinewidth=1,showgrid=False,showticklabels=False),
        showlegend=True,
        legend=dict(orientation="h",y=-0.02,x=0.5,xanchor="center",
                    font=dict(size=9,color="#666")),
        annotations=[dict(
            x=0,y=-1.30,xref="x",yref="y",
            text=f"Tensión sólida | Corriente punteada | φ={phi:.1f}° (retraso inductivo)",
            showarrow=False,font=dict(size=8,color="#404040",family="IBM Plex Sans"),
            xanchor="center")]
    )
    st.plotly_chart(fig,use_container_width=True,key=_ck())


def render_radar_imbalance(df):
    """
    Radar showing desequilibrio. For balanced systems shows a triangle.
    Uses absolute values (not normalised) so differences are visible.
    Also shows a 'ideal balanced' reference triangle.
    """
    if df is None or df.empty: return

    v1=_last_num(df,"V_L1N"); v2=_last_num(df,"V_L2N"); v3=_last_num(df,"V_L3N")
    i1=_last_num(df,"I_L1");  i2=_last_num(df,"I_L2");  i3=_last_num(df,"I_L3")
    thd_v=[_last_num(df,f"THD_V_L{k}") or 0 for k in [1,2,3]]
    thd_i=[_last_num(df,f"THD_I_L{k}") or 0 for k in [1,2,3]]

    vok=[v for v in [v1,v2,v3] if v is not None]
    iok=[v for v in [i1,i2,i3] if v is not None]
    vmean=float(np.mean(vok)) if vok else 1
    imean=float(np.mean(iok)) if iok else 1

    # Calculate % deviation from mean — highlights imbalance
    def _vpct(v): return abs(v-vmean)/vmean*100 if v and vmean>0 else 0
    def _ipct(i): return abs(i-imean)/imean*100 if i and imean>0 else 0

    cats=["THD-V (%)","THD-I (%)","Desv. Tensión (%)","Desv. Corriente (%)"]
    colors=[PHASE_COLORS["L1"], PHASE_COLORS["L2"], PHASE_COLORS["L3"]]
    names=["L1","L2","L3"]
    vs=[v1,v2,v3]; iis=[i1,i2,i3]

    fig=go.Figure()

    # Reference: ideal balanced = all zeros deviation
    ref_vals=[max(thd_v)*0.5]*4  # reference at half max THD
    fig.add_trace(go.Scatterpolar(
        r=ref_vals+[ref_vals[0]], theta=cats+[cats[0]],
        name="Referencia equilibrada",
        line=dict(color="rgba(255,255,255,0.15)",width=1,dash="dot"),
        fill=None, showlegend=True))

    fill_colors=["rgba(42,42,42,0.25)","rgba(122,74,40,0.25)","rgba(176,176,176,0.18)"]
    for k in range(3):
        vals=[thd_v[k], thd_i[k], _vpct(vs[k]), _ipct(iis[k])]
        fig.add_trace(go.Scatterpolar(
            r=vals+[vals[0]], theta=cats+[cats[0]],
            fill="toself", name=names[k],
            line=dict(color=colors[k],width=2.2),
            fillcolor=fill_colors[k], opacity=0.90,
            hovertemplate=(
                f"<b>{names[k]}</b><br>"
                f"THD-V: {thd_v[k]:.2f}%<br>"
                f"THD-I: {thd_i[k]:.2f}%<br>"
                f"Desv. V: {_vpct(vs[k]):.3f}%<br>"
                f"Desv. I: {_ipct(iis[k]):.3f}%"
                "<extra></extra>")))

    _pth(fig,title="Desequilibrio entre Fases",height=420)

    # Auto-range axis based on actual max values
    all_vals=[thd_v[k] for k in range(3)]+[thd_i[k] for k in range(3)]+             [_vpct(vs[k]) for k in range(3)]+[_ipct(iis[k]) for k in range(3)]
    r_max=max(max(all_vals)*1.3,5)

    fig.update_layout(
        polar=dict(
            bgcolor="#0a0a0a",
            radialaxis=dict(visible=True,range=[0,r_max],
                tickfont=dict(size=8,color="#444",family="IBM Plex Mono"),
                gridcolor="rgba(255,255,255,0.07)",
                linecolor="rgba(255,255,255,0.07)"),
            angularaxis=dict(
                tickfont=dict(size=10,color="#666",family="IBM Plex Sans"),
                gridcolor="rgba(255,255,255,0.07)",
                linecolor="rgba(255,255,255,0.08)")),
        showlegend=True,
        legend=dict(orientation="h",y=-0.05,x=0.5,xanchor="center",
                    font=dict(size=10,color="#888")),
        annotations=[dict(
            x=0.5,y=-0.14,xref="paper",yref="paper",
            text=(f"Si las 3 fases se superponen → sistema equilibrado  |  "
                  f"V media={vmean:.1f}V  I media={imean:.1f}A"),
            showarrow=False,font=dict(size=8,color="#404040",family="IBM Plex Sans"),
            xanchor="center")]
    )
    st.plotly_chart(fig,use_container_width=True,key=_ck())

def render_power_triangle(df):
    """Power triangle: P (active), Q (reactive), S (apparent) as vector diagram."""
    if df is None or df.empty: return
    p  = _last_num(df,"P_kW");    q = _last_num(df,"Q_kVAr")
    s  = _last_num(df,"S_kVA");   pf = _last_num(df,"PF")
    if p is None or q is None: st.info("Sin datos de potencia."); return

    p = abs(p or 0); q = abs(q or 0)
    s = s or float(np.sqrt(p**2+q**2))
    phi = float(np.degrees(np.arctan2(q,p)))

    fig = go.Figure()
    # P (horizontal, green)
    fig.add_trace(go.Scatter(x=[0,p],y=[0,0],mode="lines+text",name="P — Activa",
        line=dict(color=IS_GREEN,width=3),
        text=["",f"P={p:.2f} kW"],textposition="bottom center",
        textfont=dict(size=10,color=IS_GREEN,family="IBM Plex Mono")))
    # Q (vertical, amber)
    fig.add_trace(go.Scatter(x=[p,p],y=[0,q],mode="lines+text",name="Q — Reactiva",
        line=dict(color=IS_AMBER,width=3),
        text=["",f"Q={q:.2f} kVAr"],textposition="middle right",
        textfont=dict(size=10,color=IS_AMBER,family="IBM Plex Mono")))
    # S (hypotenuse, cyan)
    fig.add_trace(go.Scatter(x=[0,p],y=[0,q],mode="lines+text",name="S — Aparente",
        line=dict(color=IS_CYAN,width=2.5,dash="dash"),
        text=["",f"S={s:.2f} kVA"],textposition="top left",
        textfont=dict(size=10,color=IS_CYAN,family="IBM Plex Mono")))
    # Arc for phi angle
    arc_t = np.linspace(0,np.radians(phi),40)
    arc_r = s*0.20
    fig.add_trace(go.Scatter(x=arc_r*np.cos(arc_t),y=arc_r*np.sin(arc_t),
        mode="lines",showlegend=False,line=dict(color="rgba(255,255,255,0.30)",width=1)))
    fig.add_annotation(x=arc_r*1.4*np.cos(np.radians(phi/2)),
        y=arc_r*1.4*np.sin(np.radians(phi/2)),
        text=f"φ={phi:.1f}°",showarrow=False,
        font=dict(size=10,color="rgba(255,255,255,0.55)",family="IBM Plex Mono"))
    # Origin
    fig.add_trace(go.Scatter(x=[0],y=[0],mode="markers",showlegend=False,
        marker=dict(color="rgba(255,255,255,0.4)",size=7,symbol="cross")))

    pf_disp = pf if pf is not None else float(np.cos(np.radians(phi)))
    _pth(fig,title=f"Triángulo de Potencias  —  PF={pf_disp:.3f}  |  φ={phi:.1f}°",height=340)
    fig.update_layout(
        xaxis=dict(scaleanchor="y",scaleratio=1,zeroline=True,
                   zerolinecolor="rgba(255,255,255,0.08)",showgrid=False,
                   title="kW"),
        yaxis=dict(zeroline=True,zerolinecolor="rgba(255,255,255,0.08)",
                   showgrid=False,title="kVAr"),
        showlegend=True)
    st.plotly_chart(fig,use_container_width=True,key=_ck())

def render_kwh_chart(df):
    """Cumulative energy (kWh) from P_kW using trapezoidal integration."""
    if df is None or df.empty or "P_kW" not in df.columns or "ts" not in df.columns:
        st.info("Sin datos de P_kW para calcular energía."); return
    d=df[["ts","P_kW"]].copy()
    d["ts"]=pd.to_datetime(d["ts"],errors="coerce"); d=d.dropna(subset=["ts","P_kW"]).sort_values("ts")
    if len(d)<2: st.info("Insuficientes puntos para calcular energía."); return
    dt_h=(d["ts"].diff().dt.total_seconds()/3600).bfill().fillna(0)
    d["kWh_inc"]=d["P_kW"]*dt_h
    d["kWh_cum"]=d["kWh_inc"].cumsum()
    total_kwh=d["kWh_cum"].iloc[-1]
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=d["ts"],y=d["kWh_cum"],mode="lines",name="Energía acumulada",
        line=dict(width=1.6,color=IS_GREEN),fill="tozeroy",fillcolor="rgba(0,179,134,0.06)",
        hovertemplate="<b>%{y:.3f} kWh</b><br>%{x|%Y-%m-%d %H:%M:%S}<extra></extra>"))
    _pth(fig,title=f"Energía activa acumulada — Total: {total_kwh:.3f} kWh",height=260)
    fig.update_layout(yaxis_title="kWh",xaxis_title="Tiempo")
    st.plotly_chart(fig,use_container_width=True,key=_ck())
    return total_kwh

def render_en50160(df):
    """EN 50160 compliance checker."""
    if df is None or df.empty:
        st.info("Sin datos para verificar norma EN 50160."); return
    section("Verificación Norma EN 50160")
    checks=[]

    # Frecuencia
    freq=_last_num(df,"Freq_Hz")
    if freq is not None:
        ok=EN50160["freq_lo"]<=freq<=EN50160["freq_hi"]
        checks.append(("Frecuencia",f"{freq:.3f} Hz",f"{EN50160['freq_lo']}–{EN50160['freq_hi']} Hz","ok" if ok else "fail"))

    # THD tensión
    for ph in ["L1","L2","L3"]:
        v=_last_num(df,f"THD_V_{ph}")
        if v is not None:
            ok=v<=EN50160["THD_V_limit"]
            checks.append((f"THD-V {ph}",f"{v:.3f}%",f"≤ {EN50160['THD_V_limit']}%","ok" if ok else "fail"))

    # Desequilibrio de tensión
    vvals=[_last_num(df,f"V_L{i}N") for i in [1,2,3]]
    vvals=[v for v in vvals if v is not None]
    if len(vvals)==3:
        vmean=np.mean(vvals)
        vimb=max(abs(v-vmean) for v in vvals)/vmean*100 if vmean>0 else 0
        ok=vimb<=EN50160["imbalance_limit"]
        checks.append(("Desequilibrio tensión",f"{vimb:.2f}%",f"≤ {EN50160['imbalance_limit']}%","ok" if ok else "fail"))

    # Variación de tensión nominal (assume 230V nominal)
    v_nom=230.0
    for ph,tag in [("L1","V_L1N"),("L2","V_L2N"),("L3","V_L3N")]:
        v=_last_num(df,tag)
        if v is not None:
            deviation=abs(v-v_nom)/v_nom
            ok=deviation<=EN50160["voltage_variation"]
            checks.append((f"Variación V {ph}",f"{v:.1f} V (Δ{deviation*100:.1f}%)",f"±{EN50160['voltage_variation']*100:.0f}% (230 V)",
                          "ok" if ok else ("warn" if deviation<=0.15 else "fail")))

    html="".join(
        f'<div class="norm-row norm-{status}"><span style="color:#888;font-size:11px;">{name}</span>'
        f'<span style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#aaa;">{val}</span>'
        f'<span style="font-size:9px;color:#555;">{limit}</span>'
        f'<span class="norm-badge {status}">{"✓ OK" if status=="ok" else ("△ WARN" if status=="warn" else "✗ FAIL")}</span></div>'
        for name,val,limit,status in checks
    )
    st.markdown(html,unsafe_allow_html=True)

def gauge_semicircle(title, value, vmin, vwarn, vmax, suffix="", key=None):
    import streamlit.components.v1 as components
    val = float(value) if value is not None and np.isfinite(value) else float(vmin)
    val = max(vmin, min(vmax, val))

    cx, cy, R, RI = 100, 108, 78, 56
    # Arc: 200° (left) → -20° (right), clockwise in math = sweep=1 in SVG outer
    S, E, SPAN = 200, -20, 220

    def _deg(v):
        return S - (v-vmin)/max(vmax-vmin,1e-9)*SPAN

    def _pt(a, r):
        rad=np.radians(a); return cx+r*np.cos(rad), cy-r*np.sin(rad)

    def _arc(a1, a2, ro, ri):
        """a1→a2 decreasing angles = clockwise in math = sweep=1 outer, sweep=0 inner."""
        span = abs(a1-a2)
        la = 1 if span > 180 else 0
        x1o,y1o=_pt(a1,ro); x2o,y2o=_pt(a2,ro)
        x1i,y1i=_pt(a1,ri); x2i,y2i=_pt(a2,ri)
        # outer: a1>a2, clockwise in standard coords → sweep-flag=1 in SVG
        # inner: return counterclockwise → sweep-flag=0
        return (f"M{x1o:.1f},{y1o:.1f} "
                f"A{ro},{ro} 0 {la},1 {x2o:.1f},{y2o:.1f} "
                f"L{x2i:.1f},{y2i:.1f} "
                f"A{ri},{ri} 0 {la},0 {x1i:.1f},{y1i:.1f}Z")

    # zone boundaries (all decreasing: green=high angle=left side)
    d0 = _deg(vmin)    # 200° — left
    d_a = _deg(vwarn*0.80)  # amber start
    d_w = _deg(vwarn)       # red start
    d1 = _deg(vmax)    # -20° — right
    dv = _deg(val)

    if val >= vwarn:       vc,bc,st="#e05050","#c03030","ALTO"
    elif val >= vwarn*0.80: vc,bc,st="#d4a820","#b08800","AVISO"
    else:                  vc,bc,st="#00c896","#009870","NORMAL"

    # arcs drawn left→right (d0→d1, angles decreasing)
    bg    = _arc(d0, d1,  R,   RI)
    green = _arc(d0, d_a, R-1, RI+1)  # left zone = low values = GREEN ✓
    amber = _arc(d_a,d_w, R-1, RI+1)  # middle = AMBER ✓
    red   = _arc(d_w,d1,  R-1, RI+1)  # right = high values = RED ✓

    # needle
    nd=np.radians(dv)
    tx=cx+(RI-5)*np.cos(nd); ty=cy-(RI-5)*np.sin(nd)
    pp=np.radians(dv+90); bw=2.4
    b1x=cx+bw*np.cos(pp); b1y=cy-bw*np.sin(pp)
    b2x=cx-bw*np.cos(pp); b2y=cy+bw*np.sin(pp)
    ndl=f"M{tx:.1f},{ty:.1f} L{b1x:.1f},{b1y:.1f} L{b2x:.1f},{b2y:.1f}Z"

    # ticks
    ticks=""
    for i in range(9):
        frac=i/8; tv=vmin+frac*(vmax-vmin); td=_deg(tv); tr=np.radians(td)
        xo=cx+R*np.cos(tr); yo=cy-R*np.sin(tr)
        xi=cx+(R-13)*np.cos(tr); yi=cy-(R-13)*np.sin(tr)
        xl=cx+(R-23)*np.cos(tr); yl=cy-(R-23)*np.sin(tr)
        ticks+=(f'<line x1="{xo:.1f}" y1="{yo:.1f}" x2="{xi:.1f}" y2="{yi:.1f}" '+
                f'stroke="rgba(255,255,255,0.38)" stroke-width="1.6"/>'+
                f'<text x="{xl:.1f}" y="{yl:.1f}" text-anchor="middle" '+
                f'dominant-baseline="middle" font-size="7" fill="#505050">{int(tv)}</text>')
        if i<8:
            for j in [1,2,3]:
                fm=(i+j/4)/8; trm=np.radians(_deg(vmin+fm*(vmax-vmin)))
                xom=cx+R*np.cos(trm); yom=cy-R*np.sin(trm)
                xim=cx+(R-7)*np.cos(trm); yim=cy-(R-7)*np.sin(trm)
                ticks+=(f'<line x1="{xom:.1f}" y1="{yom:.1f}" '+
                        f'x2="{xim:.1f}" y2="{yim:.1f}" '+
                        f'stroke="rgba(255,255,255,0.12)" stroke-width="0.7"/>'  )

    # warning line
    wr=np.radians(d_w)
    wxo=cx+(R+3)*np.cos(wr); wyo=cy-(R+3)*np.sin(wr)
    wxi=cx+(RI-2)*np.cos(wr); wyi=cy-(RI-2)*np.sin(wr)
    wl=(f'<line x1="{wxo:.1f}" y1="{wyo:.1f}" x2="{wxi:.1f}" y2="{wyi:.1f}" '+
        f'stroke="#ff3030" stroke-width="2.2" stroke-dasharray="3,2" opacity="0.85"/>'  )

    html=f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{margin:0;padding:0;background:transparent;display:flex;justify-content:center;align-items:flex-start;}}</style>
</head><body>
<svg width="196" height="148" viewBox="0 0 196 148" xmlns="http://www.w3.org/2000/svg">
<defs>
<radialGradient id="rbg" cx="50%" cy="80%" r="65%">
  <stop offset="0%" stop-color="#1a1a1a"/>
  <stop offset="100%" stop-color="#060606"/>
</radialGradient>
</defs>
<circle cx="{cx}" cy="{cy}" r="{R+9}" fill="url(#rbg)" stroke="rgba(255,255,255,0.07)" stroke-width="1.5"/>
<path d="{bg}"    fill="#080808"/>
<path d="{green}" fill="#0d4a28"/>
<path d="{amber}" fill="#5a4008"/>
<path d="{red}"   fill="#5a1010"/>
<circle cx="{cx}" cy="{cy}" r="{RI}" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="0.8"/>
{ticks}{wl}
<path d="{ndl}" fill="rgba(0,0,0,0.4)" transform="translate(1.2,1.2)"/>
<path d="{ndl}" fill="#e0e0e0"/>
<circle cx="{cx}" cy="{cy}" r="6" fill="#111" stroke="rgba(255,255,255,0.18)" stroke-width="1.2"/>
<circle cx="{cx}" cy="{cy}" r="2.8" fill="#d0d0d0"/>
<text x="{cx}" y="{cy+32}" text-anchor="middle" font-family="IBM Plex Mono,monospace"
      font-size="20" font-weight="600" fill="{vc}">{val:.1f}
  <tspan font-size="10" opacity="0.65"> {suffix}</tspan>
</text>
<rect x="{cx-20}" y="{cy+43}" width="40" height="12" rx="2" fill="{bc}" opacity="0.18"/>
<text x="{cx}" y="{cy+52}" text-anchor="middle" font-family="IBM Plex Sans,sans-serif"
      font-size="7" font-weight="700" letter-spacing="1" fill="{vc}">{st}</text>
<text x="{cx}" y="15" text-anchor="middle" font-family="IBM Plex Sans,sans-serif"
      font-size="8" font-weight="600" letter-spacing="2" fill="#505050">{title.upper()}</text>
</svg></body></html>"""
    components.html(html, height=152, scrolling=False)

def _build_segments(df,cols):
    out=[]
    if df is None or df.empty or "ts" not in df.columns: return pd.DataFrame()
    d=df.copy(); d["ts"]=pd.to_datetime(d["ts"],errors="coerce")
    d=d.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    for c in cols:
        if c not in d.columns: continue
        s=pd.to_numeric(d[c],errors="coerce").fillna(0).astype(int); ts=d["ts"]
        if s.empty: continue
        lv,lt=s.iloc[0],ts.iloc[0]
        for k in range(1,len(s)):
            if s.iloc[k]!=lv:
                out.append({"Signal":c,"Start":lt,"Finish":ts.iloc[k],"State":"On" if lv==1 else "Off"})
                lv,lt=s.iloc[k],ts.iloc[k]
        out.append({"Signal":c,"Start":lt,"Finish":ts.iloc[-1],"State":"On" if lv==1 else "Off"})
    return pd.DataFrame(out)

def onoff_timeline(df,cols,title,height=170,key=None):
    seg=_build_segments(df,cols)
    NM={"EstadoIEQ_OK":"Estado sistema","TestigoR_OK":"Fusible R","TestigoS_OK":"Fusible S",
        "TestigoT_OK":"Fusible T","Seta_OK":"Seta ByPass","Fallo_red_OK":"Fallo red"}
    if "Signal" in seg.columns: seg["Signal"]=seg["Signal"].map(lambda x: NM.get(x,x))
    if seg.empty: st.info(f'Sin datos para "{title}".'); return
    fig=px.timeline(seg,x_start="Start",x_end="Finish",y="Signal",color="State",
                    color_discrete_map={"On":"#163b28","Off":"#3a0f0f"},template="plotly_dark")
    fig.update_layout(title=dict(text=f"<b style='color:#666;font-size:11px;font-family:IBM Plex Sans'>{title}</b>",x=0.01,y=0.98),
                      height=height,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#090909",
                      margin=dict(l=10,r=10,t=26,b=16),showlegend=False)
    fig.update_yaxes(autorange="reversed",showgrid=False,zeroline=False,title_text="",color="#444",
                     tickfont=dict(size=10,color="#555",family="IBM Plex Mono"))
    fig.update_xaxes(title_text="",showgrid=True,gridcolor="rgba(255,255,255,0.04)",zeroline=False,color="#444",
                     tickfont=dict(size=10,color="#444",family="IBM Plex Mono"))
    _pth(fig,title=None,height=height); fig.update_traces(width=0.30)
    st.plotly_chart(fig,use_container_width=True,key=key)

def render_event_log(df_states):
    section("Log de Eventos")
    if df_states is None or df_states.empty: st.info("Sin datos de estados disponibles."); return
    state_cols=["EstadoIEQ_OK","TestigoR_OK","TestigoS_OK","TestigoT_OK","Seta_OK","Fallo_red_OK","Auto_Manual"]
    found=[c for c in state_cols if c in df_states.columns]
    if not found: st.info("Sin columnas de estado."); return
    NM={"EstadoIEQ_OK":"Estado sistema","TestigoR_OK":"Fusible R","TestigoS_OK":"Fusible S",
        "TestigoT_OK":"Fusible T","Seta_OK":"Seta ByPass","Fallo_red_OK":"Fallo red","Auto_Manual":"Auto/Manual"}
    events=[]
    d=df_states.copy(); d["ts"]=pd.to_datetime(d["ts"],errors="coerce")
    d=d.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    for c in found:
        s=pd.to_numeric(d[c],errors="coerce").fillna(0).astype(int); prev=s.iloc[0]
        for k in range(1,len(s)):
            if s.iloc[k]!=prev:
                nv=s.iloc[k]; sev="warn" if nv==0 else "info"
                if c in ("Fallo_red_OK","Seta_OK") and nv==0: sev="crit"
                events.append({"Timestamp":d["ts"].iloc[k].strftime("%Y-%m-%d %H:%M:%S"),
                                "Señal":NM.get(c,c),"Estado":"ON" if nv==1 else "OFF","Severidad":sev.upper()})
                prev=nv
    if not events: st.info("Sin cambios de estado en el rango."); return
    ev_df=pd.DataFrame(events).sort_values("Timestamp",ascending=False).head(200)

    def _sc(v):
        return {"CRIT":"color:#c06060","WARN":"color:#c0a040"}.get(v,"color:#888")

    rows=""
    for row in ev_df.itertuples(index=False):
        rows+=(f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">'
               f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#555;padding:5px 8px;">{row.Timestamp}</td>'
               f'<td style="font-size:11px;padding:5px 8px;color:#aaa;">{getattr(row, "Señal")}</td>'
               f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;padding:5px 8px;color:#aaa;">{row.Estado}</td>'
               f'<td style="font-size:10px;padding:5px 8px;{_sc(row.Severidad)}">{row.Severidad}</td></tr>')
    th="font-family:IBM Plex Sans,sans-serif;font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#3a3a3a;padding:7px 8px;text-align:left;"
    st.markdown(f'<div style="background:#0b0b0b;border:1px solid rgba(255,255,255,0.07);border-radius:4px;overflow:auto;max-height:340px;">'
                f'<table style="width:100%;border-collapse:collapse;"><thead><tr style="border-bottom:1px solid rgba(255,255,255,0.10);">'
                f'<th style="{th}">Timestamp</th><th style="{th}">Señal</th><th style="{th}">Estado</th><th style="{th}">Sev.</th>'
                f'</tr></thead><tbody>{rows}</tbody></table></div>',unsafe_allow_html=True)

_EXCEL_MAX_ROWS = 50_000

def render_excel_download(con, dt_from, dt_to):
    dfm=_pivot_if_long(read_table_between(con,"measurements",dt_from,dt_to,limit=_EXCEL_MAX_ROWS))
    dfs=_pivot_if_long(read_table_between(con,"states",dt_from,dt_to,limit=_EXCEL_MAX_ROWS))
    if dfm is not None and not dfm.empty:
        dfm=_dedup_cols(dfm.rename(columns=MEAS_RENAME))
    if dfm is None or dfm.empty: return None

    def _safe(dfx):
        if dfx is None or dfx.empty: return dfx
        out=dfx.copy()
        if "ts" in out.columns:
            ts=pd.to_datetime(out["ts"],errors="coerce")
            try:
                ts = ts.dt.tz_localize(None)
            except TypeError:
                pass  # Series is already timezone-naive
            out["ts"]=ts
        return out

    def _order(cols):
        prio=[]
        for g in [["ts"],["V_L1N","V_L2N","V_L3N","V_L1L2","V_L2L3","V_L3L1"],
                  ["I_L1","I_L2","I_L3","I_N"],["P_kW","Q_kVAr","S_kVA","PF","Freq_Hz"],
                  ["THD_V_L1","THD_V_L2","THD_V_L3","THD_I_L1","THD_I_L2","THD_I_L3"]]:
            for c in g:
                if c in cols and c not in prio: prio.append(c)
        return prio+[c for c in cols if c not in prio]

    dfm=_safe(dfm); dfm=dfm[_order(list(dfm.columns))]
    dfs2=_safe(dfs) if (dfs is not None and not dfs.empty) else pd.DataFrame()
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as w:
        dfm.to_excel(w,sheet_name="Medidas",index=False)
        if not dfs2.empty: dfs2.to_excel(w,sheet_name="Estados",index=False)
        _truncated = len(dfm) >= _EXCEL_MAX_ROWS
        pd.DataFrame([
            {"Campo":"Cliente","Valor":st.session_state.get("client_name","")},
            {"Campo":"Client ID","Valor":int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))},
            {"Campo":"Desde","Valor":dt_from.strftime("%Y-%m-%d %H:%M:%S")},
            {"Campo":"Hasta","Valor":dt_to.strftime("%Y-%m-%d %H:%M:%S")},
            {"Campo":"Filas medidas","Valor":len(dfm)},
            {"Campo":"Filas estados","Valor":len(dfs2)},
            {"Campo":"Datos truncados","Valor":f"Si (max {_EXCEL_MAX_ROWS} filas)" if _truncated else "No"},
        ]).to_excel(w,sheet_name="Resumen",index=False)
    return output.getvalue()

def render_pdf_report(df, client_name, rng, alarms):
    """Generate PDF report — improved design with cards, table and charts."""
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except ImportError:
        st.warning("PDF no disponible. Instala fpdf2: `pip install fpdf2`")
        return

    _TRANS_TABLE = str.maketrans({
        "—": "-", "–": "-", "→": "->", "←": "<-",
        "°": "deg", "±": "+/-", "σ": "sigma", "Σ": "Suma",
        "\u00b2": "2", "\u00b3": "3",
        "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "á":"a","é":"e","í":"i","ó":"o","ú":"u",
        "Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U",
        "ñ":"n","Ñ":"N","ü":"u","Ü":"U",
    })
    def _s(text) -> str:
        if text is None:
            return ""
        return str(text).translate(_TRANS_TABLE).encode("latin-1", errors="replace").decode("latin-1")

    now_str = (datetime.now(LOCAL_TZ) if LOCAL_TZ else datetime.now()).strftime("%d/%m/%Y %H:%M:%S")

    class ImprovePDF(FPDF):
        def header(self):
            self.set_fill_color(0, 179, 134)
            self.rect(0, 0, 210, 6, style="F")
            self.set_fill_color(22, 22, 30)
            self.rect(0, 6, 210, 18, style="F")
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(0, 210, 160)
            self.set_xy(10, 9)
            self.cell(100, 9, "IMPROVE SANKEY")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(150, 150, 160)
            self.set_xy(10, 19)
            self.cell(190, 5, _s(f"Informe de Monitorizacion  |  Cliente: {client_name}  |  {now_str}"), align="R")
            self.set_y(28)

        def footer(self):
            self.set_y(-12)
            self.set_draw_color(210, 215, 220)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(1)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(160, 160, 160)
            self.cell(0, 6, _s(f"Improve Sankey v3.0  |  Documento confidencial  |  Pagina {self.page_no()}"), align="C")

    pdf = ImprovePDF()
    pdf.set_margins(10, 30, 10)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    def section_title(text):
        y = pdf.get_y()
        pdf.set_fill_color(0, 179, 134)
        pdf.rect(10, y, 3, 7, style="F")
        pdf.set_x(15)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 7, _s(text.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(0, 179, 134)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    # ── Barra de resumen ──────────────────────────────────────
    pdf.set_fill_color(240, 245, 250)
    pdf.set_draw_color(200, 215, 225)
    y0 = pdf.get_y()
    pdf.rect(10, y0, 190, 14, style="FD")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(70, 70, 70)
    pdf.set_xy(14, y0 + 3)
    pdf.cell(62, 5, _s(f"Cliente: {client_name}"))
    pdf.set_xy(82, y0 + 3)
    pdf.cell(80, 5, _s(f"Rango: {rng}"))
    pdf.set_xy(14, y0 + 9)
    pdf.cell(100, 4, _s(f"Generado: {now_str}"))
    pdf.set_y(y0 + 18)

    # ── KPIs en tarjetas 3 columnas ──────────────────────────
    section_title("Valores en Tiempo Real")

    kpis_pdf = [
        ("V_L1N",   "Tension L1-N",   "V",    (20, 120, 200)),
        ("V_L2N",   "Tension L2-N",   "V",    (20, 120, 200)),
        ("V_L3N",   "Tension L3-N",   "V",    (20, 120, 200)),
        ("I_L1",    "Corriente L1",   "A",    (200, 100, 20)),
        ("I_L2",    "Corriente L2",   "A",    (200, 100, 20)),
        ("I_L3",    "Corriente L3",   "A",    (200, 100, 20)),
        ("P_kW",    "Pot. Activa",    "kW",   (0, 179, 134)),
        ("Q_kVAr",  "Pot. Reactiva",  "kVAr", (140, 60, 160)),
        ("S_kVA",   "Pot. Aparente",  "kVA",  (60, 100, 200)),
        ("PF",      "Factor Potencia","",     (180, 150, 0)),
        ("Freq_Hz", "Frecuencia",     "Hz",   (80, 160, 80)),
        ("THD_V_L1","THD-V L1",      "%",    (190, 60, 60)),
        ("THD_V_L2","THD-V L2",      "%",    (190, 60, 60)),
        ("THD_V_L3","THD-V L3",      "%",    (190, 60, 60)),
        ("THD_I_L1","THD-I L1",      "%",    (180, 80, 40)),
        ("THD_I_L2","THD-I L2",      "%",    (180, 80, 40)),
        ("THD_I_L3","THD-I L3",      "%",    (180, 80, 40)),
    ]

    cell_w, cell_h, gap = 60, 16, 5
    x_positions = [10, 10 + cell_w + gap, 10 + 2 * (cell_w + gap)]
    col_idx = 0
    y_row = pdf.get_y()

    for col, label, unit, accent in kpis_pdf:
        val = _last_num(df, col)
        if val is None:
            continue
        if col_idx == 0:
            y_row = pdf.get_y()
        x = x_positions[col_idx]
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(220, 226, 232)
        pdf.rect(x, y_row, cell_w, cell_h, style="FD")
        pdf.set_fill_color(*accent)
        pdf.rect(x, y_row, 4, cell_h, style="F")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(120, 120, 130)
        pdf.set_xy(x + 6, y_row + 2)
        pdf.cell(cell_w - 8, 4, _s(label))
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(25, 25, 30)
        pdf.set_xy(x + 6, y_row + 7)
        pdf.cell(cell_w - 8, 6, f"{val:.3f} {_s(unit)}")
        col_idx += 1
        if col_idx >= 3:
            col_idx = 0
            pdf.set_y(y_row + cell_h + 3)

    if col_idx != 0:
        pdf.set_y(y_row + cell_h + 3)
    pdf.ln(5)

    # ── Alarmas ──────────────────────────────────────────────
    section_title("Estado de Alarmas")

    if not alarms:
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(140, 140, 140)
        pdf.set_x(14)
        pdf.cell(0, 7, "Sin alarmas activas.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        for i, a in enumerate(alarms):
            bg = 253 if i % 2 == 0 else 246
            if a["level"] == "crit":
                badge_col = (190, 40, 40)
                badge_txt = "CRITICO"
            elif a["level"] == "warn":
                badge_col = (200, 130, 0)
                badge_txt = "AVISO"
            else:
                badge_col = (0, 160, 110)
                badge_txt = "OK"
            y_a = pdf.get_y()
            pdf.set_fill_color(bg, bg, bg)
            pdf.rect(10, y_a, 190, 8, style="F")
            pdf.set_fill_color(*badge_col)
            pdf.set_font("Helvetica", "B", 6.5)
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(12, y_a + 1.5)
            pdf.cell(16, 5, badge_txt, fill=True, align="C")
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(45, 45, 45)
            pdf.set_xy(31, y_a + 1.5)
            pdf.cell(125, 5, _s(a["msg"]))
            pdf.set_font("Helvetica", "", 6.5)
            pdf.set_text_color(150, 150, 150)
            pdf.set_xy(155, y_a + 1.5)
            pdf.cell(45, 5, _s(a["ts"]), align="R")
            pdf.set_y(y_a + 8)

    pdf.ln(5)

    # ── Estadísticas completas ────────────────────────────────
    section_title("Estadisticas del Rango")

    stat_cols_all = [
        ("V_L1N","V"), ("V_L2N","V"), ("V_L3N","V"),
        ("I_L1","A"), ("I_L2","A"), ("I_L3","A"),
        ("P_kW","kW"), ("Q_kVAr","kVAr"), ("S_kVA","kVA"),
        ("PF",""), ("Freq_Hz","Hz"),
        ("THD_V_L1","%"), ("THD_V_L2","%"), ("THD_V_L3","%"),
        ("THD_I_L1","%"), ("THD_I_L2","%"), ("THD_I_L3","%"),
    ]
    tbl_widths = [38, 27, 27, 27, 27, 18, 22]
    tbl_headers = ["Variable", "Min", "Media", "Max", "Desv.Est.", "Unidad", "Muestras"]
    pdf.set_fill_color(28, 32, 42)
    pdf.set_text_color(195, 210, 225)
    pdf.set_font("Helvetica", "B", 7.5)
    for h, w in zip(tbl_headers, tbl_widths):
        pdf.cell(w, 7, h, border=0, align="C", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    row_i = 0
    for col, unit in stat_cols_all:
        try:
            if col not in (df.columns if df is not None else []):
                continue
            col_data = df[col]
            if isinstance(col_data, pd.DataFrame):
                col_data = col_data.iloc[:, 0]
            s = pd.to_numeric(col_data, errors="coerce").dropna()
            if s.empty:
                continue
            bg = 252 if row_i % 2 == 0 else 244
            pdf.set_fill_color(bg, bg, bg)
            pdf.set_draw_color(220, 220, 220)
            row_data = [col, f"{s.min():.3f}", f"{s.mean():.3f}", f"{s.max():.3f}", f"{s.std():.3f}", unit, str(len(s))]
            for j, (val_txt, w) in enumerate(zip(row_data, tbl_widths)):
                pdf.set_font("Helvetica", "B" if j == 0 else "", 7.5)
                if j == 0:
                    pdf.set_text_color(50, 50, 50)
                else:
                    pdf.set_text_color(30, 30, 30)
                pdf.cell(w, 6, _s(val_txt), border="B", align="L" if j == 0 else "C",
                         fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(6)
            row_i += 1
        except Exception as _row_err:
            _log.debug("PDF table row rendering failed: %s", _row_err)
            continue

    # ── Gráficas ──────────────────────────────────────────────
    chart_groups = [
        (["V_L1N","V_L2N","V_L3N"], "Tensiones Fase-Neutro",       "V"),
        (["I_L1","I_L2","I_L3"],    "Corrientes por Fase",          "A"),
        (["P_kW","Q_kVAr","S_kVA"], "Potencias (kW / kVAr / kVA)", ""),
        (["PF"],                    "Factor de Potencia",           ""),
        (["THD_V_L1","THD_V_L2","THD_V_L3"], "THD Tension (%)",    "%"),
        (["THD_I_L1","THD_I_L2","THD_I_L3"], "THD Corriente (%)",  "%"),
    ]
    if _mpl_ok and df is not None and not df.empty and "ts" in df.columns:
        pdf.add_page()
        section_title("Graficas del Rango")
        ts_col = pd.to_datetime(df["ts"], errors="coerce")
        if LOCAL_TZ:
            try:
                if ts_col.dt.tz is None:
                    ts_col = ts_col.dt.tz_localize("UTC").dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
                else:
                    ts_col = ts_col.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
            except (TypeError, AttributeError):
                _log.debug("PDF chart: timezone conversion failed, using series as-is")
        palette = ["#00b386","#e07b2a","#3d6fa8","#c44a4a","#9b59b6","#f39c12"]
        for cols, title, unit in chart_groups:
            def _col_series(df, c):
                v = df[c]
                return v.iloc[:, 0] if isinstance(v, pd.DataFrame) else v
            cols_ok = [c for c in cols if c in df.columns and pd.to_numeric(_col_series(df, c), errors="coerce").notna().any()]
            if not cols_ok:
                continue
            try:
                fig_mpl, ax = plt.subplots(figsize=(9, 3.2))
                fig_mpl.patch.set_facecolor("white")
                ax.set_facecolor("#f7f9fb")
                for i, c in enumerate(cols_ok):
                    s_data = pd.to_numeric(_col_series(df, c), errors="coerce")
                    ax.plot(ts_col, s_data, linewidth=1.6, color=palette[i % len(palette)], label=c, alpha=0.9)
                ax.set_title(title, fontsize=11, color="#1a1a2e", fontweight="bold", pad=7)
                if unit:
                    ax.set_ylabel(unit, fontsize=8, color="#555555")
                ax.tick_params(axis="both", labelsize=8, colors="#555555")
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
                fig_mpl.autofmt_xdate(rotation=30, ha="right")
                ax.grid(True, color="#e0e4e8", linewidth=0.6, linestyle="--", alpha=0.8)
                for sp in ["top","right"]:
                    ax.spines[sp].set_visible(False)
                for sp in ["left","bottom"]:
                    ax.spines[sp].set_color("#cccccc")
                    ax.spines[sp].set_linewidth(0.7)
                ax.legend(fontsize=8, loc="upper right", framealpha=0.85, edgecolor="#dddddd", fancybox=True)
                plt.tight_layout(pad=0.8)
                buf = io.BytesIO()
                fig_mpl.savefig(buf, format="png", dpi=120, bbox_inches="tight")
                plt.close(fig_mpl)
                buf.seek(0)
                if pdf.get_y() > 210:
                    pdf.add_page()
                    section_title("Graficas del Rango (cont.)")
                pdf.image(buf, x=10, w=190)
                pdf.ln(5)
            except Exception as _chart_err:
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(180, 60, 60)
                pdf.cell(0, 4, _s(f"[Error grafica '{title}': {str(_chart_err)[:120]}]"),
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(2)

    return bytes(pdf.output())

# ============================================================
# UI HELPERS
# ============================================================
def section(label):
    st.markdown(f'<div class="is-section-title"><span class="is-mark"></span>{label}<span class="is-rule"></span></div>',unsafe_allow_html=True)

def card_open():  st.markdown('<div class="is-card">',unsafe_allow_html=True)
def card_close(): st.markdown('</div>',unsafe_allow_html=True)

# ============================================================
# ALARM HISTORY (SQLite persistence)
# ============================================================
def ensure_alarm_history_schema(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS alarm_history(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts TEXT NOT NULL,
          client_id INTEGER NOT NULL,
          level TEXT NOT NULL,
          msg TEXT NOT NULL,
          acknowledged INTEGER DEFAULT 0
        )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_alarm_history_client_ts ON alarm_history(client_id, ts)")
    con.commit()

def persist_alarms(con, alarms):
    cid = _get_cid()
    cur = con.cursor()
    for a in alarms:
        if a["level"] == "info": continue
        cur.execute("INSERT INTO alarm_history(ts,client_id,level,msg) VALUES(?,?,?,?)",
            (a["ts"], cid, a["level"], a["msg"]))
    con.commit()

def render_alarm_history(con):
    section("Histórico de Alarmas")
    cid = _get_cid()
    try:
        rows = con.execute(
            "SELECT ts,level,msg,acknowledged FROM alarm_history "
            "WHERE client_id=? ORDER BY id DESC LIMIT 300", (cid,)).fetchall()
    except sqlite3.OperationalError:
        st.info("Sin historial de alarmas aún."); return
    if not rows: st.info("Sin alarmas registradas."); return

    def _sc(v): return {"crit":"color:#c06060","warn":"color:#c0a040"}.get(v,"color:#888")
    rows_html = "".join(
        f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">'
        f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#555;padding:5px 8px;">{r[0]}</td>'
        f'<td style="font-size:10px;padding:5px 8px;{_sc(r[1])};">{r[1].upper()}</td>'
        f'<td style="font-size:11px;padding:5px 8px;color:#aaa;">{r[2]}</td>'
        f'<td style="font-size:10px;padding:5px 8px;color:#555;">{"Sí" if r[3] else "No"}</td></tr>'
        for r in rows
    )
    th = "font-family:IBM Plex Sans,sans-serif;font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#3a3a3a;padding:7px 8px;text-align:left;"
    st.markdown(
        f'<div style="background:#0b0b0b;border:1px solid rgba(255,255,255,0.07);border-radius:4px;overflow:auto;max-height:360px;">' +
        f'<table style="width:100%;border-collapse:collapse;"><thead>' +
        f'<tr style="border-bottom:1px solid rgba(255,255,255,0.10);">' +
        f'<th style="{th}">Timestamp</th><th style="{th}">Nivel</th>' +
        f'<th style="{th}">Descripción</th><th style="{th}">ACK</th>' +
        f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True)
    col_cl,col_ack = st.columns(2)
    with col_cl:
        if st.button("Limpiar historial", use_container_width=True):
            con.execute("DELETE FROM alarm_history WHERE client_id=?",(cid,)); con.commit()
            st.session_state["_last_persist_alarms_ts"] = datetime.now(timezone.utc).timestamp()
            st.rerun()
    with col_ack:
        if st.button("Reconocer todas", use_container_width=True):
            con.execute("UPDATE alarm_history SET acknowledged=1 WHERE client_id=?",(cid,)); con.commit(); st.rerun()

# ============================================================
# TREND ANALYSIS
# ============================================================
def render_trend_analysis(df):
    section("Análisis de Tendencias")
    if df is None or df.empty: st.info("Sin datos para análisis de tendencias."); return
    trend_cols = [c for c in ["P_kW","THD_V_L1","THD_I_L1","T_Nucleo","PF","Freq_Hz"] if c in df.columns]
    if not trend_cols: st.info("Sin señales disponibles."); return
    sel = st.selectbox("Señal para análisis de tendencia", trend_cols, key="trend_sel")
    d = df[["ts",sel]].copy()
    d["ts"] = pd.to_datetime(d["ts"],errors="coerce")
    d[sel]  = pd.to_numeric(d[sel],errors="coerce")
    d = d.dropna().sort_values("ts")
    if len(d)<5: st.info("Insuficientes puntos."); return
    t0 = d["ts"].iloc[0]
    d["t_sec"] = (d["ts"]-t0).dt.total_seconds()
    coeffs = np.polyfit(d["t_sec"],d[sel],1); slope=coeffs[0]; slope_h=slope*3600
    trend_y = np.polyval(coeffs,d["t_sec"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["ts"],y=d[sel],mode="lines",name=sel,
        line=dict(width=1.4,color=IS_GREEN),opacity=0.7))
    fig.add_trace(go.Scatter(x=d["ts"],y=trend_y,mode="lines",name="Tendencia",
        line=dict(width=2,color=IS_AMBER,dash="dash")))
    direction = "↑ Creciente" if slope>0 else "↓ Decreciente"
    color_dir = "#c06060" if slope>0 else IS_GREEN
    _pth(fig,title=f"Tendencia — {sel}  ({direction}  {abs(slope_h):.4f}/h)",height=280)
    st.plotly_chart(fig,use_container_width=True,key=_ck())
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;color:{color_dir};">{direction}<br><span style="font-size:20px;font-weight:600;">{abs(slope_h):.4f}</span><span style="font-size:10px;color:#555;"> /hora</span></div>',unsafe_allow_html=True)
    with c2:
        val_proj = float(d[sel].iloc[-1])+slope_h*24
        st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#888;">Proyección +24h<br><span style="font-size:20px;font-weight:600;color:#ccc;">{val_proj:.3f}</span></div>',unsafe_allow_html=True)
    with c3:
        corr=np.corrcoef(d["t_sec"],d[sel])[0,1]; r2=corr**2
        color_r2=IS_GREEN if r2>0.7 else (IS_AMBER if r2>0.3 else "#888")
        st.markdown(f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#888;">R² (confianza)<br><span style="font-size:20px;font-weight:600;color:{color_r2};">{r2:.3f}</span></div>',unsafe_allow_html=True)

# ============================================================
# PERIOD COMPARISON
# ============================================================
def render_period_comparison(con):
    section("Comparativa entre Periodos")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<div style="font-size:9px;color:#3a3a3a;font-weight:700;letter-spacing:.12em;text-transform:uppercase;font-family:IBM Plex Sans,sans-serif;margin-bottom:4px;">PERIODO A</div>',unsafe_allow_html=True)
        pa_from=st.date_input("Desde A",value=(datetime.now()-timedelta(days=7)).date(),key="cmp_a_from")
        pa_to  =st.date_input("Hasta A",value=(datetime.now()-timedelta(days=1)).date(),key="cmp_a_to")
    with c2:
        st.markdown('<div style="font-size:9px;color:#3a3a3a;font-weight:700;letter-spacing:.12em;text-transform:uppercase;font-family:IBM Plex Sans,sans-serif;margin-bottom:4px;">PERIODO B</div>',unsafe_allow_html=True)
        pb_from=st.date_input("Desde B",value=(datetime.now()-timedelta(days=1)).date(),key="cmp_b_from")
        pb_to  =st.date_input("Hasta B",value=datetime.now().date(),key="cmp_b_to")

    if st.button("Comparar periodos",use_container_width=True,key="btn_compare"):
        def _dt(d): return datetime.combine(d,datetime.min.time()).replace(tzinfo=LOCAL_TZ) if LOCAL_TZ else datetime.combine(d,datetime.min.time())
        def _dt2(d): return datetime.combine(d,datetime.max.time()).replace(tzinfo=LOCAL_TZ) if LOCAL_TZ else datetime.combine(d,datetime.max.time())
        with st.spinner("Cargando datos..."):
            dfa=_pivot_if_long(read_table_between(con,"measurements",_dt(pa_from),_dt2(pa_to)))
            dfb=_pivot_if_long(read_table_between(con,"measurements",_dt(pb_from),_dt2(pb_to)))
            if dfa is not None and not dfa.empty:
                dfa=_dedup_cols(dfa.rename(columns=MEAS_RENAME))
            if dfb is not None and not dfb.empty:
                dfb=_dedup_cols(dfb.rename(columns=MEAS_RENAME))
        metrics=["P_kW","Q_kVAr","PF","Freq_Hz","THD_V_L1","THD_I_L1","V_L1N","I_L1"]
        rows=[]
        for m in metrics:
            va=pd.to_numeric(dfa[m],errors="coerce").dropna() if dfa is not None and not dfa.empty and m in dfa.columns else pd.Series(dtype=float)
            vb=pd.to_numeric(dfb[m],errors="coerce").dropna() if dfb is not None and not dfb.empty and m in dfb.columns else pd.Series(dtype=float)
            if va.empty and vb.empty: continue
            ma=va.mean() if not va.empty else None; mb=vb.mean() if not vb.empty else None
            delta=((mb-ma)/ma*100) if ma and mb and ma!=0 else None
            rows.append({"Señal":m,"Media A":f"{ma:.3f}" if ma is not None else "—",
                         "Media B":f"{mb:.3f}" if mb is not None else "—",
                         "Δ%":f"{delta:+.2f}%" if delta is not None else "—","_d":delta})
        if not rows: st.warning("Sin datos comparables."); return
        def _dc(d): return "#c06060" if d and d>5 else ("#c0a040" if d and d>1 else IS_GREEN if d and d<=-1 else "#888")
        html_rows="".join(
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#aaa;padding:6px 10px;">{r["Señal"]}</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#888;padding:6px 10px;">{r["Media A"]}</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#888;padding:6px 10px;">{r["Media B"]}</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:12px;font-weight:600;color:{_dc(r.get("_d"))};padding:6px 10px;">{r["Δ%"]}</td></tr>'
            for r in rows
        )
        th="font-family:IBM Plex Sans,sans-serif;font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#3a3a3a;padding:7px 10px;text-align:left;"
        st.markdown(f'<div style="background:#0b0b0b;border:1px solid rgba(255,255,255,0.07);border-radius:4px;overflow:auto;"><table style="width:100%;border-collapse:collapse;"><thead><tr style="border-bottom:1px solid rgba(255,255,255,0.10);"><th style="{th}">Señal</th><th style="{th}">Periodo A</th><th style="{th}">Periodo B</th><th style="{th}">Variación</th></tr></thead><tbody>{html_rows}</tbody></table></div>',unsafe_allow_html=True)
        if dfa is not None and dfb is not None and "P_kW" in dfa.columns and "P_kW" in dfb.columns:
            fig=go.Figure()
            for dff,label,color in [(dfa,f"A ({pa_from})",IS_CYAN),(dfb,f"B ({pb_from})",IS_AMBER)]:
                dd=dff[["ts","P_kW"]].copy(); dd["ts"]=pd.to_datetime(dd["ts"],errors="coerce")
                if dd.empty: continue
                dd["h"]=(dd["ts"]-dd["ts"].min()).dt.total_seconds()/3600
                fig.add_trace(go.Scatter(x=dd["h"],y=pd.to_numeric(dd["P_kW"],errors="coerce"),
                    mode="lines",name=label,line=dict(color=color,width=1.4)))
            _pth(fig,title="Comparativa P_kW superpuesta",height=260)
            fig.update_layout(xaxis_title="Horas desde inicio",yaxis_title="kW")
            st.plotly_chart(fig,use_container_width=True,key=_ck())

# ============================================================
# ANNOTATIONS
# ============================================================
def ensure_annotations_schema(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS annotations(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts TEXT NOT NULL,
          client_id INTEGER NOT NULL,
          author TEXT,
          note TEXT NOT NULL
        )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_annotations_client_ts ON annotations(client_id, ts)")
    con.commit()



def render_annotations(con, df):
    section("Anotaciones del Operario")
    cid=int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
    author=st.session_state.get("username","operario")
    with st.form("form_annotation"):
        c1,c2=st.columns([0.35,0.65])
        with c1: ts_val=st.text_input("Timestamp",value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),key="ann_ts")
        with c2: note=st.text_input("Anotación",placeholder="Ej: Se cambió condensador banco C",key="ann_note")
        if st.form_submit_button("Guardar anotación"):
            note=(note or "").strip()
            if note:
                con.execute("INSERT INTO annotations(ts,client_id,author,note) VALUES(?,?,?,?)",(ts_val,cid,author,note))
                con.commit(); st.success("Guardado."); st.rerun()
            else: st.error("La anotación no puede estar vacía.")
    try:
        rows=con.execute("SELECT ts,author,note,id FROM annotations WHERE client_id=? ORDER BY ts DESC LIMIT 100",(cid,)).fetchall()
    except sqlite3.OperationalError:
        rows=[]
    if not rows: st.info("Sin anotaciones todavía."); return
    for ts_,auth_,note_,ann_id in rows:
        col_n,col_d=st.columns([0.87,0.13])
        with col_n:
            st.markdown(f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.06);border-left:2px solid {IS_AMBER};border-radius:3px;padding:7px 12px;margin-bottom:5px;"><span style="font-family:IBM Plex Mono,monospace;font-size:9px;color:#3a3a3a;">{_html.escape(str(ts_))} · {_html.escape(str(auth_))}</span><br><span style="font-size:12px;color:#aaa;">{_html.escape(str(note_))}</span></div>',unsafe_allow_html=True)
        with col_d:
            if st.button("✕",key=f"del_ann_{ann_id}"):
                con.execute("DELETE FROM annotations WHERE id=?",(ann_id,)); con.commit(); st.rerun()

# ============================================================
# DATA QUALITY METRICS
# ============================================================
def render_data_quality(df, dt_from, dt_to):
    section("Calidad del Sistema de Monitorización")
    if df is None or df.empty: st.info("Sin datos para analizar calidad."); return
    d=df[["ts"]].copy(); d["ts"]=pd.to_datetime(d["ts"],errors="coerce"); d=d.dropna(subset=["ts"]).sort_values("ts")
    span_sec=(dt_to-dt_from).total_seconds() if dt_to and dt_from else 0
    n_received=len(d); nominal_interval_s=5
    n_expected=max(int(span_sec/nominal_interval_s),1)
    completeness=min(n_received/n_expected*100,100)
    if len(d)>1:
        gaps=d["ts"].diff().dt.total_seconds().dropna()
        max_gap=gaps.max(); mean_gap=gaps.mean(); n_gaps=int((gaps>nominal_interval_s*3).sum())
    else:
        max_gap=mean_gap=0; n_gaps=0
    now_local=datetime.now(LOCAL_TZ) if LOCAL_TZ else datetime.now()
    last_ts=d["ts"].iloc[-1]
    if last_ts.tzinfo is None and LOCAL_TZ: last_ts=last_ts.replace(tzinfo=LOCAL_TZ)
    latency_s=max((now_local-last_ts).total_seconds(),0)
    key_cols=[c for c in ["V_L1N","I_L1","P_kW","PF","Freq_Hz"] if c in d.columns]
    nan_rates={c:d[c].isna().sum()/len(d)*100 for c in key_cols}
    color_comp=IS_GREEN if completeness>90 else (IS_AMBER if completeness>70 else IS_RED)
    color_lat =IS_GREEN if latency_s<30 else (IS_AMBER if latency_s<120 else IS_RED)
    color_gap =IS_GREEN if n_gaps==0 else (IS_AMBER if n_gaps<5 else IS_RED)
    def _met(col,label,val,unit,color):
        with col:
            st.markdown(f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);border-radius:4px;padding:10px 12px;"><div style="font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;margin-bottom:4px;">{label}</div><div style="font-family:IBM Plex Mono,monospace;font-size:22px;font-weight:500;color:{color};">{val}<span style="font-size:11px;color:#555;margin-left:3px;">{unit}</span></div></div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    _met(c1,"Completitud",f"{completeness:.1f}","%",color_comp)
    _met(c2,"Latencia",f"{latency_s:.0f}","s",color_lat)
    _met(c3,"Gaps detectados",str(n_gaps),"",color_gap)
    _met(c4,"Intervalo medio",f"{mean_gap:.1f}","s","#888")
    if len(d)>1:
        gaps_series=d["ts"].diff().dt.total_seconds().fillna(0)
        fig=go.Figure()
        fig.add_trace(go.Bar(x=d["ts"],y=gaps_series,
            marker_color=[IS_RED if g>nominal_interval_s*3 else "rgba(0,179,134,0.35)" for g in gaps_series],
            hovertemplate="<b>%{y:.1f}s</b><br>%{x|%H:%M:%S}<extra></extra>"))
        fig.add_hline(y=nominal_interval_s*3,line_dash="dash",line_color="rgba(196,154,10,0.50)",line_width=1,
            annotation_text=f"Umbral ({nominal_interval_s*3}s)",annotation_font=dict(size=9,color="rgba(196,154,10,0.70)"))
        _pth(fig,title="Intervalos entre muestras — Detección de gaps",height=200)
        fig.update_layout(yaxis_title="segundos",xaxis_title="Tiempo",showlegend=False)
        st.plotly_chart(fig,use_container_width=True,key=_ck())
    if nan_rates:
        cells=""
        for c,rate in nan_rates.items():
            col_r=IS_GREEN if rate<1 else (IS_AMBER if rate<5 else IS_RED)
            cells+=f'<div style="display:inline-flex;flex-direction:column;background:#101010;border:1px solid rgba(255,255,255,0.06);border-radius:3px;padding:6px 10px;margin:3px;"><span style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;">{c}</span><span style="font-family:IBM Plex Mono,monospace;font-size:14px;color:{col_r};">{rate:.2f}%</span></div>'
        st.markdown(f'<div style="margin-top:10px"><div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;margin-bottom:6px;">Tasa de valores nulos por señal</div><div style="display:flex;flex-wrap:wrap;gap:4px;">{cells}</div></div>',unsafe_allow_html=True)

# ============================================================
# ENERGY ANALYSIS — ADVANCED
# ============================================================

def ensure_energy_schema(con):
    con.execute("""CREATE TABLE IF NOT EXISTS daily_summary(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL, client_id INTEGER NOT NULL,
        kwh REAL, pf_mean REAL, thd_v_mean REAL, thd_i_mean REAL,
        p_max REAL, p_min REAL, alarm_count INTEGER DEFAULT 0,
        UNIQUE(date,client_id))""")
    con.execute("""CREATE TABLE IF NOT EXISTS motor_starts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL, client_id INTEGER NOT NULL,
        phase TEXT, peak_current REAL, duration_s REAL,
        UNIQUE(ts, client_id, phase))""")
    con.execute("""CREATE TABLE IF NOT EXISTS voltage_dips(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL, client_id INTEGER NOT NULL,
        phase TEXT, depth_pct REAL, duration_ms REAL,
        UNIQUE(ts, client_id, phase))""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_daily_summary_client_date ON daily_summary(client_id, date)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_motor_starts_client_ts    ON motor_starts(client_id, ts)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_voltage_dips_client_ts    ON voltage_dips(client_id, ts)")
    con.commit()

def save_daily_summary(con, df, dt_date):
    """Save aggregated daily stats to daily_summary table."""
    if df is None or df.empty: return
    cid = _get_cid()
    date_str = dt_date.strftime("%Y-%m-%d")
    kwh = None
    if "P_kW" in df.columns and "ts" in df.columns:
        d = df[["ts","P_kW"]].copy()
        d["ts"] = pd.to_datetime(d["ts"], errors="coerce")
        d["P_kW"] = pd.to_numeric(d["P_kW"], errors="coerce")
        d = d.dropna().sort_values("ts")
        if len(d) > 1:
            dt_h = (d["ts"].diff().dt.total_seconds()/3600).bfill().fillna(0)
            kwh = float((d["P_kW"] * dt_h).sum())
    def _m(col): return float(pd.to_numeric(df[col],errors="coerce").mean()) if col in df.columns else None
    def _mx(col): return float(pd.to_numeric(df[col],errors="coerce").max()) if col in df.columns else None
    def _mn(col): return float(pd.to_numeric(df[col],errors="coerce").min()) if col in df.columns else None
    try:
        con.execute("""INSERT OR REPLACE INTO daily_summary
            (date,client_id,kwh,pf_mean,thd_v_mean,thd_i_mean,p_max,p_min)
            VALUES(?,?,?,?,?,?,?,?)""",
            (date_str,cid,kwh,_m("PF"),_m("THD_V_L1"),_m("THD_I_L1"),_mx("P_kW"),_mn("P_kW")))
        con.commit()
    except Exception as _e: _log.debug("save_daily_summary: %s", _e)

def detect_motor_starts(df, con):
    """Detect current spikes >4x mean as motor starts."""
    if df is None or df.empty: return []
    cid = _get_cid()
    starts = []
    for ph in ["L1","L2","L3"]:
        col = f"I_{ph}"
        if col not in df.columns: continue
        d = df[["ts",col]].copy()
        d["ts"] = pd.to_datetime(d["ts"], errors="coerce")
        d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna().sort_values("ts")
        if d.empty: continue
        baseline = d[col].quantile(0.5)
        threshold = baseline * 4.0
        in_spike = False; spike_start = None; spike_peak = 0
        _db_rows = []
        for row in d.itertuples(index=False):
            val = getattr(row, col)
            if val > threshold:
                if not in_spike:
                    in_spike = True; spike_start = row.ts; spike_peak = val
                else:
                    spike_peak = max(spike_peak, val)
            else:
                if in_spike:
                    in_spike = False
                    dur = (row.ts - spike_start).total_seconds()
                    if 0.5 < dur < 30:  # valid start: 0.5s to 30s
                        starts.append({"ts":spike_start,"phase":ph,"peak":spike_peak,"dur":dur})
                        _db_rows.append((str(spike_start),cid,ph,spike_peak,dur))
        if _db_rows:
            try:
                con.executemany("INSERT OR IGNORE INTO motor_starts(ts,client_id,phase,peak_current,duration_s) VALUES(?,?,?,?,?)", _db_rows)
            except Exception as _e: _log.debug("motor_starts insert: %s", _e)
    if starts: con.commit()
    return starts

def detect_voltage_dips(df, con, nominal_v=230.0):
    """Detect voltage dips >10% for >10ms per IEC 61000-4-30."""
    if df is None or df.empty: return []
    cid = _get_cid()
    dips = []; threshold = nominal_v * 0.90
    for ph in ["L1","L2","L3"]:
        col = f"V_L{ph[-1]}N"
        if col not in df.columns: continue
        d = df[["ts",col]].copy()
        d["ts"] = pd.to_datetime(d["ts"], errors="coerce")
        d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna().sort_values("ts")
        if d.empty: continue
        in_dip = False; dip_start = None; dip_min = nominal_v
        _db_rows = []
        for row in d.itertuples(index=False):
            val = getattr(row, col)
            if val < threshold:
                if not in_dip:
                    in_dip = True; dip_start = row.ts; dip_min = val
                else:
                    dip_min = min(dip_min, val)
            else:
                if in_dip:
                    in_dip = False
                    dur_ms = (row.ts - dip_start).total_seconds() * 1000
                    if dur_ms >= 10:
                        depth = (nominal_v - dip_min)/nominal_v*100
                        dips.append({"ts":dip_start,"phase":ph,"depth_pct":depth,"dur_ms":dur_ms})
                        _db_rows.append((str(dip_start),cid,ph,depth,dur_ms))
        if _db_rows:
            try:
                con.executemany("INSERT OR IGNORE INTO voltage_dips(ts,client_id,phase,depth_pct,duration_ms) VALUES(?,?,?,?,?)", _db_rows)
            except Exception as _e: _log.debug("voltage_dips insert: %s", _e)
    if dips: con.commit()
    return dips

def render_load_heatmap(con):
    """Power heatmap by hour-of-day vs day-of-week from daily data."""
    section("Mapa de Calor — Consumo por Hora y Día")
    cid = _get_cid()
    try:
        rows = con.execute(
            "SELECT date,kwh FROM daily_summary WHERE client_id=? AND kwh IS NOT NULL ORDER BY date",
            (cid,)).fetchall()
    except sqlite3.OperationalError:
        rows = []

    # Fall back to current df if no daily summary yet
    df_h = _load_heatmap_data(con, cid)
    if df_h is None or df_h.empty:
        st.info("Se necesitan datos de al menos una semana para el mapa de calor. Los datos se van acumulando automáticamente.")
        return

    pivot = df_h.pivot_table(index="hour", columns="weekday", values="P_kW", aggfunc="mean")
    pivot.columns = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][:len(pivot.columns)]

    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=list(pivot.columns), y=[f"{h:02d}:00" for h in pivot.index],
        colorscale=[[0,"#0a0a0a"],[0.3,"rgba(0,100,60,0.8)"],[0.7,IS_AMBER],[1.0,IS_RED]],
        hovertemplate="<b>%{z:.2f} kW</b><br>%{x} %{y}<extra></extra>",
        colorbar=dict(title="kW",tickfont=dict(size=9,color="#555",family="IBM Plex Mono"),
                      titlefont=dict(size=9,color="#555"))))
    _pth(fig, title="Consumo medio por hora y día de la semana", height=380)
    fig.update_layout(yaxis=dict(autorange="reversed"),xaxis_title="",yaxis_title="Hora")
    st.plotly_chart(fig, use_container_width=True, key=_ck())

def _load_heatmap_data(con, cid):
    """Try to load measurements for heatmap from DB (last 30 days)."""
    now_local = datetime.now(LOCAL_TZ) if LOCAL_TZ else datetime.now()
    dt_from = now_local - timedelta(days=30)
    try:
        df = read_table_between(con, "measurements", dt_from, now_local, limit=500_000)
        df = _pivot_if_long(df)
        if df is None or df.empty: return None
        df = _dedup_cols(df.rename(columns=MEAS_RENAME))
        if "P_kW" not in df.columns or "ts" not in df.columns: return None
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df["P_kW"] = pd.to_numeric(df["P_kW"], errors="coerce")
        df = df.dropna(subset=["ts","P_kW"])
        df["hour"]    = df["ts"].dt.hour
        df["weekday"] = df["ts"].dt.dayofweek
        return df
    except Exception as _e:
        _log.warning("_load_heatmap_data: failed to load data: %s", _e)
        return None

def render_load_percentiles(df):
    """Daily load curve with P10/P50/P90 bands."""
    section("Curva de Carga — Percentiles P10/P50/P90")
    if df is None or df.empty or "P_kW" not in df.columns:
        st.info("Sin datos de P_kW."); return
    d = df[["ts","P_kW"]].copy()
    d["ts"] = pd.to_datetime(d["ts"], errors="coerce")
    d["P_kW"] = pd.to_numeric(d["P_kW"], errors="coerce")
    d = d.dropna().sort_values("ts")
    d["hour"] = d["ts"].dt.hour
    grp = d.groupby("hour")["P_kW"]
    p10 = grp.quantile(0.10); p50 = grp.quantile(0.50); p90 = grp.quantile(0.90)
    hours = list(range(24))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hours+hours[::-1],
        y=list(p90.reindex(hours,fill_value=0))+list(p10.reindex(hours,fill_value=0))[::-1],
        fill="toself",fillcolor="rgba(0,179,134,0.07)",line=dict(color="rgba(0,0,0,0)"),
        name="Rango P10-P90",showlegend=True))
    fig.add_trace(go.Scatter(x=hours,y=p10.reindex(hours,fill_value=0),mode="lines",
        line=dict(color=IS_CYAN,width=1,dash="dot"),name="P10"))
    fig.add_trace(go.Scatter(x=hours,y=p50.reindex(hours,fill_value=0),mode="lines",
        line=dict(color=IS_GREEN,width=2),name="P50 (mediana)"))
    fig.add_trace(go.Scatter(x=hours,y=p90.reindex(hours,fill_value=0),mode="lines",
        line=dict(color=IS_AMBER,width=1,dash="dot"),name="P90"))
    _pth(fig,title="Curva de carga diaria — Percentiles",height=300)
    fig.update_layout(xaxis=dict(tickmode="linear",tick0=0,dtick=1,title="Hora del día"),
                      yaxis_title="kW")
    st.plotly_chart(fig,use_container_width=True,key=_ck())

def render_motor_starts(df, con):
    section("Detección de Arranques de Motor")
    _now_e = datetime.now(timezone.utc).timestamp()
    if _now_e - st.session_state.get("_last_motor_detect_ts", 0) > 60:
        starts = detect_motor_starts(df, con)
        st.session_state["_last_motor_detect_ts"] = _now_e
    else:
        starts = []
    cid = int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
    # Also load historical
    try:
        hist = con.execute(
            "SELECT ts,phase,peak_current,duration_s FROM motor_starts "
            "WHERE client_id=? ORDER BY ts DESC LIMIT 100",(cid,)).fetchall()
    except sqlite3.OperationalError:
        hist=[]

    c1,c2 = st.columns(2)
    with c1:
        color = IS_GREEN if len(starts)==0 else IS_AMBER
        st.markdown(f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);'
                    f'border-radius:4px;padding:12px 16px;">'
                    f'<div style="font-size:9px;color:#3a3a3a;font-weight:700;letter-spacing:.12em;'
                    f'text-transform:uppercase;font-family:IBM Plex Sans,sans-serif;margin-bottom:4px;">Arranques detectados (rango actual)</div>'
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:28px;font-weight:500;color:{color};">'
                    f'{len(starts)}</div></div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);'
                    f'border-radius:4px;padding:12px 16px;">'
                    f'<div style="font-size:9px;color:#3a3a3a;font-weight:700;letter-spacing:.12em;'
                    f'text-transform:uppercase;font-family:IBM Plex Sans,sans-serif;margin-bottom:4px;">Arranques totales registrados</div>'
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:28px;font-weight:500;color:#888;">'
                    f'{len(hist)}</div></div>',unsafe_allow_html=True)

    if starts:
        fig = go.Figure()
        for ph,color in [("L1",PHASE_COLORS["L1"]),("L2",PHASE_COLORS["L2"]),("L3",PHASE_COLORS["L3"])]:
            ph_starts = [s for s in starts if s["phase"]==ph]
            if ph_starts:
                fig.add_trace(go.Scatter(
                    x=[s["ts"] for s in ph_starts],
                    y=[s["peak"] for s in ph_starts],
                    mode="markers", name=f"L{ph[-1]}",
                    marker=dict(color=color,size=10,symbol="triangle-up"),
                    hovertemplate="<b>%{y:.1f} A</b><br>%{x|%H:%M:%S}<extra></extra>"))
        if "I_L1" in df.columns:
            line_hud(df,["I_L1","I_L2","I_L3"],"A",
                [PHASE_COLORS["L1"],PHASE_COLORS["L2"],PHASE_COLORS["L3"]],
                "Corriente con arranques detectados")
        _pth(fig,title="Arranques de motor detectados",height=220)
        st.plotly_chart(fig,use_container_width=True,key=_ck())

    if hist:
        st.markdown("<div style='font-size:9px;color:#3a3a3a;font-weight:700;letter-spacing:.12em;"
                    "text-transform:uppercase;font-family:IBM Plex Sans,sans-serif;margin:10px 0 6px;'>"
                    "Últimos arranques registrados</div>",unsafe_allow_html=True)
        rows_html="".join(
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#555;padding:5px 8px;">{r[0]}</td>'
            f'<td style="font-size:10px;padding:5px 8px;color:#aaa;">L{r[1][-1]}</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;padding:5px 8px;color:#aaa;">{r[2]:.1f} A</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;padding:5px 8px;color:#aaa;">{r[3]:.1f} s</td></tr>'
            for r in hist[:20]
        )
        th="font-family:IBM Plex Sans,sans-serif;font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#3a3a3a;padding:7px 8px;text-align:left;"
        st.markdown(f'<div style="background:#0b0b0b;border:1px solid rgba(255,255,255,0.07);border-radius:4px;overflow:auto;max-height:280px;">'
            f'<table style="width:100%;border-collapse:collapse;"><thead>'
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.10);">'
            f'<th style="{th}">Timestamp</th><th style="{th}">Fase</th>'
            f'<th style="{th}">Pico</th><th style="{th}">Duración</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>',unsafe_allow_html=True)

def render_voltage_dips(df, con):
    section("Huecos de Tensión — IEC 61000-4-30")
    _now_e = datetime.now(timezone.utc).timestamp()
    if _now_e - st.session_state.get("_last_dip_detect_ts", 0) > 60:
        dips = detect_voltage_dips(df, con)
        st.session_state["_last_dip_detect_ts"] = _now_e
    else:
        dips = []
    cid = int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
    try:
        hist = con.execute(
            "SELECT ts,phase,depth_pct,duration_ms FROM voltage_dips "
            "WHERE client_id=? ORDER BY ts DESC LIMIT 100",(cid,)).fetchall()
    except sqlite3.OperationalError:
        hist=[]

    c1,c2 = st.columns(2)
    with c1:
        color = IS_GREEN if len(dips)==0 else IS_RED
        st.markdown(f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);'
                    f'border-radius:4px;padding:12px 16px;">'
                    f'<div style="font-size:9px;color:#3a3a3a;font-weight:700;letter-spacing:.12em;'
                    f'text-transform:uppercase;font-family:IBM Plex Sans,sans-serif;margin-bottom:4px;">Huecos detectados (rango actual)</div>'
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:28px;font-weight:500;color:{color};">'
                    f'{len(dips)}</div></div>',unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);'
                    f'border-radius:4px;padding:12px 16px;">'
                    f'<div style="font-size:9px;color:#3a3a3a;font-weight:700;letter-spacing:.12em;'
                    f'text-transform:uppercase;font-family:IBM Plex Sans,sans-serif;margin-bottom:4px;">Total registrados históricamente</div>'
                    f'<div style="font-family:IBM Plex Mono,monospace;font-size:28px;font-weight:500;color:#888;">'
                    f'{len(hist)}</div></div>',unsafe_allow_html=True)

    if hist:
        rows_html="".join(
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.04);">'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;color:#555;padding:5px 8px;">{r[0]}</td>'
            f'<td style="font-size:10px;padding:5px 8px;color:#aaa;">V L{r[1][-1] if r[1] else "?"}</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;padding:5px 8px;'
            f'color:{IS_RED if r[2]>20 else (IS_AMBER if r[2]>10 else "#888")};">{r[2]:.1f}%</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:10px;padding:5px 8px;color:#aaa;">{r[3]:.0f} ms</td></tr>'
            for r in hist[:20]
        )
        th="font-family:IBM Plex Sans,sans-serif;font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#3a3a3a;padding:7px 8px;text-align:left;"
        st.markdown(f'<div style="background:#0b0b0b;border:1px solid rgba(255,255,255,0.07);border-radius:4px;overflow:auto;max-height:280px;">'
            f'<table style="width:100%;border-collapse:collapse;"><thead>'
            f'<tr style="border-bottom:1px solid rgba(255,255,255,0.10);">'
            f'<th style="{th}">Timestamp</th><th style="{th}">Fase</th>'
            f'<th style="{th}">Profundidad</th><th style="{th}">Duración</th>'
            f'</tr></thead><tbody>{rows_html}</tbody></table></div>',unsafe_allow_html=True)

def render_anomaly_detection(df):
    """Flag points >3σ from rolling mean."""
    section("Detección de Anomalías Estadísticas (3σ)")
    if df is None or df.empty: st.info("Sin datos."); return
    sig_cols = [c for c in ["P_kW","V_L1N","I_L1","THD_V_L1","PF"] if c in df.columns]
    if not sig_cols: st.info("Sin señales disponibles."); return
    sel = st.selectbox("Señal para análisis de anomalías",sig_cols,key="anom_sel")
    d = df[["ts",sel]].copy()
    d["ts"] = pd.to_datetime(d["ts"],errors="coerce")
    d[sel] = pd.to_numeric(d[sel],errors="coerce"); d = d.dropna().sort_values("ts")
    if len(d)<20: st.info("Insuficientes puntos."); return
    win = max(20,len(d)//10)
    d["roll_mean"] = d[sel].rolling(win,center=True,min_periods=5).mean()
    d["roll_std"]  = d[sel].rolling(win,center=True,min_periods=5).std()
    d["upper"] = d["roll_mean"]+3*d["roll_std"]
    d["lower"] = d["roll_mean"]-3*d["roll_std"]
    d["anomaly"] = (d[sel]>d["upper"])|(d[sel]<d["lower"])
    n_anom = d["anomaly"].sum()
    fig=go.Figure()
    # Confidence band
    fig.add_trace(go.Scatter(
        x=list(d["ts"])+list(d["ts"])[::-1],
        y=list(d["upper"])+list(d["lower"])[::-1],
        fill="toself",fillcolor="rgba(0,179,134,0.06)",
        line=dict(color="rgba(0,0,0,0)"),name="Banda 3σ",showlegend=True))
    fig.add_trace(go.Scatter(x=d["ts"],y=d[sel],mode="lines",name=sel,
        line=dict(width=1.4,color="rgba(160,160,160,0.60)"),showlegend=True))
    fig.add_trace(go.Scatter(x=d["ts"],y=d["roll_mean"],mode="lines",name="Media móvil",
        line=dict(width=1.8,color=IS_GREEN,dash="dash")))
    anom_pts = d[d["anomaly"]]
    if not anom_pts.empty:
        fig.add_trace(go.Scatter(x=anom_pts["ts"],y=anom_pts[sel],mode="markers",
            name="Anomalía",marker=dict(color=IS_RED,size=8,symbol="x")))
    _pth(fig,title=f"Anomalías 3σ — {sel}  ({n_anom} detectadas)",height=300)
    st.plotly_chart(fig,use_container_width=True,key=_ck())
    if n_anom>0:
        st.markdown(f'<div style="background:rgba(176,48,48,0.08);border:1px solid rgba(176,48,48,0.25);'
                    f'border-radius:3px;padding:8px 12px;font-size:11px;color:#c06060;">'
                    f'⚠ {int(n_anom)} punto(s) fuera del rango estadístico normal (±3σ). '
                    f'Revisar transitorios o eventos anómalos.</div>',unsafe_allow_html=True)

# ============================================================
# PREDICTIVE & MAINTENANCE
# ============================================================
def render_capacitor_bank(df):
    section("Corrección de Factor de Potencia — Banco de Condensadores")
    if df is None or df.empty: st.info("Sin datos de potencia."); return
    pf_now  = _last_num(df,"PF")
    p_kw    = _last_num(df,"P_kW")
    if pf_now is None or p_kw is None or pf_now<=0:
        st.info("Sin datos de PF o P_kW."); return

    st.markdown(f'<div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;">'
        f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);border-radius:4px;'
        f'padding:10px 16px;min-width:140px;">'
        f'<div style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;'
        f'font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:3px;">PF Actual</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:24px;color:{"#c06060" if pf_now<0.9 else IS_GREEN};">{pf_now:.3f}</div></div>'
        f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);border-radius:4px;'
        f'padding:10px 16px;min-width:140px;">'
        f'<div style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;'
        f'font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:3px;">P Activa</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:24px;color:#aaa;">{p_kw:.2f} <span style="font-size:12px;color:#555;">kW</span></div></div>'
        f'</div>',unsafe_allow_html=True)

    pf_target = st.slider("Factor de potencia objetivo",min_value=0.90,max_value=1.00,
                          value=0.95,step=0.01,key="pf_target_slider")

    if pf_now >= pf_target:
        st.success(f"✓ PF actual ({pf_now:.3f}) ya supera el objetivo ({pf_target:.3f}). No se requiere corrección.")
        return

    phi_actual = np.arccos(np.clip(pf_now,0,1))
    phi_target = np.arccos(np.clip(pf_target,0,1))
    q_needed   = p_kw * (np.tan(phi_actual) - np.tan(phi_target))

    # Standard capacitor bank sizes (kVAr)
    std_sizes = [5,10,15,20,25,30,40,50,60,75,100,150,200]
    best_single  = min(std_sizes, key=lambda x: abs(x-q_needed))
    # Find combination of 2
    best_combo = None; best_err = float("inf")
    for a in std_sizes:
        for b in std_sizes:
            if abs(a+b-q_needed) < best_err:
                best_err=abs(a+b-q_needed); best_combo=(a,b)

    st.markdown(
        f'<div style="background:#0b0b0b;border:1px solid rgba(255,255,255,0.09);border-radius:4px;padding:16px 20px;margin:10px 0;">'
        f'<div style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px;">Resultado del cálculo</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:13px;color:#aaa;line-height:2.2;">'
        f'kVAr necesarios: <span style="color:{IS_GREEN};font-size:18px;font-weight:600;">{q_needed:.2f} kVAr</span><br>'
        f'Banco individual más cercano: <span style="color:#ccc;">{best_single} kVAr</span><br>'
        f'Combinación óptima: <span style="color:#ccc;">{best_combo[0]} + {best_combo[1]} kVAr = {sum(best_combo)} kVAr</span><br>'
        f'PF resultante (teórico): <span style="color:{IS_GREEN};">'
        f'{np.cos(np.arctan(np.tan(phi_actual)-q_needed/p_kw)):.3f}</span>'
        f'</div></div>',unsafe_allow_html=True)

def render_k_factor(df):
    """K-factor (transformer heating due to harmonics) and cumulative THD damage."""
    section("Factor K — Daño Acumulado por Armónicos en Transformador")
    if df is None or df.empty: st.info("Sin datos."); return

    # K-factor = sum(h^2 * Ih^2) / sum(Ih^2)
    harmonics = {}
    for o in ORDERS:
        for ph in ["L1"]:
            col = f"H{o}_I_{ph}"
            v = _last_num(df,col,mode="max_tail",tail=30)
            if v is not None: harmonics[o] = v

    i_fund = _last_num(df,"I_L1")
    if not harmonics or i_fund is None:
        st.info("Sin datos de armónicos de corriente por orden."); return

    # Normalise harmonics to per-unit of fundamental
    h_pu = {h: v/max(i_fund,0.001) for h,v in harmonics.items()}
    sum_h2_ih2 = sum(h**2 * v**2 for h,v in h_pu.items())
    sum_ih2    = sum(v**2 for v in h_pu.values()) + 1.0  # +1 for fundamental
    k_factor   = sum_h2_ih2 / sum_ih2 if sum_ih2>0 else 1.0

    color_k = IS_GREEN if k_factor<4 else (IS_AMBER if k_factor<13 else IS_RED)
    rating_text = ("K-1 (transformador estándar)" if k_factor<4
                   else "K-4 (moderado)" if k_factor<13
                   else "K-13+ (alto — transformador especial recomendado)")

    st.markdown(
        f'<div style="background:#0b0b0b;border:1px solid rgba(255,255,255,0.09);border-radius:4px;padding:16px 20px;">'
        f'<div style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px;">Factor K calculado</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:40px;font-weight:600;color:{color_k};">{k_factor:.2f}</div>'
        f'<div style="font-size:11px;color:#888;margin-top:6px;">{rating_text}</div>'
        f'<div style="font-size:10px;color:#444;margin-top:10px;">Fórmula: K = Σ(h² × I_h²) / Σ(I_h²) — IEEE C57.110</div>'
        f'</div>',unsafe_allow_html=True)

    # Bar chart of harmonic contribution to K-factor
    if harmonics:
        fig=go.Figure()
        h_list=sorted(harmonics.keys()); contributions=[h**2*h_pu.get(h,0)**2 for h in h_list]
        fig.add_trace(go.Bar(x=[f"H{h}" for h in h_list],y=contributions,
            marker_color=[IS_RED if c==max(contributions) else IS_AMBER for c in contributions],
            hovertemplate="<b>%{y:.4f}</b><br>%{x}<extra></extra>"))
        _pth(fig,title="Contribución de cada armónico al Factor K",height=230)
        fig.update_layout(yaxis_title="h²·I_h²",xaxis_title="Orden armónico",showlegend=False)
        st.plotly_chart(fig,use_container_width=True,key=_ck())

def render_transformer_hotspot(df):
    """Estimate transformer hot-spot temperature per IEC 60076-7."""
    section("Temperatura de Punto Caliente del Transformador — IEC 60076-7")
    if df is None or df.empty: st.info("Sin datos."); return
    p_kw = _last_num(df,"P_kW"); s_kva = _last_num(df,"S_kVA")
    # Need ambient temp — use T_Nucleo if available
    t_amb = _last_num(df,"T_Nucleo") or 20.0
    if p_kw is None or s_kva is None:
        st.info("Se necesitan P_kW y S_kVA para estimar la temperatura."); return

    # Assume rated kVA = max S_kVA seen in last 200 samples
    s_rated = _last_num(df,"S_kVA",mode="max_tail",tail=200) or s_kva
    load_factor = min(s_kva/max(s_rated,0.001),1.2)

    # IEC 60076-7 simplified: delta_theta_oil = delta_theta_oil_rated * K^(2*n)
    # Typical ONAN: delta_theta_oil_rated=55°C, n=0.8, delta_theta_hs=23°C
    delta_oil_rated = 55.0; n = 0.8; delta_hs = 23.0
    delta_oil = delta_oil_rated * (load_factor**(2*n))
    t_hotspot = t_amb + delta_oil + delta_hs

    color_t = IS_GREEN if t_hotspot<98 else (IS_AMBER if t_hotspot<108 else IS_RED)
    limit_text = "Normal" if t_hotspot<98 else ("Atención" if t_hotspot<108 else "CRÍTICO — riesgo de degradación")

    st.markdown(
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;">'
        f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);border-radius:4px;padding:12px 16px;min-width:160px;">'
        f'<div style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:3px;">Temperatura Punto Caliente (est.)</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:28px;color:{color_t};">{t_hotspot:.1f}°C</div>'
        f'<div style="font-size:10px;color:#555;margin-top:4px;">{limit_text}</div></div>'
        f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);border-radius:4px;padding:12px 16px;min-width:160px;">'
        f'<div style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:3px;">Factor de carga</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:28px;color:#aaa;">{load_factor:.2f}</div></div>'
        f'<div style="background:#101010;border:1px solid rgba(255,255,255,0.07);border-radius:4px;padding:12px 16px;min-width:160px;">'
        f'<div style="font-size:9px;color:#3a3a3a;font-family:IBM Plex Sans,sans-serif;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-bottom:3px;">Temp. ambiente / núcleo</div>'
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:28px;color:#aaa;">{t_amb:.1f}°C</div></div>'
        f'</div>',unsafe_allow_html=True)
    st.markdown('<div style="font-size:9px;color:#2a2a2a;font-family:IBM Plex Sans,sans-serif;margin-top:8px;">Modelo: IEC 60076-7 simplificado (ONAN). Para cálculo exacto se requiere curva térmica del transformador.</div>',unsafe_allow_html=True)

def render_daily_summary_chart(con):
    section("Resumen Diario Histórico")
    cid = int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
    try:
        rows = con.execute(
            "SELECT date,kwh,pf_mean,thd_v_mean,p_max FROM daily_summary "
            "WHERE client_id=? AND kwh IS NOT NULL ORDER BY date DESC LIMIT 90",(cid,)).fetchall()
    except sqlite3.OperationalError:
        rows=[]
    if not rows: st.info("Aún no hay resúmenes diarios. Se generan automáticamente al cargar datos de días completos."); return
    ds = pd.DataFrame(rows,columns=["Fecha","kWh","PF_medio","THD_V_medio","P_max"])
    ds["Fecha"] = pd.to_datetime(ds["Fecha"])
    ds = ds.sort_values("Fecha")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ds["Fecha"],y=ds["kWh"],name="kWh/día",
        marker_color=IS_GREEN,opacity=0.75,
        hovertemplate="<b>%{y:.2f} kWh</b><br>%{x|%Y-%m-%d}<extra></extra>"))
    _pth(fig,title="Consumo diario (kWh)",height=260)
    fig.update_layout(yaxis_title="kWh",xaxis_title="",showlegend=False)
    st.plotly_chart(fig,use_container_width=True,key=_ck())

    col_pf,col_thd = st.columns(2)
    with col_pf:
        fig2=go.Figure()
        fig2.add_trace(go.Scatter(x=ds["Fecha"],y=ds["PF_medio"],mode="lines+markers",
            name="PF medio",line=dict(color=IS_CYAN,width=1.6),
            marker=dict(size=4)))
        fig2.add_hline(y=0.9,line_dash="dash",line_color="rgba(196,154,10,0.50)",line_width=1)
        _pth(fig2,title="Factor de potencia medio diario",height=220)
        fig2.update_layout(yaxis_title="PF",showlegend=False)
        st.plotly_chart(fig2,use_container_width=True,key=_ck())
    with col_thd:
        fig3=go.Figure()
        fig3.add_trace(go.Scatter(x=ds["Fecha"],y=ds["THD_V_medio"],mode="lines+markers",
            name="THD-V",line=dict(color=IS_AMBER,width=1.6),
            marker=dict(size=4)))
        fig3.add_hline(y=8,line_dash="dash",line_color="rgba(196,154,10,0.50)",line_width=1,
            annotation_text="EN 50160",annotation_font=dict(size=9,color="rgba(196,154,10,0.70)"))
        _pth(fig3,title="THD-V medio diario (%)",height=220)
        fig3.update_layout(yaxis_title="%",showlegend=False)
        st.plotly_chart(fig3,use_container_width=True,key=_ck())

# ============================================================
# TABS
# ============================================================
# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    cid_now=int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
    st.session_state["client_name"]=CLIENT_LABEL_BY_ID.get(cid_now,st.session_state.get("client_name","—"))
    client_name=st.session_state.get("client_name","—")
    now_local=datetime.now(LOCAL_TZ) if LOCAL_TZ else datetime.now()

    st.markdown(f'<div class="is-client-card"><div class="cc-label">Cliente activo</div>'
                f'<div class="cc-name">{client_name}</div>'
                f'<div class="cc-sub"><span class="is-led"></span>Monitorización en línea</div></div>',
                unsafe_allow_html=True)

    if st.button("Cerrar sesión",use_container_width=True):
        st.session_state.clear(); st.rerun()

    st.markdown("<div style='height:5px'></div>",unsafe_allow_html=True)

    with st.expander("Visualización",expanded=True):
        RANGES=["Últimos 5 min","Últimos 15 min","Últimos 30 min","Última 1 h","Últimas 6 h",
                "Últimas 12 h","Últimas 24 h","Últimos 2 días","Última semana","Último mes",
                "Últimos 6 meses","Último año","Últimos 2 años","Personalizado (desde / hasta)"]
        rng=st.selectbox("Rango temporal",RANGES,index=0,key="cfg_rng")

        custom_from=custom_to=None
        if rng=="Personalizado (desde / hasta)":
            c1,c2=st.columns(2)
            with c1:
                df_d=st.date_input("Desde (día)",value=datetime.now().date(),key="rng_from_day")
                tf_d=st.time_input("Desde (hora)",value=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).time(),key="rng_from_time")
            with c2:
                dt_d=st.date_input("Hasta (día)",value=datetime.now().date(),key="rng_to_day")
                tt_d=st.time_input("Hasta (hora)",value=datetime.now().replace(hour=23,minute=59,second=0,microsecond=0).time(),key="rng_to_time")
            dtf=datetime.combine(df_d,tf_d); dtt=datetime.combine(dt_d,tt_d)
            if LOCAL_TZ: custom_from=dtf.replace(tzinfo=LOCAL_TZ); custom_to=dtt.replace(tzinfo=LOCAL_TZ)
            else: custom_from,custom_to=dtf,dtt
            if custom_to<custom_from: st.error("Rango inválido."); custom_from=custom_to=None

        st.session_state["custom_from"]=custom_from; st.session_state["custom_to"]=custom_to

        allowed=[int(c) for c in st.session_state.get("allowed_client_ids",list(CLIENT_LABEL_BY_ID.keys()))]
        allowed=[c for c in allowed if c in CLIENT_LABEL_BY_ID] or [DEFAULT_CLIENT_ID]
        labels=[CLIENT_LABEL_BY_ID[c] for c in allowed]
        cur_cid=int(st.session_state.get("client_id",DEFAULT_CLIENT_ID))
        if cur_cid not in allowed: cur_cid=allowed[0]; st.session_state["client_id"]=cur_cid
        cur_lbl=CLIENT_LABEL_BY_ID.get(cur_cid,labels[0])
        if cur_lbl not in labels: cur_lbl=labels[0]
        new_lbl=st.selectbox("Cliente (datos)",labels,index=labels.index(cur_lbl))
        new_cid=CLIENT_ID_BY_LABEL[new_lbl]
        if int(new_cid)!=int(st.session_state.get("client_id",DEFAULT_CLIENT_ID)):
            st.session_state["client_id"]=int(new_cid)
            st.session_state["client_name"]=CLIENT_LABEL_BY_ID.get(int(new_cid),new_lbl)
            try:
                st.cache_data.clear()
            except AttributeError:
                pass  # st.cache_data.clear() not available in this Streamlit version
            st.rerun()

        refresh_mode=st.selectbox("Auto-refresh",["Cada 5 s (normal)","Cada 1 s (rápido)","Cada 10 s (ahorro)","Manual"],key="cfg_refresh_mode")
        if st.button("Actualizar ahora",use_container_width=True): st.rerun()

    st.session_state["refresh_mode"]=refresh_mode
    st.session_state["rng"]=rng


    with st.expander("Sistema",expanded=False):
        st.markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#3a3a3a;line-height:2.0;'>"
                    f"<span style='color:#252525'>HORA&nbsp;&nbsp;</span>{now_local.strftime('%Y-%m-%d %H:%M:%S')}<br>"
                    f"<span style='color:#252525'>ZONA&nbsp;&nbsp;</span>{LOCAL_TZ_NAME}<br>"
                    f"<span style='color:#252525'>VER&nbsp;&nbsp;&nbsp;</span>v3.0.0</div>",unsafe_allow_html=True)

enable_refresh(_refresh_seconds(st.session_state.get("refresh_mode","Cada 5 s (normal)")))

# ============================================================
# CARGA DATOS
# ============================================================
rng=st.session_state.get("rng","Últimos 15 min")
now_local=datetime.now(LOCAL_TZ) if LOCAL_TZ else datetime.now()
custom_from=st.session_state.get("custom_from"); custom_to=st.session_state.get("custom_to")

if rng=="Personalizado (desde / hasta)" and custom_from and custom_to: dt_from,dt_to=custom_from,custom_to
else: dt_to=now_local; dt_from=now_local-_range_to_td(rng)

# Calcular span y bucket ANTES de la query para elegir estrategia de carga
span_sec=int((dt_to-dt_from).total_seconds()) if dt_to and dt_from else 3600
bucket=(1 if span_sec<=900 else 2 if span_sec<=1800 else 5 if span_sec<=3600
        else 15 if span_sec<=6*3600 else 30 if span_sec<=12*3600 else 60 if span_sec<=2*86400
        else 300 if span_sec<=7*86400 else 900 if span_sec<=30*86400 else 3600)

# Para rangos > 2 días intentar agregación SQL; si devuelve vacío, fallback con límite mayor
_use_sql_agg = bucket > 1 and span_sec > 2 * 86400
if _use_sql_agg:
    df_meas_all=read_table_between_agg(conn,"measurements",dt_from,dt_to,bucket,limit=500_000)
    df_states_all=read_table_between_agg(conn,"states",dt_from,dt_to,bucket,limit=500_000)
    # Si la agregación SQL no devuelve datos, reintentar con límite dinámico
    if df_meas_all is None or df_meas_all.empty:
        _use_sql_agg=False
        HARD_LIMIT=min(2_000_000,max(250_000,span_sec))
        df_meas_all=read_table_between(conn,"measurements",dt_from,dt_to,limit=HARD_LIMIT)
    if df_states_all is None or df_states_all.empty:
        HARD_LIMIT=min(2_000_000,max(250_000,span_sec))
        df_states_all=read_table_between(conn,"states",dt_from,dt_to,limit=HARD_LIMIT)
else:
    HARD_LIMIT=250_000
    df_meas_all=read_table_between(conn,"measurements",dt_from,dt_to,limit=HARD_LIMIT)
    df_states_all=read_table_between(conn,"states",dt_from,dt_to,limit=HARD_LIMIT)

df_meas_all=_pivot_if_long(df_meas_all); df_states_all=_pivot_if_long(df_states_all)

if df_meas_all is not None and not df_meas_all.empty:
    df_meas_all=_dedup_cols(df_meas_all.rename(columns=MEAS_RENAME))
    if "ts" in df_meas_all.columns: df_meas_all=df_meas_all.dropna(subset=["ts"]).sort_values("ts")

MAX_POINTS=50_000
_need_ds=bucket>1 and not _use_sql_agg
if df_meas_all  is not None and not df_meas_all.empty  and (len(df_meas_all)  >MAX_POINTS or _need_ds): df_meas_all  =_downsample(df_meas_all,  bucket,how="max")
if df_states_all is not None and not df_states_all.empty and (len(df_states_all)>MAX_POINTS or _need_ds): df_states_all=_downsample(df_states_all,bucket,how="last")

df=df_meas_all; df_states=df_states_all

# Pre-process states
states_proc=df_states.copy() if isinstance(df_states,pd.DataFrame) else pd.DataFrame()
if not states_proc.empty:
    for c in ["EstadoIEQ","TestigoR","TestigoS","TestigoT","Seta","Fallo_red"]:
        if c in states_proc.columns:
            states_proc[c]=pd.to_numeric(states_proc[c],errors="coerce").fillna(0).astype(int)
            states_proc[c+"_OK"]=(1-states_proc[c]).clip(0,1)

# Last update time
last_update=df["ts"].iloc[-1] if df is not None and not df.empty and "ts" in df.columns else None
if last_update is not None:
    _lu = last_update if (hasattr(last_update,"tzinfo") and last_update.tzinfo is not None) else (last_update.replace(tzinfo=LOCAL_TZ) if LOCAL_TZ else last_update)
    try:
        seconds_ago=int((now_local-_lu).total_seconds())
    except TypeError:
        seconds_ago=None
else: seconds_ago=None

# Generación de informes fuera de contextos sidebar/tab para evitar excepciones internas de Streamlit

if st.session_state.get("_export_xls_pending"):
    _ef, _et = st.session_state.pop("_export_xls_pending")
    with st.spinner("Generando Excel…"):
        try:
            _xls2 = render_excel_download(conn, _ef, _et)
            if _xls2:
                st.session_state["_export_xls"] = _xls2
            else:
                st.session_state["_export_xls_err"] = "Sin datos en el rango seleccionado."
        except Exception as _e:
            _log.error("Excel export failed: %s", _e, exc_info=True)
            st.session_state["_export_xls_err"] = f"{type(_e).__name__}: {str(_e)[:200]}"

if st.session_state.get("_export_pdf_pending"):
    _pf, _pt = st.session_state.pop("_export_pdf_pending")
    with st.spinner("Generando PDF…"):
        try:
            _df_exp = read_table_between(conn, "measurements", _pf, _pt)
            _df_exp = _pivot_if_long(_df_exp)
            if _df_exp is not None and not _df_exp.empty:
                _df_exp = _dedup_cols(_df_exp.rename(columns=MEAS_RENAME))
                if "ts" in _df_exp.columns:
                    _df_exp = _df_exp.dropna(subset=["ts"]).sort_values("ts")
                # Downsample para rangos largos (evita timeout con matplotlib)
                _exp_span = int((_pt - _pf).total_seconds())
                _exp_bucket = (1 if _exp_span<=900 else 2 if _exp_span<=1800 else 5 if _exp_span<=3600
                               else 15 if _exp_span<=6*3600 else 30 if _exp_span<=12*3600
                               else 60 if _exp_span<=2*86400 else 300 if _exp_span<=7*86400
                               else 900 if _exp_span<=30*86400 else 3600)
                if _exp_bucket > 1 and _df_exp is not None and not _df_exp.empty:
                    _df_exp = _downsample(_df_exp, _exp_bucket, how="mean")
            _alarms_exp = compute_alarms(_df_exp)
            _rng_exp = f"{_pf.strftime('%Y-%m-%d %H:%M')} — {_pt.strftime('%Y-%m-%d %H:%M')}"
            _pdf_result = render_pdf_report(_df_exp, client_name, _rng_exp, _alarms_exp)
            if _pdf_result:
                _pdf_name = f"Informe_{client_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.session_state["_export_pdf"] = (_pdf_result, _pdf_name)
            else:
                st.session_state["_export_pdf_err"] = "El PDF no pudo generarse."
        except Exception as _e:
            _log.error("PDF export failed: %s", _e, exc_info=True)
            _err_msg = str(_e) or type(_e).__name__
            st.session_state["_export_pdf_err"] = f"Error al generar PDF: {type(_e).__name__}: {_err_msg[:300]}"

# ============================================================
# PAGE HEADER
# ============================================================

st.session_state["_ck"]=0  # reset chart key counter each render

alarms_now=compute_alarms(df)
# persist_alarms throttled: max once per 60s para no llenar alarm_history con duplicados
_now_epoch_alarms = datetime.now(timezone.utc).timestamp()
if _now_epoch_alarms - st.session_state.get("_last_persist_alarms_ts", 0) > 60:
    persist_alarms(conn, alarms_now)
    st.session_state["_last_persist_alarms_ts"] = _now_epoch_alarms
# Save daily summary for historical charts (throttled: max once per 60s)
_now_epoch = datetime.now(timezone.utc).timestamp()
if _now_epoch - st.session_state.get("_last_daily_summary_ts", 0) > 60:
    save_daily_summary(conn, df, dt_from.date() if hasattr(dt_from,'date') else datetime.now().date())
    st.session_state["_last_daily_summary_ts"] = _now_epoch

n_crit=sum(1 for a in alarms_now if a["level"]=="crit")
n_warn=sum(1 for a in alarms_now if a["level"]=="warn")
if n_crit>0: alarm_tag=f'<span class="is-tag err">⚠ {n_crit} CRIT</span>'
elif n_warn>0: alarm_tag=f'<span class="is-tag wrn">△ {n_warn} WARN</span>'
else: alarm_tag='<span class="is-tag ok">✓ Sin alarmas</span>'

if seconds_ago is not None:
    if seconds_ago<10: upd_tag=f'<span class="is-tag ok">↺ hace {seconds_ago}s</span>'
    elif seconds_ago<60: upd_tag=f'<span class="is-tag">↺ hace {seconds_ago}s</span>'
    else: upd_tag=f'<span class="is-tag wrn">↺ hace {seconds_ago//60}m</span>'
else: upd_tag='<span class="is-tag">Sin datos</span>'

st.markdown(
    f'<div class="is-header">'
    f'<div class="is-header-left"><div class="brand">Improve Sankey</div>'
    f'<div class="sub">Energy Monitoring System · Industrial · v3.0</div></div>'
    f'<div class="is-header-right">'
    f'<span class="is-tag ok"><span class="is-led"></span>Online</span>'
    f'{alarm_tag}{upd_tag}'
    f'<span class="is-tag">{client_name}</span>'
    f'<span class="is-tag">{now_local.strftime("%Y-%m-%d")}</span>'
    f'<span class="is-tag">{now_local.strftime("%H:%M:%S")}</span>'
    f'<span class="is-tag">{rng}</span>'
    f'</div></div>',unsafe_allow_html=True)

# Init new DB schemas — wrapped in cache_resource so solo corren una vez por proceso
@st.cache_resource
def _init_extra_schemas():
    ensure_alarm_history_schema(conn)
    ensure_annotations_schema(conn)
    ensure_energy_schema(conn)
    # Índice de expresión para acelerar agregaciones temporales (GROUP BY epoch)
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_meas_client_epoch ON measurements(client_id, CAST(strftime('%s',ts) AS INTEGER))")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_states_client_epoch ON states(client_id, CAST(strftime('%s',ts) AS INTEGER))")
        conn.commit()
    except Exception as _ei:
        _log.debug("No se pudo crear índice de epoch: %s", _ei)
_init_extra_schemas()

# ============================================================
# TABS
# ============================================================
tabs = st.tabs([
    "Resumen",
    "Monitorizacion",
    "Calidad Electrica",
    "Estado del Sistema",
    "APF & SVG",
    "Historico",
])

window_seconds = span_sec

# ────────────────────────────────────────────────────────────
# TAB 0 — RESUMEN
# KPIs instantáneos + alarmas + energía + exportar
# ────────────────────────────────────────────────────────────
with tabs[0]:
    section("Valores Actuales")
    render_kpi_strip(df)

    render_alarm_panel(df)

    section("Estadísticas del Rango Seleccionado")
    render_stats_panel(df)

    section("Energía Consumida en el Rango")
    card_open()
    render_kwh_chart(df)
    card_close()

    section("Exportar Informe")
    # Selectores de fecha/hora para el rango de exportación
    _ec1, _ec2 = st.columns(2, gap="small")
    with _ec1:
        _exp_d_from = st.date_input("Desde", value=dt_from.date() if hasattr(dt_from,"date") else datetime.now().date(), key="exp_from_day")
        _exp_t_from = st.time_input("Hora desde", value=dt_from.time() if hasattr(dt_from,"time") else datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).time(), key="exp_from_time")
    with _ec2:
        _exp_d_to = st.date_input("Hasta", value=dt_to.date() if hasattr(dt_to,"date") else datetime.now().date(), key="exp_to_day")
        _exp_t_to = st.time_input("Hora hasta", value=dt_to.time() if hasattr(dt_to,"time") else datetime.now().replace(hour=23,minute=59,second=0,microsecond=0).time(), key="exp_to_time")
    _exp_from = datetime.combine(_exp_d_from, _exp_t_from)
    _exp_to   = datetime.combine(_exp_d_to,   _exp_t_to)
    if LOCAL_TZ:
        _exp_from = _exp_from.replace(tzinfo=LOCAL_TZ)
        _exp_to   = _exp_to.replace(tzinfo=LOCAL_TZ)

    if _exp_to < _exp_from:
        st.warning("El rango 'Hasta' debe ser posterior a 'Desde'.")
    col_xl, col_pdf = st.columns(2, gap="medium")
    with col_xl:
        if st.button("Generar Excel", use_container_width=True):
            st.session_state["_export_xls_pending"] = (_exp_from, _exp_to)
            st.session_state.pop("_export_xls", None)
    with col_pdf:
        if st.button("Generar PDF", use_container_width=True):
            st.session_state["_export_pdf_pending"] = (_exp_from, _exp_to)
            st.session_state.pop("_export_pdf", None)
            st.session_state.pop("_export_pdf_err", None)

    if st.session_state.get("_export_xls"):
        st.success("Excel listo.")
        st.download_button("⬇️ Descargar Excel",
            st.session_state["_export_xls"],
            f"Informe_{st.session_state.get('client_name','cliente')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_xls_main", use_container_width=True)
    if st.session_state.get("_export_pdf_err"):
        st.error(st.session_state["_export_pdf_err"])
    if st.session_state.get("_export_pdf"):
        _pdf_bytes, _pdf_name = st.session_state["_export_pdf"]
        st.success("PDF listo.")
        st.download_button("⬇️ Descargar PDF",
            _pdf_bytes, _pdf_name, "application/pdf",
            key="dl_pdf_main", use_container_width=True)


# ────────────────────────────────────────────────────────────
# TAB 1 — MONITORIZACIÓN
# Gráficas en tiempo real de todas las señales eléctricas
# ────────────────────────────────────────────────────────────
with tabs[1]:
    if df is None or df.empty:
        st.warning("No hay datos para el rango seleccionado.")
    else:
        section("Tensiones")
        card_open()
        render_chart_with_values(df,
            [c for c in ["V_L1N","V_L2N","V_L3N"] if c in df.columns], "V",
            [_color_sig(c) for c in ["V_L1N","V_L2N","V_L3N"]],
            "Tensión Fase-Neutro (V)", x_window_seconds=window_seconds)
        card_close()

        card_open()
        render_chart_with_values(df,
            [c for c in ["V_L1L2","V_L2L3","V_L3L1"] if c in df.columns], "V",
            None, "Tensión Fase-Fase (V)", x_window_seconds=window_seconds)
        card_close()

        section("Corrientes")
        card_open()
        render_chart_with_values(df,
            [c for c in ["I_L1","I_L2","I_L3","I_N"] if c in df.columns], "A",
            [_color_sig(c) for c in ["I_L1","I_L2","I_L3","I_N"]],
            "Corrientes por Fase (A)", x_window_seconds=window_seconds)
        card_close()

        section("Potencias")
        cols_p = [c for c in ["P_kW","Q_kVAr","S_kVA"] if c in df.columns]
        if cols_p:
            card_open()
            render_chart_with_values(df, cols_p, "",
                [IS_GREEN, IS_AMBER, IS_CYAN],
                "Potencia Activa / Reactiva / Aparente",
                x_window_seconds=window_seconds)
            card_close()

        section("Factor de Potencia y Frecuencia")
        col_pf, col_fr = st.columns(2, gap="medium")
        with col_pf:
            if "PF" in df.columns:
                card_open()
                render_chart_with_values(df, ["PF"], "", [IS_GREEN],
                    "Factor de Potencia", x_window_seconds=window_seconds,
                    ref_line=0.9)
                card_close()
        with col_fr:
            if "Freq_Hz" in df.columns:
                card_open()
                render_chart_with_values(df, ["Freq_Hz"], "Hz", [IS_CYAN],
                    "Frecuencia (Hz)", x_window_seconds=window_seconds,
                    ref_line=50.5)
                card_close()


# ────────────────────────────────────────────────────────────
# TAB 2 — CALIDAD ELÉCTRICA
# THD, armónicos, fasorial, desequilibrio, norma EN 50160
# ────────────────────────────────────────────────────────────
with tabs[2]:
    if df is None or df.empty:
        st.warning("Sin datos para el rango seleccionado.")
    else:
        section("Distorsión Armónica Total (THD)")
        col_tv, col_ti = st.columns(2, gap="medium")
        with col_tv:
            card_open()
            cols_thdv = [c for c in ["THD_V_L1","THD_V_L2","THD_V_L3"] if c in df.columns]
            if cols_thdv:
                render_chart_with_values(df, cols_thdv, "%",
                    [PHASE_COLORS["L1"], PHASE_COLORS["L2"], PHASE_COLORS["L3"]],
                    "THD Tensión (%)", x_window_seconds=window_seconds,
                    ref_line=EN50160["THD_V_limit"])
            else:
                st.info("Sin datos de THD de tensión.")
            card_close()
        with col_ti:
            card_open()
            cols_thdi = [c for c in ["THD_I_L1","THD_I_L2","THD_I_L3"] if c in df.columns]
            if cols_thdi:
                render_chart_with_values(df, cols_thdi, "%",
                    [PHASE_COLORS["L1"], PHASE_COLORS["L2"], PHASE_COLORS["L3"]],
                    "THD Corriente (%)", x_window_seconds=window_seconds)
            else:
                st.info("Sin datos de THD de corriente.")
            card_close()

        section("Espectro de Armónicos")
        col_bi, col_bv = st.columns(2, gap="medium")
        with col_bi:
            card_open()
            render_harmonic_bar(df, "I", "Armónicos de Corriente por Orden (%)")
            card_close()
        with col_bv:
            card_open()
            render_harmonic_bar(df, "V", "Armónicos de Tensión por Orden (%)")
            card_close()

        section("Diagrama Fasorial y Desequilibrio entre Fases")
        col_fas, col_rad = st.columns(2, gap="medium")
        with col_fas:
            card_open()
            render_phasor(df)
            card_close()
        with col_rad:
            card_open()
            render_radar_imbalance(df)
            card_close()

        render_en50160(df)

        section("Triángulo de Potencias")
        card_open()
        render_power_triangle(df)
        card_close()


# ────────────────────────────────────────────────────────────
# TAB 3 — ESTADO DEL SISTEMA
# Temperaturas, fusibles, estados, APF & SVG
# ────────────────────────────────────────────────────────────
with tabs[3]:
    cid = _get_cid()

    section("Temperaturas del Equipo")
    _papelera = (cid == 12)
    temp_tags = ["T_Nucleo"] if _papelera else ["T_Nucleo","T_Tiristor_R","T_Tiristor_S","T_Tiristor_T"]
    if df is not None and not df.empty and any(t in df.columns for t in temp_tags):
        _avail = [t for t in temp_tags if t in df.columns]
        df_temp = df[["ts"]+_avail].copy().rename(columns={
            "T_Nucleo":"CORE", "T_Tiristor_R":"R",
            "T_Tiristor_S":"S",  "T_Tiristor_T":"T"})
        _tcols  = [c for c in ["CORE","R","S","T"] if c in df_temp.columns]
        _tcolors = [IS_GREEN, PHASE_COLORS["L1"], PHASE_COLORS["L2"], PHASE_COLORS["L3"]][:len(_tcols)]
        card_open()
        line_hud(df_temp, _tcols, "°C", colors=_tcolors, title_text="Temperaturas internas (°C)")
        card_close()

        def _lv(df_, col):
            s = pd.to_numeric(df_[col], errors="coerce").dropna() if col in df_.columns else pd.Series()
            return float(s.iloc[-1]) if not s.empty else None

        if _papelera:
            gauge_semicircle("Núcleo", _lv(df_temp,"CORE") or 0.0, 0, 45, 80, "°C", key=f"g_core_{cid}")
        else:
            c1,c2,c3,c4 = st.columns(4)
            for ctx,col,label,gkey,warn in [
                (c1,"CORE","Núcleo",    f"g_core_{cid}", 45),
                (c2,"R",   "Tiristor R",f"g_r_{cid}",   55),
                (c3,"S",   "Tiristor S",f"g_s_{cid}",   55),
                (c4,"T",   "Tiristor T",f"g_t_{cid}",   55),
            ]:
                with ctx:
                    gauge_semicircle(label, _lv(df_temp,col) or 0.0, 0, warn, 80, "°C", key=gkey)
    else:
        st.info("Sin datos de temperatura en el rango seleccionado.")

    section("Estados del Sistema")
    if states_proc.empty:
        st.warning("Sin datos de estados disponibles.")
    else:
        col_left, col_right = st.columns(2, gap="large")
        left_cols  = [b+"_OK" for b in ["EstadoIEQ","Seta","Fallo_red"]
                      if b+"_OK" in states_proc.columns]
        right_cols = [b+"_OK" for b in ["TestigoR","TestigoS","TestigoT"]
                      if b+"_OK" in states_proc.columns]
        with col_left:
            if left_cols:
                card_open()
                onoff_timeline(states_proc, left_cols,
                    "Estado General / Seta / Fallo de Red", 240, key=f"tl_left_{cid}")
                card_close()
        with col_right:
            if right_cols:
                card_open()
                onoff_timeline(states_proc, right_cols,
                    "Fusibles (R / S / T)", 240, key=f"tl_right_{cid}")
                card_close()


# ────────────────────────────────────────────────────────────
# TAB 4 — APF & SVG
# ────────────────────────────────────────────────────────────
with tabs[4]:
    cid = _get_cid()

    if states_proc.empty:
        st.warning("Sin datos de estados disponibles.")
    else:
        section("Modo Auto / Manual")
        if "Auto_Manual" in states_proc.columns:
            states_proc["Auto_Manual"] = (
                pd.to_numeric(states_proc["Auto_Manual"], errors="coerce")
                .fillna(0).astype(int))
            card_open()
            onoff_timeline(states_proc, ["Auto_Manual"],
                "Modo Auto / Manual", 120, key=f"apf_am_{cid}")
            card_close()

        section("Reset de Modulos")
        rst_cols = [c for c in [f"M{i}_Reset" for i in range(1,7)]
                    if c in states_proc.columns]
        if rst_cols:
            for c in rst_cols:
                states_proc[c] = pd.to_numeric(states_proc[c], errors="coerce").fillna(0).astype(int)
            card_open()
            onoff_timeline(states_proc, rst_cols, "Reset de Modulos", 220, key=f"apf_rst_{cid}")
            card_close()
        else:
            st.info("Sin datos de reset de modulos.")

        section("Arranque y Parada de Modulos")
        run_cols = [c for c in [f"M{i}_RunStop" for i in range(1,7)]
                    if c in states_proc.columns]
        if run_cols:
            for c in run_cols:
                states_proc[c] = pd.to_numeric(states_proc[c], errors="coerce").fillna(0).astype(int)
            card_open()
            onoff_timeline(states_proc, run_cols, "Arranque / Parada", 220, key=f"apf_run_{cid}")
            card_close()
        else:
            st.info("Sin datos de arranque/parada.")


# ────────────────────────────────────────────────────────────
# TAB 5 — HISTÓRICO
# Alarmas pasadas, anotaciones, log de eventos, resumen diario
# ────────────────────────────────────────────────────────────
with tabs[5]:
    section("Resumen Diario")
    card_open()
    render_daily_summary_chart(conn)
    card_close()

    section("Historial de Alarmas")
    card_open()
    render_alarm_history(conn)
    card_close()

    section("Anotaciones del Operario")
    card_open()
    render_annotations(conn, df)
    card_close()

    section("Log de Cambios de Estado")
    card_open()
    render_event_log(states_proc)
    card_close()