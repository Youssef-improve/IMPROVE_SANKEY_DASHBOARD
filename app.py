from __future__ import annotations

# ============================================================
# 1. IMPORTS Y CONSTANTES BÁSICAS
# ============================================================
from pathlib import Path
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Carga .env opcional (para usuario/contraseña)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Rutas base
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite"
LOGO_PATH = ASSETS_DIR / "logo.png"

# Colores Improve Sankey
IS_BG = "#d15f13"
IS_PANEL = "#11161c"
IS_STROKE = "#1c2426"
IS_GREEN = "#39FF88"
IS_CYAN = "#47E3FF"
IS_AMBER = "#F5B400"
IS_RED = "#FF4D5A"
IS_TEXT = "#E0F2E9"

import plotly.express as px

px.defaults.template = "plotly_dark"  # déjalo así, sin más cosas raras


# ============================================================
# 2. CONFIGURACIÓN DE PÁGINA + CSS GLOBAL
# ============================================================
st.set_page_config(
    page_title="Improve Sankey — Sistema de Monitorización",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

px.defaults.template = "plotly_dark"


# ===== TEMA "DASHBOARD TÉCNICO PRO" (mantiene verdes, quita neones) =====
PRO_TECH_CSS = """
<style>
/* Fondo general oscuro sobrio */
html, body, .stApp {
    background-color: #02040b !important;
    color: #e5e7eb;
}

/* Contenedor principal */
.block-container {
    max-width: 1300px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}

/* Título principal: sin glow, alineado a la izquierda */
h1 {
    text-align: left;
    color: #e5e7eb;
    text-shadow: none;
    letter-spacing: .04em;
    font-weight: 700;
}

/* Títulos HUD (mantiene el verde pero sin efectos gamer) */
.hud-title,
.hud-section-title {
    color: #a9ff9f !important;
    text-shadow: none !important;
    font-weight: 600;
    font-size: 18px;
    margin: 18px 0 10px;
}

/* Punto verde sencillo, sin glow */
.hud-title .dot,
.hud-section-title .dot {
    display:inline-block;
    width:8px;
    height:8px;
    border-radius:50%;
    margin-right:8px;
    background:#39ff88 !important;
    box-shadow:none !important;
}

/* Quitamos la rayita animada y cualquier pseudo-elemento decorativo */
.hud-title::after,
.hud-section-title::after {
    content:none !important;
}

/* Tarjetas HUD: fondo gris oscuro, borde limpio, sin brillos */
.card,
.hud-card {
    background:#050816 !important;
    border-radius:10px !important;
    border:1px solid #111827 !important;
    padding:12px 14px 10px;
    margin:10px 0 14px;
    box-shadow:0 1px 3px rgba(0,0,0,0.7) !important;
}

/* Apagar halos/auras de gauges y tarjetas */
.is-gauge-neon::before,
.is-gauge-neon::after,
.hud-card::before,
.hud-card::after {
    content:none !important;
}

/* El contenedor del gauge se queda como simple tarjeta */
.is-gauge-neon {
    margin: 4px 0 10px;
}

/* Quitar partículas / fondos animados si siguen por ahí */
.is-particles-holder,
.is-particles {
    display:none !important;
}

/* Sidebar técnico y sobrio */
[data-testid="stSidebar"] {
    background:#020617 !important;
    border-right:1px solid #0f172a !important;
    box-shadow:none !important;
}
[data-testid="stSidebar"] .block-container {
    padding-top:.6rem;
}

/* Tipografía en sidebar */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {
    color:#e5e7eb !important;
}

/* Expanders del sidebar */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border-radius:10px !important;
    border:1px solid #111827 !important;
    background:#020617 !important;
}

/* Tabs: oscuros, con verde sólido para el seleccionado */
.stTabs [data-baseweb="tab-list"] {
    gap:.25rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius:999px;
    padding:6px 14px;
    background:#020617;
    border:1px solid #111827;
    color:#9ca3af;
    font-size:.9rem;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background:#111827;
    border-color:#39ff88;
    color:#e5e7eb;
}

/* Métricas (st.metric) estilo panel técnico */
[data-testid="stMetric"] {
    background:#020617;
    border-radius:10px;
    border:1px solid #111827;
    padding:8px 10px;
}
[data-testid="stMetricLabel"] {
    color:#9ca3af;
    font-weight:500;
}
[data-testid="stMetricValue"] {
    color:#e5e7eb;
    font-weight:700;
    font-size:1.4rem;
}

/* Mensajes info/warning integrados en el tema */
.stAlert {
    border-radius:8px;
    border:1px solid #1f2937;
}

/* Plotly: que respete el fondo oscuro (ya usamos plotly_dark) */
.js-plotly-plot .plotly,
.js-plotly-plot .main-svg {
    background:transparent !important;
}
</style>
"""
st.markdown(PRO_TECH_CSS, unsafe_allow_html=True)


# ============================================================
# 3. SQLITE: CREAR TABLAS Y CONEXIÓN
# ============================================================


def ensure_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Medidas instantáneas
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS measurements (
        ts TEXT PRIMARY KEY,
        source TEXT,
        tag TEXT,

        -- Tensiones
        V_L1N REAL, V_L2N REAL, V_L3N REAL,
        V_L1L2 REAL, V_L2L3 REAL, V_L3L1 REAL,

        -- Corrientes
        I_L1 REAL, I_L2 REAL, I_L3 REAL, I_N REAL,

        -- Potencias totales
        P_kW REAL,      -- Activa
        Q_kVAr REAL,    -- Reactiva
        S_kVA REAL,     -- Aparente

        -- PF y frecuencia
        PF REAL,
        Freq_Hz REAL,

        -- THD global (SIN % en el nombre de columna)
        THD_V REAL,
        THD_I REAL
    );
    """
    )

    # Estados ON/OFF de máquina / APF / SVG
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS states (
        ts TEXT,
        maquina INTEGER,
        apf INTEGER,
        svg INTEGER
    );
    """
    )

    con.commit()
    con.close()

 

