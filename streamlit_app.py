# =========================================================
# 🛰️ COCKPIT DÉCISIONNEL BOURSIER - VERSION SYNCHRONISÉE
# Alignée sur historique réel du portefeuille
# =========================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
import warnings

warnings.filterwarnings("ignore")

# =========================================================
# CONFIG STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Cockpit Décisionnel Expert",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

PARIS_TZ = ZoneInfo("Europe/Paris")

# =========================================================
# CSS PREMIUM
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: #0E1117;
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
    font-size: 1.15rem;
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
    margin-top: 1rem;
}

.ok-alert {
    background: #123524;
    border: 1px solid #198754;
    color: white;
    padding: 1rem;
    border-radius: 12px;
    font-weight: 700;
    margin-top: 1rem;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# PARAMÈTRES HISTORIQUES RÉELS
# =========================================================

DATE_DEBUT = "2025-09-17"

CAPITAL_NET = 13796.71

BONUS_FORTUNEO = 160.0

POSITIONS = [

    {
        "nom": "MSCI World AV",
        "ticker": "MWRD.PA",
        "parts": 36.33,
        "prm": 140.41,
        "type": "core"
    },

    {
        "nom": "MSCI World PEA",
        "ticker": "DCAM.PA",
        "parts": 481.0,
        "prm": 5.5937,
        "type": "core"
    },

    {
        "nom": "Global Hydrogen",
        "ticker": "ANRJ.PA",
        "parts": 4.7701,
        "prm": 707.55,
        "type": "satellite"
    },

    {
        "nom": "EM Asia",
        "ticker": "AASI.PA",
        "parts": 40.8272,
        "prm": 49.96,
        "type": "satellite"
    },

    {
        "nom": "Or Physique",
        "ticker": "CGLD.PA",
        "parts": 4.5902,
        "prm": 163.39,
        "type": "gold"
    }
]

# =========================================================
# BONUS FORTUNEO -> AJUSTEMENT PRM PEA
# =========================================================

for pos in POSITIONS:

    if pos["nom"] == "MSCI World PEA":

        reduction = BONUS_FORTUNEO / pos["parts"]

        pos["prm"] = pos["prm"] - reduction

# =========================================================
# PROXIES
# =========================================================

PROXIES = {
    "ANRJ.PA": ["PLUG", "BE", "NEL.OL"],
    "AASI.PA": ["TSM", "005930.KS"]
}

# =========================================================
# ROBUST DATA ENGINE
# =========================================================

def flatten_columns(df):

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Correction MultiIndex yfinance
    if isinstance(df.columns, pd.MultiIndex):

        df.columns = [col[0] for col in df.columns]

    # Suppression colonnes dupliquées
    df = df.loc[:, ~df.columns.duplicated()]

    return df


@st.cache_data(ttl=60, show_spinner=False)
def download_data(tickers):

    data = {}

    for ticker in tickers:

        try:

            df = yf.download(
                ticker,
                start=DATE_DEBUT,
                progress=False,
                auto_adjust=False,
                threads=False
            )

            df = flatten_columns(df)

            if df.empty:
                continue

            # Sécurisation types
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df.dropna(how="all", inplace=True)

            if df.empty:
                continue

            data[ticker] = df

        except Exception as e:

            print(f"Erreur téléchargement {ticker}: {e}")

    return data

# =========================================================
# INDICATEURS TECHNIQUES
# =========================================================

def safe_close(df):

    if df is None:
        return pd.Series(dtype=float)

    if df.empty:
        return pd.Series(dtype=float)

    if "Close" not in df.columns:
        return pd.Series(dtype=float)

    return pd.to_numeric(
        df["Close"],
        errors="coerce"
    ).dropna()


def last_value(series):

    if series is None:
        return None

    if len(series) == 0:
        return None

    return float(series.iloc[-1])


def previous_value(series):

    if len(series) < 2:
        return None

    return float(series.iloc[-2])


def compute_sma(series, window):

    if len(series) < window:
        return pd.Series(dtype=float)

    return series.rolling(window).mean()


def compute_rsi(series, period=14):

    if len(series) < period + 1:
        return pd.Series(dtype=float)

    delta = series.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))

# =========================================================
# CHARGEMENT DES DONNÉES
# =========================================================

ALL_TICKERS = []

for pos in POSITIONS:
    ALL_TICKERS.append(pos["ticker"])

