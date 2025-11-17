from pathlib import Path
import streamlit as st
import os, sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import re
import plotly.graph_objects as go
    

ATS_LIGHTS_CSS = """
<style>
.ats-wrap{display:flex;flex-direction:column;gap:14px;margin:6px 0 18px;}
.ats-row{display:grid;grid-template-columns:86px 28px 1fr;align-items:center;gap:14px}
.ats-label{color:#A9FF9F;font-weight:700;letter-spacing:.3px;}
.led{
width:22px;height:22px;border-radius:50%;
box-shadow:0 0 10px rgba(0,0,0,.6) inset, 0 0 16px rgba(0,0,0,.25);
border:1px solid #0b0f0f;
}
.led.on{ background: radial-gradient(circle at 30% 30%, #9cffb5, #39FF88 70%); box-shadow:0 0 10px rgba(57,255,136,.9); }
.led.off{ background: radial-gradient(circle at 30% 30%, #ff9a9a, #FF4D5A 70%); box-shadow:0 0 10px rgba(255,77,90,.9); }

.ats-bar{
height:16px;border-radius:10px;position:relative;overflow:hidden;
background:linear-gradient(90deg,rgba(255,255,255,.06),rgba(255,255,255,.06));
border:1px solid #1c2426;
}
.ats-bar .fill.on{
position:absolute;inset:0;
background:linear-gradient(90deg, #39FF88, #27d96f 70%);
box-shadow:0 0 18px rgba(57,255,136,.25);
}
.ats-bar .fill.off{
position:absolute;inset:0;
background:linear-gradient(90deg, #FF4D5A, #d93b47 70%);
box-shadow:0 0 18px rgba(255,77,90,.2);
}

/* rayita decorativa */
.ats-bar::after{
content:""; position:absolute; left:0; top:0; height:100%; width:100%;
background:linear-gradient(180deg, rgba(255,255,255,.12), rgba(255,255,255,0));
mix-blend-mode:overlay; opacity:.25;
}
</style>
"""
st.markdown(ATS_LIGHTS_CSS, unsafe_allow_html=True)


# === CSS efecto futurista para gauges Improve Sankey ===
st.markdown("""
<style>
    /* --- Contenedor del gauge --- */
    .is-gauge-neon {
    position: relative;
    overflow: visible !important;
    isolation: isolate;
    z-index: 0;
    margin: 4px 2px 10px 2px;
    }

    /* --- Halo futurista DETRÁS del gauge --- */
    .is-gauge-neon::before {
    content: "";
    position: absolute;
    left: -12px;
    right: -12px;
    top: 45%;
    bottom: -10px;
    border-radius: 40px;
    background: radial-gradient(circle at 50% 100%,
    rgba(57,255,136,0.3) 0%,
    rgba(57,255,136,0.15) 30%,
    rgba(0,0,0,0) 80%);
    filter: blur(12px);
    opacity: 0.50;
    z-index: -1; /* <-- detrás del gauge */
    animation: halo-breathe 3s ease-in-out infinite;
    }

    /* --- Animación del halo --- */
    @keyframes halo-breathe {
    0% { opacity: .55; transform: scale(0.98); }
    50% { opacity: .95; transform: scale(1.02); }
    100% { opacity: .55; transform: scale(0.98); }
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <style>
    .is-gauge-neon{
    position:relative; isolation:isolate; z-index:0; overflow:visible !important;
    margin: 6px 2px 14px 2px;
    }
    .is-gauge-neon::before{
    content:"";
    position:absolute; left:-18px; right:-60px; top:50%; bottom:-55px;
    border-radius:100px;
    background:
    radial-gradient(60% 80% at 50% 100%, rgba(57,255,136,0.45) 0%, rgba(57,255,136,0.22) 45%, rgba(0,0,0,0) 80%),
    radial-gradient(40% 70% at 50% 100%, rgba(0,229,255,0.25) 0%, rgba(0,0,0,0) 70%);
    filter: blur(10px);
    opacity: 1; /* <-- más visible */
    z-index: -1;
    animation: halo-breathe 2.8s ease-in-out infinite;
    }
    .is-gauge-neon::after{
    content:"";
    position:absolute; left:-8px; right:-8px; top:55%; bottom:-0px;
    border-radius:40px;
    box-shadow: 0 0 22px rgba(57,255,136,0.45), 0 0 42px rgba(57,255,136,0.25);
    z-index:-1;
    pointer-events:none;
    }
    @keyframes halo-breathe{
    0% { opacity:.75; transform:translateY(0) scale(0.985); }
    50% { opacity:1; transform:translateY(-2px) scale(1.015); }
    100% { opacity:.75; transform:translateY(0) scale(0.985); }
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
/* Tarjetas HUD con brillo sutil */
.hud-card{background:rgba(0,0,0,0.15);border:1px solid rgba(127,255,163,0.15);
border-radius:14px;padding:10px 12px;margin:10px 0;
box-shadow:0 0 20px rgba(0,255,120,0.06) inset}
.hud-title{color:#9bffb4;font-weight:700;letter-spacing:.3px;margin:6px 0 4px}
</style>
""", unsafe_allow_html=True)


# ========= RUN/STOP TIMELINE para APF / SVG =========
import pandas as pd
import plotly.express as px

import streamlit as st
import plotly.express as px

# ========= UI helpers (chips, tarjetas, plot y timeline) =========

def neon_title(text: str, variant: str = ""):
    # variant: "", "apf-blue", "apf-red"
    st.markdown(
        f"""
        <div class="apf-sec {variant}">
        <div class="apf-title">{text}</div>
        <div class="apf-underline"></div>
        </div>
        """,
        unsafe_allow_html=True
    )



def _flag_bool(v):
    """Normaliza a True/False a partir de 1/0, bool, 'ON'/'OFF', etc."""
    try:
        if isinstance(v, str):
            s = v.strip().upper()
            if s in ("ON","RUN","TRUE","ENCENDIDO","1"): return True
            if s in ("OFF","STOP","FALSE","APAGADO","0"): return False
        return bool(int(v))
    except Exception:
        return False

def ats_status_from_df(df: pd.DataFrame, aliases: list[str]) -> bool | None:
    """Devuelve el último valor de la primera columna que exista en df según alias."""
    for c in aliases:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            v = s.iloc[-1] if len(s) else None
            return _flag_bool(v) if v is not None else None
    return None

def render_ats_lights(df: pd.DataFrame | None = None):
    """
    Dibuja los 3 ATS como 'luz + barra' (verde=ON, rojo=OFF).
    Si no hay columnas reales, usa toggles de simulación en la sidebar.
    """
    _df = df if (isinstance(df, pd.DataFrame) and not df.empty) else pd.DataFrame()

    a1 = ats_status_from_df(_df, ["ATS1","ATS_1","A1","ATS_SUP","ATS_TOP"])
    a2 = ats_status_from_df(_df, ["ATS2","ATS_2","A2","ATS_MID","ATS_MEDIO"])
    a3 = ats_status_from_df(_df, ["ATS3","ATS_3","A3","ATS_BOT","ATS_ABAJO"])


    # Si no hay datos reales, usa toggles (persisten en sesión)
    if a1 is None:
        st.session_state.setdefault("sim_ats1", True)
        a1 = st.session_state["sim_ats1"]
    if a2 is None:
        st.session_state.setdefault("sim_ats2", False)
        a2 = st.session_state["sim_ats2"]
    if a3 is None:
        st.session_state.setdefault("sim_ats3", True)
        a3 = st.session_state["sim_ats3"]

    html = f"""
    <div class="ats-wrap">
    <div class="ats-row">
    <div class="ats-label">ATS 1</div>
    <div class="led {'on' if a1 else 'off'}"></div>
    <div class="ats-bar"><div class="fill {'on' if a1 else 'off'}"></div></div>
    </div>
    <div class="ats-row">
    <div class="ats-label">ATS 2</div>
    <div class="led {'on' if a2 else 'off'}"></div>
    <div class="ats-bar"><div class="fill {'on' if a2 else 'off'}"></div></div>
    </div>
    <div class="ats-row">
    <div class="ats-label">ATS 3</div>
    <div class="led {'on' if a3 else 'off'}"></div>
    <div class="ats-bar"><div class="fill {'on' if a3 else 'off'}"></div></div>
    </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# ================== SIDEBAR HUD GENERAL ======================



# ---------- ON/OFF timeline estilo "segmentos" (tipo Grafana) ----------
def _build_onoff_segments(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Convierte series binarias por columna en intervalos Start/Finish con etiqueta On/Off."""
    out = []
    if df is None or df.empty or "ts" not in df.columns:
        return pd.DataFrame(out)

    d = df.copy()
    d["ts"] = pd.to_datetime(d["ts"], errors="coerce")
    d = d.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)

    for c in cols:
        if c not in d.columns:
            continue
        s = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int)
        ts = d["ts"]
        if s.empty:
            continue

        last_val = s.iloc[0]
        last_t = ts.iloc[0]

        for k in range(1, len(s)):
            if s.iloc[k] != last_val:
                out.append({
                    "Signal": c,
                    "Start": last_t,
                    "Finish": ts.iloc[k],
                    "State": "On" if last_val == 1 else "Off"
                })
                last_val = s.iloc[k]
                last_t = ts.iloc[k]

        # cierra el último tramo hasta el final
        out.append({
            "Signal": c,
            "Start": last_t,
            "Finish": ts.iloc[-1],
            "State": "On" if last_val == 1 else "Off"
        })
    return pd.DataFrame(out)


def onoff_timeline(df: pd.DataFrame, cols: list[str], title: str,
    height: int = 170, key: str | None = None):
    seg = _build_onoff_segments(df, cols)
    if seg.empty:
        st.info(f"No hay datos para “{title}”.")
        return

    # Colores Improve Sankey
    colmap = {"On": "#026D2D", "Off": "#64010B"} # verde y rojo oscuro
    fig = px.timeline(
        seg, x_start="Start", x_end="Finish", y="Signal",
        color="State", color_discrete_map=colmap,
        template="plotly_dark"
    )

    fig.update_traces(
        marker=dict(line=dict(width=1)),
        width=0.3
    )


    # Texto centrado dentro de cada tramo
    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        marker_line_width=0,
        opacity=0.96,
        hovertemplate="<b>%{y}</b><br>%{x|%H:%M:%S} → %{x_end|%H:%M:%S}<br>%{text}<extra></extra>",
    )
    
    fig.update_layout(
        title=dict(text=f"<b style='color:{IS_TEXT};font-size:12px;text-shadow:0 0 6px #00FF88AA'>{title}</b>", x=0.01, y=0.98),
        height=height,
        paper_bgcolor=IS_PANEL,
        plot_bgcolor=IS_PANEL,
        margin=dict(l=10, r=10, t=28, b=18),
        showlegend=False,
    )

    # Fila superior arriba (como Grafana)
    fig.update_yaxes(
        autorange="reversed",
        color="#8ea39a",
        showgrid=False,
        zeroline=False,
        title_text="", # 🔥 Esto quita "Signal"
    )

    # Grid vertical sutil como en tu HUD
    fig.update_xaxes(
        title_text="Tiempo", color="#035f14",
        showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False
    )

    fig.update_traces(
        marker=dict(line=dict(width=1)),
        width=0.3
    )

    st.plotly_chart(fig, use_container_width=True, key=key)
    # ----------------------------------------------------------------------

import plotly.graph_objects as go
from datetime import datetime

# ---------- helper: convierte columnas binarias en segmentos (start, finish, label, text/color) ----------
def _segments_from_binary(df, col, on_text, off_text, on_color, off_color, y_label):
    ts = df["ts"]
    v = df[col].astype(int).values
    segs = []
    if len(v) == 0:
        return segs
    last = v[0]
    t0 = ts.iloc[0]
    for i in range(1, len(v)):
        if v[i] != last:
            segs.append({
                "y": y_label,
                "start": t0,
                "finish": ts.iloc[i],
                "text": on_text if last==1 else off_text,
                "color": on_color if last==1 else off_color
            })
            t0 = ts.iloc[i]
            last = v[i]
    # cierre
    segs.append({
        "y": y_label,
        "start": t0,
        "finish": ts.iloc[-1],
        "text": on_text if last==1 else off_text,
        "color": on_color if last==1 else off_color
    })
    return segs