@st.cache_resource
def get_conn():
    ensure_db()
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# ============================================================
# 4. HELPERS DE DATOS Y GRÁFICAS
# ============================================================

def query_measurements(
    conn: sqlite3.Connection,
    t_from: datetime,
    t_to: datetime,
    source: str | None = None,
    tag: str | None = None,
) -> pd.DataFrame:
    q = "SELECT * FROM measurements WHERE ts BETWEEN ? AND ?"
    params: list = [t_from.isoformat(), t_to.isoformat()]

    # Detectar columnas opcionales
    cols_info = conn.execute("PRAGMA table_info(measurements)").fetchall()
    cols = [c[1] for c in cols_info]

    if source and "source" in cols:
        q += " AND source = ?"
        params.append(source)
    if tag and "tag" in cols:
        q += " AND tag = ?"
        params.append(tag)

    q += " ORDER BY ts ASC"
    df = pd.read_sql_query(q, conn, params=params)

    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts")

    return df


def read_last_samples(conn: sqlite3.Connection, limit: int = 100) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT * FROM measurements ORDER BY ts DESC LIMIT ?",
        conn,
        params=[limit],
    )
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts")
    return df


def query_states(conn: sqlite3.Connection, t_from: datetime, t_to: datetime) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT * FROM states WHERE ts BETWEEN ? AND ? ORDER BY ts ASC",
        conn,
        params=[t_from.isoformat(), t_to.isoformat()],
    )
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df = df.dropna(subset=["ts"]).sort_values("ts")
    return df