for arr in PROXIES.values():
    ALL_TICKERS.extend(arr)

ALL_TICKERS = list(set(ALL_TICKERS))

MARKET_DATA = download_data(ALL_TICKERS)

# =========================================================
# CALCULS PORTEFEUILLE
# =========================================================

portfolio_rows = []

VALEUR_TOTALE = 0.0

for pos in POSITIONS:

    ticker = pos["ticker"]

    if ticker not in MARKET_DATA:
        continue

    df = MARKET_DATA[ticker]

    close = safe_close(df)

    if close.empty:
        continue

    prix = last_value(close)

    previous_close = previous_value(close)

    valeur = prix * pos["parts"]

    gain_eur = valeur - (pos["parts"] * pos["prm"])

    perf_position = ((prix / pos["prm"]) - 1) * 100

    # Variation journalière
    if previous_close and previous_close != 0:

        var_jour = (
            (prix - previous_close)
            / previous_close
        ) * 100

    else:

        var_jour = 0

    sma20 = last_value(
        compute_sma(close, 20)
    )

    sma50 = last_value(
        compute_sma(close, 50)
    )

    rsi14 = last_value(
        compute_rsi(close)
    )

    portfolio_rows.append({

        "Nom": pos["nom"],
        "Ticker": ticker,
        "Type": pos["type"],

        "Prix": prix,
        "Parts": pos["parts"],
        "PRM": pos["prm"],

        "Valeur": valeur,
        "Gain €": gain_eur,

        "Performance": perf_position,
        "Var. Jour %": var_jour,

        "SMA20": sma20,
        "SMA50": sma50,
        "RSI": rsi14
    })

    VALEUR_TOTALE += valeur

PORTFOLIO_DF = pd.DataFrame(portfolio_rows)

# =========================================================
# PERFORMANCE RÉELLE PORTEFEUILLE
# =========================================================

PERFORMANCE_PORTEFEUILLE = (
    (VALEUR_TOTALE / CAPITAL_NET) - 1
) * 100

GAIN_NET = VALEUR_TOTALE - CAPITAL_NET

# =========================================================
# PERFORMANCE BENCHMARK
# =========================================================

PERFORMANCE_BENCHMARK = 0

if "MWRD.PA" in MARKET_DATA:

    benchmark_close = safe_close(
        MARKET_DATA["MWRD.PA"]
    )

    if len(benchmark_close) > 2:

        start_price = float(
            benchmark_close.iloc[0]
        )

        current_price = float(
            benchmark_close.iloc[-1]
        )

        PERFORMANCE_BENCHMARK = (
            (current_price / start_price) - 1
        ) * 100

# =========================================================
# GAP
# =========================================================

GAP = (
    PERFORMANCE_PORTEFEUILLE
    - PERFORMANCE_BENCHMARK
)

# =========================================================
# PHASES
# =========================================================

if GAP < 0:

    PHASE = "PHASE 1 · RECONQUÊTE"
    PHASE_COLOR = "#DC3545"

else:

    PHASE = "PHASE 2 · ALPHA"
    PHASE_COLOR = "#198754"

# =========================================================
# HEADER
# =========================================================

now = datetime.now(PARIS_TZ)

st.title("🛰️ Cockpit Décisionnel Expert")

st.caption(
    f"Synchronisé historique réel • "
    f"{now.strftime('%d/%m/%Y %H:%M')} • Paris"
)