def _timeline_figure(segs, height=220, title=""):
    fig = go.Figure()
    for s in segs:
        fig.add_trace(go.Bar(
            x=[(s["finish"]-s["start"]).total_seconds()/3600.0], # horas como ancho
            y=[s["y"]],
            base=s["start"],
            orientation="h",
            text=s["text"],
            textposition="inside",
            insidetextanchor="middle",
            textfont=dict(size=14, color="rgba(10,10,10,0.95)"),
            hovertemplate="%{y}<br>%{base} → %{x}h<br>%{text}<extra></extra>",
            marker=dict(
                color=s["color"],
                line=dict(color="rgba(0,0,0,0.25)", width=1)
            )
        ))
    fig.update_layout(
        barmode="stack",
        bargap=0.35, # grosor uniforme y fino
        bargroupgap=0.0,
        height=height,
        title=dict(text=title, font=dict(size=16, color="#9bffb4")),
        paper_bgcolor=IS_PANEL, plot_bgcolor=IS_PANEL, # usa tu color de panel
        margin=dict(l=90, r=20, t=35, b=45),
        xaxis=dict(
            title="Tiempo",
            showgrid=True, gridcolor="rgba(255,255,255,0.07)",
            zeroline=False, showline=False,
            tickformat="%H:%M"
        ),
        yaxis=dict(
            title="",
            showgrid=False, zeroline=False, showline=False,
            categoryorder="array",
            categoryarray=sorted(list({s['y'] for s in segs})) # respeta orden alfabético; puedes personalizar
        ),
        font=dict(color="#cfead9"),
    )
    return fig
    
# ---------- 1) Banda Auto/Manual (1 fila) ----------

def band_auto_manual(df: pd.DataFrame, col: str, title="Auto / Manual", height=70, key="apf_auto"):
    segs = _segments_from_binary(
        df, col,
        on_text="Auto", off_text="Manual",
        on_color="#9bd6a2", # verde suave
        off_color="#d08a00", # ámbar manual
        y_label="Device State"
    )
    fig = _timeline_figure(segs, height=height, title=title)
    st.plotly_chart(fig, use_container_width=True, key=key)

# ---------- 2) Banda múltiple Device Reset (varias filas) ----------
def band_device_reset(df: pd.DataFrame, cols: list[str], title="Device Reset", height=180, key="apf_reset"):
    all_segs = []
    for c in cols:
        label = c.replace("RST", "Device reset ")
        all_segs += _segments_from_binary(
            df, c,
            on_text="Yes", off_text="No",
            on_color="#3b82f6", # azul vivo (Yes)
            off_color="#243b7b", # azul oscuro (No)
            y_label=label
        )
    fig = _timeline_figure(all_segs, height=height, title=title)
    st.plotly_chart(fig, use_container_width=True, key=key)

# ---------- 3) Run / Stop (varias filas, texto dentro del bloque) ----------
def band_run_stop(df: pd.DataFrame, cols: list[str], title="Run / Stop", height=220, key="apf_runstop"):
    all_segs = []
    for c in cols:
        label = c.replace("DEV", "Device ")
        all_segs += _segments_from_binary(
            df, c,
            on_text="Run", off_text="Stop",
            on_color="#7cc88f", # verde HUD
            off_color="#c94149", # rojo HUD
            y_label=label
        )
    fig = _timeline_figure(all_segs, height=height, title=title)
    st.plotly_chart(fig, use_container_width=True, key=key)

# === COLORES HUD (por si no están ya definidos) ===
IS_PANEL = "#b4bac4" # Fondo general del panel
IS_TEXT = "#E0E0E0" # Texto claro
IS_GREEN = "#00FF9D" # Verde energía
IS_AMBER = "#F5B200" # Ámbar de aviso
IS_RED = "#FF4D4D" # Rojo alerta
IS_CYAN = "#00FFFF" # Cian de progreso
IS_STROKE = "#1f2a2e" # Borde oscuro

def _resolve_cols(df, desired_names):
    # Devuelve solo los que existan (case-insensitive)
    up = {c.upper(): c for c in df.columns}
    out, missing = [], []
    for name in desired_names:
        real = up.get(name.upper())
        if real:
            out.append(real)
        else:
            missing.append(name)
    return out, missing

def _chip(texto:str, ok:bool=True):
    color = "ok" if ok else "warn"
    st.markdown(f'<span class="badge {color}">{texto}</span>', unsafe_allow_html=True)

def _last_num(df, col, default=None):
    """Devuelve el último valor numérico válido de una columna."""
    try:
        if col in df.columns and not df.empty:
            val = pd.to_numeric(df[col].iloc[-1], errors="coerce")
            if pd.notna(val):
                return float(val)
    except Exception:
        pass
    return default

def _last_change_ts(df, col):
    if col not in df.columns or df[col].dropna().empty:
        return "–"
    s = pd.to_numeric(df[col], errors="coerce").fillna(method="ffill")
    idx = (s.diff().fillna(0) != 0)
    if not idx.any():
        return "–"
    pos = idx[idx].index[-1]
    try:
        return pd.to_datetime(df.loc[pos, "ts"]).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "–"
    