def ensure_time(df: Optional[pd.DataFrame], minutes: int = 30, freq: str = "min") -> pd.DataFrame:
    """Asegura un eje temporal razonable aunque el df esté vacío."""
    if df is None or "ts" not in df.columns or df["ts"].isna().all():
        base = pd.DataFrame({"ts": pd.date_range(end=pd.Timestamp.now(), periods=minutes, freq=freq)})
        return base
    out = df.copy()
    out["ts"] = pd.to_datetime(out["ts"], errors="coerce")
    out = out.dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
    return out


import pandas as pd
import streamlit as st

def _last_numeric(df: pd.DataFrame, col: str):
    """Devuelve el último valor numérico válido de una columna."""
    if col not in df.columns or df.empty:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return None
    return float(s.iloc[-1])

def mini_metrics_row(df: pd.DataFrame, cols: list[str], unit: str = "", title: str | None = None):
    """
    Pinta una fila de mini-métricas (st.metric) con los últimos valores de cada columna.
    Ej: mini_metrics_row(df, ["V_L1N","V_L2N","V_L3N"], "V", "Tensiones F-N (última muestra)")
    """
    if df is None or df.empty:
        return

    if title:
        st.markdown(f"**{title}**")

    c = st.columns(len(cols))
    for i, col in enumerate(cols):
        val = _last_numeric(df, col)
        etiqueta = col.replace("_", " ")
        if val is None:
            c[i].metric(etiqueta, "–")
        else:
            if unit:
                c[i].metric(etiqueta, f"{val:0.2f} {unit}")
            else:
                c[i].metric(etiqueta, f"{val:0.2f}")


