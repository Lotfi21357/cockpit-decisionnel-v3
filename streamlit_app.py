# =========================================================
# 🛰️ COCKPIT DÉCISIONNEL BOURSIER - VERSION EXPERT STABLE
# Architecture robuste Streamlit + yFinance
# =========================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import warnings

warnings.filterwarnings("ignore")

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Cockpit Décisionnel Expert",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

PARIS_TZ = ZoneInfo("Europe/Paris")

# =========================================================
# CSS PREMIUM DARK MODE
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #0E1117;
}

.block-container {
    padding-top: 1.2rem;
}

.card {
    background: #161B22;
    border: 1px solid #2B313A;
    border-radius: 18px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}

.kpi-title {
    color: #9AA4AF;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.kpi-value {
    color: white;
    font-size: 2rem;
    font-weight: 700;
}

.phase-banner {
    padding: 1rem;
    border-radius: 14px;
    text-align: center;
    color: white;
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

.sell-alert {
    background: #4B1113;
    border: 1px solid #DC3545;
    color: white;
    padding: 1rem;
    border-radius: 12px;
    font-weight: 700;
    margin-top: 0.8rem;
}

.success-alert {
    background: #0E3B2C;
    border: 1px solid #198754;
    color: white;
    padding: 1rem;
    border-radius: 12px;
    font-weight: 700;
    margin-top: 0.8rem;
}

.small-muted {
    color: #9AA4AF;
    font-size: 0.85rem;
}

.metric-green {
    color: #00D26A;
}

.metric-red {
    color: #FF5B5B;
}

hr {
    border-color: #2B313A;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# PORTFOLIO CONFIG
# =========================================================

POSITIONS_BASE = [
    {
        "nom": "MSCI World AV",
        "ticker": "MWRD.PA",
        "parts": 36.33,
        "prm": 140.41,
        "enveloppe": "AV",
        "type": "core"
    },

    {
        "nom": "MSCI World PEA",
        "ticker": "DCAM.PA",
        "parts": 481.0,
        "prm": 5.5937,
        "enveloppe": "PEA",
        "type": "core"
    },

    {
        "nom": "Global Hydrogen",
        "ticker": "ANRJ.PA",
        "parts": 4.7701,
        "prm": 707.55,
        "enveloppe": "AV",
        "type": "satellite"
    },

    {
        "nom": "EM Asia",
        "ticker": "AASI.PA",
        "parts": 40.8272,
        "prm": 49.96,
        "enveloppe": "AV",
        "type": "satellite"
    },

    {
        "nom": "Or Physique",
        "ticker": "CGLD.PA",
        "parts": 4.5902,
        "prm": 163.39,
        "enveloppe": "AV",
        "type": "gold"
    }
]

PROXIES = {
    "ANRJ.PA": ["PLUG", "BE", "NEL.OL"],
    "AASI.PA": ["TSM", "005930.KS"]
}

MACRO = [
    "NQ=F",
    "ES=F",
    "^TNX",
    "GC=F",
    "BZ=F",
    "EURUSD=X"
]

BENCHMARK = "MWRD.PA"

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("⚙️ Paramètres")

capital_investi = st.sidebar.number_input(
    "Capital investi (€)",
    value=13956.49,
    step=100.0
)

bonus_fortuneo = st.sidebar.number_input(
    "Bonus Fortuneo (€)",
    value=160.0,
    step=10.0
)

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Positions")

POSITIONS = []

for pos in POSITIONS_BASE:

    parts = st.sidebar.number_input(
        f"Parts - {pos['nom']}",
        value=float(pos["parts"]),
        step=0.0001,
        key=f"parts_{pos['nom']}"
    )

    prm = st.sidebar.number_input(
        f"PRM - {pos['nom']}",
        value=float(pos["prm"]),
        step=0.0001,
        key=f"prm_{pos['nom']}"
    )

    new_pos = pos.copy()
    new_pos["parts"] = parts
    new_pos["prm"] = prm

    POSITIONS.append(new_pos)

# Ajustement bonus sur MSCI World PEA
for pos in POSITIONS:
    if pos["nom"] == "MSCI World PEA":
        pos["prm"] = pos["prm"] - (bonus_fortuneo / pos["parts"])

# =========================================================
# ROBUST DATA ENGINE
# =========================================================

def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Corrige définitivement les problèmes MultiIndex yfinance.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # MultiIndex => flatten
    if isinstance(df.columns, pd.MultiIndex):

        new_cols = []

        for col in df.columns:

            if isinstance(col, tuple):
                clean = str(col[0])
            else:
                clean = str(col)

            new_cols.append(clean)

        df.columns = new_cols

    # Colonnes dupliquées
    df = df.loc[:, ~df.columns.duplicated()]

    # Standardisation
    expected = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

    for col in expected:
        if col not in df.columns:
            df[col] = np.nan

    return df


@st.cache_data(ttl=300, show_spinner=False)
def download_market_data(tickers, period="1y"):

    data_dict = {}

    for ticker in tickers:

        try:

            raw = yf.download(
                ticker,
                period=period,
                auto_adjust=False,
                progress=False,
                threads=False
            )

            raw = flatten_columns(raw)

            if raw.empty:
                continue

            # Conversion sécurisée
            for col in raw.columns:
                raw[col] = pd.to_numeric(raw[col], errors="coerce")

            raw.dropna(how="all", inplace=True)

            if raw.empty:
                continue

            data_dict[ticker] = raw

        except Exception as e:
            print(f"Erreur téléchargement {ticker}: {e}")

    return data_dict


# =========================================================
# TECHNICAL INDICATORS
# =========================================================

def safe_series(df, column="Close"):

    if df is None or df.empty:
        return pd.Series(dtype=float)

    if column not in df.columns:
        return pd.Series(dtype=float)

    series = pd.to_numeric(df[column], errors="coerce")

    return series.dropna()


def last_value(series):

    if series is None:
        return None

    if len(series) == 0:
        return None

    return float(series.iloc[-1])


def sma(series, window):

    if len(series) < window:
        return pd.Series(dtype=float)

    return series.rolling(window).mean()


def rsi(series, period=14):

    if len(series) < period + 1:
        return pd.Series(dtype=float)

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss

    rsi_calc = 100 - (100 / (1 + rs))

    return rsi_calc


# =========================================================
# LOAD DATA
# =========================================================

all_tickers = []

for pos in POSITIONS:
    all_tickers.append(pos["ticker"])

for arr in PROXIES.values():
    all_tickers.extend(arr)

all_tickers.extend(MACRO)

all_tickers = list(set(all_tickers))

market_data = download_market_data(all_tickers)

# =========================================================
# PORTFOLIO ENGINE
# =========================================================

portfolio_rows = []

valeur_totale = 0
investi_net = capital_investi - bonus_fortuneo

for pos in POSITIONS:

    ticker = pos["ticker"]

    if ticker not in market_data:
        continue

    df = market_data[ticker]

    close = safe_series(df)

    if close.empty:
        continue

    current_price = last_value(close)

    valeur = current_price * pos["parts"]

    perf_pct = ((current_price - pos["prm"]) / pos["prm"]) * 100

    gain_eur = valeur - (pos["parts"] * pos["prm"])

    sma20 = last_value(sma(close, 20))
    sma50 = last_value(sma(close, 50))
    rsi14 = last_value(rsi(close))

    portfolio_rows.append({
        "Nom": pos["nom"],
        "Ticker": ticker,
        "Type": pos["type"],
        "Prix": current_price,
        "Parts": pos["parts"],
        "PRM": pos["prm"],
        "Valeur": valeur,
        "Performance": perf_pct,
        "Gain €": gain_eur,
        "SMA20": sma20,
        "SMA50": sma50,
        "RSI": rsi14,
        "Enveloppe": pos["enveloppe"]
    })

    valeur_totale += valeur

portfolio_df = pd.DataFrame(portfolio_rows)

gain_total = valeur_totale - investi_net
performance_totale = (gain_total / investi_net) * 100

# =========================================================
# BENCHMARK
# =========================================================

benchmark_perf = 0
gap_vs_world = 0

if BENCHMARK in market_data:

    bench_close = safe_series(market_data[BENCHMARK])

    if len(bench_close) > 60:

        start_price = bench_close.iloc[0]
        end_price = bench_close.iloc[-1]

        benchmark_perf = ((end_price / start_price) - 1) * 100

        gap_vs_world = performance_totale - benchmark_perf

# =========================================================
# PHASE ENGINE
# =========================================================

phase_text = ""
phase_color = "#198754"

if gap_vs_world < 0:

    phase_text = "PHASE 1 · RECONQUÊTE"
    phase_color = "#DC3545"

else:

    satellite_warning = False

    for _, row in portfolio_df.iterrows():

        if row["Type"] == "satellite":

            if row["Prix"] < row["SMA20"]:
                satellite_warning = True

    if satellite_warning:

        phase_text = "PHASE 3 · ROTATION"
        phase_color = "#FD7E14"

    else:

        phase_text = "PHASE 2 · ALPHA"
        phase_color = "#198754"

# =========================================================
# HEADER
# =========================================================

now = datetime.now(PARIS_TZ)

st.title("🛰️ Cockpit Décisionnel Expert")

st.caption(
    f"Temps réel • {now.strftime('%d/%m/%Y %H:%M')} • Europe/Paris"
)

st.markdown(
    f"""
    <div class="phase-banner" style="background:{phase_color};">
        {phase_text}
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# KPI SECTION
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">Valeur Totale</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="kpi-value">{valeur_totale:,.2f}€</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

with col2:

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">Gain Net</div>',
        unsafe_allow_html=True
    )

    color = "metric-green" if gain_total >= 0 else "metric-red"

    st.markdown(
        f'<div class="kpi-value {color}">{gain_total:+,.2f}€</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

with col3:

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">Performance</div>',
        unsafe_allow_html=True
    )

    color = "metric-green" if performance_totale >= 0 else "metric-red"

    st.markdown(
        f'<div class="kpi-value {color}">{performance_totale:+.2f}%</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

with col4:

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">Gap vs MSCI World</div>',
        unsafe_allow_html=True
    )

    color = "metric-green" if gap_vs_world >= 0 else "metric-red"

    st.markdown(
        f'<div class="kpi-value {color}">{gap_vs_world:+.2f}%</div>',
        unsafe_allow_html=True
    )

    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PORTFOLIO TABLE
# =========================================================

st.markdown("## 📦 Portefeuille")

display_df = portfolio_df.copy()

display_df["Prix"] = display_df["Prix"].map(lambda x: f"{x:.2f}€")
display_df["Valeur"] = display_df["Valeur"].map(lambda x: f"{x:,.2f}€")
display_df["Performance"] = display_df["Performance"].map(lambda x: f"{x:+.2f}%")
display_df["Gain €"] = display_df["Gain €"].map(lambda x: f"{x:+,.2f}€")

# IMPORTANT : 3 décimales sur World PEA
display_df["Parts"] = display_df.apply(
    lambda row:
        f"{row['Parts']:.3f}"
        if row["Nom"] == "MSCI World PEA"
        else f"{row['Parts']:.4f}",
    axis=1
)

st.dataframe(
    display_df[
        [
            "Nom",
            "Parts",
            "Prix",
            "PRM",
            "Valeur",
            "Performance",
            "RSI"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

# =========================================================
# DONUT CHART
# =========================================================

st.markdown("## 🍩 Allocation")

fig = px.pie(
    portfolio_df,
    values="Valeur",
    names="Nom",
    hole=0.55
)

fig.update_layout(
    paper_bgcolor="#161B22",
    font_color="white",
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# SATELLITE ENGINE
# =========================================================

st.markdown("## 🚨 Moteur Décisionnel Satellites")

for _, row in portfolio_df.iterrows():

    if row["Type"] != "satellite":
        continue

    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.subheader(row["Nom"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Prix", f"{row['Prix']:.2f}€")
    c2.metric("SMA20", f"{row['SMA20']:.2f}€")
    c3.metric("SMA50", f"{row['SMA50']:.2f}€")
    c4.metric("RSI", f"{row['RSI']:.1f}")

    sell_signal = False

    if row["Prix"] < row["SMA20"]:
        sell_signal = True

    if gap_vs_world > 5:
        sell_signal = True

    if sell_signal:

        sell_amount = row["Valeur"] * 0.25

        st.markdown(
            f"""
            <div class="sell-alert">
                🚨 VENDRE {sell_amount:,.2f}€ pour arbitrage vers MSCI World
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="success-alert">
                ✅ Maintien de position
            </div>
            """,
            unsafe_allow_html=True
        )

    # =========================
    # PROXIES
    # =========================

    st.markdown("### 🔎 Analyse des Proxies")

    proxies = PROXIES.get(row["Ticker"], [])

    proxy_rows = []

    for proxy in proxies:

        if proxy not in market_data:
            continue

        proxy_close = safe_series(market_data[proxy])

        if proxy_close.empty:
            continue

        proxy_price = last_value(proxy_close)
        proxy_sma20 = last_value(sma(proxy_close, 20))
        proxy_rsi = last_value(rsi(proxy_close))

        proxy_rows.append({
            "Proxy": proxy,
            "Prix": round(proxy_price, 2),
            "SMA20": round(proxy_sma20, 2),
            "RSI": round(proxy_rsi, 1)
        })

    if proxy_rows:

        st.dataframe(
            pd.DataFrame(proxy_rows),
            use_container_width=True,
            hide_index=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PERFORMANCE CHART
# =========================================================

st.markdown("## 📈 Évolution du Benchmark")

if BENCHMARK in market_data:

    benchmark_close = safe_series(market_data[BENCHMARK])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=benchmark_close.index,
            y=benchmark_close.values,
            mode="lines",
            name="MSCI World"
        )
    )

    fig.update_layout(
        paper_bgcolor="#161B22",
        plot_bgcolor="#161B22",
        font_color="white",
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# MACRO DASHBOARD
# =========================================================

st.markdown("## 🌍 Macro Dashboard")

macro_cols = st.columns(3)

for i, ticker in enumerate(MACRO):

    if ticker not in market_data:
        continue

    close = safe_series(market_data[ticker])

    if close.empty:
        continue

    current = last_value(close)

    prev = close.iloc[-2] if len(close) > 2 else current

    variation = ((current - prev) / prev) * 100

    with macro_cols[i % 3]:

        st.metric(
            ticker,
            f"{current:.2f}",
            f"{variation:+.2f}%"
        )

# =========================================================
# FISCAL SIMULATOR
# =========================================================

st.markdown("## 🧮 Simulateur Fiscal")

def simulate_tax(
    amount,
    gain_ratio,
    mode="flat_tax"
):

    gain_part = amount * gain_ratio

    if mode == "flat_tax":

        taxes = gain_part * 0.30

    else:

        taxes = gain_part * 0.172

    return amount - taxes


col1, col2 = st.columns(2)

with col1:

    withdrawal = st.number_input(
        "Montant retrait (€)",
        value=1000.0,
        step=100.0
    )

with col2:

    tax_mode = st.selectbox(
        "Fiscalité",
        ["flat_tax", "abattement_av"]
    )

gain_ratio = gain_total / valeur_totale if valeur_totale > 0 else 0

net_amount = simulate_tax(
    withdrawal,
    gain_ratio,
    tax_mode
)

st.success(
    f"💰 Montant net estimé : {net_amount:,.2f}€"
)

# =========================================================
# TARGET ALLOCATION
# =========================================================

st.markdown("## 🎯 Allocation Patrimoniale Cible")

target_df = pd.DataFrame({
    "Allocation": ["MSCI World", "Or"],
    "Objectif": [94, 6]
})

fig = px.bar(
    target_df,
    x="Allocation",
    y="Objectif",
    text="Objectif"
)

fig.update_layout(
    paper_bgcolor="#161B22",
    plot_bgcolor="#161B22",
    font_color="white",
    height=350
)

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "Cockpit Décisionnel Expert • Architecture robuste yFinance • Streamlit Institutional Grade"
)