CARD_CSS = """
<style>
.section {margin:12px 0 8px;}
.card {background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08);
        border-radius:14px; padding:14px 16px; margin:10px 0;}
.grid {display:grid; gap:12px;}
.grid.cols2{grid-template-columns:1fr 1fr;}
.grid.cols3{grid-template-columns:1fr 1fr 1fr;}
.badge{display:inline-block; padding:.35rem .9rem; border-radius:999px; font-weight:600; color:#fff;}
.badge.ok{background:#00C853;} .badge.off{background:#C62828;} .badge.warn{background:#FF8F00;}
.subtle{opacity:.75; font-size:.9rem; margin-top:4px}
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

def chip(text:str, kind:str="ok"):
    kinds = {"ok":"ok","off":"off","warn":"warn"}
    k = kinds.get(kind,"ok")
    st.markdown(f'<span class="badge {k}">{text}</span>', unsafe_allow_html=True)

def section(title:str):
    st.markdown(f'<div class="section"><h3>{title}</h3></div>', unsafe_allow_html=True)

def card_start(title:str=None, descr:str=None):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if title: st.markdown(f"**{title}**")
    if descr: st.markdown(f'<div class="subtle">{descr}</div>', unsafe_allow_html=True)

def card_end():
    st.markdown("</div>", unsafe_allow_html=True)

def last_of(df, col, default=None):
    try:
        return None if df.empty or col not in df.columns else df[col].iloc[-1]
    except Exception:
        return default

def plot_lines(df, cols, title, key=None):
    cols_ok = [c for c in cols if c in df.columns]
    if not cols_ok:
        st.info(f"No hay columnas disponibles para **{title}** ({', '.join(cols)}).")
        return
    dfx = df[["ts"]+cols_ok].copy()
    dfx["ts"] = pd.to_datetime(dfx["ts"], errors="coerce")
    dfx = dfx.dropna(subset=["ts"]).sort_values("ts")
    fig = px.line(dfx, x="ts", y=cols_ok, template="plotly_dark",
                    labels={"ts":"Tiempo","value":"Valor","variable":"Señal"}, title=title)
    st.plotly_chart(fig, use_container_width=True, key=key)

def runstop_timeline(conn, col: str, title: str, key: str = None):
    """
    Dibuja timeline ON/OFF leyendo de la tabla 'states' (col en ['maquina','apf','svg',...]).
    Representa 1=ON, 0=OFF con trazo escalonado.
    """
    try:
        d = pd.read_sql("SELECT ts, {c} AS val FROM states ORDER BY ts ASC".format(c=col), conn)
    except Exception as e:
        st.info("Sin datos de estados. ({})".format(e))
        return

    if d.empty:
        st.info("Sin datos de estados.")
        return

    # Normaliza tipos y orden
    d["ts"] = pd.to_datetime(d["ts"], errors="coerce")
    d = d.dropna(subset=["ts"]).sort_values("ts")
    # Asegura 0/1
    d["val"] = d["val"].fillna(0).astype(int).clip(0, 1)

    # Línea escalonada con Plotly Express
    fig = px.line(
        d, x="ts", y="val",
        template="plotly_dark",
        title=title,
        line_shape="hv" # <- este es el truco para el “step”
    )

    # Etiquetas 0/1 -> OFF/ON, y algo de estética
    fig.update_yaxes(
        tickmode="array",
        tickvals=[0, 1],
        ticktext=["OFF", "ON"],
        range=[-0.2, 1.2]
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=height)

    st.plotly_chart(fig, use_container_width=True, key=key)

st.set_page_config(layout="wide")

UI_CSS = """
<style>
/* Layout general */
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
html, body { background-color: #0f1216 !important; }

/* Titulares */
h1, h2, h3 { color: #A9FF9F; letter-spacing:.3px; }

/* Tarjetas (cards) */
.card {
background: linear-gradient(180deg,#1a1f26 0%,#14181f 100%);
border: 1px solid #27303b; border-radius: 14px;
padding: 14px 16px; margin: 10px 0 16px;
box-shadow: 0 3px 10px rgba(0,0,0,.25);
}
.card h3 { margin: 0 0 8px; color: #e6edf3; }

/* Widget ATS */
.ats-panel { display:flex; flex-direction: column; gap: 12px; }
.ats-vert { display:flex; flex-direction: column; gap:8px; align-items:flex-start; }
.ats {
display:flex; align-items:center; gap:8px;
background:#161b22; border:1px solid #2b3542; border-radius:12px;
padding:10px 12px;
}
.led { width:12px; height:12px; border-radius:50%; border:1px solid #111; box-shadow:0 0 8px rgba(0,0,0,.5) inset; }
.led.g { background:#2ecc71; border-color:#1b8f53; }
.led.r { background:#e74c3c; border-color:#9e2b20; }
.ats label { color:#cfd8e3; font-size:.9rem; opacity:.9; }

/* Badges ON/OFF */
.badges { display:flex; gap:.5rem; flex-wrap:wrap; }
.badge { padding:.35rem .9rem; border-radius:999px; color:#fff; font-weight:600; border:1px solid transparent; }
.badge.on { background:#00c853; border-color:#198754; }
.badge.off { background:#c62828; border-color:#7f1d1d; }

/* Métricas (st.metric) */
[data-testid="stMetric"]{
background:#12161c; border:1px solid #263040;
border-radius:12px; padding:10px 12px;
}
[data-testid="stMetricValue"] { font-size:1.6rem; font-weight:800; color:#e6edf3; }
[data-testid="stMetricLabel"] { color:#9fb3c8; font-weight:600; }

/* Plotly */
.js-plotly-plot .plotly, .js-plotly-plot .main-svg { background: transparent !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"]{ gap:.25rem; }
.stTabs [data-baseweb="tab"]{
background:#12161a; border:1px solid #2a3340; border-radius:10px;
padding:10px 14px; color:#c7d0dc;
}
.stTabs [data-baseweb="tab"][aria-selected="true"]{
background:#1b2330; border-color:#3c485a; color:#a9ff9f;
}

/* Sidebar */
[data-testid="stSidebar"]{ background:#0d1117; }
[data-testid="stSidebar"] .block-container{ padding-top:.5rem; }
</style>
"""
st.markdown(UI_CSS, unsafe_allow_html=True)

# Tema oscuro de Plotly por defecto
px.defaults.template = "plotly_dark"



# ---- Helpers de UI para tarjetas/secciones ----
# ==== HUD THEME / HELPERS =====================================================

import uuid

def _last_bool_series(df: pd.DataFrame, col: str) -> tuple[bool, str]:
    """Devuelve (estado_actual, ts_ultimo_cambio_formateado) para una señal binaria."""
    if col not in df.columns or df.empty:
        return False, "–"
    s = pd.to_numeric(df[col], errors="coerce").fillna(method="ffill").fillna(0).astype(int)
    # último cambio:
    diff = s.diff().fillna(0) != 0
    if diff.any():
        pos = diff[diff].index[-1]
        try:
            ts = pd.to_datetime(df.loc[pos, "ts"]).strftime("%H:%M:%S")
        except Exception:
            ts = "–"
    else:
        ts = "–"
    return bool(s.iloc[-1]), ts

def status_led_row(df: pd.DataFrame, signals: list[str], title: str, key: str):
    """Fila de LEDs HUD: estado actual + último cambio."""
    st.markdown(f"<div class='hud-title'><span class='dot'></span> {title}</div>", unsafe_allow_html=True)
    html = ["<div class='is-led-row'>"]
    for sig in signals:
        on, ts = _last_bool_series(df, sig)
        html.append(
            f"<div class='is-led'><span class='is-dot {'is-on' if on else 'is-off'}'></span>"
            f"<b>{sig}</b><span class='is-ts'>• last: {ts}</span></div>"
        )
        html.append("</div>")
        st.markdown("".join(html), unsafe_allow_html=True)


from typing import List, Optional

def pick_col(df: pd.DataFrame, candidates: List[str], default: Optional[str] = None) -> Optional[str]:
    """Devuelve el primer nombre de columna que exista; si no, default."""
    for c in candidates:
        if c in df.columns:
            return c
    return default


import pandas as pd, numpy as np, plotly.graph_objects as go, streamlit as st
from datetime import datetime, timedelta

IS_GREEN = "#3cf57a" # Verde Improve Sankey (neón)
IS_CYAN = "#00e5ff"
IS_AMBER = "#ffb74d"
BG_DARK = "#0b0f12"
PAPER_DARK = "#0b0f12"
GRID_DARK = "rgba(255,255,255,0.06)"
TXT_DIM = "rgba(255,255,255,0.85)"

import plotly.graph_objects as go
import pandas as pd
import numpy as np
import streamlit as st
from typing import List, Optional

# Paleta Improve Sankey (verde HUD)
IS_BG = "#0b0f0c" # fondo
IS_PANEL = "#121714" # tarjetas
IS_STROKE = "#1c261e" # bordes/splits
IS_GREEN = "#5CFF7A" # verde primario
IS_CYAN = "#056B27" # cian acento
IS_AMBER = "#F5B400" # amarillo/umbral
IS_RED = "#FF4D5A" # alarma
IS_TEXT = "#048B34" # texto






   

def ensure_time(df: Optional[pd.DataFrame], minutes:int=35, freq:str="min")->pd.DataFrame:
    if df is None or "ts" not in df.columns or df["ts"].isna().all():
        base = pd.DataFrame({"ts": pd.date_range(end=pd.Timestamp.now(), periods=minutes, freq=freq)})
        return base
    out = df.copy()
    out["ts"] = pd.to_datetime(out["ts"], errors="coerce")
    out = out.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    return out

def pick_col(df: pd.DataFrame, candidates: List[str], default: Optional[str]=None)->Optional[str]:
    for c in candidates:
        if c in df.columns: return c
    return default


    

def gauge_semicircle(title: str, value: float, vmin: float, vwarn: float, vmax: float, key: str):
    """
    Semicírculo estilo HUD con brillo neón y fondo totalmente transparente.
    - title : texto arriba
    - value : valor numérico
    - vmin : mínimo escala
    - vwarn : umbral de aviso (se marca en ámbar)
    - vmax : máximo escala
    - key : clave única Streamlit
    """
    import plotly.graph_objects as go
    import numpy as np
    import streamlit as st

    # ---- (1) Marcador para aplicar CSS al contenedor que viene justo después ----
    st.markdown(f'<div class="gauge-neon" id="g-{key}"></div>', unsafe_allow_html=True)

    # ---- (2) Valor seguro y paleta Improve Sankey ----
    val = float(value) if value is not None and np.isfinite(value) else 0.0
    IS_PANEL = "#121617"
    IS_STROKE = "#1c2426"
    IS_TEXT = "#D6F5E1"
    IS_CYAN = "#012C16"
    IS_GREEN = "#5CFF7A"
    IS_AMBER = "#F5B400"
    IS_RED = "#FF4D5A"

    # Pasos para “glow” + zonas (verde tenue global, ámbar en warn, rojo en alto)
    steps = [
        {"range": [vmin, vmax], "color": "rgba(92,255,122,0.10)"}, # halo suave
        {"range": [vmin, max(vmin, vwarn*0.95)], "color": "rgba(92,255,122,0.35)"},
        {"range": [vwarn*0.95, vwarn*1.08], "color": "rgba(92,255,122,0.35)"},
        {"range": [vwarn*1.08, vmax], "color": "rgba(92,255,122,0.35)"},
    ]
    # Reducimos grosor del aro exterior para que quede fino
    for s in steps:
        s["thickness"] = 0.4 # 8% del radio

    # ---- (3) Indicador semicircular sin fondo ----
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={"suffix": " °C", "font": {"color": IS_TEXT, "size": 30}},
        title={"text": f"<b style='color:{IS_GREEN};font-size:13px'>{title}</b>"},
        gauge={
            "shape": "angular", # semicircular
            "axis": {"range": [vmin, vmax], "tickcolor": "#3b4648", "tickwidth": 1, "ticklen": 4},
            "bar": {"color": IS_CYAN, "thickness": 0.2}, # barra fina (6%)
            "bgcolor": "rgba(0,0,0,0)", # fondo interior TRANSPARENTE
            "bordercolor": "rgba(0,0,0,0)", # sin borde del gauge
            "steps": steps,
        
        },
        domain={"x": [0, 1], "y": [0, 1]},
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", # sin fondo del lienzo
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=34, b=0),
        height=180,
    )

    st.markdown('<div class="is-gauge-neon">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, key=key)


def kpi_tile(title:str, value:float, unit:str, key:str, warn_high:Optional[float]=None):
    cls = "bar-ok"
    if warn_high is not None and value is not None:
        if value >= warn_high: cls = "bar-bad"
        elif value >= 0.8*warn_high: cls = "bar-warn"
    st.markdown(f"""
    <div class="hud-card {cls}">
        <div class="hdr">{title}</div>
        <div style="display:flex;align-items:baseline;gap:6px;margin-top:6px;">
            <div class="kpi-value">{value:0.1f}</div><div class="kpi-unit">{unit}</div>
        </div>
    </div>
    """, unsafe_allow_html=True, key=key)

def ensure_binary(df: pd.DataFrame, cols: List[str])->pd.DataFrame:
    out = df.copy()
    n = len(out)
    for c in cols:
        if c not in out.columns:
            s = (np.random.rand(n) > 0.85).astype(int)
            s = pd.Series(s).rolling(3, min_periods=1).max().values
            out[c] = s
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype(int)
    return out

def step_timeline_hud(df: pd.DataFrame, cols: list[str], title: str, height: int, key: str):
    """Timeline ON/OFF con 'barras' escalonadas (líneas gruesas) + estética HUD."""
    base = ensure_time(df)
    cols = [c for c in cols if c in df.columns]
    if not cols:
        st.info(f"No hay señales para “{title}”.")
        return

    d = df.copy().merge(base[["ts"]], on="ts", how="right").sort_values("ts").reset_index(drop=True)

    fig = go.Figure()
    lane_h = 1.2 # separación vertical entre carriles
    bar_h = 0.85 # altura visual de la barra (escala 0..1)
    y_ticks = []

    palette_on = ["#5CFF7A", "#47E3FF", "#F5B400", "#9E77FF", "#7CF5E6"]
    palette_off = ["rgba(92,255,122,0.12)"] # base apagada muy tenue

    for i, c in enumerate(cols):
        s = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int)
        y_base = i*lane_h
        y_on = y_base + s*bar_h

        # base "apagada"
        fig.add_trace(go.Scatter(
            x=d["ts"], y=[y_base]*len(d), mode="lines",
            line=dict(width=10, color=palette_off[0]), hoverinfo="skip", showlegend=False
        ))
        # barra ON (línea gruesa escalonada)
        fig.add_trace(go.Scatter(
            x=d["ts"], y=y_on, mode="lines",
            line=dict(width=14, color=palette_on[i % len(palette_on)]),
            line_shape="hv", name=c, hovertemplate=f"<b>{c}</b><br>%{{x|%H:%M:%S}}<extra></extra>"
        ))
        y_ticks.append(y_base + bar_h/2)

    fig.update_layout(
        title=dict(text=f"<b style='color:{IS_TEXT};font-size:13px'>{title}</b>", x=0.01, y=0.98),
        height=height, paper_bgcolor=IS_PANEL, plot_bgcolor=IS_PANEL,
        margin=dict(l=10, r=10, t=36, b=24),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    fig.update_xaxes(title_text="Tiempo", showgrid=False, color="#8ea39a")
    fig.update_yaxes(
        tickmode="array", tickvals=y_ticks, ticktext=cols,
        zeroline=False, showgrid=False, color="#8ea39a", range=[-0.4, (len(cols)-1)*lane_h + 1.0]
    )

    st.plotly_chart(fig, use_container_width=True, key=key)

def line_trend(df: pd.DataFrame, cols: List[str], title: str, key: str,
                height: int = 260, unit: str = "°C"):
    base = ensure_time(df)
    d = df.copy().merge(base[["ts"]], on="ts", how="right").sort_values("ts")

    fig = go.Figure()
    pal = [IS_GREEN, IS_CYAN, IS_AMBER, "#8A7CFF", "#FF8AD1", "#6EE7F9"]

    cols_ok = [c for c in cols if c in d.columns]
    for i, c in enumerate(cols_ok):
        fig.add_trace(go.Scatter(
            x=d["ts"], y=d[c], mode="lines",
            name=c, line=dict(width=2.2, color=pal[i % len(pal)])
        ))

    fig.update_layout(
        title=dict(text=f"<b style='color:{IS_TEXT}'>{title}</b>", x=0.01, y=0.98),
        height=height, paper_bgcolor=IS_PANEL, plot_bgcolor=IS_PANEL,
        margin=dict(l=10, r=10, t=36, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    fig.update_xaxes(title_text="Tiempo", color="#8ea39a")
    fig.update_yaxes(title_text=unit, color="#8ea39a", zeroline=False)

    st.plotly_chart(fig, use_container_width=True, key=key)

# ==== HELPERS ARMÓNICOS (V e I, órdenes 2..32) ====
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import streamlit as st

def _last_series(df: pd.DataFrame, cols: list[str]) -> dict[str, float]:
    """Devuelve el último valor numérico de cada columna (o 0.0 si no existe)."""
    out = {}
    for c in cols:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce").dropna()
            out[c] = float(s.iloc[-1]) if len(s) else 0.0
        else:
            out[c] = 0.0
    return out

def _bar_spectrum(orders: list[int], values: list[float], title: str, unit="%", key=None, height=260):
    fig = go.Figure(go.Bar(
        x=orders, y=values,
        marker=dict(color="#39FF88"),
        hovertemplate="Orden %{x}º<br><b>%{y:.2f}"+unit+"</b><extra></extra>"
    ))
    fig.update_layout(
        height=height, template="plotly_dark",
        margin=dict(l=10,r=10,t=30,b=30),
        paper_bgcolor="#0b0f12", plot_bgcolor="#0b0f12",
        title=dict(text=f"<b style='color:#39FF88'>{title}</b>", x=0.02),
        xaxis=dict(title="Orden armónico", tickmode="linear", dtick=2, gridcolor="rgba(255,255,255,0.08)"),
        yaxis=dict(title=unit, gridcolor="rgba(255,255,255,0.08)")
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

def _simulate_harmonics_df(minutes=10, freq_s=5) -> pd.DataFrame:
    """Crea un df con 'ts' y columnas V_H2_%..V_H32_% e I_H2_%..I_H32_%."""
    n = int((minutes*60)//freq_s)
    t0 = pd.Timestamp.now() - pd.Timedelta(minutes=minutes)
    ts = pd.date_range(t0, periods=n, freq=f"{freq_s}s")
    rng = np.random.default_rng(7)
    base_v, base_i = 3.0, 6.0
    data = {"ts": ts}
    for k in range(2, 33):
        # pequeñas variaciones
        data[f"V_H{k}_%"] = np.clip(base_v/k + rng.normal(0, 0.05, size=n), 0, None)
        data[f"I_H{k}_%"] = np.clip(base_i/k + rng.normal(0, 0.08, size=n), 0, None)
    return pd.DataFrame(data)

def spectrum_bar(title: str, orders: list[int], values: list[float], unit="%", key=None):
    fig = go.Figure(go.Bar(
        x=orders, y=values,
        marker=dict(color="#39FF88", line=dict(width=0)),
        hovertemplate="Orden %{x}º<br><b>%{y:.2f}"+unit+"</b><extra></extra>"
    ))
    fig.update_layout(
        height=260, template="plotly_dark",
        margin=dict(l=10, r=10, t=30, b=30),
        paper_bgcolor="#0b0f12", plot_bgcolor="#0b0f12",
        title=dict(text=f"<b style='color:#39FF88'>{title}</b>", x=0.02),
        xaxis=dict(title="Orden armónico", tickmode="linear", dtick=2, gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title=unit, gridcolor="rgba(255,255,255,0.06)")
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

def get_harmonics_from_df(df: pd.DataFrame, prefix: str) -> list[float]:
    """
    Lee columnas con nombre: f"{prefix}_H2_%", ..., f"{prefix}_H32_%"
    Ejemplos de prefix: "V" (tensión), "I" (corriente)
    Devuelve lista de 31 valores (%), del orden 2 al 32.
    """
    vals = []
    for n in range(2, 33):
        col = f"{prefix}_H{n}_%"
        if col in df.columns:
            v = pd.to_numeric(df[col], errors="coerce").dropna()
            vals.append(float(v.iloc[-1]) if len(v) else 0.0)
        else:
            vals.append(0.0)
    return vals


def enable_particles_bg():
    st.markdown("""
    <style>
    /* Capa de partículas */
    .is-particles {
    position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background:
    radial-gradient(2px 2px at 10% 20%, rgba(57,255,136,.28) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 30% 35%, rgba(71,227,255,.27) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 55% 15%, rgba(57,255,136,.23) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 70% 40%, rgba(71,227,255,.22) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 85% 25%, rgba(57,255,136,.20) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 25% 70%, rgba(71,227,255,.18) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 45% 80%, rgba(57,255,136,.22) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 75% 75%, rgba(71,227,255,.20) 40%, transparent 41%);
    animation: is-drift 26s linear infinite alternate;
    opacity: .55;
    }
    .is-particles::after{
    content:""; position:absolute; inset:0;
    background:
    radial-gradient(2px 2px at 15% 60%, rgba(57,255,136,.22) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 40% 55%, rgba(71,227,255,.22) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 60% 65%, rgba(57,255,136,.20) 40%, transparent 41%) ,
    radial-gradient(2px 2px at 78% 55%, rgba(71,227,255,.20) 40%, transparent 41%);
    animation: is-drift-2 34s linear infinite alternate;
    opacity:.7;
    }
    @keyframes is-drift {
    0% { transform: translate3d(-1%, -1%, 0) }
    100%{ transform: translate3d( 1%, 1%, 0) }
    }
    @keyframes is-drift-2 {
    0% { transform: translate3d( 1%, -1%, 0) }
    100%{ transform: translate3d(-1%, 1%, 0) }
    }
    /* mete la capa de partículas detrás del contenido */
    .stApp > div:first-child { position: relative; z-index: 1; }
    .stApp .is-particles-holder { position: fixed; inset:0; z-index:0; pointer-events:none; }
    </style>
    <div class="is-particles-holder"><div class="is-particles"></div></div>
    """, unsafe_allow_html=True)

def enable_energy_bg():
# Fondo dinámico con rejilla sutil y glows verdes/cián
    st.markdown("""
    <style>
    .stApp::before{
    content:"";
    position:fixed; inset:-10% -10% -10% -10%;
    /* Capas: halos + rejilla sutil */
    background:
    radial-gradient(60% 40% at 10% 0%, rgba(57,255,136,.06), transparent 60%),
    radial-gradient(50% 35% at 90% 10%, rgba(0,209,255,.05), transparent 55%),
    repeating-linear-gradient(0deg, rgba(57,255,136,.06) 0 2px, transparent 2px 40px),
    repeating-linear-gradient(90deg, rgba(57,255,136,.035) 0 2px, transparent 2px 40px);
    filter: blur(0.2px);
    animation: gridFloat 24s linear infinite;
    z-index:0; pointer-events:none;
    }
    .stApp::after{
    content:"";
    position:fixed; inset:0;
    /* Glows pulsantes */
    background-image:
    radial-gradient(18rem 12rem at 20% 30%, rgba(57,255,136,.10), transparent 60%),
    radial-gradient(14rem 10rem at 80% 20%, rgba(0,209,255,.08), transparent 60%);
    animation: pulseGlow 9s ease-in-out infinite alternate;
    z-index:0; pointer-events:none;
    }
    /* Asegura que el contenido queda por encima del fondo animado */
    .stApp > div:first-child { position: relative; z-index: 1; }

    @keyframes gridFloat{
    0% { transform: translate3d(0,0,0) }
    50% { transform: translate3d(-2%, -1%, 0) }
    100% { transform: translate3d(0,0,0) }
    }
    @keyframes pulseGlow{
    0% { opacity:.55; }
    100% { opacity:.9; }
    }
    </style>
    """, unsafe_allow_html=True)

def hud_css():
    st.markdown("""
    <style>
    :root{
    --is-green:#39FF88; /* Verde Improve Sankey */
    --is-cyan:#47E3FF;
    --is-bg:#0b0f12;
    }

    /* Título HUD con punto y subrayado neón animado */
    .hud-title{
    position:relative;
    font-weight:800;
    font-size:22px;
    letter-spacing:.2px;
    color:var(--is-green);
    margin:18px 0 28px;
    text-shadow:0 0 8px rgba(57,255,136,.65);
    }
    .hud-title .dot{
    display:inline-block;
    width:10px;height:10px;border-radius:50%;
    margin-right:10px;transform:translateY(-1px);
    background:radial-gradient(circle at 30% 30%, #6bffb5, var(--is-green));
    box-shadow:0 0 10px var(--is-green), 0 0 22px rgba(57,255,136,.55);
    }
    .hud-title::after{
    content:""; position:absolute; left:26px; bottom:-10px; height:2px; width:0;
    background:linear-gradient(90deg,
    rgba(57,255,136,0.0) 0%,
    var(--is-green) 25%,
    var(--is-cyan) 50%,
    var(--is-green) 75%,
    rgba(57,255,136,0.0) 100%);
    box-shadow:0 0 12px var(--is-green);
    animation:neon-underline 2.6s ease-in-out infinite;
    }
    @keyframes neon-underline{
    0% { width:0; opacity:.7; }
    50% { width:260px; opacity:1; }
    100% { width:0; opacity:.7; }
    }

    /* Variante sin animación (por si algún título lo quieres fijo) */
    .hud-title.static::after{
    animation:none; width:220px; opacity:1;
    }
     /* ===== Tarjeta HUD lateral (CORE STATUS) ===== */
    .hud-side-card{
        border-radius: 20px;
        padding: 14px 16px;
        margin-bottom: 12px;
        border: 1px solid rgba(0,255,140,0.4);
        background:
            radial-gradient(circle at 0% 0%, rgba(0,255,140,0.16), transparent 55%),
            radial-gradient(circle at 100% 0%, rgba(0,180,255,0.10), transparent 55%),
            rgba(4,8,20,0.96);
        box-shadow: 0 0 20px rgba(0,255,140,0.18);
    }

    .hud-chip{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: #8BFFCF;
        margin-bottom: 8px;
    }

    .hud-row{
        display:flex;
        justify-content:space-between;
        gap:10px;
        margin-bottom:10px;
    }

    .hud-col{
        flex:1;
    }

    .hud-col-right{
        text-align:right;
    }

    .hud-label{
        font-size:11px;
        color:#9fa6b2;
    }

    .hud-value{
        font-size:13px;
        font-weight:500;
    }

    .hud-value-main{
        font-size:18px;
        font-weight:700;
        color:#5CFF7A;
    }

    /* Pastillas de estado */
    .hud-pill-row{
        display:flex;
        flex-wrap:wrap;
        gap:6px;
        margin-top:4px;
        }

    .hud-pill{
        font-size:11px;
        padding:4px 10px;
        border-radius:999px;
        border:1px solid rgba(0,255,140,0.4);
        background:rgba(0,255,140,0.08);
        color:#CFFFE7;
        }  
    /* ===== Fondo verde para la tarjeta de Información ===== */
    [data-testid="stExpander"] .st-expander-content {
        background: #003b1f !important; /* verde oscuro elegante */
        border-radius: 12px !important;
    }

    [data-testid="stExpander"] {
        background: #005226 !important; /* verde más brillante */
        border-radius: 12px !important;
        border: 1px solid #06ff77 !important; /* borde neón verde Improve Sankey */
    }  
    /* ===== Sidebar completa: verde casi negro + borde neón ===== */
    [data-testid="stSidebar"] {
        background: #00140d !important; /* VERDE MUY OSCURO CASI NEGRO */
        border-right: 2px solid #00ff88 !important; /* borde neón */
        box-shadow: 0 0 25px #00ff88aa !important; /* resplandor hacia adentro */
    }

    /* Fondo interno más homogéneo */
        [data-testid="stSidebar"] .css-1d391kg,
        [data-testid="stSidebar"] .css-1n76uvr {
            background-color: #00140d !important;
    }

    /* Encabezados dentro del sidebar con brillo */
    [data-testid="stSidebar"] .st-expanderHeader {
        background: rgba(0, 255, 136, 0.05) !important;
        border: 1px solid rgba(0, 255, 136, 0.3) !important;
        box-shadow: 0 0 12px #00ff8899 inset !important;
        color: #00ff99 !important;
    }

    /* Títulos */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #00ffbf !important; /* texto verde neón */
    }

    /* Líneas separadoras con glow */
    [data-testid="stSidebar"] hr {
        border: 0;
        height: 1px;
        background: linear-gradient(90deg, #00ff88, transparent);
        box-shadow: 0 0 10px #00ff8866;
    }
    </style>
    """, unsafe_allow_html=True)
    

def line_hud(df, series, title="", yaxis="",
    colors=None, height=260, key=None):
    """
    df: DataFrame con columna 'ts' (datetime)
    series: lista de nombres de columnas a pintar
    """
    colors = colors or [IS_GREEN, IS_CYAN, IS_AMBER, "#9E77FF", "#FF6E6E", "#7CF5E6"]
    fig = go.Figure()
    for i, c in enumerate(series):
        if c not in df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=df["ts"], y=pd.to_numeric(df[c], errors="coerce"),
            mode="lines", name=c, line=dict(width=2, color=colors[i % len(colors)]),
            hovertemplate="<b>%{y:.2f}</b><br>%{x|%H:%M:%S}<extra>"+c+"</extra>"
        ))
    fig.update_layout(
        height=height, template="plotly_dark",
        margin=dict(l=10, r=10, t=28, b=30),
        paper_bgcolor=PAPER_DARK, plot_bgcolor=BG_DARK,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        title=dict(text=title, x=0.02, font=dict(size=15, color=IS_GREEN)),
        xaxis=dict(title="Tiempo", gridcolor=GRID_DARK, zeroline=False, showspikes=True, spikemode="across"),
        yaxis=dict(title=yaxis, gridcolor=GRID_DARK, zeroline=False),
        hoverlabel=dict(bgcolor="#0f141a"),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)

def simulate_df(minutes=30, freq_s=5, seed=None):
    """Genera dataframe simulado con las columnas estándar y ts."""
    rng = np.random.default_rng(seed or int(pd.Timestamp.now().timestamp()))
    n = int((minutes*60)//freq_s)
    ts = pd.date_range(end=pd.Timestamp.now(), periods=n, freq=f"{freq_s}s")

    def jitter(base, amp, drift=0):
        x = base + amp*rng.standard_normal(n)
        if drift:
            x = x + np.linspace(0, drift, n)
        return np.round(x, 3)

    df = pd.DataFrame({"ts": ts})
    # Tensiones
    df["V_L1N"] = jitter(230, 2)
    df["V_L2N"] = jitter(230, 2)
    df["V_L3N"] = jitter(230, 2)
    df["V_L1L2"]= jitter(400, 3)
    df["V_L2L3"]= jitter(400, 3)
    df["V_L3L1"]= jitter(400, 3)
    # Corrientes
    df["I_L1"] = jitter(120, 4)
    df["I_L2"] = jitter(118, 4)
    df["I_L3"] = jitter(122, 4)
    df["I_N"] = np.abs(jitter(8, 2))
    # Potencias
    df["P_kW"] = jitter(150, 6, drift=3)
    df["Q_kVAr"]= jitter(35, 4)
    df["S_kVA"] = np.sqrt(df["P_kW"]**2 + df["Q_kVAr"]**2)
    # PF, Freq
    df["PF"] = np.clip(df["P_kW"]/df["S_kVA"], 0.6, 1.0)
    df["Freq_Hz"]= jitter(50, 0.03)
    # THD
    df["THD_V_%"]= np.clip(jitter(2.8, 0.4), 0, None)
    df["THD_I_%"]= np.clip(jitter(5.5, 1.2), 0, None)
    return df

# Columnas esperadas cuando conectes datos REALES (mismo nombre que arriba)
REQUIRED_COLS = [
    "V_L1N","V_L2N","V_L3N","V_L1L2","V_L2L3","V_L3L1",
    "I_L1","I_L2","I_L3","I_N","P_kW","Q_kVAr","S_kVA",
    "PF","Freq_Hz","THD_V_%","THD_I_%","ts"
]
# ==============================================================================



# ---------- Detección en df de columnas reales ----------
def detect_ats_from_df(df):
    # 1) Intento con columnas ATS1/ATS2/ATS3 (muchos alias posibles)
    aliases = [
        ["ATS1","ATS_1","A1","ATS_SUP","ATS_TOP"],
        ["ATS2","ATS_2","A2","ATS_MID","ATS_MEDIO"],
        ["ATS3","ATS_3","A3","ATS_BOT","ATS_ABAJO"],
    ]
    found = []
    for group in aliases:
        for c in group:
            if c in df.columns:
                found.append(c)
                break
        else:
            found.append(None)

        if all(found): # tenemos 3 columnas reales
            last = df.iloc[-1]
            def on(c):
                v = last[c]
                # acepta bool/0-1/num
                try:
                    return bool(int(v))
                except:
                    return bool(v)
            ats1 = "green" if on(found[0]) else "red"
            ats2 = "green" if on(found[1]) else "red"
            ats3 = "green" if on(found[2]) else "red"
            return ats1, ats2, ats3, "AUTO(ATS1/2/3)"

        # 2) Intento con columna de modo
        for modo_col in ["MODO","MODE","ESTADO_MAQ","STATE","RUN_MODE"]:
            if modo_col in df.columns:
                modo = str(df.iloc[-1][modo_col])
                return (*map_by_mode(modo), f"AUTO({modo_col})")

        # Nada detectado
        return None, None, None, None

def badge_html(nombre: str, encendido: bool) -> str:
    clase = "on" if encendido else "off"
    etiqueta = "ON" if encendido else "OFF"
    return f'<span class="badge {clase}"><span class="dot"></span>{nombre}: {etiqueta}</span>'

# Lee un "flag" ON/OFF desde df (última fila). Admite 1/0, True/False, "ON"/"OFF"
def read_flag_from_df(df, candidatos):
    c = pick_col(df, candidatos)
    if not c:
        return None # no hay columna
    v = df.iloc[-1][c]
    try:
        # normalizar
        if isinstance(v, str):
            v = v.strip().upper()
            if v in ("ON","RUN","ENCENDIDO","TRUE","1"): return True
            if v in ("OFF","STOP","APAGADO","FALSE","0"): return False
        return bool(int(v))
    except Exception:
        return None
# ===========================================================

# ====== Simulador con TODOS los parámetros ======
import pandas as pd, numpy as np
from datetime import datetime, timedelta

def simulate_full(n=600, dt_seconds=1):
    now = datetime.now()
    ts = pd.date_range(end=now, periods=n, freq=f"{dt_seconds}S")

    # Base valores nominales
    Vll_nom = 400.0
    Vln_nom = Vll_nom/np.sqrt(3)
    I_nom = 50.0
    freq = 50.0

    # Variaciones suaves
    noise = lambda s: np.random.normal(0, s, size=n)

    V_L1N = Vln_nom + noise(1.5)
    V_L2N = Vln_nom + noise(1.5)
    V_L3N = Vln_nom + noise(1.5)

    # Línea–línea calculadas
    V_L1L2 = np.sqrt(V_L1N**2 + V_L2N**2 - V_L1N*V_L2N)
    V_L2L3 = np.sqrt(V_L2N**2 + V_L3N**2 - V_L2N*V_L3N)
    V_L3L1 = np.sqrt(V_L3N**2 + V_L1N**2 - V_L3N*V_L1N)

    I_L1 = I_nom + noise(1.8)
    I_L2 = I_nom + noise(1.8)
    I_L3 = I_nom + noise(1.8)
    I_N = np.clip(noise(2.5), 0, None)

    # PF por fase y total
    PF_L1 = np.clip(np.random.normal(0.96, 0.01, size=n), 0.85, 0.99)
    PF_L2 = np.clip(np.random.normal(0.95, 0.015, size=n), 0.80, 0.99)
    PF_L3 = np.clip(np.random.normal(0.97, 0.01, size=n), 0.85, 0.99)
    PF_TOT = (PF_L1+PF_L2+PF_L3)/3

    # Potencias por fase y totales (kW/kvar/kVA)
    P_L1 = (V_L1N*I_L1*PF_L1)/1000*np.sqrt(3)
    P_L2 = (V_L2N*I_L2*PF_L2)/1000*np.sqrt(3)
    P_L3 = (V_L3N*I_L3*PF_L3)/1000*np.sqrt(3)
    P_TOT = P_L1+P_L2+P_L3

    S_L1 = (V_L1N*I_L1)/1000*np.sqrt(3)
    S_L2 = (V_L2N*I_L2)/1000*np.sqrt(3)
    S_L3 = (V_L3N*I_L3)/1000*np.sqrt(3)
    S_TOT = S_L1+S_L2+S_L3

    Q_L1 = np.sqrt(np.maximum(S_L1**2 - P_L1**2, 0))
    Q_L2 = np.sqrt(np.maximum(S_L2**2 - P_L2**2, 0))
    Q_L3 = np.sqrt(np.maximum(S_L3**2 - P_L3**2, 0))
    Q_TOT = Q_L1+Q_L2+Q_L3

    # Frecuencia y THD
    FREQ = freq + noise(0.02)
    THD_V_L1 = np.clip(np.random.normal(3.5, 0.6, size=n), 1, 10)
    THD_V_L2 = np.clip(np.random.normal(3.7, 0.6, size=n), 1, 10)
    THD_V_L3 = np.clip(np.random.normal(3.6, 0.6, size=n), 1, 10)
    THD_I_L1 = np.clip(np.random.normal(6.0, 1.0, size=n), 1, 20)
    THD_I_L2 = np.clip(np.random.normal(6.5, 1.0, size=n), 1, 20)
    THD_I_L3 = np.clip(np.random.normal(6.2, 1.0, size=n), 1, 20)

    # Desequilibrios y demanda
    UNB_U = np.abs((V_L1N - (V_L2N+V_L3N)/2)/Vln_nom)*100
    UNB_I = np.abs((I_L1 - (I_L2+I_L3)/2)/I_nom)*100
    DEMANDA_KW = pd.Series(P_TOT).rolling(60, min_periods=1).max().values # demanda 1 min

    # Energías acumuladas (kWh, kvarh) integrando potencia
    dt_h = dt_seconds/3600
    EP_IMP = np.cumsum(np.clip(P_TOT,0,None))*dt_h
    EP_EXP = np.cumsum(np.clip(-P_TOT,0,None))*dt_h
    EQ_IMP = np.cumsum(np.clip(Q_TOT,0,None))*dt_h
    EQ_EXP = np.cumsum(np.clip(-Q_TOT,0,None))*dt_h

    df = pd.DataFrame({
        "ts": ts,
        "V_L1N": V_L1N, "V_L2N": V_L2N, "V_L3N": V_L3N,
        "V_L1L2": V_L1L2, "V_L2L3": V_L2L3, "V_L3L1": V_L3L1,
        "I_L1": I_L1, "I_L2": I_L2, "I_L3": I_L3, "I_N": I_N,
        "P_L1": P_L1, "P_L2": P_L2, "P_L3": P_L3, "P_TOT": P_TOT,
        "Q_L1": Q_L1, "Q_L2": Q_L2, "Q_L3": Q_L3, "Q_TOT": Q_TOT,
        "S_L1": S_L1, "S_L2": S_L2, "S_L3": S_L3, "S_TOT": S_TOT,
        "PF_L1": PF_L1, "PF_L2": PF_L2, "PF_L3": PF_L3, "PF_TOT": PF_TOT,
        "FREQ": FREQ,
        "THD_V_L1": THD_V_L1, "THD_V_L2": THD_V_L2, "THD_V_L3": THD_V_L3,
        "THD_I_L1": THD_I_L1, "THD_I_L2": THD_I_L2, "THD_I_L3": THD_I_L3,
        "UNB_U": UNB_U, "UNB_I": UNB_I, "DEMANDA_KW": DEMANDA_KW,
        "EP_IMP": EP_IMP, "EP_EXP": EP_EXP, "EQ_IMP": EQ_IMP, "EQ_EXP": EQ_EXP
    })
    return df

def save_to_db(df: pd.DataFrame):
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    df_meas = df.drop(columns=["EP_IMP","EP_EXP","EQ_IMP","EQ_EXP"]).copy()
    df_meas["ts"] = df_meas["ts"].astype(str)
    df_meas.to_sql("measurements", con, if_exists="append", index=False)

    df_energy = df[["ts","EP_IMP","EP_EXP","EQ_IMP","EQ_EXP"]].copy()
    df_energy["ts"] = df_energy["ts"].astype(str)
    df_energy.to_sql("energy_counters", con, if_exists="append", index=False)
    con.close()

# Definir rutas de base y logo
BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "assets" / "logo.png"
# ====== Persistencia: SQLite con todos los parámetros ======
DB_PATH = "data/db.sqlite"

import sqlite3, os
os.makedirs("data", exist_ok=True)

DB_PATH = "data/db.sqlite"

def ensure_db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = con.cursor()

    # Medidas instantáneas (por muestra)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS measurements (
        ts TEXT PRIMARY KEY,
        -- Tensiones
        V_L1N REAL, V_L2N REAL, V_L3N REAL,
        V_L1L2 REAL, V_L2L3 REAL, V_L3L1 REAL,
        -- Corrientes
        I_L1 REAL, I_L2 REAL, I_L3 REAL, I_N REAL,
        -- Potencias
        P_L1 REAL, P_L2 REAL, P_L3 REAL, P_TOT REAL,
        Q_L1 REAL, Q_L2 REAL, Q_L3 REAL, Q_TOT REAL,
        S_L1 REAL, S_L2 REAL, S_L3 REAL, S_TOT REAL,
        -- Factor de potencia y frecuencia
        PF_L1 REAL, PF_L2 REAL, PF_L3 REAL, PF_TOT REAL,
        FREQ REAL,
        -- THD
        THD_V_L1 REAL, THD_V_L2 REAL, THD_V_L3 REAL,
        THD_I_L1 REAL, THD_I_L2 REAL, THD_I_L3 REAL,
        -- Desequilibrio y demanda (por si los usas luego)
        UNB_U REAL, UNB_I REAL, DEMANDA_KW REAL,
        -- Temperaturas
        CORE_TEMP REAL, R_TEMP REAL, S_TEMP REAL, T_TEMP REAL,
        -- Estados máquina / bypass / filtros / ventilación
        STATE_MACHINE INTEGER, STATE_BYPASS INTEGER,
        APF_ON INTEGER, SVG_ON INTEGER,
        FAN INTEGER,
        FUSE_R INTEGER, FUSE_S INTEGER, FUSE_T INTEGER,
        -- Alarmas
        ALARM_OVERTEMP_CORE INTEGER,
        ALARM_THY_R INTEGER,
        ALARM_THY_S INTEGER,
        ALARM_THY_T INTEGER
    );
    """)

    # Contadores de energía (cumulativos)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS energy_counters (
        ts TEXT PRIMARY KEY,
        EP_IMP REAL, EP_EXP REAL, -- kWh import/export
        EQ_IMP REAL, EQ_EXP REAL -- kvarh import/export
    );
    """)

    # Armónicos (1–31) por fase: tensión
    cur.execute("""
    CREATE TABLE IF NOT EXISTS harmonics_voltage (
        ts TEXT, phase TEXT,
        h1 REAL,h2 REAL,h3 REAL,h4 REAL,h5 REAL,h6 REAL,h7 REAL,h8 REAL,h9 REAL,h10 REAL,
        h11 REAL,h12 REAL,h13 REAL,h14 REAL,h15 REAL,h16 REAL,h17 REAL,h18 REAL,h19 REAL,h20 REAL,
        h21 REAL,h22 REAL,h23 REAL,h24 REAL,h25 REAL,h26 REAL,h27 REAL,h28 REAL,h29 REAL,h30 REAL,h31 REAL,
        PRIMARY KEY (ts, phase)
    );
    """)

    # Armónicos (1–31) por fase: corriente
    cur.execute("""
    CREATE TABLE IF NOT EXISTS harmonics_current (
        ts TEXT, phase TEXT,
        h1 REAL,h2 REAL,h3 REAL,h4 REAL,h5 REAL,h6 REAL,h7 REAL,h8 REAL,h9 REAL,h10 REAL,
        h11 REAL,h12 REAL,h13 REAL,h14 REAL,h15 REAL,h16 REAL,h17 REAL,h18 REAL,h19 REAL,h20 REAL,
        h21 REAL,h22 REAL,h23 REAL,h24 REAL,h25 REAL,h26 REAL,h27 REAL,h28 REAL,h29 REAL,h30 REAL,h31 REAL,
        PRIMARY KEY (ts, phase)
    );
    """)

    # Índices para gráficas rápidas
    cur.execute("CREATE INDEX IF NOT EXISTS idx_meas_ts ON measurements(ts);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_energy_ts ON energy_counters(ts);")
    con.commit()
    con.close()

    ensure_db()
    st.set_page_config(
    page_title="Improve Sankey",
    page_icon=str(LOGO_PATH),
    layout="wide"
    )


from dotenv import load_dotenv

load_dotenv()
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "improve")

def do_login():
    with st.sidebar:
        st.markdown("### Acceso")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar", use_container_width=True):
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")
    st.stop()

if "auth" not in st.session_state:
    st.session_state.auth = False
if not st.session_state.auth:
    do_login()

with st.sidebar:

    # ---- Tarjeta HEADER ----
    st.markdown("""
    <div class="hud-side-card">
    <div class="hud-side-title">⚙️ Improve Sankey </div>
    <div class="hud-side-sub"> </div>
    </div>
    """, unsafe_allow_html=True)


# === Resumen HUD del sistema (solo lectura, sin APF/SVG) ===
from datetime import datetime


pass 
from datetime import datetime # puedes dejarlo una sola vez en el archivo

with st.sidebar.expander(" Sistema", expanded=True):

    # Estado actual (de momento simulamos; luego lo leerás del PLC)
    estado_actual = st.session_state.get("estado_maquina_actual", "Activo") # "Activo" o "Bypass"

# Colores según estado
    if str(estado_actual).lower() == "activo":
        color_estado = "#39FF88" # verde Improve
        glow = "0 0 12px rgba(57,255,136,0.9)"
        icono = " "
        texto_estado = "Activo"
    else:
        color_estado = "#00E5FF" # azul para bypass
        glow = "0 0 12px rgba(0,229,255,0.9)"
        icono = "⭮"
        texto_estado = "Bypass"

    ahora = datetime.now().strftime("%H:%M:%S")

    st.markdown(f"""
        <div style="
        border-radius: 14px;
        padding: 10px 12px;
        margin-top: 4px;
        background: linear-gradient(135deg, rgba(7,15,15,0.98), rgba(4,10,12,0.99));
        border: 1px solid rgba(90, 255, 160, 0.35);
        box-shadow: 0 0 18px rgba(0,0,0,0.8);
        position: relative;
        overflow: hidden;
        ">

        <div style="
        font-size: 11px;
        letter-spacing: .18em;
        text-transform: uppercase;
        color: rgba(190, 230, 210, 0.75);
        margin-bottom: 4px;
        display:flex;
        align-items:center;
        gap:6px;
        ">
        <span style="
        width:8px;height:8px;border-radius:50%;
        background: radial-gradient(circle at 30% 30%, #6bffb5, {color_estado});
        box-shadow:{glow};
        "></span>
        ESTADO
        </div>

        <div style="display:flex; align-items:baseline; justify-content:space-between; margin-bottom:6px;">
        <div>
        <div style="font-size:13px; color:rgba(200,230,220,0.75);">
        Modo de operación
        </div>
        <div style="
        font-size:20px;
        font-weight:800;
        color:{color_estado};
        text-shadow:{glow};
        display:flex;
        align-items:center;
        gap:6px;
        ">
        <span>{icono}</span>
        <span>{texto_estado}</span>
        </div>
        </div>
        <div style="text-align:right; font-size:11px; color:rgba(180,210,200,0.65);">
        <div style="opacity:.8;">Última lectura</div>
        <div style="font-family:monospace; font-size:12px;">{ahora}</div>
        </div>
        </div>

        <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;">
        <span style="
        font-size:11px; padding:2px 8px; border-radius:999px;
        border:1px solid rgba(80, 200, 150, 0.6);
        color:rgba(220,255,240,0.9); background:rgba(40,80,60,0.25);
        ">
        ● Operación estable
        </span>
        <span style="
        font-size:11px; padding:2px 8px; border-radius:999px;
        border:1px solid rgba(0, 229, 255, 0.45);
        color:rgba(210,240,255,0.9); background:rgba(10,40,60,0.3);
        ">
        ● Improve Sankey
        </span>
        </div>

        <div style="
        position:absolute;
        left:10px;
        right:10px;
        bottom:4px;
        height:2px;
        background:linear-gradient(90deg,
        rgba(57,255,136,0.0) 0%,
        rgba(57,255,136,0.7) 25%,
        rgba(0,229,255,0.7) 50%,
        rgba(57,255,136,0.7) 75%,
        rgba(57,255,136,0.0) 100%
        );
        opacity:.85;
        "></div>
        </div>
        """, unsafe_allow_html=True)
                
                

with st.sidebar:
    # ================== CONFIGURACIÓN ==================
    with st.expander("⚙️ Configuración", expanded=False):

        # -------- 1) Histórico --------
        st.markdown("### 📚 Histórico")
        rng = st.selectbox(
            "Rango temporal",
            [
                "Últimos 15 min",
                "Última 1 h",
                "Últimas 6 h",
                "Últimas 12 h",
                "Últimas 24 h",
                "Hoy",
                "Esta semana",
            ],
            index=0,
            key="cfg_rng",
        )

        # -------- 2) Intervalo de refresco --------
        st.markdown("### ⏱ Intervalo de refresco")
        refresh_mode = st.radio(
            "Frecuencia de actualización",
            [
                "Cada 1 s (rápido)",
                "Cada 5 s (normal)",
                "Cada 10 s (ahorro)",
                "Manual (solo botón Actualizar)",
            ],
            index=1,
            key="cfg_refresh_mode",
        )

        # -------- 3) Fuente de datos --------
        st.markdown("### 🔌 Fuente de datos")
        preferred_source = st.radio(
            "Fuente preferida",
            ["Simulador", "SQLite", "Modbus", "MQTT"],
            index=0,
            key="cfg_preferred_source",
        )

    # Guardamos en session_state por si lo usas en otras pestañas
    st.session_state["rng"] = rng
    st.session_state["refresh_mode"] = refresh_mode
    st.session_state["preferred_source"] = preferred_source   

# ---- Información global ----
with st.sidebar.expander("ℹ️ Información", expanded=True):
    import datetime
    st.write("Hora actual:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.write("Equipo:", "Improve Sankey #001")
    st.write("Versión:", "v1.0.1")

from pathlib import Path
from PIL import Image
import base64






@st.cache_resource
def get_conn():
    # --- Utilidad: horas ON por cada señal en la tabla 'states' ---
    def horas_on_por_col(conn, cols=("maquina", "apf", "svg")):
        import pandas as pd
        from datetime import datetime

        # Leemos el histórico de estados
        try:
            df = pd.read_sql_query(
                "SELECT ts, maquina, apf, svg FROM states ORDER BY ts ASC",
                conn,
                parse_dates=["ts"]
            )
        except Exception:
            # Si la tabla no existe o falla la lectura, devolvemos 0.0 horas
            return {c: 0.0 for c in cols}

        # Si no hay datos, devolvemos 0.0 horas
        if df.empty:
            return {c: 0.0 for c in cols}

        # Asegurar orden, unicidad y timestamps válidos
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts").drop_duplicates(subset=["ts"])

        # Siguiente marca temporal; la última hasta "ahora"
        now_ts = pd.Timestamp(datetime.now().replace(microsecond=0))
        df["ts_next"] = df["ts"].shift(-1)
        df.loc[df.index[-1], "ts_next"] = now_ts

        # Duración de cada tramo en horas
        df["dt_h"] = (df["ts_next"] - df["ts"]).dt.total_seconds() / 3600.0

        # Por si alguna columna no existe, la creamos a 0
        for c in cols:
            if c not in df.columns:
                df[c] = 0

        # Suma de horas cuando el estado está a 1
        totales = {c: float((df["dt_h"] * (df[c] == 1)).sum()) for c in cols}
        return totales
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS measurements(
        ts TEXT PRIMARY KEY,
        source TEXT,
        tag TEXT,
                             
        -- TENSIONES
        V_L1N REAL,
        V_L2N REAL,
        V_L3N REAL,
        V_L1L2 REAL,
        V_L2L3 REAL,
        V_L3L1 REAL,

        -- CORRIENTES
        I_L1 REAL,
        I_L2 REAL,
        I_L3 REAL,
        I_N REAL,

        -- POTENCIAS
        P_kW REAL,
        Q_kVAr REAL,
        S_kVA REAL,

        -- OTROS
        PF REAL,
        Freq_Hz REAL,

        THD_V REAL,
        THD_I REAL
    )
    """)
    conn.execute("""CREATE TABLE IF NOT EXISTS alarms(
        ts TEXT, tag TEXT, type TEXT, message TEXT
    )""")
    # Crear tabla de estados si no existe
    conn.execute("""
    CREATE TABLE IF NOT EXISTS states (
        ts TEXT,
        maquina INTEGER,
        apf INTEGER,
        svg INTEGER
    )
    """)
    conn.commit()
    return conn
conn = get_conn()


from datetime import datetime, timedelta

# === Sidebar completamente vacío (temporal) ===
with st.sidebar:
    st.markdown("### ")
    st.markdown(" ") # Espacio en blanco
# Variables temporales mientras la barra está vacía
val_m = False
val_apf = False
val_svg = False
modo = "OFF"

# ─────────────────────────────────────────────────────────


from datetime import datetime

def save_state(conn, m_on: bool, a_on: bool, s_on: bool):
    from datetime import datetime
    conn.execute(
        "INSERT INTO states (ts, maquina, apf, svg) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"),
        1 if m_on else 0,
        1 if a_on else 0,
        1 if s_on else 0)
    )
    conn.commit()
    
# Guardar cambio solo si hay modificación
prev = (
    st.session_state.get("_prev_m"),
    st.session_state.get("_prev_apf"),
    st.session_state.get("_prev_svg"),
)
now = (val_m, val_apf, val_svg)

if prev != now:
    save_state(conn, val_m, val_apf, val_svg)
    st.session_state["_prev_m"], st.session_state["_prev_apf"], st.session_state["_prev_svg"] = now

now = datetime.now()

# valor por defecto, por si aún no hay nada en la sesión
rng = st.session_state.get("rng", "Últimos 15 min")

# Calcula t_from y t_to según el rango elegido
if rng == "Últimos 15 min":
    t_from, t_to = now - timedelta(minutes=15), now
elif rng == "Última 1 h":
    t_from, t_to = now - timedelta(hours=1), now
elif rng == "Últimas 6 h":
    t_from, t_to = now - timedelta(hours=6), now
elif rng == "Últimas 12 h":
    t_from, t_to = now - timedelta(hours=12), now
elif rng == "Últimas 24 h":
    t_from, t_to = now - timedelta(hours=24), now
elif rng == "Hoy":
    t_from, t_to = datetime(now.year, now.month, now.day), now
elif rng == "Esta semana":
    start = datetime(now.year, now.month, now.day) - timedelta(days=now.weekday())
    t_from, t_to = start, now
else:
    t_from = now - timedelta(hours=1)
    t_to = now


f_source = "ewon"
f_tag = "cualquiera"

def query(t0, t1, source, tag):
    q = "SELECT * FROM measurements WHERE ts BETWEEN ? AND ?"
    args = [t0.isoformat(), t1.isoformat()]

    # Miramos qué columnas existen realmente en la tabla
    cols = [row[1] for row in conn.execute("PRAGMA table_info(measurements)")]

    if "source" in cols and source != "cualquiera":
        q += " AND source = ?"
        args.append(source)

    if "tag" in cols and tag != "cualquiera":
        q += " AND tag = ?"
        args.append(tag)

    q += " ORDER BY ts ASC"
    return pd.read_sql_query(q, conn, params=args, parse_dates=["ts"])

df = query(t_from, t_to, f_source, f_tag)
# ---------- Estados de máquina y filtros ----------
# Intentar leer de columnas (pon aquí los alias reales si tu equipo los expone)
col_mode = ["MODE", "MODO", "STATE", "RUN_STATE", "ON_OFF"]
col_apf = ["APF", "APF_ON", "FILTRO_APF", "APF_STATE"]
col_svg = ["SVG", "SVG_ON", "STATCOM", "SVG_STATE"]

estado_maquina = read_flag_from_df(df, col_mode)
estado_apf = read_flag_from_df(df, col_apf)
estado_svg = read_flag_from_df(df, col_svg)


# Guardamos para usarlos en cualquier pestaña
m_on = bool(st.session_state.get("sim_modo_on", False))
a_on = bool(st.session_state.get("sim_apf_on", False))
s_on = bool(st.session_state.get("sim_svg_on", False))
# --- Normalizar nombres de columnas ---
df = df.copy()
df["ts"] = pd.to_datetime(df["ts"], errors="coerce") # Convierte el tiempo a datetime

# Si no existe 'power_kw', la creamos a partir de P_TOT u otra parecida
if "power_kw" not in df.columns:
    for cand in ["P_TOT", "P_ACT", "P_TOTAL", "P"]:
        if cand in df.columns:
            df["power_kw"] = df[cand]
            break





import pandas as pd
import streamlit as st
import plotly.express as px
import re

def find_h_order_cols(df, tipo: str, order: int):
    """Busca columnas de armónicos (por orden y fase) dentro del DataFrame."""
    cols = [c for c in df.columns if isinstance(c, str)]
    norm = {c: re.sub(r"\s+", "", c).upper() for c in cols}
    o2 = f"{order:02d}"
    o = f"{order}"
    t = tipo.upper()[0]

    patrones = [
        rf"^H_{o}_L{{phase}}$", rf"^H_{o2}_L{{phase}}$",
        rf"^{t}H_{o}_L{{phase}}$", rf"^{t}H_{o2}_L{{phase}}$",
        rf"^H_{o}_{t}_L{{phase}}$", rf"^H_{o2}_{t}_L{{phase}}$",
        rf"^{t}_H{o}_L{{phase}}$", rf"^{t}_H{o2}_L{{phase}}$",
    ]

    out = []
    for fase in ("L1", "L2", "L3"):
        encontrada = None
        for pat in patrones:
            regex = re.compile(pat.format(phase=fase))
            for orig, normed in norm.items():
                if regex.fullmatch(normed):
                    encontrada = orig
                    break
            if encontrada:
                break
        if encontrada:
            out.append(encontrada)
    return out

# =====================================================================
# LAYOUT PRINCIPAL DE PESTAÑAS — Improve Sankey Dashboard (HUD)
# =====================================================================

import streamlit as st

# ====== Configuración base de página ======

st.set_page_config(
    page_title="Improve Sankey — Sistema de Monitorización",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====== Header del Dashboard ======
st.markdown("""
    <h1 style="text-align:center; color:#3cf57a; text-shadow:0 0 15px #3cf57a;">
         Improve Sankey — Sistema de Monitorización
    </h1>
    <p style="text-align:center; color:rgba(255,255,255,0.7); margin-top:-10px;">
        Datos reales • MODBUS TCP / MQTT • Histórico • Alarmas
    </p>
    <hr style="opacity:0.2;">
""", unsafe_allow_html=True)


tabs = st.tabs([
    "🧭 Monitorización en Tiempo Real",
    "🧩 Estado del Sistema",
    "⚙️ APF & SVG"
])


import uuid

def K(ns: str, name: str, unique: bool=False) -> str:
    """
    ns: namespace/pestaña; p.ej. 'mon', 'est', 'apf'
    name: nombre corto del elemento
    unique=True añade sufijo aleatorio (para gráficos que se regeneran)
    """
    return f"{ns}_{name}" if not unique else f"{ns}_{name}_{uuid.uuid4().hex[:6]}"

# ============== TAB 1: MONITORIZACIÓN (HUD futurista) =========================
def render_tab_monitorizacion(df: pd.DataFrame | None = None, simulate: bool = True):
    st.markdown('<div class="hud-title"> Monitorización en Tiempo Real</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-sub"> </div>', unsafe_allow_html=True)
    hud_css()
    enable_energy_bg()
    enable_particles_bg()
    

    # Toggle Simulación / Real
    simulate = st.toggle("Simulación", value=simulate, help="Desactívalo cuando tengas columnas reales mapeadas.")

    if simulate or df is None or not set(REQUIRED_COLS).issubset(df.columns):
        df = simulate_df(minutes=35, freq_s=5)
    else:
        df = df.copy()
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts")

    # ---------- LAYOUT HUD ----------
    # Tensiones F-N
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> Tensiones F-N</div>', unsafe_allow_html=True)
    line_hud(df, ["V_L1N","V_L2N","V_L3N"], " ", "V", [IS_GREEN, IS_CYAN, IS_AMBER], key=K("mon","v_fn"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Tensiones F-F
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> Tensiones F-F</div>', unsafe_allow_html=True)
    line_hud(df, ["V_L1L2","V_L2L3","V_L3L1"], " ", "V", [IS_GREEN, IS_CYAN, IS_AMBER], key=K("mon","v_ff"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Corrientes (incl. Neutro)
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> Corrientes (incl. Neutro)</div>', unsafe_allow_html=True)
    line_hud(df, ["I_L1","I_L2","I_L3","I_N"], " ", "A", [IS_GREEN, IS_CYAN, IS_AMBER, "#7CF5E6"], key=K("mon","i_In"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Potencias P/Q/S
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> Potencias</div>', unsafe_allow_html=True)
    line_hud(df, ["P_kW","Q_kVAr","S_kVA"], " ", "kW / kVAr / kVA", [IS_GREEN, IS_AMBER, IS_CYAN], key=K("mon","pqs"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Factor de potencia
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> Factor de Potencia</div>', unsafe_allow_html=True)
    line_hud(df, ["PF"], "", "", [IS_GREEN], height=220, key=K("mon","pf"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Frecuencia
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> Frecuencia</div>', unsafe_allow_html=True)
    line_hud(df, ["Freq_Hz"], " ", "Hz", [IS_CYAN], height=220, key=K("mon","freq"))
    st.markdown('</div>', unsafe_allow_html=True)

    # THD V
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> THD Tensión</div>', unsafe_allow_html=True)
    line_hud(df, ["THD_V_%"], " ", "%", [IS_AMBER], height=220, key=K("mon","thdv"))
    st.markdown('</div>', unsafe_allow_html=True)

    # THD I
    st.markdown('<div class="hud-card">', unsafe_allow_html=True)
    st.markdown('<div class="hud-title"> THD Corriente</div>', unsafe_allow_html=True)
    line_hud(df, ["THD_I_%"], " ", "%", ["#FF6E6E"], height=220, key=K("mon","thdi"))
    st.markdown('</div>', unsafe_allow_html=True)

    # Espectros armónicos por orden (simulado por ahora)
    render_armonicos_por_orden(df=None, simulate=True)


def render_armonicos_por_orden(df: pd.DataFrame | None = None, simulate: bool = True):
    """
    Barras de armónicos 2..32: tensión (V_Hn_%) y corriente (I_Hn_%).
    """
    if (df is None) or ("ts" not in (df.columns if df is not None else [])) or simulate:
        dfh = _simulate_harmonics_df()
    else:
        dfh = df.copy()
        dfh["ts"] = pd.to_datetime(dfh["ts"], errors="coerce")
        dfh = dfh.dropna(subset=["ts"]).sort_values("ts")

    orders = list(range(2, 33))
    cols_v = [f"V_H{o}_%" for o in orders]
    cols_i = [f"I_H{o}_%" for o in orders]
    last_v = _last_series(dfh, cols_v)
    last_i = _last_series(dfh, cols_i)
    values_v = [last_v.get(c, 0.0) for c in cols_v]
    values_i = [last_i.get(c, 0.0) for c in cols_i]

    st.markdown('<div class="hud-title"> Armónicos por orden </div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        _bar_spectrum(orders, values_v, " THD — Tensión", unit="%", key="mon_spec_v")
    with c2:
        _bar_spectrum(orders, values_i, " THD — Corriente", unit="%", key="mon_spec_i")


# ================= TAB 2: ESTADO DEL SISTEMA (HUD) ============================
def render_tab_estado(df: Optional[pd.DataFrame] = None, simulate: bool = True):
    st.markdown('<div class="hud-title">Estado del sistema</div>', unsafe_allow_html=True)
    st.markdown('<div class="hud-sub"> </div>', unsafe_allow_html=True)
    
    # Si no hay DF, o para demo, creamos uno con las columnas básicas
    if df is None:
        import numpy as np
        now = pd.Timestamp.now()
        ts = pd.date_range(now - pd.Timedelta(minutes=30), now, freq="1min")
        df = pd.DataFrame({
            "ts": ts,
            "CORE_TEMP": 25 + np.random.randn(len(ts))*0.5,
            "R_TEMP": 26 + np.random.randn(len(ts))*0.5,
            "S_TEMP": 27 + np.random.randn(len(ts))*0.5,
            "T_TEMP": 25 + np.random.randn(len(ts))*0.5,
        })

    # Asegurar ts ordenado y crear flags binarios si faltan
    df = df.copy()
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts")

    # columnas binarias que usan los timelines
    needed_flags = [
        "Core_High_Temp_ALARM", "Thyristor_High_Temp_ALARM",
        "SETA", "Network_Status", "SC6006_Status",
        "R_Fuse_Status", "S_Fuse_Status", "T_Fuse_Status",
        "SEL0", "SEL1", "SEL2",
        "AIC", "AOC", "AIS",
        "Button", "Fan",
    ]
    for c in needed_flags:
        if c not in df.columns:
            # señal tranquila con algunos eventos (simulada)
            df[c] = (pd.Series(np.random.rand(len(df)) > 0.92, index=df.index)
                    .rolling(3, min_periods=1).max().astype(int))


    # ---- Tendencia de temperaturas
    import uuid
    line_trend(df, ["CORE_TEMP", "R_TEMP", "S_TEMP", "T_TEMP"],
                "Temperaturas", key=K("est","trend_temp", unique=True), height=260, unit="°C")


    # ---- Gauges semicirculares (Core + R,S,T)
    gcol = st.columns(4)
    labels = ["Core Temp", "Thyristor R Temp", "Thyristor S Temp", "Thyristor T Temp"]
    last_vals = [
        float(df["CORE_TEMP"].iloc[-1]),
        float(df["R_TEMP"].iloc[-1]),
        float(df["S_TEMP"].iloc[-1]),
        float(df["T_TEMP"].iloc[-1]),
    ]

    for i, col in enumerate(gcol):
        with col:
            gauge_semicircle(
                labels[i], last_vals[i],
                vmin=20, vwarn=55 if i>0 else 45, vmax=80,
                key=K("est", f"gtemp_{i}")
    ) 

    st.divider()

    st.markdown('<div class="hud-title"><span class="dot"></span> Alarmas y Estados</div>', unsafe_allow_html=True)

    # Core & Thyristor (dos filas)
    onoff_timeline(df,
                    ["Core_High_Temp_ALARM", "Thyristor_High_Temp_ALARM"],
                    "Core & Thyristor Alarms", height=160, key="seg_core")

    # Sistema (3 filas)
    onoff_timeline(df,
                    ["SETA", "Network_Status", "SC6006_Status"],
                    "Sistema", height=160, key="seg_sys")

    # Fusibles (3 filas)
    onoff_timeline(df,
                    ["R_Fuse_Status", "S_Fuse_Status", "T_Fuse_Status"],
                    "Fusibles", height=160, key="seg_fuse")

    # --- Ventiladores ---
    onoff_timeline(
        df,
        ["Fan"], # solo la señal de ventiladores
        "Ventiladores", # título
        height=150,
        key="tl_ventiladores"
    )

    # --- Conmutación ---
    onoff_timeline(
        df,
        ["Button"], # solo la señal de conmutación
        "Conmutación", # título
        height=150,
        key="tl_conmutacion"
    )

    # 🔆 Indicadores ATS estilo semáforo
    st.markdown("<hr style='margin:20px 0;opacity:0.2;'>", unsafe_allow_html=True)
    render_ats_lights(df)

def render_tab_apf_svg(df: pd.DataFrame):

    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    st.markdown('<div class="hud-title">  APF / SVG </div>', unsafe_allow_html=True)
    

    # ---------- 0) Utilidades ----------
    def _segments_from_binary(ts: pd.Series, y_row: float, on_color: str, off_color: str,
        on_label="On", off_label="Off"):
        """
        Convierte una serie binaria (0/1) en una lista de 'shapes' rectangulares para plotly,
        representando las bandas ON/OFF a lo largo del tiempo.
        """
        s = ts.astype(int)
        s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq=s.index.inferred_freq or "1min"))
        s = s.fillna(method="ffill").astype(int)

        changes = s.diff().fillna(0).ne(0)
        idxs = list(s.index[changes]) + [s.index[-1]]
        start = s.index[0]
        current = int(s.iloc[0])
        shapes, annots = [], []
        h = 0.74 # alto de cada banda (más fino = look pro)
        y0, y1 = y_row - h/2, y_row + h/2

        for t in idxs:
            color = on_color if current == 1 else off_color
            label = on_label if current == 1 else off_label
            shapes.append(dict(
                type="rect",
                xref="x", yref="y",
                x0=start, x1=t,
                y0=y0, y1=y1,
                line=dict(width=0),
                fillcolor=color,
                layer="below"
            ))
            # etiqueta tenue centrada
            annots.append(dict(
                x=start + (t-start)/2, y=y_row,
                xref="x", yref="y",
                text=label, showarrow=False,
                font=dict(size=12, color="rgba(255,255,255,0.55)")
            ))
            current = int(1-current) if t in s.index and changes.loc[t] else current
            start = t
        return shapes, annots

    def _figure_band(t_min, t_max, y_ticks, title):
        fig = go.Figure()
        fig.update_layout(
            title=dict(text=title, x=0.01, font=dict(size=16, color="#A8FFB7")),
            height=100 + 26*max(0, len(y_ticks)-1),
            margin=dict(l=70, r=20, t=40, b=35),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(range=[t_min, t_max], showgrid=True, gridcolor="rgba(120,255,120,0.06)",
                        zeroline=False, showline=False, tickfont=dict(color="#bfbfbf")),
            yaxis=dict(showgrid=False, zeroline=False, tickmode="array",
                        tickvals=[y for y,_ in y_ticks],
                        ticktext=[lbl for _,lbl in y_ticks],
                        tickfont=dict(color="#9BE29C")),
            showlegend=False
        )
        # marcador invisible para fijar los ejes
        fig.add_trace(go.Scatter(x=[t_min, t_max], y=[y_ticks[0][0], y_ticks[-1][0]],
                                    mode="markers", marker=dict(opacity=0)))
        return fig

    # ---------- 1) Datos de entrada / simulación segura ----------
    # Esperamos columnas:
    # - AUTO_MODE (0/1)
    # - RST10, RST20, ..., RST60 (0/1)
    # - RUN10, RUN20, ..., RUN60 (0/1)
    # Si faltan, generamos demo estable (no-ruidosa) para que SIEMPRE se vea algo.

    def _make_demo_index(n_hours=36):
        end = pd.Timestamp.now().floor("min")
        idx = pd.date_range(end - pd.Timedelta(hours=n_hours), end, freq="5min")
        return idx

    idx = df.index if isinstance(df.index, pd.DatetimeIndex) and len(df.index)>10 else _make_demo_index()

    def _demo_binary(idx, prob_on=0.5, min_chunk=6, max_chunk=24):
        # bandas largas tipo estados (no ruido)
        state = np.random.rand() < prob_on
        arr = []
        i = 0
        while i < len(idx):
            ln = np.random.randint(min_chunk, max_chunk+1)
            arr.extend([1 if state else 0] * min(ln, len(idx)-i))
            i += ln
            state = not state
        return pd.Series(arr, index=idx)

    df_band = pd.DataFrame(index=idx)
    
    # Auto/Manual
    if "AUTO_MODE" in df.columns:
        df_band["AUTO_MODE"] = df["AUTO_MODE"].reindex(idx).ffill().bfill().astype(int)
    else:
        df_band["AUTO_MODE"] = _demo_binary(idx, prob_on=0.7)

    # Resets
    rst_names = [f"RST{i}" for i in (10,20,30,40,50,60)]
    for name in rst_names:
        if name in df.columns:
            df_band[name] = df[name].reindex(idx).ffill().bfill().astype(int)
        else:
            df_band[name] = _demo_binary(idx, prob_on=0.1, min_chunk=18, max_chunk=48)

    # Run/Stop
    run_names = [f"RUN{i}" for i in (10,20,30,40,50,60)]
    for name in run_names:
        if name in df.columns:
            df_band[name] = df[name].reindex(idx).ffill().bfill().astype(int)
        else:
            df_band[name] = _demo_binary(idx, prob_on=0.4, min_chunk=10, max_chunk=30)

    # Paleta Improve Sankey (neón suave)
    C_BG = "rgba(0,0,0,0)" # fondo transparente
    C_GRID = "#8B0000"
    C_OK = "#01360A" # verde “Run / Auto”
    C_BAD = "#460101" # rojo “Stop”
    C_RST = "#022D5C" # azul “Reset”
    C_OFF = "#4E0101"

    # ---------- 2) Auto / Manual ----------
    st.markdown('<div class="hud-title"> Auto / Manual </div>', unsafe_allow_html=True)
    t0, t1 = df_band.index.min(), df_band.index.max()
    y_ticks = [(1.0, "Device State")]
    fig_auto = _figure_band(t0, t1, y_ticks, " ")

    shapes, annots = _segments_from_binary(df_band["AUTO_MODE"], 1.0, C_OK, C_OFF, " ", " ")
    fig_auto.update_layout(shapes=shapes, annotations=annots)
    st.plotly_chart(fig_auto, use_container_width=True)

    # ---------- 3) Device Reset ----------
    st.markdown('<div class="hud-title"> Device reset </div>', unsafe_allow_html=True)
    y_ticks = []
    fig_rst = _figure_band(t0, t1, [(i, "") for i in range(6)], " ")
    all_shapes, all_ann = [], []
    for row, name in enumerate(rst_names):
        y = 1 + row # 1..6
        y_ticks.append((y, name))
        sh, an = _segments_from_binary(df_band[name], y, C_RST, C_OFF, " ", " ")
        # Para “reset” mostramos azul solo cuando hay 1 y gris suave en 0 (sin texto en gris)
        for a in an:
            if df_band[name].max() == 0: # si nunca hay 1, evita spam
                a["text"] = ""
            else:
                # Solo rotulamos cuando está azul (valor=1). Tramo “Off” sin texto
                pass
        all_shapes += sh
        all_ann += [aa for aa in an if aa["text"]]

    fig_rst.update_layout(
        yaxis=dict(tickmode="array",
                    tickvals=[y for y,_ in y_ticks],
                    ticktext=[lbl for _,lbl in y_ticks],
                    tickfont=dict(color="#9BBFF9"))
    )
    fig_rst.update_layout(shapes=all_shapes, annotations=all_ann)
    st.plotly_chart(fig_rst, use_container_width=True)

    # ---------- 4) Run / Stop ----------
    st.markdown('<div class="hud-title"> Run / Stop</div>', unsafe_allow_html=True)
    y_ticks = []
    fig_run = _figure_band(t0, t1, [(i, "") for i in range(6)], " ")
    all_shapes, all_ann = [], []
    for row, name in enumerate(run_names):
        y = 1 + row
        y_ticks.append((y, name.replace("RUN", "Device ")))
        sh, an = _segments_from_binary(df_band[name], y, C_OK, C_BAD, " ", " ")
        all_shapes += sh
        all_ann += an

    fig_run.update_layout(
        yaxis=dict(tickmode="array",
                    tickvals=[y for y,_ in y_ticks],
                    ticktext=[lbl for _,lbl in y_ticks],
                    tickfont=dict(color="#A8FFB7"))
    )
    fig_run.update_layout(shapes=all_shapes, annotations=all_ann)
    st.plotly_chart(fig_run, use_container_width=True)
    # ===================== FIN APF / SVG =====================

# ================= Wiring de Pestañas (manteniendo tu Tab 1 tal cual) =========
with tabs[0]:
    render_tab_monitorizacion(df=None, simulate=True)

with tabs[1]:
    
    render_tab_estado(df=None, simulate=True)
    

with tabs[2]: # <-- el índice del tab "APF & SVG"
    render_tab_apf_svg(df) # <-- ESTA ES LA LLAMADA