def line_hud(df, cols, unit="", colors=None, title_text="", height=260):
    """Líneas de tendencia para señales eléctricas (sin etiquetas a la derecha)."""
    if df is None or df.empty:
        st.write("Sin datos todavía…")
        return

    # Paleta por defecto si no se pasan colores
    if colors is None:
        default_palette = [IS_GREEN, IS_CYAN, IS_AMBER, "#7CF5E6", "#F5B400"]
        colors = [default_palette[i % len(default_palette)] for i in range(len(cols))]

    # Aseguramos ts como datetime
    if "ts" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["ts"]):
        df = df.copy()
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    df = df.dropna(subset=["ts"]).sort_values("ts")

    fig = go.Figure()
    cols_ok = [c for c in cols if c in df.columns]

    for i, col in enumerate(cols_ok):
        serie = pd.to_numeric(df[col], errors="coerce")

        fig.add_trace(
            go.Scatter(
                x=df["ts"],
                y=serie,
                mode="lines",
                name=col,
                line=dict(width=2, color=colors[i % len(colors)]),
                line_shape="spline",
                hovertemplate=(
                    "<b>%{y:.2f} " + unit + "</b><br>" +
                    "%{x|%Y-%m-%d %H:%M:%S}<br>" +
                    "<span style='font-size:11px;color:#9ca3af;'>" + col + "</span>"
                    "<extra></extra>"
                ),
            )
        )

    # Auto-escala Y
    if cols_ok:
        num_df = df[cols_ok].select_dtypes(include="number")
        if not num_df.empty:
            y_min = num_df.min().min()
            y_max = num_df.max().max()
            if pd.notna(y_min) and pd.notna(y_max) and y_min != y_max:
                margen = (y_max - y_min) * 0.1
                fig.update_yaxes(range=[y_min - margen, y_max + margen])

    fig.update_layout(
        height=height,
        template="plotly_dark",
        margin=dict(l=30, r=20, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis_title="Tiempo",
        yaxis_title=unit,
        title=dict(
            text=title_text,
            x=0.01,
            font=dict(size=15, color=IS_GREEN),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")

    st.plotly_chart(fig, use_container_width=True)


def render_chart_with_values(df, cols, unit, colors, title_text):
    """Renderiza una gráfica con sus valores a la derecha, fuera del gráfico."""
    
    col_chart, col_vals = st.columns([0.80, 0.20])  # 80% gráfico, 20% valores

    with col_chart:
        line_hud(df, cols, unit, colors, title_text=title_text)

    with col_vals:
        st.markdown(
            f"<div style='font-size:14px;color:#9ca3af;font-weight:600;margin-bottom:6px;'>{title_text}</div>",
            unsafe_allow_html=True
        )

        for i, col in enumerate(cols):
            val = _last_numeric(df, col)
            if val is None:
                continue

            st.markdown(
                f"""
                <div style="
                    margin-bottom:6px;
                    padding:6px 8px;
                    background-color:rgba(0,0,0,0.25);
                    border-left:3px solid {colors[i % len(colors)]};
                    border-radius:6px;
                    font-size:13px;
                    color:#e5e7eb;">
                    <b>{col}</b><br>
                    {val:.2f} {unit}
                </div>
                """,
                unsafe_allow_html=True
            )


def gauge_semicircle(
    title: str,
    value: float,
    vmin: float,
    vwarn: float,
    vmax: float,
    suffix: str = "",
    key: Optional[str] = None,
):
    """Gauge semicircular con halo neón."""
    val = float(value) if value is not None and np.isfinite(value) else 0.0

    steps = [
        {"range": [vmin, vmax], "color": "rgba(92,255,122,0.10)", "thickness": 0.4},
        {"range": [vmin, vwarn * 0.95], "color": "rgba(92,255,122,0.35)", "thickness": 0.4},
        {"range": [vwarn * 0.95, vwarn * 1.05], "color": "rgba(245,180,0,0.55)", "thickness": 0.4},
        {"range": [vwarn * 1.05, vmax], "color": "rgba(255,77,90,0.55)", "thickness": 0.4},
    ]

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=val,
            number={"suffix": f" {suffix}", "font": {"color": IS_TEXT, "size": 28}},
            title={"text": f"<b style='color:{IS_GREEN};font-size:13px'>{title}</b>"},
            gauge={
                "shape": "angular",
                "axis": {"range": [vmin, vmax], "tickcolor": "#3b4648", "tickwidth": 1, "ticklen": 4},
                "bar": {"color": IS_CYAN, "thickness": 0.2},
                "bgcolor": "rgba(0,0,0,0)",
                "bordercolor": "rgba(0,0,0,0)",
                "steps": steps,
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=6, r=6, t=34, b=0),
        height=180,
    )

    st.markdown('<div class="is-gauge-neon">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, key=key)
    st.markdown("</div>", unsafe_allow_html=True)


def _flag_bool(v) -> bool:
    """Normaliza valores tipo 1/0, 'ON'/'OFF', True/False a bool."""
    try:
        if isinstance(v, str):
            s = v.strip().upper()
            if s in ("ON", "RUN", "TRUE", "ENCENDIDO", "1"):
                return True
            if s in ("OFF", "STOP", "FALSE", "APAGADO", "0"):
                return False
        return bool(int(v))
    except Exception:
        return False


def ats_status_from_df(df: pd.DataFrame, aliases: list[str]) -> Optional[bool]:
    """Devuelve último valor de la primera columna encontrada en df según alias."""
    for c in aliases:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            if len(s):
                return _flag_bool(s.iloc[-1])
            return None
    return None


def render_ats_lights(df: Optional[pd.DataFrame] = None):
    """Dibuja 3 ATS con leds y barra. Si no hay datos, usa simulación en sesión."""
    _df = df if isinstance(df, pd.DataFrame) and not df.empty else pd.DataFrame()

    a1 = ats_status_from_df(_df, ["ATS1", "ATS_1", "A1", "ATS_SUP", "ATS_TOP"])
    a2 = ats_status_from_df(_df, ["ATS2", "ATS_2", "A2", "ATS_MID", "ATS_MEDIO"])
    a3 = ats_status_from_df(_df, ["ATS3", "ATS_3", "A3", "ATS_BOT", "ATS_ABAJO"])

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


def _build_onoff_segments(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    """Convierte columnas binarias en segmentos Start/Finish/State/Signal."""
    out = []
    if df is None or df.empty or "ts" not in df.columns:
        return pd.DataFrame()

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
                out.append(
                    {
                        "Signal": c,
                        "Start": last_t,
                        "Finish": ts.iloc[k],
                        "State": "On" if last_val == 1 else "Off",
                    }
                )
                last_val = s.iloc[k]
                last_t = ts.iloc[k]

        # cierre hasta el último ts
        out.append(
            {
                "Signal": c,
                "Start": last_t,
                "Finish": ts.iloc[-1],
                "State": "On" if last_val == 1 else "Off",
            }
        )
    return pd.DataFrame(out)


def onoff_timeline(df: pd.DataFrame, cols: List[str], title: str, height: int = 170, key: Optional[str] = None):
    """Timeline ON/OFF tipo Grafana."""
    seg = _build_onoff_segments(df, cols)
    if seg.empty:
        st.info(f"No hay datos para “{title}”.")
        return

    colmap = {"On": "#026D2D", "Off": "#64010B"}

    fig = px.timeline(
        seg,
        x_start="Start",
        x_end="Finish",
        y="Signal",
        color="State",
        color_discrete_map=colmap,
        template="plotly_dark",
    )
    fig.update_traces(marker=dict(line=dict(width=1)), width=0.3)
    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        marker_line_width=0,
        opacity=0.96,
        hovertemplate="<b>%{y}</b><br>%{x|%H:%M:%S} → %{x_end|%H:%M:%S}<br>%{text}<extra></extra>",
    )

    fig.update_layout(
        title=dict(
            text=f"<b style='color:{IS_TEXT};font-size:12px;text-shadow:0 0 6px #00FF88AA'>{title}</b>",
            x=0.01,
            y=0.98,
        ),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=28, b=18),
        showlegend=False,
    )

    fig.update_yaxes(
        autorange="reversed",
        color="#8ea39a",
        showgrid=False,
        zeroline=False,
        title_text="",
    )
    fig.update_xaxes(
        title_text="Tiempo",
        color="#035f14",
        showgrid=True,
        gridcolor="rgba(255,255,255,0.08)",
        zeroline=False,
    )

    st.plotly_chart(fig, use_container_width=True, key=key)


# -------- Armónicos (simulados) --------

def _simulate_harmonics_df(minutes: int = 10, freq_s: int = 5) -> pd.DataFrame:
    n = int((minutes * 60) // freq_s)
    t0 = pd.Timestamp.now() - pd.Timedelta(minutes=minutes)
    ts = pd.date_range(t0, periods=n, freq=f"{freq_s}s")
    rng = np.random.default_rng(7)
    base_v, base_i = 3.0, 6.0
    data = {"ts": ts}
    for k in range(2, 33):
        data[f"V_H{k}_%"] = np.clip(base_v / k + rng.normal(0, 0.05, size=n), 0, None)
        data[f"I_H{k}_%"] = np.clip(base_i / k + rng.normal(0, 0.08, size=n), 0, None)
    return pd.DataFrame(data)


def _last_series(df: pd.DataFrame, cols: List[str]) -> dict[str, float]:
    out = {}
    for c in cols:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce").dropna()
            out[c] = float(s.iloc[-1]) if len(s) else 0.0
        else:
            out[c] = 0.0
    return out


def _bar_spectrum(orders: List[int], values: List[float], title: str, unit="%", key: Optional[str] = None):
    fig = go.Figure(
        go.Bar(
            x=orders,
            y=values,
            marker=dict(color=IS_GREEN),
            hovertemplate="Orden %{x}º<br><b>%{y:.2f}" + unit + "</b><extra></extra>",
        )
    )
    fig.update_layout(
        height=260,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=30, b=30),
        paper_bgcolor=IS_BG,
        plot_bgcolor=IS_BG,
        title=dict(text=f"<b style='color:{IS_GREEN}'>{title}</b>", x=0.02),
        xaxis=dict(title="Orden armónico", tickmode="linear", dtick=2, gridcolor="rgba(255,255,255,0.08)"),
        yaxis=dict(title=unit, gridcolor="rgba(255,255,255,0.08)"),
    )
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_armonicos_por_orden():
    dfh = _simulate_harmonics_df()
    orders = list(range(2, 33))
    cols_v = [f"V_H{o}_%" for o in orders]
    cols_i = [f"I_H{o}_%" for o in orders]
    last_v = _last_series(dfh, cols_v)
    last_i = _last_series(dfh, cols_i)
    values_v = [last_v.get(c, 0.0) for c in cols_v]
    values_i = [last_i.get(c, 0.0) for c in cols_i]

    st.markdown('<div class="hud-title"><span class="dot"></span> Armónicos por orden</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        _bar_spectrum(orders, values_v, "THD — Tensión", unit="%", key="spec_v")
    with c2:
        _bar_spectrum(orders, values_i, "THD — Corriente", unit="%", key="spec_i")


# ============================================================
# 5. LOGIN SENCILLO
# ============================================================

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

# ============================================================
# 6. SIDEBAR: ESTADO, CONFIGURACIÓN, INFO
# ============================================================
conn = get_conn()

with st.sidebar:
    # Header
    st.markdown(
        """
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
          background: radial-gradient(circle at 30% 30%, #6bffb5, #39FF88);
          box-shadow:0 0 10px #39FF88, 0 0 22px rgba(57,255,136,.75);
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
            color:#39FF88;
            text-shadow:0 0 12px rgba(57,255,136,0.9);
            display:flex;
            align-items:center;
            gap:6px;
          ">
            <span>●</span>
            <span>Activo</span>
          </div>
        </div>
        <div style="text-align:right; font-size:11px; color:rgba(180,210,200,0.65);">
          <div style="opacity:.8;">Última lectura</div>
          <div style="font-family:monospace; font-size:12px;"> </div>
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
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Configuración
    with st.expander("⚙️ Configuración", expanded=False):
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

    st.session_state["rng"] = rng
    st.session_state["refresh_mode"] = refresh_mode

    # Información
    with st.expander("ℹ️ Información", expanded=True):
        st.write("Hora actual:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        st.write("Equipo:", "CIE PEMSA CELAYA TR2")
        st.write("Versión:", "v1.0.1")

# ============================================================
# 7. CÁLCULO DE RANGO Y CARGA DE DATOS
# ============================================================

now = datetime.now()
rng = st.session_state.get("rng", "Últimos 15 min")

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
    t_from, t_to = now - timedelta(hours=1), now

# Fuente/Tag opcionales (por ahora fijos; puedes añadir selectbox en sidebar si quieres)
df = query_measurements(conn, t_from, t_to, source=None, tag=None)
df_states = query_states(conn, t_from, t_to)

# ============================================================
# 8. HEADER PRINCIPAL
# ============================================================
st.markdown(
    """
<h1 style="text-align:center; color:#3cf57a; text-shadow:0 0 15px #3cf57a;">
    Improve Sankey — Sistema de Monitorización
</h1>
<p style="text-align:center; color:rgba(255,255,255,0.7); margin-top:-10px;">
    Datos reales • MODBUS TCP / MQTT • Histórico • Alarmas
</p>
<hr style="opacity:0;">
""",
    unsafe_allow_html=True,
)

# ============================================================
# 9. TABS PRINCIPALES
# ============================================================
tabs = st.tabs(
    [
        "🧭 Monitorización en Tiempo Real",
        "🧩 Estado del Sistema",
        "⚙️ APF & SVG",
    ]
)

# -------- TAB 1: MONITORIZACIÓN ---------------------------------

from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# --- Datos simulados para DISEÑO ---
ts = pd.date_range(datetime.now() - timedelta(minutes=30), periods=180, freq="10s")

df = pd.DataFrame({
    "ts": ts,
    "V_L1N": 230 + np.random.normal(0, 1, len(ts)),
    "V_L2N": 230 + np.random.normal(0, 1, len(ts)),
    "V_L3N": 230 + np.random.normal(0, 1, len(ts)),
    "V_L1L2": 400 + np.random.normal(0, 2, len(ts)),
    "V_L2L3": 400 + np.random.normal(0, 2, len(ts)),
    "V_L3L1": 400 + np.random.normal(0, 2, len(ts)),
    "I_L1": 120 + np.random.normal(0, 3, len(ts)),
    "I_L2": 115 + np.random.normal(0, 3, len(ts)),
    "I_L3": 130 + np.random.normal(0, 3, len(ts)),
    "I_N": np.random.uniform(0, 10, len(ts)),
    "P_kW": 150 + np.random.normal(0, 5, len(ts)),
    "Q_kVAr": 35 + np.random.normal(0, 3, len(ts)),
    "S_kVA": 180 + np.random.normal(0, 5, len(ts)),
    "PF": np.random.uniform(0.85, 0.99, len(ts)),
    "Freq_Hz": 50 + np.random.normal(0, 0.05, len(ts)),
    "THD_V_%": np.random.uniform(1, 5, len(ts)),
    "THD_I_%": np.random.uniform(3, 10, len(ts)),
})


with tabs[0]:
    st.markdown('<div class="hud-title"><span class="dot"></span> Monitorización en Tiempo Real</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("No hay datos todavía en la base de datos (tabla measurements).")
    else:
        # 🔹 Tensiones F-N
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["V_L1N", "V_L2N", "V_L3N"],
            "V",
            [IS_GREEN, IS_CYAN, IS_AMBER],
            "Tensiones F-N"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 Tensiones F-F
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["V_L1L2", "V_L2L3", "V_L3L1"],
            "V",
            [IS_GREEN, IS_CYAN, IS_AMBER],
            "Tensiones F-F"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 Corrientes (incl. neutro)
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["I_L1", "I_L2", "I_L3", "I_N"],
            "A",
            [IS_GREEN, IS_CYAN, IS_AMBER, "#7CF5E6"],
            "Corrientes (incl. Neutro)"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 Potencia activa (kW)
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["P_kW"],
            "kW",
            [IS_GREEN],
            "Potencia activa (kW)"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 Potencias P / Q / S
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["P_kW", "Q_kVAr", "S_kVA"],
            "kW / kVAr / kVA",
            [IS_GREEN, IS_AMBER, IS_CYAN],
            "Potencias"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 Factor de potencia
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["PF"],
            "",
            [IS_GREEN],
            "Factor de potencia"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 Frecuencia
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["Freq_Hz"],
            "Hz",
            [IS_CYAN],
            "Frecuencia"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 THD tensión
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["THD_V_%"],   # si en tu tabla se llama THD_V_% cambia aquí el nombre
            "%",
            [IS_AMBER],
            "THD Tensión"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # 🔹 THD corriente
        st.markdown('<div class="hud-card">', unsafe_allow_html=True)
        render_chart_with_values(
            df,
            ["THD_I_%"],   # si en tu tabla se llama THD_V_% cambia aquí el nombre
            "%",
            ["#FF6E6E"],
            "THD Corriente"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Espectro armónico (simulado)
    render_armonicos_por_orden()

# -------- TAB 2: ESTADO DEL SISTEMA -----------------------------
with tabs[1]:
    st.markdown('<div class="hud-title"><span class="dot"></span> Estado del Sistema</div>', unsafe_allow_html=True)

    # Temperaturas (simuladas si no existen)
    if df.empty or "CORE_TEMP" not in df.columns:
        # Demo de 30 min de temperaturas
        ts = pd.date_range(datetime.now() - timedelta(minutes=30), datetime.now(), freq="1min")
        rng = np.random.default_rng(0)
        df_temp = pd.DataFrame(
            {
                "ts": ts,
                "CORE_TEMP": 25 + rng.normal(0, 0.3, size=len(ts)),
                "R_TEMP": 26 + rng.normal(0, 0.3, size=len(ts)),
                "S_TEMP": 27 + rng.normal(0, 0.3, size=len(ts)),
                "T_TEMP": 25 + rng.normal(0, 0.3, size=len(ts)),
            }
        )
    else:
        df_temp = df[["ts", "CORE_TEMP", "R_TEMP", "S_TEMP", "T_TEMP"]].copy()

    line_hud(df_temp, ["CORE_TEMP", "R_TEMP", "S_TEMP", "T_TEMP"], "°C", title_text="Temperaturas")

    last_row = df_temp.dropna().iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        gauge_semicircle("Core Temp", last_row["CORE_TEMP"], 20, 45, 80, "°C", key="g_core")
    with c2:
        gauge_semicircle("Thy R Temp", last_row["R_TEMP"], 20, 55, 80, "°C", key="g_r")
    with c3:
        gauge_semicircle("Thy S Temp", last_row["S_TEMP"], 20, 55, 80, "°C", key="g_s")
    with c4:
        gauge_semicircle("Thy T Temp", last_row["T_TEMP"], 20, 55, 80, "°C", key="g_t")

    st.markdown("---")

    # Timeline de máquina / APF / SVG usando tabla states (si hay datos)
    if df_states.empty:
        st.info("No hay datos en la tabla 'states' para mostrar los estados de máquina/APF/SVG.")
    else:
        onoff_timeline(df_states, ["maquina", "apf", "svg"], "Estados máquina / APF / SVG")

    st.markdown("---")

    # ATS
    st.markdown("### ATS")
    render_ats_lights(df)

# -------- TAB 3: APF & SVG --------------------------------------
with tabs[2]:
    st.markdown('<div class="hud-title"><span class="dot"></span> APF & SVG</div>', unsafe_allow_html=True)

    # Para esta pestaña, por ahora hacemos demo de bandas (Auto/Manual, Reset, Run/Stop)
    # sobre un índice temporal fabricado.

    idx = pd.date_range(datetime.now() - timedelta(hours=24), datetime.now(), freq="5min")

    def demo_binary(idx_, prob_on=0.5, min_chunk=6, max_chunk=24):
        rng = np.random.default_rng(42)
        state = rng.random() < prob_on
        arr = []
        i = 0
        while i < len(idx_):
            ln = rng.integers(min_chunk, max_chunk + 1)
            arr.extend([1 if state else 0] * min(ln, len(idx_) - i))
            i += ln
            state = not state
        return pd.Series(arr, index=idx_)

    df_band = pd.DataFrame(index=idx)
    df_band["AUTO_MODE"] = demo_binary(idx, prob_on=0.7)
    rst_names = [f"RST{i}" for i in (10, 20, 30, 40, 50, 60)]
    run_names = [f"RUN{i}" for i in (10, 20, 30, 40, 50, 60)]

    for name in rst_names:
        df_band[name] = demo_binary(idx, prob_on=0.1, min_chunk=18, max_chunk=48)
    for name in run_names:
        df_band[name] = demo_binary(idx, prob_on=0.4, min_chunk=10, max_chunk=30)

    t0, t1 = df_band.index.min(), df_band.index.max()

    # Auto/Manual simple
    st.markdown("#### Auto / Manual")
    df_auto = pd.DataFrame({"ts": df_band.index, "AUTO_MODE": df_band["AUTO_MODE"].values})
    onoff_timeline(df_auto, ["AUTO_MODE"], "Auto / Manual", height=120, key="auto_manual")

    # Device Reset
    st.markdown("#### Device Reset")
    df_rst = df_band.reset_index().rename(columns={"index": "ts"})
    onoff_timeline(df_rst, rst_names, "Device Reset", height=220, key="rst_band")

    # Run / Stop
    st.markdown("#### Run / Stop")
    onoff_timeline(df_rst, run_names, "Run / Stop", height=220, key="run_band")