st.markdown(
    f"""
    <div class="phase-banner"
         style="background:{PHASE_COLOR};">

        {PHASE}

    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# KPIs
# =========================================================

k1, k2, k3, k4 = st.columns(4)

with k1:

    st.markdown('<div class="card">',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">'
        'Valeur Totale'
        '</div>',

        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="kpi-value">'
        f'{VALEUR_TOTALE:,.2f}€'
        f'</div>',

        unsafe_allow_html=True
    )

    st.markdown('</div>',
                unsafe_allow_html=True)

with k2:

    st.markdown('<div class="card">',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">'
        'Gain Net'
        '</div>',

        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="kpi-value">'
        f'{GAIN_NET:+,.2f}€'
        f'</div>',

        unsafe_allow_html=True
    )

    st.markdown('</div>',
                unsafe_allow_html=True)

with k3:

    st.markdown('<div class="card">',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">'
        'Performance'
        '</div>',

        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="kpi-value">'
        f'{PERFORMANCE_PORTEFEUILLE:+.2f}%'
        f'</div>',

        unsafe_allow_html=True
    )

    st.markdown('</div>',
                unsafe_allow_html=True)

with k4:

    st.markdown('<div class="card">',
                unsafe_allow_html=True)

    st.markdown(
        '<div class="kpi-title">'
        'GAP vs World'
        '</div>',

        unsafe_allow_html=True
    )

    st.markdown(
        f'<div class="kpi-value">'
        f'{GAP:+.2f}%'
        f'</div>',

        unsafe_allow_html=True
    )

    st.markdown('</div>',
                unsafe_allow_html=True)

# =========================================================
# TABLEAU POSITIONS
# =========================================================

st.markdown("## 📦 Positions")

display_df = PORTFOLIO_DF.copy()

# Formatage spécifique
display_df["Prix"] = display_df.apply(

    lambda row:

    f"{row['Prix']:.3f}"

    if row["Nom"] == "MSCI World PEA"

    else f"{row['Prix']:.2f}",

    axis=1
)

display_df["Parts"] = display_df.apply(

    lambda row:

    f"{row['Parts']:.3f}"

    if row["Nom"] == "MSCI World PEA"

    else f"{row['Parts']:.4f}",

    axis=1
)

display_df["PRM"] = display_df["PRM"].map(
    lambda x: f"{x:.4f}"
)

display_df["Valeur"] = display_df["Valeur"].map(
    lambda x: f"{x:,.2f}€"
)

display_df["Gain €"] = display_df["Gain €"].map(
    lambda x: f"{x:+,.2f}€"
)

display_df["Performance"] = display_df["Performance"].map(
    lambda x: f"{x:+.2f}%"
)

display_df["Var. Jour %"] = display_df["Var. Jour %"].map(
    lambda x: f"{x:+.2f}%"
)

display_df["RSI"] = display_df["RSI"].map(
    lambda x: f"{x:.1f}"
)

st.dataframe(

    display_df[
        [
            "Nom",
            "Parts",
            "Prix",
            "PRM",
            "Valeur",
            "Gain €",
            "Performance",
            "Var. Jour %",
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

    PORTFOLIO_DF,

    values="Valeur",
    names="Nom",
    hole=0.55
)

fig.update_layout(

    paper_bgcolor="#161B22",
    font_color="white",
    height=500
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================================================
# SIGNALS SATELLITES
# =========================================================

st.markdown("## 🚨 Signaux Satellites")

for _, row in PORTFOLIO_DF.iterrows():

    if row["Type"] != "satellite":
        continue

    st.markdown(
        '<div class="card">',
        unsafe_allow_html=True
    )

    st.subheader(row["Nom"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Prix",
        f"{row['Prix']:.2f}€"
    )

    c2.metric(
        "SMA20",
        f"{row['SMA20']:.2f}€"
    )

    c3.metric(
        "SMA50",
        f"{row['SMA50']:.2f}€"
    )

    c4.metric(
        "RSI",
        f"{row['RSI']:.1f}"
    )

    SIGNAL = False

    # Règle stratégique
    if row["Prix"] < row["SMA20"]:
        SIGNAL = True

    if GAP > 5:
        SIGNAL = True

    if SIGNAL:

        montant = row["Valeur"] * 0.25

        st.markdown(

            f"""
            <div class="sell-alert">

            🚨 Signal d'arbitrage :
            Sécuriser {montant:,.2f}€
            vers le MSCI World

            </div>
            """,

            unsafe_allow_html=True
        )

    else:

        st.markdown(

            """
            <div class="ok-alert">

            ✅ Aucun signal vendeur

            </div>
            """,

            unsafe_allow_html=True
        )

    # ======================
    # PROXIES
    # ======================

    st.markdown("### 🔎 Analyse Proxies")

    proxies = PROXIES.get(
        row["Ticker"],
        []
    )

    proxy_rows = []

    for proxy in proxies:

        if proxy not in MARKET_DATA:
            continue

        proxy_close = safe_close(
            MARKET_DATA[proxy]
        )

        if proxy_close.empty:
            continue

        proxy_price = last_value(proxy_close)

        proxy_sma20 = last_value(
            compute_sma(proxy_close, 20)
        )

        proxy_rsi = last_value(
            compute_rsi(proxy_close)
        )

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

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "Cockpit Décisionnel • "
    "Synchronisé avec historique réel • "
    "Architecture robuste yFinance"
)
