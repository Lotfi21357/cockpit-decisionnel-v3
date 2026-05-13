# =============================================================================
# COCKPIT DÉCISIONNEL BOURSIER v4.0 — "INSTITUTIONAL GRADE"
# Lead Dev: Claude (Anthropic)
# v3.4 → v4.0 :
#   • Thème anthracite institutionnel (or #D4AF37, bleu #007BFF, rouge #FF3131)
#   • Strategic Score Engine 6 couches (-5 → +5) par satellite
#   • Calculateur d'Arbitrage Chirurgical (Target Weight Matrix)
#   • Alertes Leadership/Gap persistant 14j
#   • Executive UI : Radar Chart Plotly + Carte de Décision en euros
#   • Graphique de performance relative (Actif / MSCI World)
# =============================================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
import os
import warnings
warnings.filterwarnings("ignore")

# =============================================================================
# ██  BLOC 1 : CONFIGURATION & CSS INSTITUTIONNEL
# =============================================================================

st.set_page_config(
    page_title="Cockpit Décisionnel v4.0 · Institutional",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

/* ── Base Anthracite (pas noir pur) ── */
.stApp { background-color: #1C1F26; font-family: 'DM Sans', sans-serif; }
section[data-testid="stSidebar"] {
    background-color: #22252E;
    border-right: 1px solid #2E3340;
}
.stApp > header { background-color: #1C1F26; }
.main .block-container { padding-top: 1.5rem; max-width: 1400px; }

/* ── Cards ── */
.card {
    background: linear-gradient(145deg, #252932 0%, #2A2D38 100%);
    border-radius: 12px; padding: 1.4rem; margin-bottom: 1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35), 0 1px 0 rgba(255,255,255,0.03);
    border: 1px solid #32363F;
}
.card-gold   { border-left: 4px solid #D4AF37; }
.card-blue   { border-left: 4px solid #007BFF; }
.card-red    { border-left: 4px solid #FF3131; }
.card-orange { border-left: 4px solid #F97316; }
.card-green  { border-left: 4px solid #22C55E; }
.card-purple { border-left: 4px solid #A855F7;
               background: linear-gradient(145deg, #1E1A30 0%, #221D35 100%); }

/* ── KPIs ── */
.kpi-value { font-size:2rem; font-weight:700; color:#FFFFFF;
             font-family:'Space Mono',monospace; letter-spacing:-1px; }
.kpi-label { font-size:0.72rem; color:#6B7585; text-transform:uppercase;
             letter-spacing:2px; margin-bottom:0.3rem; font-family:'DM Sans',sans-serif; }
.kpi-delta-pos { color:#22C55E; font-size:0.82rem; font-weight:600; }
.kpi-delta-neg { color:#FF3131; font-size:0.82rem; font-weight:600; }

/* ── Score Badge ── */
.score-badge {
    font-family:'Space Mono',monospace; font-size:2.6rem; font-weight:700;
    padding: 0.4rem 1.2rem; border-radius: 10px; display: inline-block;
    border: 2px solid; letter-spacing:-1px;
}
.score-pos  { color:#D4AF37; border-color:#D4AF37; background:rgba(212,175,55,0.08); }
.score-neut { color:#F97316; border-color:#F97316; background:rgba(249,115,22,0.08); }
.score-neg  { color:#FF3131; border-color:#FF3131; background:rgba(255,49,49,0.08); }

/* ── Status Labels ── */
.status-maintain  { background:linear-gradient(135deg,#2D3F1F,#344A22); color:#86EFAC;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700;
                    font-size:1rem; text-align:center; letter-spacing:1px; }
.status-lighten   { background:linear-gradient(135deg,#3B3208,#453B0A); color:#FDE68A;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700;
                    font-size:1rem; text-align:center; letter-spacing:1px; }
.status-vigilance { background:linear-gradient(135deg,#3B2008,#47260A); color:#FDBA74;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700;
                    font-size:1rem; text-align:center; letter-spacing:1px; }
.status-reduce    { background:linear-gradient(135deg,#3B0F0F,#4A1414); color:#FCA5A5;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700;
                    font-size:1rem; text-align:center; letter-spacing:1px; }
.status-exit      { background:linear-gradient(135deg,#2D0505,#3A0808); color:#FF3131;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700;
                    font-size:1rem; text-align:center; letter-spacing:1px;
                    box-shadow:0 0 20px rgba(255,49,49,0.2); }

/* ── Arbitrage Block ── */
.arb-sell {
    background:linear-gradient(135deg,#350808,#420B0B);
    border: 1px solid #FF3131; border-radius:10px; padding:1rem 1.2rem;
    margin:.5rem 0; font-family:'Space Mono',monospace;
    box-shadow: 0 0 15px rgba(255,49,49,0.15);
}
.arb-buy {
    background:linear-gradient(135deg,#083508,#0B4A0B);
    border: 1px solid #22C55E; border-radius:10px; padding:1rem 1.2rem;
    margin:.5rem 0; font-family:'Space Mono',monospace;
}
.arb-neutral {
    background:linear-gradient(135deg,#1A1F26,#1E242D);
    border: 1px solid #32363F; border-radius:10px; padding:1rem 1.2rem;
    margin:.5rem 0; font-family:'Space Mono',monospace;
}

/* ── Alert Leadership ── */
.alert-leadership {
    background:linear-gradient(135deg,#2A1A00,#331F00);
    border: 1px solid #D4AF37; border-radius:10px;
    padding:.9rem 1.2rem; margin:.5rem 0;
    box-shadow: 0 0 20px rgba(212,175,55,0.15);
    color: #FDE68A; font-weight: 600;
}
.alert-critical {
    background:linear-gradient(135deg,#2D0505,#380909);
    border: 1px solid #FF3131; border-radius:10px;
    padding:.9rem 1.2rem; margin:.5rem 0;
    box-shadow: 0 0 20px rgba(255,49,49,0.2);
    color: #FCA5A5; font-weight: 600;
}

/* ── Score Layer Row ── */
.layer-row {
    display:flex; align-items:center; gap:.8rem;
    padding:.5rem .7rem; border-radius:6px; margin:.2rem 0;
    background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04);
}
.layer-name { font-size:.8rem; color:#8892AA; width:110px; flex-shrink:0; }
.layer-bar-wrap { flex:1; background:#1C1F26; border-radius:4px; height:8px; }
.layer-val { font-family:'Space Mono',monospace; font-size:.85rem; width:50px;
             text-align:right; flex-shrink:0; }

/* ── Phase Banner ── */
.phase-banner {
    padding:.8rem 1.4rem; border-radius:10px; font-weight:700;
    font-size:.95rem; margin-bottom:1.2rem; text-align:center;
    letter-spacing:.5px;
}
/* ── Mode Direct Banner ── */
.mode-direct-banner {
    background:linear-gradient(135deg,#2D1060,#38138A);
    border:1px solid #7C3AED; border-radius:10px;
    padding:.7rem 1.2rem; margin-bottom:1rem;
    color:#E9D5FF; font-weight:700; font-size:.9rem; text-align:center;
}
/* ── Misc ── */
h2 { color:#E2E8F0 !important; border-bottom:1px solid #2E3340; padding-bottom:.4rem;
     font-family:'DM Sans',sans-serif; font-weight:600; }
h3, h4 { color:#CBD5E1 !important; font-family:'DM Sans',sans-serif; font-weight:600; }
.small { font-size:.82rem; color:#6B7585; }
.info-box { background:#0F1E35; border-left:4px solid #007BFF; border-radius:8px;
            padding:.75rem 1rem; margin:.4rem 0; font-size:.9rem; }
.alert-box { background:#2D1515; border-left:4px solid #FF3131; border-radius:8px;
             padding:.75rem 1rem; margin:.4rem 0; font-size:.9rem; }
.save-box { background:#0D1F0D; border-left:4px solid #22C55E; border-radius:8px;
            padding:.6rem 1rem; margin:.3rem 0; font-size:.85rem; color:#86EFAC; }
.net-box { background:#0D2818; border-left:4px solid #22C55E; border-radius:8px;
           padding:1rem; margin-top:.75rem; }
.live-badge { display:inline-block; background:#22C55E; color:#0B0E15; border-radius:4px;
              font-size:.62rem; font-weight:800; padding:.1rem .4rem;
              letter-spacing:.5px; vertical-align:middle; margin-left:.4rem; }
.badge { display:inline-block; padding:.2rem .8rem; border-radius:20px;
         font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.5px; }
.badge-red    { background:#FF3131; color:white; }
.badge-orange { background:#F97316; color:white; }
.badge-green  { background:#22C55E; color:#0B0E15; }
.badge-gold   { background:#D4AF37; color:#0B0E15; }
.badge-gray   { background:#374151; color:#D1D5DB; }
.badge-blue   { background:#007BFF; color:white; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# ██  BLOC 2 : CONSTANTES & PERSISTANCE JSON
# =============================================================================

POSITIONS_BASE = [
    {"nom": "MSCI World AV",   "tickers": ["MWRD.PA","IWDA.AS","EUNL.DE"], "parts": 36.33,   "prm": 140.41,  "enveloppe": "AV"},
    {"nom": "MSCI World PEA",  "tickers": ["DCAM.PA"],                      "parts": 481.0,   "prm": 5.5937,  "enveloppe": "PEA"},
    {"nom": "Global Hydrogen", "tickers": ["ANRJ.PA"],                      "parts": 4.7701,  "prm": 707.55,  "enveloppe": "AV"},
    {"nom": "EM Asia",         "tickers": ["AASI.PA"],                      "parts": 40.8272, "prm": 49.96,   "enveloppe": "AV"},
    {"nom": "Or Physique",     "tickers": ["OR-EUR.PA","DE000SLA8RU8.SG","CGLD.PA","GOLD.PA"], "parts": 4.5902, "prm": 163.39, "enveloppe": "AV"},
]

_DEFAULT_CAPITAL_REEL   = 13_796.71
_DEFAULT_AJUSTEMENT_PAT = 219.97
_DEFAULT_BONUS_FORTUNEO = 160.0
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_perso.json")

# Targets institutionnels initiaux par satellite (% du portefeuille total)
INITIAL_TARGETS = {
    "Global Hydrogen": 0.25,
    "EM Asia":         0.25,
}

BENCHMARK_NOM = "MSCI World AV"
WORLD_TICKERS = ["MWRD.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]

PROXIES_ANRJ = ["PLUG", "BE", "NEL.OL"]
PROXIES_AASI = ["TSM", "005930.KS", "AAXJ"]

MACRO_TICKERS = {
    "NQ=F":     "Nasdaq 100",
    "ES=F":     "S&P 500",
    "^TNX":     "US 10Y (%)",
    "EURUSD=X": "EUR/USD",
    "BZ=F":     "Brent ($)",
    "GC=F":     "Or ($)",
    "DX-Y.NYB": "Dollar Index",
    "MCHI":     "iShares MSCI China",
}
SENTINELLES = {
    "TSMC":        ["TSM"],
    "Samsung":     ["005930.KS"],
    "Air Liquide": ["AI.PA"],
    "Bloom Energy":["BE"],
    "SK Hynix":    ["000660.KS"],
}
DATE_DEBUT = datetime(2025, 9, 17)


def load_config() -> dict:
    defaults = {"capital_reel": _DEFAULT_CAPITAL_REEL,
                "ajustement_pat": _DEFAULT_AJUSTEMENT_PAT,
                "bonus_fortuneo": _DEFAULT_BONUS_FORTUNEO}
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**defaults, **{k: float(v) for k, v in data.items() if k in defaults}}
    except Exception:
        pass
    return defaults


def save_config(capital_reel, ajustement_pat, bonus_fortuneo) -> bool:
    try:
        payload = {"capital_reel": round(capital_reel, 2),
                   "ajustement_pat": round(ajustement_pat, 2),
                   "bonus_fortuneo": round(bonus_fortuneo, 2)}
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


if "config_loaded" not in st.session_state:
    cfg = load_config()
    st.session_state["cfg_capital_reel"]   = cfg["capital_reel"]
    st.session_state["cfg_ajustement_pat"] = cfg["ajustement_pat"]
    st.session_state["cfg_bonus_fortuneo"] = cfg["bonus_fortuneo"]
    st.session_state["config_loaded"]      = True
    st.session_state["save_feedback"]      = ""

# =============================================================================
# ██  BLOC 3 : SIDEBAR
# =============================================================================

st.sidebar.markdown("## ⚙️ Paramètres v4.0")
mode_direct = st.sidebar.toggle("🔌 Mode Direct (Vue Brute)", value=False,
    help="Désactive tous les ajustements — valeur marchande pure.")
st.sidebar.markdown("---")

capital_reel_input   = st.sidebar.number_input("Capital réel sorti banque (€)",
    value=st.session_state["cfg_capital_reel"], step=100.0, format="%.2f", key="input_capital_reel")
ajustement_pat_input = st.sidebar.number_input("Ajustement patrimonial (€)",
    value=st.session_state["cfg_ajustement_pat"], step=1.0, format="%.2f",
    help="Bonus Fortuneo (160€) + TBC (59.97€)", key="input_ajustement_pat")
bonus_fortuneo_input = st.sidebar.number_input("Bonus Fortuneo seul (€, PRM PEA)",
    value=st.session_state["cfg_bonus_fortuneo"], step=10.0, format="%.2f", key="input_bonus_fortuneo")

if st.sidebar.button("💾 Sauvegarder les paramètres", use_container_width=True):
    ok = save_config(capital_reel_input, ajustement_pat_input, bonus_fortuneo_input)
    if ok:
        st.session_state["cfg_capital_reel"]   = capital_reel_input
        st.session_state["cfg_ajustement_pat"] = ajustement_pat_input
        st.session_state["cfg_bonus_fortuneo"] = bonus_fortuneo_input
        st.session_state["save_feedback"] = "✅ Paramètres sauvegardés"
    else:
        st.session_state["save_feedback"] = "❌ Erreur d'écriture"

if st.session_state.get("save_feedback"):
    fb  = st.session_state["save_feedback"]
    cls = "save-box" if fb.startswith("✅") else "alert-box"
    st.sidebar.markdown(f'<div class="{cls}">{fb}</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Positions")

positions_conf = []
for pos in POSITIONS_BASE:
    with st.sidebar.expander(pos["nom"]):
        parts = st.number_input("Parts",   value=float(pos["parts"]), step=0.0001, format="%.4f", key=f"p_{pos['nom']}")
        prm   = st.number_input("PRM (€)", value=float(pos["prm"]),  step=0.0001, format="%.4f", key=f"r_{pos['nom']}")
        positions_conf.append({**pos, "parts": parts, "prm": prm})

if mode_direct:
    capital_reel   = capital_reel_input
    ajustement_pat = 0.0
    bonus_fortuneo = 0.0
else:
    capital_reel   = capital_reel_input
    ajustement_pat = ajustement_pat_input
    bonus_fortuneo = bonus_fortuneo_input

for pos in positions_conf:
    if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0:
        pos["prm"] -= bonus_fortuneo / pos["parts"]

# =============================================================================
# ██  BLOC 4 : DATA ENGINE — PRIX LIVE + HISTORIQUE TECHNIQUE
# =============================================================================

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        try:
            tickers_available = df.columns.get_level_values(1).unique().tolist()
            if tickers_available:
                df = df.xs(tickers_available[0], axis=1, level=1)
        except Exception:
            df = df.copy(); df.columns = df.columns.get_level_values(0)
    df = df.dropna(axis=1, how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={"Adj Close": "Close", "Adj_Close": "Close", "adj close": "Close"})
    df = df.rename(columns={c: c.title() for c in df.columns})
    if "Close" not in df.columns:
        return pd.DataFrame()
    df = df.dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def fetch_live_price(tk: str) -> tuple:
    try:
        fi   = yf.Ticker(tk).fast_info
        prix = getattr(fi, "last_price", None)
        prev = getattr(fi, "previous_close", None)
        if prix and float(prix) > 0:
            return float(prix), float(prev) if prev else None
    except Exception:
        pass
    try:
        info = yf.Ticker(tk).info
        prix = (info.get("regularMarketPrice") or info.get("currentPrice") or info.get("navPrice"))
        prev = (info.get("regularMarketPreviousClose") or info.get("previousClose"))
        if prix and float(prix) > 0:
            return float(prix), float(prev) if prev else None
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=30, show_spinner=False)
def load_all_live_prices() -> dict:
    all_tickers = []
    for pos in POSITIONS_BASE:
        all_tickers.extend(pos["tickers"])
    all_tickers.extend(list(MACRO_TICKERS.keys()))
    all_tickers.extend(PROXIES_ANRJ)
    all_tickers.extend(PROXIES_AASI)
    for tlist in SENTINELLES.values():
        all_tickers.extend(tlist)
    all_tickers = list(dict.fromkeys(all_tickers))
    live = {}
    for tk in all_tickers:
        prix, prev = fetch_live_price(tk)
        live[tk] = {"prix": prix, "prev": prev}
    return live


@st.cache_data(ttl=90, show_spinner=False)
def load_all_data() -> dict:
    start = (datetime.now() - timedelta(days=600)).strftime("%Y-%m-%d")  # 600j pour SMA200
    all_tickers = []
    for pos in POSITIONS_BASE:
        all_tickers.extend(pos["tickers"])
    all_tickers.extend(PROXIES_ANRJ)
    all_tickers.extend(PROXIES_AASI)
    all_tickers.extend(list(MACRO_TICKERS.keys()))
    for tlist in SENTINELLES.values():
        all_tickers.extend(tlist)
    all_tickers = list(dict.fromkeys(all_tickers))
    result = {}
    try:
        raw = yf.download(all_tickers, start=start, group_by="ticker",
                          auto_adjust=True, progress=False, threads=True)
    except Exception:
        raw = pd.DataFrame()
    if not raw.empty and isinstance(raw.columns, pd.MultiIndex):
        for tk in all_tickers:
            try:
                df = normalize_df(raw[tk].copy())
                if not df.empty:
                    result[tk] = df
            except Exception:
                pass
    elif not raw.empty and len(all_tickers) == 1:
        df = normalize_df(raw.copy())
        if not df.empty:
            result[all_tickers[0]] = df
    for tk in [t for t in all_tickers if t not in result]:
        try:
            df = normalize_df(yf.download(tk, start=start, auto_adjust=True, progress=False))
            if not df.empty:
                result[tk] = df
        except Exception:
            pass
    return result


def get_price_info(live_prices: dict, tickers: list) -> tuple:
    for tk in tickers:
        info = live_prices.get(tk, {})
        prix = info.get("prix")
        prev = info.get("prev")
        if prix and float(prix) > 0:
            return float(prix), float(prev) if prev else None, tk
    return None, None, None

# =============================================================================
# ██  BLOC 5 : INDICATEURS TECHNIQUES
# =============================================================================

def sma(series: pd.Series, n: int):
    s = series.dropna()
    return float(s.rolling(n).mean().iloc[-1]) if len(s) >= n else None


def rsi_indicator(series: pd.Series, period: int = 14):
    s = series.dropna()
    if len(s) < period + 1:
        return None
    delta = s.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    r     = (100 - (100 / (1 + rs))).dropna()
    return float(r.iloc[-1]) if not r.empty else None


def adx_indicator(df: pd.DataFrame, period: int = 14):
    try:
        close = df["Close"].dropna()
        high  = df.get("High", pd.Series(dtype=float)).dropna()
        low   = df.get("Low",  pd.Series(dtype=float)).dropna()
        idx   = close.index.intersection(high.index).intersection(low.index)
        if len(idx) < period + 1:
            return None
        c, h, l = close[idx], high[idx], low[idx]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        up, down = h.diff(), -l.diff()
        pdm = np.where((up > down) & (up > 0), up, 0.0)
        mdm = np.where((down > up) & (down > 0), down, 0.0)
        atr_s = tr.rolling(period).mean()
        pdi   = 100 * pd.Series(pdm, index=idx).rolling(period).mean() / atr_s
        mdi   = 100 * pd.Series(mdm, index=idx).rolling(period).mean() / atr_s
        dx    = ((pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)) * 100
        adx_s = dx.rolling(period).mean().dropna()
        return float(adx_s.iloc[-1]) if not adx_s.empty else None
    except Exception:
        return None


def volume_signal(df: pd.DataFrame) -> int:
    """+1 volumes acheteurs, -1 volumes vendeurs, 0 neutre"""
    if df.empty or "Volume" not in df.columns or "Close" not in df.columns:
        return 0
    vol   = df["Volume"].dropna()
    close = df["Close"].dropna()
    if len(vol) < 25 or len(close) < 6:
        return 0
    vol_5  = vol.iloc[-5:].mean()
    vol_20 = vol.iloc[-20:].mean()
    if vol_20 == 0:
        return 0
    vol_ratio    = vol_5 / vol_20
    price_change = (close.iloc[-1] / close.iloc[-6] - 1)
    if vol_ratio > 1.3 and price_change > 0.01:
        return 1
    if vol_ratio > 1.3 and price_change < -0.01:
        return -1
    return 0


def relative_strength_slope(data: dict, ticker: str, days: int = 14):
    """Pente de (Actif / MSCI World) sur N jours. Positif = leadership."""
    df_asset = data.get(ticker, pd.DataFrame())
    df_world = pd.DataFrame()
    for wt in WORLD_TICKERS:
        df = data.get(wt, pd.DataFrame())
        if not df.empty and "Close" in df.columns:
            df_world = df
            break
    if df_asset.empty or df_world.empty:
        return None
    ac = df_asset["Close"].dropna()
    wc = df_world["Close"].dropna()
    common = ac.index.intersection(wc.index)
    if len(common) < days + 2:
        return None
    common = common[-(days + 2):]
    ratio = ac[common] / wc[common]
    x = np.arange(len(ratio))
    y = ratio.values.astype(float)
    if np.any(np.isnan(y)):
        return None
    return float(np.polyfit(x, y, 1)[0])


def analyze_ticker(data: dict, live_prices: dict, ticker: str):
    lp   = live_prices.get(ticker, {})
    prix_live = lp.get("prix")
    df   = data.get(ticker, pd.DataFrame())
    if df.empty or "Close" not in df.columns:
        if prix_live:
            return {"ticker": ticker, "prix": prix_live,
                    "sma20": None, "sma50": None, "sma200": None,
                    "rsi": None, "adx": None, "ath30": None}
        return None
    close = df["Close"].dropna()
    if close.empty:
        return None
    prix = prix_live if (prix_live and prix_live > 0) else float(close.iloc[-1])
    return {
        "ticker":  ticker,
        "prix":    prix,
        "sma20":   sma(close, 20),
        "sma50":   sma(close, 50),
        "sma200":  sma(close, 200),
        "rsi":     rsi_indicator(close),
        "adx":     adx_indicator(df),
        "ath30":   float(close.rolling(30, min_periods=1).max().iloc[-1]),
    }

# =============================================================================
# ██  BLOC 6 : STRATEGIC SCORE ENGINE — 6 COUCHES
# =============================================================================

def rsi_to_radar(rsi) -> float:
    """Convertit RSI en score radar 0-10 (optimal = 50-65)"""
    if rsi is None:
        return 5.0
    if rsi < 30:
        return 2.0
    if rsi < 40:
        return 4.0
    if rsi <= 65:
        return 8.0 + (rsi - 50) / 15 * 1.5 if rsi >= 50 else 6.0
    if rsi <= 75:
        return max(3.0, 8.0 - (rsi - 65) * 0.4)
    return 2.0


def adx_to_radar(adx) -> float:
    """Convertit ADX en score radar 0-10"""
    if adx is None:
        return 4.0
    if adx < 15:
        return 2.0
    if adx < 25:
        return 5.0
    if adx < 35:
        return 8.0
    return 9.5


def get_institutional_score(
    ticker: str, theme: str,
    data: dict, live_prices: dict, macro_info: dict
) -> dict:
    """
    Analyse 6 couches institutionnelles. Retourne score -5 → +5 et détails radar.
    theme: 'hydrogen' | 'em_asia'
    """
    info   = analyze_ticker(data, live_prices, ticker)
    df     = data.get(ticker, pd.DataFrame())
    details = []
    score   = 0

    # ── COUCHE 1 : Tendance (max ±2) ─────────────────────────────────────────
    trend_score = 0
    if info:
        p = info["prix"]
        if info["sma50"] is not None:
            if p < info["sma50"]:
                trend_score = -2
                details.append(("Tendance", -2, "Prix < SMA50 — Tendance baissière confirmée"))
            else:
                trend_score += 1
                details.append(("Tendance", +1, "Prix > SMA50 ✓"))
                if info["sma200"] is not None:
                    if p > info["sma200"]:
                        trend_score += 1
                        details.append(("Tendance", +1, "Prix > SMA200 — Structure haussière LT ✓"))
                    else:
                        details.append(("Tendance", 0, "Prix < SMA200 — Sous résistance LT"))
        else:
            details.append(("Tendance", 0, "SMA50 indisponible"))
    else:
        details.append(("Tendance", 0, "Données indisponibles"))

    score += trend_score

    # ── COUCHE 2 : Macro (max ±1) ────────────────────────────────────────────
    macro_score = 0
    if theme == "hydrogen":
        tnx   = (macro_info.get("^TNX") or {}).get("prix")
        nq_df = data.get("NQ=F", pd.DataFrame())
        nq_lp = (live_prices.get("NQ=F") or {}).get("prix")
        if tnx is not None:
            if float(tnx) > 4.50:
                macro_score -= 1
                details.append(("Macro", -1, f"US 10Y = {tnx:.2f}% > 4.50% — Défavorable aux taux longs"))
            else:
                details.append(("Macro", 0, f"US 10Y = {tnx:.2f}% ≤ 4.50% — OK"))
        if not nq_df.empty and "Close" in nq_df.columns:
            nq_sma50 = sma(nq_df["Close"].dropna(), 50)
            nq_price = nq_lp if nq_lp else float(nq_df["Close"].dropna().iloc[-1])
            if nq_sma50 and nq_price > nq_sma50:
                macro_score += 1
                details.append(("Macro", +1, "Nasdaq > SMA50 — Appétit risque haussier ✓"))
            elif nq_sma50:
                details.append(("Macro", 0, "Nasdaq < SMA50 — Appétit risque neutre"))

    elif theme == "em_asia":
        dxy_lp = (live_prices.get("DX-Y.NYB") or {}).get("prix")
        dxy_df = data.get("DX-Y.NYB", pd.DataFrame())
        mchi_df = data.get("MCHI", pd.DataFrame())
        mchi_lp = (live_prices.get("MCHI") or {}).get("prix")
        if dxy_lp is not None:
            if float(dxy_lp) > 105:
                macro_score -= 1
                details.append(("Macro", -1, f"DXY = {dxy_lp:.1f} > 105 — Dollar fort, pression EM"))
            else:
                details.append(("Macro", 0, f"DXY = {dxy_lp:.1f} ≤ 105 — OK"))
        if not mchi_df.empty and "Close" in mchi_df.columns:
            mchi_sma50 = sma(mchi_df["Close"].dropna(), 50)
            mchi_px    = mchi_lp if mchi_lp else float(mchi_df["Close"].dropna().iloc[-1])
            if mchi_sma50 and mchi_px > mchi_sma50:
                macro_score += 1
                details.append(("Macro", +1, "MCHI (Chine) > SMA50 — Flux EM Asia positifs ✓"))
            elif mchi_sma50:
                details.append(("Macro", 0, "MCHI (Chine) < SMA50 — Flux neutres"))

    macro_score = max(-1, min(1, macro_score))
    score += macro_score

    # ── COUCHE 3 : Leadership — Force Relative (max ±2) ──────────────────────
    leader_score = 0
    rs_slope = relative_strength_slope(data, ticker, days=14)
    if rs_slope is not None:
        if rs_slope < 0:
            leader_score = -2
            details.append(("Leadership", -2, f"Pente FR négative ({rs_slope:.5f}) — Sous-performance vs World"))
        elif rs_slope > 0:
            leader_score = 2
            details.append(("Leadership", +2, f"Pente FR positive ({rs_slope:.5f}) — Leadership vs World ✓"))
        else:
            details.append(("Leadership", 0, "Force relative neutre"))
    else:
        details.append(("Leadership", 0, "Données FR insuffisantes"))
    score += leader_score

    # ── COUCHE 4 : Flux / Volumes (bonus/malus ±1) ───────────────────────────
    vol_score = volume_signal(df) if not df.empty else 0
    if vol_score == 1:
        details.append(("Volumes", +1, "Volumes acheteurs croissants ✓"))
    elif vol_score == -1:
        details.append(("Volumes", -1, "Volumes vendeurs massifs — Pression baissière"))
    else:
        details.append(("Volumes", 0, "Volumes neutres"))
    score += vol_score

    # ── Score total capped ────────────────────────────────────────────────────
    score = max(-5, min(5, score))

    # ── Couches 5-6 : Momentum & Structure (radar only) ──────────────────────
    rsi_val = info["rsi"] if info else None
    adx_val = info["adx"] if info else None
    rsi_radar_val = rsi_to_radar(rsi_val)
    adx_radar_val = adx_to_radar(adx_val)

    if rsi_val:
        details.append(("Momentum", None, f"RSI = {rsi_val:.1f}"))
    if adx_val:
        details.append(("Structure", None, f"ADX = {adx_val:.1f}"))

    # ── Normalisation pour radar 0-10 ────────────────────────────────────────
    radar = {
        "Tendance":   (trend_score  + 2) * 2.5,   # -2/+2 → 0/10
        "Macro":      (macro_score  + 1) * 5.0,   # -1/+1 → 0/10
        "Leadership": (leader_score + 2) * 2.5,   # -2/+2 → 0/10
        "Volumes":    (vol_score    + 1) * 5.0,   # -1/+1 → 0/10
        "Momentum":   rsi_radar_val,               # 0-10
        "Structure":  adx_radar_val,               # 0-10
    }

    return {
        "total":       score,
        "trend":       trend_score,
        "macro":       macro_score,
        "leadership":  leader_score,
        "volume":      vol_score,
        "rsi_score":   rsi_radar_val,
        "adx_score":   adx_radar_val,
        "radar":       radar,
        "details":     details,
        "rsi_raw":     rsi_val,
        "adx_raw":     adx_val,
    }

# =============================================================================
# ██  BLOC 7 : CALCULATEUR D'ARBITRAGE CHIRURGICAL
# =============================================================================

def get_target_weight(score: int, initial_target: float) -> float:
    """Matrice de Target Weight selon le score institutionnel."""
    if score >= 4:
        return initial_target      # Maintenir (ex: 25%)
    elif score >= 2:
        return 0.20               # Allègement léger
    elif score >= 0:
        return 0.15               # Vigilance
    else:
        return 0.05               # Réduction forte / sortie


def get_status_label(score: int) -> tuple:
    """(label, css_class)"""
    if score >= 4:
        return "MAINTIEN TOTAL", "status-maintain"
    elif score >= 2:
        return "ALLÈGEMENT LÉGER", "status-lighten"
    elif score >= 0:
        return "VIGILANCE", "status-vigilance"
    elif score >= -2:
        return "RÉDUCTION PARTIELLE", "status-reduce"
    else:
        return "SORTIE / RÉDUCTION FORTE", "status-exit"


def compute_strategic_arbitrage(positions_calculees: list, valeur_totale: float,
                                scores: dict) -> list:
    """
    Calcule le montant exact à vendre/acheter par satellite.
    Montant = Valeur_Actuelle - (Valeur_Totale × Target_Weight_Score)
    """
    if valeur_totale <= 0:
        return []
    actions = []
    for nom, initial_target in INITIAL_TARGETS.items():
        score         = scores.get(nom, {}).get("total", 0)
        target_weight = get_target_weight(score, initial_target)
        target_value  = valeur_totale * target_weight
        current_value = next((p["valeur"] for p in positions_calculees if p["nom"] == nom), 0)
        if current_value == 0:
            continue
        montant = current_value - target_value
        actions.append({
            "nom":           nom,
            "score":         score,
            "current_value": current_value,
            "current_pct":   current_value / valeur_totale * 100,
            "target_pct":    target_weight * 100,
            "target_value":  target_value,
            "montant":       montant,
            "action":        "VENDRE" if montant > 50 else ("ACHETER" if montant < -50 else "MAINTENIR"),
        })
    return actions

# =============================================================================
# ██  BLOC 8 : ALERTES LEADERSHIP (GAP 14J)
# =============================================================================

def check_leadership_alerts(data: dict) -> list:
    """Calcule le gap cumulé vs MSCI World sur 14j glissants."""
    alerts = []
    world_df = None
    for wt in WORLD_TICKERS:
        df = data.get(wt, pd.DataFrame())
        if not df.empty and "Close" in df.columns:
            world_df = df
            break
    if world_df is None:
        return alerts

    world_close = world_df["Close"].dropna()
    SAT_MAP = [("Global Hydrogen", "ANRJ.PA"), ("EM Asia", "AASI.PA")]
    for nom, tk in SAT_MAP:
        sat_df = data.get(tk, pd.DataFrame())
        if sat_df.empty or "Close" not in sat_df.columns:
            continue
        sat_close = sat_df["Close"].dropna()
        common    = sat_close.index.intersection(world_close.index)
        if len(common) < 16:
            continue
        recent = common[-15:]
        s_perf = (sat_close[recent].iloc[-1] / sat_close[recent].iloc[0] - 1) * 100
        w_perf = (world_close[recent].iloc[-1] / world_close[recent].iloc[0] - 1) * 100
        gap    = s_perf - w_perf
        alerts.append({"nom": nom, "sat_perf": s_perf, "world_perf": w_perf, "gap": gap})
    return alerts

# =============================================================================
# ██  BLOC 9 : CALCULS PORTEFEUILLE (identique v3.4)
# =============================================================================

def compute_portfolio(positions_conf, capital_reel, ajustement_pat, bonus_fortuneo, live_prices):
    positions_calculees = []
    valeur_totale = valeur_veille = 0.0
    val_env  = {"PEA": 0.0, "AV": 0.0}
    gain_env = {"PEA": 0.0, "AV": 0.0}
    for pos in positions_conf:
        prix, prev, tk_used = get_price_info(live_prices, pos["tickers"])
        env = pos["enveloppe"]
        if prix is None:
            positions_calculees.append({"nom": pos["nom"], "ticker": None, "prix": None,
                "valeur": 0.0, "perf_pct": None, "var_jour_pct": 0.0,
                "var_jour_eur": 0.0, "enveloppe": env})
            continue
        valeur       = pos["parts"] * prix
        gain_unit    = prix - pos["prm"]
        perf_pct     = gain_unit / pos["prm"] * 100
        gain_total   = gain_unit * pos["parts"]
        var_jour_pct = (prix - prev) / prev * 100 if prev and prev != 0 else 0.0
        var_jour_eur = (prix - prev) * pos["parts"] if prev else 0.0
        positions_calculees.append({
            "nom": pos["nom"], "ticker": tk_used, "prix": prix,
            "valeur": valeur, "perf_pct": perf_pct,
            "var_jour_pct": var_jour_pct, "var_jour_eur": var_jour_eur,
            "enveloppe": env,
        })
        valeur_totale += valeur
        val_env[env]  += valeur
        gain_env[env] += gain_total
        valeur_veille += pos["parts"] * (prev if prev else prix)
    solde_total  = valeur_totale + ajustement_pat
    gain_reel    = solde_total - capital_reel
    perf_tot_pct = (gain_reel / capital_reel * 100) if capital_reel else 0.0
    perf_j_eur   = valeur_totale - valeur_veille
    perf_j_pct   = perf_j_eur / valeur_veille * 100 if valeur_veille else 0.0
    return {"positions": positions_calculees, "valeur_totale": valeur_totale,
            "solde_total": solde_total, "gain_reel": gain_reel,
            "perf_tot_pct": perf_tot_pct, "valeur_veille": valeur_veille,
            "val_env": val_env, "gain_env": gain_env,
            "ajustement_pat": ajustement_pat, "capital_reel": capital_reel,
            "perf_j_eur": perf_j_eur, "perf_j_pct": perf_j_pct}


def compute_benchmark(data, live_prices, positions_conf, perf_tot_pct):
    bench_pos = next((p for p in positions_conf if p["nom"] == BENCHMARK_NOM), None)
    if not bench_pos:
        return None, None, None, None
    prix, prev, tk = get_price_info(live_prices, bench_pos["tickers"])
    if not prix:
        return None, None, None, None
    df_hist = data.get(tk, pd.DataFrame())
    if df_hist.empty:
        for t in bench_pos["tickers"]:
            df_hist = data.get(t, pd.DataFrame())
            if not df_hist.empty:
                break
    if df_hist.empty:
        return None, None, prix, None
    close     = df_hist["Close"].dropna()
    start_str = DATE_DEBUT.strftime("%Y-%m-%d")
    try:
        start_val = float(close.loc[start_str])
    except KeyError:
        candidates = close.loc[:start_str]
        start_val  = float(candidates.iloc[-1]) if not candidates.empty else float(close.iloc[0])
    perf_bench   = (prix / start_val - 1) * 100 if start_val else None
    gap          = perf_tot_pct - perf_bench if perf_bench is not None else None
    perf_bench_j = (prix - prev) / prev * 100 if prev and prev != 0 else None
    return perf_bench, gap, prix, perf_bench_j

# =============================================================================
# ██  BLOC 10 : FISCAL
# =============================================================================

def net_apres_impots(enveloppe, montant, val_poche, gain_poche):
    if montant <= 0:
        return 0.0, ""
    if montant > val_poche:
        return 0.0, "⚠️ Montant supérieur à la valeur de la poche"
    ratio_gain   = gain_poche / val_poche if val_poche else 0
    gain_retrait = montant * ratio_gain
    now_tz       = datetime.now(ZoneInfo("Europe/Paris"))
    if enveloppe == "PEA":
        limite = datetime(2031, 4, 1, tzinfo=ZoneInfo("Europe/Paris"))
        if now_tz < limite:
            return 0.0, "⚠️ Retrait PEA impossible avant le 01/04/2031 (fermeture enveloppe)"
        return montant - 0.172 * gain_retrait, ""
    if enveloppe == "AV":
        limite_8ans = datetime(2033, 9, 17, tzinfo=ZoneInfo("Europe/Paris"))
        if now_tz < limite_8ans:
            return montant - 0.30 * gain_retrait, ""
        ps = 0.172 * gain_retrait
        ir = 0.128 * max(0, gain_retrait - 9200)
        return montant - ps - ir, ""
    return montant, ""

# =============================================================================
# ██  BLOC 11 : VISUALISATIONS — RADAR & PERFORMANCE RELATIVE
# =============================================================================

def plot_radar(score_details: dict, nom: str) -> go.Figure:
    cats   = ["Tendance", "Macro", "Leadership", "Volumes", "Momentum", "Structure"]
    vals   = [score_details["radar"][c] for c in cats]
    cats_c = cats + [cats[0]]
    vals_c = vals + [vals[0]]

    total = score_details["total"]
    color = "#D4AF37" if total >= 4 else "#22C55E" if total >= 2 else "#F97316" if total >= 0 else "#FF3131"

    fig = go.Figure()
    # Zone neutre (référence 5/10)
    fig.add_trace(go.Scatterpolar(
        r=[5]*7, theta=cats_c,
        line=dict(color="#3D4454", width=1, dash="dot"),
        fill="toself", fillcolor="rgba(255,255,255,0.02)",
        showlegend=False, name="Neutre"
    ))
    # Score actuel
    fig.add_trace(go.Scatterpolar(
        r=vals_c, theta=cats_c,
        fill="toself",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.18)",
        line=dict(color=color, width=2.5),
        showlegend=False, name=nom
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 10], gridcolor="#2E3340",
                            tickfont=dict(size=8, color="#6B7585"), tickvals=[2.5, 5, 7.5, 10],
                            ticktext=["", "", "", ""], showticklabels=False),
            angularaxis=dict(gridcolor="#2E3340", tickfont=dict(size=11, color="#CBD5E1",
                             family="DM Sans")),
        ),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#CBD5E1"),
        margin=dict(t=30, b=30, l=50, r=50), height=330, showlegend=False,
    )
    return fig


def plot_relative_perf(data: dict, ticker: str, nom: str) -> go.Figure | None:
    world_df = None
    for wt in WORLD_TICKERS:
        df = data.get(wt, pd.DataFrame())
        if not df.empty and "Close" in df.columns:
            world_df = df
            break
    sat_df = data.get(ticker, pd.DataFrame())
    if world_df is None or sat_df is None or sat_df.empty:
        return None
    wc     = world_df["Close"].dropna()
    sc     = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 20:
        return None
    # Fenêtre : depuis DATE_DEBUT ou 120j max
    cutoff = max(DATE_DEBUT.date(), (datetime.now() - timedelta(days=120)).date())
    common_f = [d for d in common if d.date() >= cutoff]
    if len(common_f) < 5:
        common_f = list(common[-90:])
    ratio = (sc[common_f] / wc[common_f])
    rel   = (ratio / ratio.iloc[0] - 1) * 100

    colors_pos = ["rgba(212,175,55,0.3)"  if v >= 0 else "rgba(255,49,49,0.0)"  for v in rel.values]
    colors_neg = ["rgba(255,49,49,0.3)"   if v < 0  else "rgba(212,175,55,0.0)" for v in rel.values]

    fig = go.Figure()
    # Fill positive
    fig.add_trace(go.Scatter(
        x=rel.index, y=rel.values.clip(min=0),
        fill="tozeroy", fillcolor="rgba(212,175,55,0.12)",
        line=dict(color="rgba(0,0,0,0)", width=0), showlegend=False,
    ))
    # Fill negative
    fig.add_trace(go.Scatter(
        x=rel.index, y=rel.values.clip(max=0),
        fill="tozeroy", fillcolor="rgba(255,49,49,0.12)",
        line=dict(color="rgba(0,0,0,0)", width=0), showlegend=False,
    ))
    # Main line
    fig.add_trace(go.Scatter(
        x=rel.index, y=rel.values,
        line=dict(color="#D4AF37", width=2),
        name=f"{nom} / World (%)",
    ))
    # Fenêtre 14j
    if len(rel) >= 14:
        last14 = rel.iloc[-14:]
        fig.add_vrect(x0=last14.index[0], x1=last14.index[-1],
                      fillcolor="rgba(0,123,255,0.06)", layer="below", line_width=0)
        fig.add_annotation(
            x=last14.index[-1], y=float(last14.max()) * 1.05,
            text="◀ 14j", font=dict(color="#007BFF", size=9),
            showarrow=False, xanchor="right"
        )
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=0.7)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CBD5E1", family="DM Sans"),
        margin=dict(t=20, b=20, l=50, r=20), height=200,
        showlegend=False,
        xaxis=dict(gridcolor="#2E3340", showgrid=True),
        yaxis=dict(gridcolor="#2E3340", showgrid=True, ticksuffix="%"),
        title=dict(text=f"Performance relative : {nom} vs MSCI World",
                   font=dict(size=12, color="#6B7585"), x=0)
    )
    return fig

# =============================================================================
# ██  BLOC 12 : RÈGLES DÉCISIONNELLES (compatibilité v3.4)
# =============================================================================

def evaluate_hydrogen(anrj):
    if anrj is None:
        return "⚠️ ANRJ données indisponibles", "gray"
    p = anrj["prix"]
    if p < 706.06:
        return "🚨 STOP-LOSS DÉCLENCHÉ", "red"
    if p > 812 and anrj["rsi"] and anrj["rsi"] > 68:
        return "💰 TAKE PROFIT 30% recommandé", "green"
    if anrj["ath30"] and p < anrj["ath30"] * 0.95:
        return "🔶 ALLÉGEMENT PRÉVENTIF (–5% vs ATH30)", "orange"
    if anrj["sma20"] and p < anrj["sma20"]:
        return "🔶 SOUS SMA20 — Surveillance active", "orange"
    if anrj["sma50"] and p > anrj["sma50"]:
        return "✅ MAINTIEN — Au-dessus SMA50", "green"
    return "ℹ️ SURVEILLANCE NEUTRE", "orange"


def evaluate_em_asia(aasi):
    if aasi is None:
        return "⚠️ AASI données indisponibles", "gray"
    p = aasi["prix"]
    if p > 60.35:
        if aasi["ath30"] and p < aasi["ath30"] * 0.92:
            return "🎯 TRAILING STOP –8% ATH déclenché", "red"
        return "📈 TRAILING STOP ACTIF — Surveiller", "green"
    if aasi["sma20"] and p < aasi["sma20"]:
        return "🔶 SOUS SMA20 — Surveillance active", "orange"
    if aasi["sma50"] and p > aasi["sma50"]:
        return "✅ MAINTIEN — Au-dessus SMA50", "green"
    return "ℹ️ SURVEILLANCE NEUTRE", "orange"


def evaluate_sentinelles(data, live_prices):
    alerts, rows = [], []
    for name, tickers in SENTINELLES.items():
        info = None
        for tk in tickers:
            info = analyze_ticker(data, live_prices, tk)
            if info:
                break
        alerte = ""
        if info and info["sma20"] and info["prix"] < info["sma20"]:
            alerte = "⚠️"
            alerts.append(name)
        rows.append({
            "Sentinelle": name,
            "Prix":   f"{info['prix']:.2f}"  if info else "N/A",
            "SMA20":  f"{info['sma20']:.2f}" if (info and info["sma20"]) else "N/A",
            "RSI":    f"{info['rsi']:.1f}"   if (info and info["rsi"])   else "N/A",
            "Alerte": alerte,
        })
    msg = " | ".join([f"⚠️ {a} sous SMA20" for a in alerts]) if alerts else "✅ Sentinelles OK"
    col = "orange" if alerts else "green"
    return msg, col, rows


def determine_phase(gap, anrj, aasi, proxies_a, proxies_em):
    if gap is None:
        return "⏳ Phase indéterminée — Données insuffisantes", "#374151"
    if gap < 0:
        return "📉 Phase 1 : Reconquête — Revenir à l'équilibre vs World AV", "#7F1D1D"
    signals = []
    if anrj and anrj["sma20"] and anrj["prix"] < anrj["sma20"]:
        signals.append("ANRJ<SMA20")
    if aasi and aasi["sma20"] and aasi["prix"] < aasi["sma20"]:
        signals.append("AASI<SMA20")
    proxies_sous = sum(1 for v in {**proxies_a, **proxies_em}.values()
                      if v and v.get("sma20") and v["prix"] < v["sma20"])
    if proxies_sous >= 2:
        signals.append(f"{proxies_sous} proxies<SMA20")
    if signals:
        return f"🔄 Phase 3 : Rotation — Sécuriser les gains ({', '.join(signals)})", "#78350F"
    return "🚀 Phase 2 : Alpha — Battre le MSCI World", "#14532D"

# =============================================================================
# ██  BLOC 13 : CHARGEMENT DES DONNÉES
# =============================================================================

with st.spinner("📡 Récupération des prix en direct..."):
    LIVE = load_all_live_prices()

with st.spinner("📊 Chargement de l'historique technique (600j)..."):
    DATA = load_all_data()

if not LIVE:
    st.error("❌ Aucun prix live. Vérifiez votre connexion.")
    st.stop()

ptf               = compute_portfolio(positions_conf, capital_reel, ajustement_pat, bonus_fortuneo, LIVE)
positions_calculees = ptf["positions"]
valeur_totale       = ptf["valeur_totale"]
solde_total         = ptf["solde_total"]
gain_reel           = ptf["gain_reel"]
val_env             = ptf["val_env"]
gain_env            = ptf["gain_env"]

perf_bench, gap, bench_prix, perf_bench_j = compute_benchmark(
    DATA, LIVE, positions_conf, ptf["perf_tot_pct"])

anrj_info  = analyze_ticker(DATA, LIVE, "ANRJ.PA")
aasi_info  = analyze_ticker(DATA, LIVE, "AASI.PA")
proxies_a  = {tk: analyze_ticker(DATA, LIVE, tk) for tk in PROXIES_ANRJ}
proxies_em = {tk: analyze_ticker(DATA, LIVE, tk) for tk in PROXIES_AASI}

h_msg, h_col = evaluate_hydrogen(anrj_info)
a_msg, a_col = evaluate_em_asia(aasi_info)
s_msg, s_col, sent_rows = evaluate_sentinelles(DATA, LIVE)
phase_text, phase_color = determine_phase(gap, anrj_info, aasi_info, proxies_a, proxies_em)

macro_info = {}
for sym in MACRO_TICKERS:
    lp    = LIVE.get(sym, {})
    prix_m = lp.get("prix")
    prev_m = lp.get("prev")
    macro_info[sym] = {"prix": prix_m, "prev": prev_m} if prix_m else None

# ── Score Engine ───────────────────────────────────────────────────────────────
score_h = get_institutional_score("ANRJ.PA", "hydrogen", DATA, LIVE, macro_info)
score_a = get_institutional_score("AASI.PA", "em_asia",  DATA, LIVE, macro_info)
scores  = {"Global Hydrogen": score_h, "EM Asia": score_a}

# ── Arbitrage Chirurgical ─────────────────────────────────────────────────────
arb_actions = compute_strategic_arbitrage(positions_calculees, valeur_totale, scores)

# ── Alertes Leadership ────────────────────────────────────────────────────────
leadership_alerts = check_leadership_alerts(DATA)

now        = datetime.now(ZoneInfo("Europe/Paris"))
live_ok    = sum(1 for v in LIVE.values() if v.get("prix"))
live_total = len(LIVE)


def sign_str(v):
    return "+" if v >= 0 else ""

# =============================================================================
# ██  SECTION UI 1 : HEADER
# =============================================================================

st.markdown(
    '<div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:.2rem;">'
    '<span style="font-family:Space Mono,monospace;font-size:1.6rem;font-weight:700;color:#D4AF37;">◈</span>'
    '<span style="font-size:1.5rem;font-weight:700;color:#E2E8F0;">COCKPIT DÉCISIONNEL</span>'
    '<span style="font-family:Space Mono,monospace;font-size:.9rem;color:#6B7585;">'
    'v4.0 · INSTITUTIONAL GRADE</span>'
    '</div>',
    unsafe_allow_html=True
)
col_hd1, col_hd2 = st.columns([3, 1])
with col_hd1:
    st.caption(f"Prix live (fast_info) · {now.strftime('%d/%m/%Y %H:%M:%S')} (Paris) · Cache 30s/90s")
with col_hd2:
    live_pct  = live_ok / live_total * 100 if live_total else 0
    badge_clr = "#22C55E" if live_pct >= 80 else "#F97316" if live_pct >= 50 else "#FF3131"
    st.markdown(
        f'<div style="text-align:right;padding-top:.2rem;">'
        f'<span class="badge" style="background:{badge_clr};color:{"#0B0E15" if live_pct>=80 else "white"};">'
        f'📡 {live_ok}/{live_total} LIVE</span></div>',
        unsafe_allow_html=True
    )

if mode_direct:
    st.markdown('<div class="mode-direct-banner">🔌 MODE DIRECT ACTIF — Ajustements désactivés · Valeur marchande pure</div>',
                unsafe_allow_html=True)

st.markdown(
    f'<div class="phase-banner" style="background-color:{phase_color};color:white;">'
    f'{phase_text}</div>', unsafe_allow_html=True
)

# ── Alertes Leadership ─────────────────────────────────────────────────────────
for al in leadership_alerts:
    gap_val = al["gap"]
    nom_al  = al["nom"]
    s_pf    = al["sat_perf"]
    w_pf    = al["world_perf"]
    if gap_val < -5:
        cls_al = "alert-critical"
        ico    = "🚨"
    elif gap_val < -2:
        cls_al = "alert-leadership"
        ico    = "⚠️"
    else:
        continue
    st.markdown(
        f'<div class="{cls_al}">'
        f'{ico} <b>ALERTE LEADERSHIP : {nom_al}</b> — '
        f'Sous-performance persistante de <b>{abs(gap_val):.1f}%</b> vs World sur 14 jours glissants. '
        f'({nom_al} : {sign_str(s_pf)}{s_pf:.1f}% vs World : {sign_str(w_pf)}{w_pf:.1f}%) — '
        f'Coût d\'opportunité détecté.'
        f'</div>', unsafe_allow_html=True
    )

# =============================================================================
# ██  SECTION UI 2 : COMMAND CENTER — KPIs
# =============================================================================

st.markdown("## 🚀 Command Center")
c1, c2, c3, c4 = st.columns(4)

with c1:
    crd = "card card-gold" if not mode_direct else "card card-purple"
    lbl = "Valeur Titres Brute" if mode_direct else "Solde Total Portefeuille"
    st.markdown(f'<div class="{crd}">', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-label">{lbl}<span class="live-badge">LIVE</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-value">{solde_total:,.2f}€</div>', unsafe_allow_html=True)
    clr = "pos" if ptf["perf_j_eur"] >= 0 else "neg"
    st.markdown(
        f'<div class="kpi-delta-{clr}">{sign_str(ptf["perf_j_eur"])}{ptf["perf_j_eur"]:,.2f}€ '
        f'({sign_str(ptf["perf_j_pct"])}{ptf["perf_j_pct"]:.2f}%) vs veille</div>',
        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    crd = "card card-blue"
    st.markdown(f'<div class="{crd}">', unsafe_allow_html=True)
    kpi2 = "Gain Boursier Brut" if mode_direct else "Gain Réel Patrimonial"
    st.markdown(f'<div class="kpi-label">{kpi2}</div>', unsafe_allow_html=True)
    g_clr = "#22C55E" if gain_reel >= 0 else "#FF3131"
    st.markdown(f'<div class="kpi-value" style="color:{g_clr};">{sign_str(gain_reel)}{gain_reel:,.2f}€</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="small">Capital réel : {ptf["capital_reel"]:,.2f}€</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    crd = "card card-blue"
    st.markdown(f'<div class="{crd}">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Performance Totale</div>', unsafe_allow_html=True)
    p     = ptf["perf_tot_pct"]
    p_clr = "#22C55E" if p >= 0 else "#FF3131"
    st.markdown(f'<div class="kpi-value" style="color:{p_clr};">{sign_str(p)}{p:.2f}%</div>',
                unsafe_allow_html=True)
    if gap is not None:
        g2_clr = "#22C55E" if gap >= 0 else "#FF3131"
        st.markdown(f'<div class="small">GAP vs World : <span style="color:{g2_clr};font-weight:700;">'
                    f'{sign_str(gap)}{gap:.2f}%</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Benchmark MSCI World<span class="live-badge">LIVE</span></div>',
                unsafe_allow_html=True)
    if perf_bench is not None:
        pb_clr = "#22C55E" if perf_bench >= 0 else "#FF3131"
        st.markdown(f'<div class="kpi-value" style="color:{pb_clr};">{sign_str(perf_bench)}{perf_bench:.2f}%</div>',
                    unsafe_allow_html=True)
        if perf_bench_j is not None:
            pj_clr = "pos" if perf_bench_j >= 0 else "neg"
            st.markdown(f'<div class="kpi-delta-{pj_clr}">{sign_str(perf_bench_j)}{perf_bench_j:.2f}% vs veille</div>',
                        unsafe_allow_html=True)
    else:
        st.markdown('<div class="kpi-value">N/A</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Positions + Donut ─────────────────────────────────────────────────────────
st.markdown("### 📊 Positions détaillées")
col_tab, col_pie = st.columns([3, 2])
with col_tab:
    rows = []
    for p in positions_calculees:
        perf_f = f"{sign_str(p['perf_pct'])}{p['perf_pct']:.2f}%" if p["perf_pct"] is not None else "N/A"
        vj_f   = f"{sign_str(p['var_jour_pct'])}{p['var_jour_pct']:.2f}%" if p["var_jour_pct"] else "–"
        vje_f  = f"{sign_str(p['var_jour_eur'])}{p['var_jour_eur']:,.2f}€" if p["var_jour_eur"] else "–"
        prix_f = f"{p['prix']:.3f}€" if p["prix"] else "N/A"
        rows.append({"Position": p["nom"], "Env.": p["enveloppe"], "Prix live": prix_f,
                     "Valeur (€)": f"{p['valeur']:,.2f}", "Perf.": perf_f,
                     "Δ Jour (%)": vj_f, "Δ Jour (€)": vje_f})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if not mode_direct:
        st.markdown(
            f'<div class="info-box">Ajust. patrimonial : +{ptf["ajustement_pat"]:,.2f}€ → '
            f'Solde total : <b>{solde_total:,.2f}€</b></div>', unsafe_allow_html=True)

with col_pie:
    donut_data = [p for p in positions_calculees if p["valeur"] > 0]
    if donut_data:
        colors_pie = ["#007BFF","#6366F1","#D4AF37","#F97316","#22C55E"]
        fig_pie = go.Figure(go.Pie(
            labels=[d["nom"] for d in donut_data],
            values=[d["valeur"] for d in donut_data],
            hole=0.6, textinfo="percent",
            marker=dict(colors=colors_pie[:len(donut_data)],
                        line=dict(color="#1C1F26", width=2)),
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E1"), margin=dict(t=10,b=10,l=10,r=10), height=280,
            legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            annotations=[dict(text=f"{valeur_totale:,.0f}€", x=.5, y=.5,
                              font=dict(size=13, color="#D4AF37", family="Space Mono"),
                              showarrow=False)]
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# =============================================================================
# ██  SECTION UI 3 : SCORE ENGINE — HYDROGÈNE
# =============================================================================

st.markdown("## 🧠 Score Stratégique Multi-Couches")

def render_score_section(nom_sat, ticker_sat, theme_sat, score_data, arb_actions,
                          positions_calculees, valeur_totale):
    """Affiche le panneau Executive : Radar (gauche) + Carte Décision (droite)."""
    total = score_data["total"]
    if total >= 4:
        score_cls = "score-pos"
        card_border = "card-gold"
    elif total >= 0:
        score_cls = "score-neut"
        card_border = "card-orange"
    else:
        score_cls = "score-neg"
        card_border = "card-red"

    status_label, status_cls = get_status_label(total)

    arb = next((a for a in arb_actions if a["nom"] == nom_sat), None)

    # Trouver la valeur actuelle
    current_val = next((p["valeur"] for p in positions_calculees if p["nom"] == nom_sat), 0)

    st.markdown(f'<div class="card {card_border}" style="padding:0;overflow:hidden;">', unsafe_allow_html=True)

    col_radar, col_decision = st.columns([1, 1])

    # ── Colonne Gauche : Radar Chart ──────────────────────────────────────────
    with col_radar:
        st.markdown(
            f'<div style="padding:1.4rem 1.4rem 0.5rem 1.4rem;">'
            f'<div class="kpi-label">{nom_sat} — Analyse 6 Couches</div>'
            f'</div>', unsafe_allow_html=True
        )
        fig_radar = plot_radar(score_data, nom_sat)
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

        # Détail des couches
        st.markdown('<div style="padding:0 1.4rem 1rem 1.4rem;">', unsafe_allow_html=True)
        for layer_name, layer_val, layer_desc in score_data["details"]:
            if layer_val is None:
                color_l = "#6B7585"
                bar_pct = "50%"
                bar_clr = "#374151"
                val_str = layer_desc
            else:
                if layer_val > 0:
                    color_l, bar_clr = "#22C55E", "#22C55E"
                elif layer_val < 0:
                    color_l, bar_clr = "#FF3131", "#FF3131"
                else:
                    color_l, bar_clr = "#6B7585", "#374151"
                # Normalise bar: map value to 0-100%
                max_abs = {"Tendance": 2, "Macro": 1, "Leadership": 2, "Volumes": 1}.get(layer_name, 1)
                bar_pct = f"{int((layer_val / max_abs + 1) / 2 * 100)}%"
                val_str = f"{'+' if layer_val > 0 else ''}{layer_val}"

            st.markdown(
                f'<div class="layer-row">'
                f'<span class="layer-name">{layer_name}</span>'
                f'<div class="layer-bar-wrap">'
                f'<div style="background:{bar_clr};width:{bar_pct};height:8px;border-radius:4px;transition:width .4s;"></div>'
                f'</div>'
                f'<span class="layer-val" style="color:{color_l};">{val_str if layer_val is not None else "—"}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Colonne Droite : Carte de Décision ───────────────────────────────────
    with col_decision:
        st.markdown('<div style="padding:1.4rem;">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-label">Score Institutionnel Final</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="margin:.5rem 0 .8rem 0;">'
            f'<span class="score-badge {score_cls}">{sign_str(total) if total != 0 else ""}{total}/5</span>'
            f'</div>', unsafe_allow_html=True
        )
        st.markdown(f'<div class="{status_cls}">{status_label}</div>', unsafe_allow_html=True)

        st.markdown('<div style="margin-top:1rem; margin-bottom:.4rem;">'
                    '<div class="kpi-label">Arbitrage Chirurgical</div></div>', unsafe_allow_html=True)

        if arb:
            target_pct = arb["target_pct"]
            cur_pct    = arb["current_pct"]
            montant    = abs(arb["montant"])
            action     = arb["action"]

            if action == "VENDRE":
                st.markdown(
                    f'<div class="arb-sell">'
                    f'<div style="font-size:.75rem;color:#FF3131;letter-spacing:1px;margin-bottom:.3rem;">🚨 ACTION REQUISE</div>'
                    f'<div style="font-size:1.4rem;color:#FCA5A5;font-weight:700;">VENDRE {montant:,.2f}€</div>'
                    f'<div style="font-size:.82rem;color:#8892AA;margin-top:.4rem;">'
                    f'de {nom_sat} → renforcer MSCI World</div>'
                    f'<div style="margin-top:.6rem;font-size:.78rem;color:#6B7585;">'
                    f'Poids actuel : <span style="color:#FCA5A5;">{cur_pct:.1f}%</span> → '
                    f'Cible score : <span style="color:#22C55E;">{target_pct:.0f}%</span>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            elif action == "ACHETER":
                st.markdown(
                    f'<div class="arb-buy">'
                    f'<div style="font-size:.75rem;color:#22C55E;letter-spacing:1px;margin-bottom:.3rem;">💡 OPPORTUNITÉ</div>'
                    f'<div style="font-size:1.4rem;color:#86EFAC;font-weight:700;">ACHETER {montant:,.2f}€</div>'
                    f'<div style="font-size:.82rem;color:#8892AA;margin-top:.4rem;">'
                    f'de {nom_sat} · Score favorable</div>'
                    f'<div style="margin-top:.6rem;font-size:.78rem;color:#6B7585;">'
                    f'Poids actuel : <span style="color:#86EFAC;">{cur_pct:.1f}%</span> → '
                    f'Cible : <span style="color:#D4AF37;">{target_pct:.0f}%</span>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="arb-neutral">'
                    f'<div style="font-size:.75rem;color:#6B7585;letter-spacing:1px;margin-bottom:.3rem;">✅ STATU QUO</div>'
                    f'<div style="font-size:1.1rem;color:#CBD5E1;font-weight:600;">MAINTENIR</div>'
                    f'<div style="font-size:.82rem;color:#8892AA;margin-top:.4rem;">'
                    f'Poids {cur_pct:.1f}% ≈ Cible {target_pct:.0f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # Mini métriques
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Valeur actuelle", f"{arb['current_value']:,.0f}€")
            col_m2.metric("Cible (€)", f"{arb['target_value']:,.0f}€")
            col_m3.metric("Δ score", f"{sign_str(total)}{total}/5")

        else:
            st.info("Données arbitrage indisponibles")

        # Mini indicateurs techniques
        info_t = analyze_ticker(DATA, LIVE, ticker_sat)
        if info_t:
            st.markdown('<div class="kpi-label" style="margin-top:1rem;">Indicateurs clés</div>',
                        unsafe_allow_html=True)
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            col_t1.metric("Prix", f"{info_t['prix']:.2f}€")
            col_t2.metric("SMA50",  f"{info_t['sma50']:.2f}€"  if info_t["sma50"]  else "–")
            col_t3.metric("SMA200", f"{info_t['sma200']:.2f}€" if info_t["sma200"] else "–")
            col_t4.metric("RSI",    f"{info_t['rsi']:.1f}"     if info_t["rsi"]    else "–")

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close card

    # ── Graphique Performance Relative ────────────────────────────────────────
    fig_rel = plot_relative_perf(DATA, ticker_sat, nom_sat)
    if fig_rel:
        st.plotly_chart(fig_rel, use_container_width=True, config={"displayModeBar": False})


# ── Hydrogène ──────────────────────────────────────────────────────────────────
render_score_section(
    "Global Hydrogen", "ANRJ.PA", "hydrogen",
    score_h, arb_actions, positions_calculees, valeur_totale
)

st.markdown("<br>", unsafe_allow_html=True)

# ── EM Asia ───────────────────────────────────────────────────────────────────
render_score_section(
    "EM Asia", "AASI.PA", "em_asia",
    score_a, arb_actions, positions_calculees, valeur_totale
)

# =============================================================================
# ██  SECTION UI 4 : SENTINELLES & MACRO
# =============================================================================

st.markdown("## 🛰️ Sentinelles & Flash Macro")
col_sent, col_macro = st.columns([3, 2])

with col_sent:
    st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
    st.markdown("### 📡 Sentinelles sectorielles")
    if "OK" in s_msg:
        st.success(s_msg)
    else:
        st.warning(s_msg)
    st.dataframe(pd.DataFrame(sent_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### ⚖️ Poids Satellites vs Cible")
    anrj_val = next((p["valeur"] for p in positions_calculees if p["nom"] == "Global Hydrogen"), 0)
    aasi_val = next((p["valeur"] for p in positions_calculees if p["nom"] == "EM Asia"), 0)
    poids_sat = (anrj_val + aasi_val) / valeur_totale * 100 if valeur_totale else 0
    delta_poids = poids_sat - 45
    col_pw1, col_pw2 = st.columns(2)
    col_pw1.metric("ANRJ + AASI", f"{poids_sat:.1f}%",
                   delta=f"{sign_str(delta_poids)}{delta_poids:.1f}% vs 45%")
    bar_clr = "#FF3131" if poids_sat > 45 else "#22C55E"
    st.markdown(
        f'<div style="background:#1C1F26;border-radius:6px;height:8px;margin-top:.3rem;">'
        f'<div style="background:{bar_clr};width:{min(poids_sat,100):.1f}%;height:8px;border-radius:6px;"></div>'
        f'</div>', unsafe_allow_html=True
    )
    st.markdown("#### 🎯 Cible 94% World / 6% Or")
    val_world = sum(p["valeur"] for p in positions_calculees if "MSCI World" in p["nom"])
    val_gold  = sum(p["valeur"] for p in positions_calculees if "Or" in p["nom"])
    pw_act = val_world / valeur_totale * 100 if valeur_totale else 0
    pg_act = val_gold  / valeur_totale * 100 if valeur_totale else 0
    col_cw, col_cg = st.columns(2)
    col_cw.metric("MSCI World",  f"{pw_act:.1f}%", delta=f"{pw_act-94:.1f}% vs 94%")
    col_cg.metric("Or Physique", f"{pg_act:.1f}%", delta=f"{pg_act-6:.1f}% vs 6%")
    st.markdown('</div>', unsafe_allow_html=True)

with col_macro:
    st.markdown('<div class="card card-gold">', unsafe_allow_html=True)
    st.markdown("### 🌍 Flash Macro <span class='live-badge'>LIVE</span>", unsafe_allow_html=True)
    FMT = {"NQ=F":".2f","ES=F":".2f","^TNX":".3f","EURUSD=X":".4f",
           "BZ=F":".2f","GC=F":".2f","DX-Y.NYB":".2f","MCHI":".2f"}
    SFX = {"^TNX":"%","BZ=F":"$","GC=F":"$","NQ=F":"","ES=F":"","EURUSD=X":"","DX-Y.NYB":"","MCHI":""}
    SIGNALS = {"^TNX": (4.50, "↑ Défavorable hydro", "↓ OK hydro"),
               "DX-Y.NYB": (105.0, "↑ Pression EM", "↓ OK EM")}
    for sym, label in MACRO_TICKERS.items():
        info_m = macro_info.get(sym)
        if info_m and info_m.get("prix"):
            p_val = info_m["prix"]
            prev_m = info_m.get("prev")
            delta_m = (
                f'{sign_str((p_val-prev_m)/prev_m*100)}{(p_val-prev_m)/prev_m*100:.2f}%'
                if prev_m and prev_m != 0 else None
            )
            signal_info = SIGNALS.get(sym)
            extra_lbl   = None
            if signal_info:
                threshold, lbl_up, lbl_dn = signal_info
                extra_lbl = lbl_up if p_val > threshold else lbl_dn
            display_val = f"{p_val:{FMT.get(sym,'.2f')}}{SFX.get(sym,'')}"
            if extra_lbl:
                display_val += f"  {extra_lbl}"
            st.metric(label, display_val, delta=delta_m)
        else:
            st.metric(label, "N/A")
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ██  SECTION UI 5 : SIMULATEUR FISCAL
# =============================================================================

st.markdown("## 🧮 Simulateur Fiscal")
col_pea, col_av = st.columns(2)

with col_pea:
    st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
    st.markdown("#### 🏦 PEA")
    net, avert = net_apres_impots("PEA", val_env["PEA"], val_env["PEA"], gain_env["PEA"])
    if avert:
        st.warning(avert)
        st.metric("Valeur brute PEA", f"{val_env['PEA']:,.2f}€")
    else:
        st.metric("Net après PS 17.2%", f"{net:,.2f}€")
    st.caption(f"Gain latent PEA : {sign_str(gain_env['PEA'])}{gain_env['PEA']:,.2f}€")
    st.markdown('</div>', unsafe_allow_html=True)

with col_av:
    st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
    st.markdown("#### 🛡️ Assurance-Vie")
    net, avert = net_apres_impots("AV", val_env["AV"], val_env["AV"], gain_env["AV"])
    if avert:
        st.warning(avert)
        st.metric("Valeur brute AV", f"{val_env['AV']:,.2f}€")
    else:
        st.metric("Net après fiscalité AV", f"{net:,.2f}€")
    st.caption(f"Gain latent AV : {sign_str(gain_env['AV'])}{gain_env['AV']:,.2f}€")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 💸 Simulateur de retrait partiel")
sc1, sc2 = st.columns([2, 1])
with sc2:
    env_sim = st.selectbox("Enveloppe", ["AV", "PEA"])
with sc1:
    max_val     = float(max(val_env.get(env_sim, 0), 1000))
    montant_sim = st.slider("Montant à retirer (€)", 0.0, max_val,
                             min(1000.0, max_val), step=100.0)
net_sim, avert_sim = net_apres_impots(env_sim, montant_sim,
                                       val_env.get(env_sim, 0), gain_env.get(env_sim, 0))
if avert_sim:
    st.warning(avert_sim)
elif montant_sim > 0:
    vp, gp   = val_env.get(env_sim, 0), gain_env.get(env_sim, 0)
    ratio    = gp / vp if vp else 0
    gain_sim = montant_sim * ratio
    imp_sim  = montant_sim - net_sim
    st.markdown(
        f'<div class="net-box" style="display:flex;gap:2.5rem;flex-wrap:wrap;align-items:center;">'
        f'<div><div class="kpi-label">Brut retiré</div><div class="kpi-value">{montant_sim:,.2f}€</div></div>'
        f'<div style="color:#6B7585;font-size:1.5rem;">→</div>'
        f'<div><div class="kpi-label">Part gains</div><div class="kpi-value" style="color:#D4AF37;">{gain_sim:,.2f}€</div></div>'
        f'<div><div class="kpi-label">Impôts/PS</div><div class="kpi-value" style="color:#FF3131;">{imp_sim:,.2f}€</div></div>'
        f'<div><div class="kpi-label">Net perçu</div><div class="kpi-value" style="color:#22C55E;">{net_sim:,.2f}€</div></div>'
        f'</div>', unsafe_allow_html=True
    )
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ██  FOOTER
# =============================================================================

st.markdown("---")
col_f1, col_f2 = st.columns([4, 1])
with col_f1:
    mode_txt  = "🔌 MODE DIRECT" if mode_direct else f"Ajust. {ajustement_pat_input:,.2f}€"
    cfg_txt   = f"Config : {_CONFIG_PATH}" if os.path.exists(_CONFIG_PATH) else "Config : défauts"
    score_txt = f"Score H={sign_str(score_h['total'])}{score_h['total']}/5 · EM={sign_str(score_a['total'])}{score_a['total']}/5"
    st.caption(
        f"◈ Cockpit v4.0 Institutional · {mode_txt} · {score_txt} · "
        f"Capital {capital_reel_input:,.2f}€ · {cfg_txt} · "
        "Outil personnel — Ne constitue pas un conseil en investissement"
    )
with col_f2:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
