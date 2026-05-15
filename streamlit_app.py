# =============================================================================
# COCKPIT DÉCISIONNEL BOURSIER v5.4 — "PLATEFORME PÉDAGOGIQUE INSTITUTIONNELLE"
# Lead Dev: Claude (Anthropic)
# v5.3 → v5.4 :
#   • Benchmark World "Cash-Flow Adjusted" (MWR) : simulation achat MWRD.PA
#     aux dates exactes des flux réels — Gap vs World désormais basé sur ce calcul
#   • Fix Or Physique : système de fallback tickers (GOLD-EUR.PA → FGLDA.DE → XAD5.MI)
#     + .dropna() systématique avant corrélation — élimine les N/A
#   • Persistance JSON des positions : sidebar DCA avec Parts+PRM éditables
#     et bouton 💾 → config_perso.json, chargement automatique au démarrage
#   • Toute la logique v5.3 préservée intégralement (pédagogie, score, fiscal…)
#
#   Requis dans requirements.txt :
#     streamlit yfinance pandas numpy plotly PyGithub
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 0 : IMPORTS & PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json, os, sqlite3, io, csv, warnings
from typing import Optional, Dict, List, Tuple
warnings.filterwarnings("ignore")

try:
    from github import Github, InputFileContent
    PYGITHUB_OK = True
except ImportError:
    PYGITHUB_OK = False

st.set_page_config(
    page_title="Cockpit v5.4 · Pédagogique",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 : CSS — DESIGN SYSTEM INSTITUTIONNEL MOBILE-FIRST (v5.3 inchangé)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
.stApp { background-color: #1C1F26; font-family: 'DM Sans', sans-serif; }
section[data-testid="stSidebar"] {
    background-color: #22252E; border-right: 1px solid #2E3340;
}
.stApp > header { background-color: #1C1F26; }
.main .block-container { padding-top: 1.2rem; max-width: 1400px; }

/* ── Cards ── */
.card {
    background: linear-gradient(145deg, #252932 0%, #2A2D38 100%);
    border-radius: 12px; padding: 1.4rem; margin-bottom: 1rem;
    box-shadow: 0 4px 24px rgba(0,0,0,.35), 0 1px 0 rgba(255,255,255,.03);
    border: 1px solid #32363F;
}
.card-gold   { border-left: 4px solid #D4AF37; }
.card-blue   { border-left: 4px solid #007BFF; }
.card-red    { border-left: 4px solid #FF3131; }
.card-orange { border-left: 4px solid #F97316; }
.card-green  { border-left: 4px solid #22C55E; }
.card-purple { border-left: 4px solid #A855F7;
               background: linear-gradient(145deg, #1E1A30 0%, #221D35 100%); }
.card-regime { border-left: 4px solid #00D4FF; }

/* ── KPIs ── */
.kpi-value { font-size:2rem; font-weight:700; color:#FFFFFF;
             font-family:'Space Mono',monospace; letter-spacing:-1px; }
.kpi-label { font-size:.72rem; color:#6B7585; text-transform:uppercase;
             letter-spacing:2px; margin-bottom:.3rem; }
.kpi-delta-pos { color:#22C55E; font-size:.82rem; font-weight:600; }
.kpi-delta-neg { color:#FF3131; font-size:.82rem; font-weight:600; }

/* ── Score Badge ── */
.score-badge {
    font-family:'Space Mono',monospace; font-size:2.6rem; font-weight:700;
    padding:.4rem 1.2rem; border-radius:10px; display:inline-block;
    border:2px solid; letter-spacing:-1px;
}
.score-pos  { color:#D4AF37; border-color:#D4AF37; background:rgba(212,175,55,.08); }
.score-neut { color:#F97316; border-color:#F97316; background:rgba(249,115,22,.08); }
.score-neg  { color:#FF3131; border-color:#FF3131; background:rgba(255,49,49,.08); }

/* ── Regime Banner ── */
.regime-banner {
    padding:.9rem 1.6rem; border-radius:12px; font-weight:700;
    font-size:1.05rem; margin-bottom:1rem; text-align:center;
    letter-spacing:.5px; display:flex; align-items:center;
    justify-content:space-between; gap:1rem;
}
.regime-euphorie   { background:linear-gradient(135deg,#7B2D8B,#9B3DB5); color:#F3E8FF; border:1px solid #A855F7; }
.regime-expansion  { background:linear-gradient(135deg,#14532D,#166534); color:#86EFAC; border:1px solid #22C55E; }
.regime-neutre     { background:linear-gradient(135deg,#1E3A5F,#1E40AF); color:#93C5FD; border:1px solid #3B82F6; }
.regime-stress     { background:linear-gradient(135deg,#78350F,#92400E); color:#FDE68A; border:1px solid #F59E0B; }
.regime-contraction{ background:linear-gradient(135deg,#450A0A,#7F1D1D); color:#FCA5A5; border:1px solid #FF3131; box-shadow:0 0 20px rgba(255,49,49,.2); }
.regime-pending    { background:linear-gradient(135deg,#1C1F26,#22252E); color:#6B7585; border:1px dashed #374151; }

/* ── Status Labels ── */
.status-maintain  { background:linear-gradient(135deg,#2D3F1F,#344A22); color:#86EFAC;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-lighten   { background:linear-gradient(135deg,#3B3208,#453B0A); color:#FDE68A;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-vigilance { background:linear-gradient(135deg,#3B2008,#47260A); color:#FDBA74;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-reduce    { background:linear-gradient(135deg,#3B0F0F,#4A1414); color:#FCA5A5;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-exit      { background:linear-gradient(135deg,#2D0505,#3A0808); color:#FF3131;
                    padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center;
                    box-shadow:0 0 20px rgba(255,49,49,.2); }

/* ── Arbitrage Blocks ── */
.arb-sell { background:linear-gradient(135deg,#350808,#420B0B); border:1px solid #FF3131;
            border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0;
            font-family:'Space Mono',monospace; box-shadow:0 0 15px rgba(255,49,49,.15); }
.arb-buy  { background:linear-gradient(135deg,#083508,#0B4A0B); border:1px solid #22C55E;
            border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0;
            font-family:'Space Mono',monospace; }
.arb-neutral { background:linear-gradient(135deg,#1A1F26,#1E242D); border:1px solid #32363F;
               border-radius:10px; padding:1rem 1.2rem; margin:.5rem 0;
               font-family:'Space Mono',monospace; }

/* ── Risk Badges ── */
.risk-flag { background:rgba(255,49,49,.15); border:1px solid #FF3131; border-radius:6px;
             padding:.3rem .8rem; color:#FCA5A5; font-size:.78rem; font-weight:700; }
.risk-ok   { background:rgba(34,197,94,.1); border:1px solid #22C55E; border-radius:6px;
             padding:.3rem .8rem; color:#86EFAC; font-size:.78rem; font-weight:700; }

/* ── Signal Badges ── */
.bg-bull { background:#22C55E; color:#0B0E15; padding:.2rem .7rem; border-radius:20px;
           font-size:.7rem; font-weight:700; letter-spacing:.5px; }
.bg-neut { background:#F97316; color:white; padding:.2rem .7rem; border-radius:20px;
           font-size:.7rem; font-weight:700; letter-spacing:.5px; }
.bg-bear { background:#FF3131; color:white; padding:.2rem .7rem; border-radius:20px;
           font-size:.7rem; font-weight:700; letter-spacing:.5px; }

/* ── Score Table ── */
.score-table { width:100%; border-collapse:collapse; margin-top:.6rem; }
.score-table th { padding:.35rem .7rem; color:#6B7585; font-size:.72rem;
    text-transform:uppercase; letter-spacing:1.5px; text-align:left;
    border-bottom:1px solid #2E3340; }
.score-table td { padding:.5rem .7rem; font-size:.84rem;
    border-bottom:1px solid rgba(46,51,64,.6); vertical-align:middle; }
.score-table td.col-name  { color:#8892AA; font-size:.8rem; }
.score-table td.col-badge { text-align:center; }
.score-table td.col-val   { font-family:'Space Mono',monospace; font-size:.8rem; color:#CBD5E1; }

/* ── Persistence Status ── */
.persist-ok   { background:#0D1F0D; border-left:4px solid #22C55E;
                border-radius:6px; padding:.5rem 1rem; font-size:.82rem; color:#86EFAC; }
.persist-warn { background:#2D1515; border-left:4px solid #F97316;
                border-radius:6px; padding:.5rem 1rem; font-size:.82rem; color:#FDBA74; }
.persist-err  { background:#2D0505; border-left:4px solid #FF3131;
                border-radius:6px; padding:.5rem 1rem; font-size:.82rem; color:#FCA5A5; }

/* ── Misc ── */
.phase-banner { padding:.8rem 1.4rem; border-radius:10px; font-weight:700;
    font-size:.95rem; margin-bottom:1.2rem; text-align:center; }
.mode-direct-banner { background:linear-gradient(135deg,#2D1060,#38138A);
    border:1px solid #7C3AED; border-radius:10px; padding:.7rem 1.2rem;
    margin-bottom:1rem; color:#E9D5FF; font-weight:700; font-size:.9rem; text-align:center; }
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
.live-badge { display:inline-block; background:#22C55E; color:#0B0E15;
    border-radius:4px; font-size:.62rem; font-weight:800; padding:.1rem .4rem;
    letter-spacing:.5px; vertical-align:middle; margin-left:.4rem; }
.alert-leadership { background:linear-gradient(135deg,#2A1A00,#331F00);
    border:1px solid #D4AF37; border-radius:10px; padding:.9rem 1.2rem; margin:.5rem 0;
    box-shadow:0 0 20px rgba(212,175,55,.15); color:#FDE68A; font-weight:600; }
.alert-critical { background:linear-gradient(135deg,#2D0505,#380909);
    border:1px solid #FF3131; border-radius:10px; padding:.9rem 1.2rem; margin:.5rem 0;
    box-shadow:0 0 20px rgba(255,49,49,.2); color:#FCA5A5; font-weight:600; }

/* ── v5.3 STYLES PÉDAGOGIQUES (inchangés) ── */
.pedagogy-box {
    background: linear-gradient(145deg, #0D1928, #111D30);
    border: 1px solid #1E3A5F;
    border-left: 4px solid #3B82F6;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: .6rem 0;
    font-size: .88rem;
    color: #93C5FD;
    line-height: 1.6;
}
.pedagogy-box .pedagogy-title {
    font-size: .72rem;
    color: #3B82F6;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 700;
    margin-bottom: .4rem;
}
.pedagogy-box .pedagogy-scale {
    display: flex;
    gap: .5rem;
    margin-top: .5rem;
    font-size: .78rem;
    flex-wrap: wrap;
}
.scale-green  { background:rgba(34,197,94,.15);  color:#86EFAC; padding:.2rem .6rem; border-radius:4px; }
.scale-orange { background:rgba(249,115,22,.15); color:#FDBA74; padding:.2rem .6rem; border-radius:4px; }
.scale-red    { background:rgba(255,49,49,.15);  color:#FCA5A5; padding:.2rem .6rem; border-radius:4px; }

.verdict-card {
    border-radius: 14px;
    padding: 1.2rem 1.6rem;
    margin: .8rem 0;
    text-align: center;
    font-weight: 700;
    font-size: 1.1rem;
    letter-spacing: .3px;
}
.verdict-green  { background:linear-gradient(135deg,#0D2218,#0E2A1C); border:2px solid #22C55E; color:#86EFAC; box-shadow:0 0 20px rgba(34,197,94,.15); }
.verdict-orange { background:linear-gradient(135deg,#2A1800,#331F00); border:2px solid #F97316; color:#FDBA74; box-shadow:0 0 20px rgba(249,115,22,.15); }
.verdict-red    { background:linear-gradient(135deg,#2D0808,#380B0B); border:2px solid #FF3131; color:#FCA5A5; box-shadow:0 0 20px rgba(255,49,49,.2); }

.simple-score-ring {
    width: 80px; height: 80px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Space Mono', monospace;
    font-size: 1.8rem; font-weight: 700;
    margin: 0 auto;
}
.ring-5 { border: 4px solid #22C55E; color:#22C55E; background:rgba(34,197,94,.1); }
.ring-4 { border: 4px solid #86EFAC; color:#86EFAC; background:rgba(134,239,172,.08); }
.ring-3 { border: 4px solid #D4AF37; color:#D4AF37; background:rgba(212,175,55,.08); }
.ring-2 { border: 4px solid #F97316; color:#F97316; background:rgba(249,115,22,.08); }
.ring-1 { border: 4px solid #EF4444; color:#EF4444; background:rgba(239,68,68,.08); }
.ring-0 { border: 4px solid #FF3131; color:#FF3131; background:rgba(255,49,49,.08); }

.pedago-metric {
    background: #252932;
    border-radius: 10px;
    padding: 1rem;
    margin: .4rem 0;
    border: 1px solid #32363F;
}
.pedago-metric-title {
    font-size: .7rem;
    color: #6B7585;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: .3rem;
}
.pedago-metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    margin-bottom: .2rem;
}
.pedago-metric-explain {
    font-size: .82rem;
    color: #8892AA;
    line-height: 1.5;
    margin-top: .3rem;
}

.leadership-header {
    background: linear-gradient(135deg, #1A1F26, #1E2530);
    border: 1px solid #2E3340;
    border-top: 3px solid #D4AF37;
    border-radius: 12px;
    padding: 1rem 1.4rem;
    margin-bottom: 1rem;
}

/* ── v5.4 : Badge MWR ── */
.mwr-badge {
    display: inline-block;
    background: linear-gradient(135deg, #0D2035, #112845);
    border: 1px solid #3B82F6;
    border-radius: 6px;
    padding: .15rem .5rem;
    font-size: .62rem;
    font-weight: 800;
    color: #93C5FD;
    letter-spacing: .5px;
    vertical-align: middle;
    margin-left: .4rem;
}

/* Mobile optimizations */
@media (max-width: 768px) {
    .kpi-value { font-size: 1.5rem; }
    .score-badge { font-size: 1.8rem; padding: .3rem .8rem; }
    .main .block-container { padding-top: .8rem; padding-left: .5rem; padding-right: .5rem; }
    .card { padding: 1rem; }
    .verdict-card { font-size: .95rem; }
    .stButton button { min-height: 48px !important; font-size: 1rem !important; }
}

.stButton > button {
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: .5px !important;
    transition: all .2s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #D4AF37, #B8952A) !important;
    border: none !important;
    color: #0B0E15 !important;
    box-shadow: 0 4px 15px rgba(212,175,55,.3) !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2 : CONSTANTES & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

POSITIONS_BASE: List[Dict] = [
    {"nom": "MSCI World AV",   "tickers": ["MWRD.PA","IWDA.AS","EUNL.DE"], "parts": 36.33,   "prm": 140.41,  "enveloppe": "AV"},
    {"nom": "MSCI World PEA",  "tickers": ["DCAM.PA"],                      "parts": 481.0,   "prm": 5.5937,  "enveloppe": "PEA"},
    {"nom": "Global Hydrogen", "tickers": ["ANRJ.PA"],                      "parts": 4.7701,  "prm": 707.55,  "enveloppe": "AV"},
    {"nom": "EM Asia",         "tickers": ["AASI.PA"],                      "parts": 40.8272, "prm": 49.96,   "enveloppe": "AV"},
    {"nom": "Or Physique",     "tickers": ["OR-EUR.PA","DE000SLA8RU8.SG","CGLD.PA","GOLD.PA"], "parts": 4.5902, "prm": 163.39, "enveloppe": "AV"},
]

# v5.4 : tickers fallback Or pour QuantRiskEngine
GOLD_TICKERS_FALLBACK = ["GOLD-EUR.PA", "OR-EUR.PA", "FGLDA.DE", "XAD5.MI",
                          "DE000SLA8RU8.SG", "CGLD.PA", "GOLD.PA"]

_DEFAULT_CAPITAL_REEL   = 13_796.71
_DEFAULT_AJUSTEMENT_PAT = 219.97
_DEFAULT_BONUS_FORTUNEO = 160.0
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_perso.json")
_DB_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local.db")

INITIAL_TARGETS: Dict[str, float] = {
    "Global Hydrogen": 0.25,
    "EM Asia":         0.25,
}

BENCHMARK_NOM  = "MSCI World AV"
WORLD_TICKERS  = ["MWRD.PA", "IWDA.AS", "EUNL.DE", "DCAM.PA"]
PROXIES_ANRJ   = ["PLUG", "BE", "NEL.OL"]
PROXIES_AASI   = ["TSM", "005930.KS", "AAXJ"]

MACRO_TICKERS: Dict[str, str] = {
    "NQ=F":     "Nasdaq 100",
    "ES=F":     "S&P 500",
    "^TNX":     "US 10Y (%)",
    "EURUSD=X": "EUR/USD",
    "BZ=F":     "Brent ($)",
    "GC=F":     "Or ($)",
    "DX-Y.NYB": "Dollar Index",
    "MCHI":     "iShares MSCI China",
}

REGIME_TICKERS = ["SPY", "QQQ", "^VIX", "^TNX", "DX-Y.NYB", "ES=F", "NQ=F"]

SENTINELLES: Dict[str, List[str]] = {
    "TSMC":        ["TSM"],
    "Samsung":     ["005930.KS"],
    "Air Liquide": ["AI.PA"],
    "Bloom Energy":["BE"],
    "SK Hynix":    ["000660.KS"],
}

SENTINELLES_HYDROGEN = ["Air Liquide", "Bloom Energy"]
SENTINELLES_EM_ASIA  = ["TSMC", "Samsung", "SK Hynix"]

DATE_DEBUT = datetime(2025, 9, 17)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 : FONCTIONS CACHÉES
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        try:
            tickers_avail = df.columns.get_level_values(1).unique().tolist()
            if tickers_avail:
                df = df.xs(tickers_avail[0], axis=1, level=1)
        except Exception:
            df = df.copy()
            df.columns = df.columns.get_level_values(0)
    df = df.dropna(axis=1, how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={"Adj Close": "Close", "Adj_Close": "Close", "adj close": "Close"})
    df = df.rename(columns={c: c.title() for c in df.columns})
    if "Close" not in df.columns:
        return pd.DataFrame()
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.ffill().dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def _fetch_live_price(tk: str) -> Tuple[Optional[float], Optional[float]]:
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
        prix = info.get("regularMarketPrice") or info.get("currentPrice") or info.get("navPrice")
        prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if prix and float(prix) > 0:
            return float(prix), float(prev) if prev else None
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=30, show_spinner=False)
def _cached_live_prices() -> Dict[str, Dict]:
    all_tickers = []
    for pos in POSITIONS_BASE:
        all_tickers.extend(pos["tickers"])
    all_tickers.extend(list(MACRO_TICKERS.keys()))
    all_tickers.extend(REGIME_TICKERS)
    all_tickers.extend(PROXIES_ANRJ + PROXIES_AASI)
    all_tickers.extend(GOLD_TICKERS_FALLBACK)  # v5.4 : inclure les fallbacks Or
    for tlist in SENTINELLES.values():
        all_tickers.extend(tlist)
    all_tickers = list(dict.fromkeys(all_tickers))

    result = {}
    for tk in all_tickers:
        prix, prev = _fetch_live_price(tk)
        result[tk] = {"prix": prix, "prev": prev}
    return result


@st.cache_data(ttl=90, show_spinner=False)
def _cached_historical_data() -> Dict[str, pd.DataFrame]:
    start = (datetime.now() - timedelta(days=600)).strftime("%Y-%m-%d")
    all_tickers = []
    for pos in POSITIONS_BASE:
        all_tickers.extend(pos["tickers"])
    all_tickers.extend(PROXIES_ANRJ + PROXIES_AASI)
    all_tickers.extend(list(MACRO_TICKERS.keys()))
    all_tickers.extend(REGIME_TICKERS)
    all_tickers.extend(GOLD_TICKERS_FALLBACK)  # v5.4 : inclure les fallbacks Or
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
                df = _normalize_df(raw[tk].copy())
                if not df.empty:
                    result[tk] = df
            except Exception:
                pass
    elif not raw.empty and len(all_tickers) == 1:
        df = _normalize_df(raw.copy())
        if not df.empty:
            result[all_tickers[0]] = df

    for tk in [t for t in all_tickers if t not in result]:
        try:
            df = _normalize_df(yf.download(tk, start=start, auto_adjust=True, progress=False))
            if not df.empty:
                result[tk] = df
        except Exception:
            pass
    return result


def _load_config() -> Dict:
    defaults = {"capital_reel": _DEFAULT_CAPITAL_REEL,
                "ajustement_pat": _DEFAULT_AJUSTEMENT_PAT,
                "bonus_fortuneo": _DEFAULT_BONUS_FORTUNEO}
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Extraire seulement les clés financières (pas les positions)
            return {**defaults, **{k: float(v) for k, v in data.items()
                                   if k in defaults and not isinstance(v, list)}}
    except Exception:
        pass
    return defaults


def _save_config(capital_reel: float, ajustement_pat: float, bonus_fortuneo: float) -> bool:
    """Sauvegarde les paramètres financiers en préservant les positions existantes."""
    try:
        # Charger la config existante pour préserver les positions
        existing = {}
        if os.path.exists(_CONFIG_PATH):
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["capital_reel"]   = round(capital_reel, 2)
        existing["ajustement_pat"] = round(ajustement_pat, 2)
        existing["bonus_fortuneo"] = round(bonus_fortuneo, 2)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _load_positions_from_config() -> Optional[List[Dict]]:
    """v5.4 : Charge les positions depuis config_perso.json si disponible."""
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "positions" in data and isinstance(data["positions"], list):
                return data["positions"]
    except Exception:
        pass
    return None


def _save_positions_to_config(positions: List[Dict]) -> bool:
    """v5.4 : Sauvegarde les positions dans config_perso.json (merge avec le reste)."""
    try:
        existing = {}
        if os.path.exists(_CONFIG_PATH):
            try:
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["positions"] = positions
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 : PERSISTENCE MANAGER (inchangé v5.2)
# ─────────────────────────────────────────────────────────────────────────────

_CSV_COLS = ["date", "capital_cloture", "valeur_titres",
             "perf_jour", "perf_cumul", "regime", "score_regime",
             "poids_h", "poids_em"]

class PersistenceManager:
    def __init__(self, static_capital: float):
        self.static_capital  = static_capital
        self._github_ok      = False
        self._gist           = None
        self._github_warning = ""
        self._history_cache: Optional[pd.DataFrame] = None

        try:
            self._conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
            self._init_db()
        except Exception:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._init_db()

        if PYGITHUB_OK:
            try:
                token   = st.secrets.get("GITHUB_TOKEN", "")
                gist_id = st.secrets.get("GIST_ID", "")
                if token and gist_id:
                    gh          = Github(token)
                    self._gist  = gh.get_gist(gist_id)
                    self._github_ok = True
                    self._sync_from_github()
            except Exception as e:
                self._github_warning = f"GitHub Gist indisponible : {str(e)[:80]}"
        else:
            self._github_warning = "PyGithub non installé — mode SQLite uniquement."

    def _init_db(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                date            TEXT PRIMARY KEY,
                capital_cloture REAL NOT NULL,
                valeur_titres   REAL,
                perf_jour       REAL,
                perf_cumul      REAL,
                regime          TEXT,
                score_regime    INTEGER,
                poids_h         REAL,
                poids_em        REAL,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        self._conn.commit()

    def _sync_from_github(self):
        if not self._gist:
            return
        try:
            files = self._gist.files
            if "history.csv" not in files:
                return
            content = files["history.csv"].content or ""
            if not content.strip():
                return
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                self._conn.execute("""
                    INSERT OR REPLACE INTO snapshots
                    (date,capital_cloture,valeur_titres,perf_jour,perf_cumul,
                     regime,score_regime,poids_h,poids_em)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    row.get("date",""),
                    float(row.get("capital_cloture") or 0),
                    float(row.get("valeur_titres") or 0),
                    float(row.get("perf_jour") or 0),
                    float(row.get("perf_cumul") or 0),
                    row.get("regime",""),
                    int(float(row.get("score_regime") or 0)),
                    float(row.get("poids_h") or 0),
                    float(row.get("poids_em") or 0),
                ))
            self._conn.commit()
        except Exception:
            pass

    def _push_to_github(self, df: pd.DataFrame):
        if not self._gist:
            return
        try:
            buf  = io.StringIO()
            df.to_csv(buf, index=False, columns=_CSV_COLS)
            self._gist.edit(files={"history.csv": InputFileContent(buf.getvalue())})
        except Exception:
            pass

    def save_snapshot(self, capital_cloture: float, valeur_titres: float,
                      perf_jour: float, perf_cumul: float, regime: str,
                      score_regime: int, poids_h: float, poids_em: float) -> bool:
        today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
        try:
            self._conn.execute("""
                INSERT OR REPLACE INTO snapshots
                (date,capital_cloture,valeur_titres,perf_jour,perf_cumul,
                 regime,score_regime,poids_h,poids_em)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (today, round(capital_cloture, 2), round(valeur_titres, 2),
                  round(perf_jour, 4), round(perf_cumul, 4), regime,
                  score_regime, round(poids_h, 4), round(poids_em, 4)))
            self._conn.commit()
            self._history_cache = None
            if self._github_ok:
                self._push_to_github(self.load_history())
            return True
        except Exception:
            return False

    def load_history(self) -> pd.DataFrame:
        if self._history_cache is not None:
            return self._history_cache
        try:
            df = pd.read_sql("SELECT * FROM snapshots ORDER BY date ASC", self._conn)
            for col in _CSV_COLS:
                if col not in df.columns:
                    df[col] = None
            self._history_cache = df[_CSV_COLS].copy()
            return self._history_cache
        except Exception:
            return pd.DataFrame(columns=_CSV_COLS)

    def get_last_snapshot(self) -> Optional[Dict]:
        hist = self.load_history()
        if hist.empty:
            return None
        row = hist.iloc[-1]
        return {c: row[c] for c in _CSV_COLS}

    def get_initial_capital(self) -> float:
        hist = self.load_history()
        if not hist.empty and hist["capital_cloture"].notna().any():
            return float(hist["capital_cloture"].dropna().iloc[0])
        return self.static_capital

    def compute_daily_performance(self, current_value: float) -> Tuple[float, float, float]:
        last    = self.get_last_snapshot()
        initial = self.get_initial_capital()
        base    = float(last["capital_cloture"]) if last else self.static_capital
        if base <= 0:
            base = self.static_capital
        perf_jour  = (current_value / base - 1) * 100 if base > 0 else 0.0
        perf_cumul = (current_value / initial - 1) * 100 if initial > 0 else 0.0
        return perf_jour, perf_cumul, base

    @property
    def status(self) -> str:
        if self._github_ok:
            return "github"
        if self._github_warning:
            return "warn"
        return "local"

    @property
    def warning_msg(self) -> str:
        return self._github_warning

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5 : DATA MANAGER (inchangé v5.2)
# ─────────────────────────────────────────────────────────────────────────────

class DataManager:
    def __init__(self):
        self.live: Dict[str, Dict]         = _cached_live_prices()
        self.data: Dict[str, pd.DataFrame] = _cached_historical_data()
        self._log_returns_cache: Optional[Dict[str, pd.Series]] = None

    def get_price_info(self, tickers: List[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        for tk in tickers:
            info = self.live.get(tk, {})
            prix = info.get("prix")
            prev = info.get("prev")
            if prix and float(prix) > 0:
                return float(prix), float(prev) if prev else None, tk
        return None, None, None

    def compute_log_returns(self) -> Dict[str, pd.Series]:
        if self._log_returns_cache is not None:
            return self._log_returns_cache
        result = {}
        for tk, df in self.data.items():
            if "Close" not in df.columns or len(df) < 2:
                continue
            close = df["Close"].dropna()
            if len(close) < 2:
                continue
            lr = np.log(close / close.shift(1)).dropna()
            if not lr.empty:
                result[tk] = lr
        self._log_returns_cache = result
        return result

    def sma(self, series: pd.Series, n: int) -> Optional[float]:
        s = series.dropna()
        return float(s.rolling(n).mean().iloc[-1]) if len(s) >= n else None

    def rsi(self, series: pd.Series, period: int = 14) -> Optional[float]:
        s = series.dropna()
        if len(s) < period + 1:
            return None
        delta = s.diff()
        gain  = delta.clip(lower=0).rolling(period).mean()
        loss  = (-delta.clip(upper=0)).rolling(period).mean()
        rs    = gain / loss.replace(0, np.nan)
        r     = (100 - (100 / (1 + rs))).dropna()
        return float(r.iloc[-1]) if not r.empty else None

    def adx(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        try:
            close = df["Close"].dropna()
            high  = df.get("High", pd.Series(dtype=float)).dropna()
            low   = df.get("Low",  pd.Series(dtype=float)).dropna()
            idx   = close.index.intersection(high.index).intersection(low.index)
            if len(idx) < period + 1:
                return None
            c, h, l = close[idx], high[idx], low[idx]
            tr   = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            up   = h.diff(); down = -l.diff()
            pdm  = np.where((up > down) & (up > 0), up, 0.0)
            mdm  = np.where((down > up) & (down > 0), down, 0.0)
            atr_s = tr.rolling(period).mean()
            pdi   = 100 * pd.Series(pdm, index=idx).rolling(period).mean() / atr_s
            mdi   = 100 * pd.Series(mdm, index=idx).rolling(period).mean() / atr_s
            dx    = ((pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)) * 100
            adx_s = dx.rolling(period).mean().dropna()
            return float(adx_s.iloc[-1]) if not adx_s.empty else None
        except Exception:
            return None

    def analyze_ticker(self, ticker: str) -> Optional[Dict]:
        lp   = self.live.get(ticker, {})
        prix = lp.get("prix")
        df   = self.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns:
            return {"ticker": ticker, "prix": prix, "sma20": None, "sma50": None,
                    "sma200": None, "rsi": None, "adx": None, "ath30": None} if prix else None
        close     = df["Close"].dropna()
        prix_live = float(prix) if (prix and float(prix) > 0) else float(close.iloc[-1])
        return {
            "ticker": ticker, "prix": prix_live,
            "sma20":  self.sma(close, 20),
            "sma50":  self.sma(close, 50),
            "sma200": self.sma(close, 200),
            "rsi":    self.rsi(close),
            "adx":    self.adx(df),
            "ath30":  float(close.rolling(30, min_periods=1).max().iloc[-1]),
        }

    def relative_strength_slope(self, ticker: str, days: int = 14) -> Optional[float]:
        df_asset = self.data.get(ticker, pd.DataFrame())
        df_world = pd.DataFrame()
        for wt in WORLD_TICKERS:
            df = self.data.get(wt, pd.DataFrame())
            if not df.empty and "Close" in df.columns:
                df_world = df
                break
        if df_asset.empty or df_world.empty:
            return None
        ac     = df_asset["Close"].dropna()
        wc     = df_world["Close"].dropna()
        common = ac.index.intersection(wc.index)
        if len(common) < days + 2:
            return None
        common = common[-(days + 2):]
        ratio  = ac[common] / wc[common]
        x = np.arange(len(ratio)); y = ratio.values.astype(float)
        return float(np.polyfit(x, y, 1)[0]) if not np.any(np.isnan(y)) else None

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 6 : MARKET REGIME ENGINE (inchangé v5.2)
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_LABELS = [
    (4,  5,  "Euphorie",    "regime-euphorie",    "#A855F7"),
    (2,  3,  "Expansion",   "regime-expansion",   "#22C55E"),
    (0,  1,  "Neutre",      "regime-neutre",      "#3B82F6"),
    (-3,-1,  "Stress",      "regime-stress",      "#F59E0B"),
    (-5,-4,  "Contraction", "regime-contraction", "#FF3131"),
]

REGIME_MULTIPLIERS = {
    "Euphorie":    1.00,
    "Expansion":   1.00,
    "Neutre":      0.85,
    "Stress":      0.70,
    "Contraction": 0.20,
}

class MarketRegimeEngine:
    def __init__(self, dm: DataManager):
        self.dm = dm

    def _compute_score_at(self, offset: int = 0) -> int:
        score = 0
        data  = self.dm.data

        def _get_close(tickers):
            for tk in tickers:
                df = data.get(tk, pd.DataFrame())
                if not df.empty and "Close" in df.columns:
                    cl = df["Close"].dropna()
                    if len(cl) > offset + 10:
                        return cl.iloc[:len(cl) - offset] if offset > 0 else cl
            return None

        cl = _get_close(["ES=F", "SPY"])
        if cl is not None and len(cl) >= 201:
            score += 1 if float(cl.iloc[-1]) > float(cl.rolling(200).mean().iloc[-1]) else -1

        cl = _get_close(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51:
            score += 1 if float(cl.iloc[-1]) > float(cl.rolling(50).mean().iloc[-1]) else -1

        cl = _get_close(["^VIX"])
        if cl is not None:
            score += 1 if float(cl.iloc[-1]) < 20 else -1

        cl = _get_close(["^TNX"])
        if cl is not None and len(cl) >= 21:
            score += 1 if float(cl.iloc[-1]) < float(cl.rolling(20).mean().iloc[-1]) else -1

        cl = _get_close(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51:
            score += 1 if float(cl.iloc[-1]) < float(cl.rolling(50).mean().iloc[-1]) else -1

        return max(-5, min(5, score))

    def _score_to_label(self, score: int) -> Tuple[str, str, str]:
        for lo, hi, label, css, color in _REGIME_LABELS:
            if lo <= score <= hi:
                return label, css, color
        return "Neutre", "regime-neutre", "#3B82F6"

    def get_full_regime(self) -> Dict:
        scores_3d = []
        for offset in range(3):
            try:
                scores_3d.append(self._compute_score_at(offset))
            except Exception:
                scores_3d.append(0)

        current_score = scores_3d[0]
        label_0, css_0, color_0 = self._score_to_label(current_score)
        labels_3d = [self._score_to_label(s)[0] for s in scores_3d]

        if len(set(labels_3d)) == 1:
            confirmed  = True; conf_label = label_0; conf_css = css_0
            conf_color = color_0; conf_score = current_score
        elif labels_3d[0] == labels_3d[1]:
            confirmed  = True; conf_label = label_0; conf_css = css_0
            conf_color = color_0; conf_score = current_score
        else:
            confirmed  = False; conf_label = "En attente"; conf_css = "regime-pending"
            conf_color = "#6B7585"; conf_score = current_score

        return {
            "current_score":   current_score,
            "confirmed_score": conf_score,
            "confirmed_label": conf_label,
            "confirmed_css":   conf_css,
            "confirmed_color": conf_color,
            "is_confirmed":    confirmed,
            "scores_3d":       scores_3d,
            "labels_3d":       labels_3d,
            "components":      self._get_component_details(),
            "multiplier":      REGIME_MULTIPLIERS.get(conf_label, 0.85),
        }

    def _get_component_details(self) -> List[Dict]:
        data   = self.dm.data
        detail = []

        def _last(tks):
            for tk in tks:
                df = data.get(tk, pd.DataFrame())
                if not df.empty and "Close" in df.columns:
                    cl = df["Close"].dropna()
                    if not cl.empty: return cl
            return None

        cl = _last(["ES=F", "SPY"])
        if cl is not None and len(cl) >= 201:
            sma = float(cl.rolling(200).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Trend (SMA200)",    "bull": v > sma, "val": f"{v:.1f} vs {sma:.1f}"})
        else:
            detail.append({"name": "Trend (SMA200)",    "bull": None, "val": "N/A"})

        cl = _last(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Breadth (SMA50)",   "bull": v > sma, "val": f"{v:.1f} vs {sma:.1f}"})
        else:
            detail.append({"name": "Breadth (SMA50)",   "bull": None, "val": "N/A"})

        cl = _last(["^VIX"])
        if cl is not None:
            v = float(cl.iloc[-1])
            detail.append({"name": "Volatilité (VIX)",  "bull": v < 20, "val": f"{v:.2f} (seuil 20)"})
        else:
            detail.append({"name": "Volatilité (VIX)",  "bull": None, "val": "N/A"})

        cl = _last(["^TNX"])
        if cl is not None and len(cl) >= 21:
            sma = float(cl.rolling(20).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Taux (US10Y SMA20)","bull": v < sma, "val": f"{v:.3f}% vs {sma:.3f}%"})
        else:
            detail.append({"name": "Taux (US10Y SMA20)","bull": None, "val": "N/A"})

        cl = _last(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1]); v = float(cl.iloc[-1])
            detail.append({"name": "Liquidité (DXY)",   "bull": v < sma, "val": f"{v:.2f} vs {sma:.2f}"})
        else:
            detail.append({"name": "Liquidité (DXY)",   "bull": None, "val": "N/A"})

        return detail

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 7 : QUANT RISK ENGINE — v5.4 : get_robust_gold_data() + dropna fix
# ─────────────────────────────────────────────────────────────────────────────

class QuantRiskEngine:
    def __init__(self, dm: DataManager):
        self.dm           = dm
        self._log_returns = dm.compute_log_returns()

    # ── v5.4 : Fallback systématique pour l'Or ─────────────────────────────
    def get_robust_gold_data(self) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Tente d'obtenir des données historiques valides pour l'Or Physique.
        Parcourt les tickers de fallback jusqu'à en trouver un avec > 60 jours de données.
        Retourne (DataFrame, ticker_utilisé) ou (None, None) si tous échouent.
        """
        for t in GOLD_TICKERS_FALLBACK:
            data = self.dm.data.get(t)
            if data is not None and not data.empty and "Close" in data.columns:
                clean = data["Close"].dropna()
                if len(clean) > 60:
                    return data, t
        return None, None

    def rolling_volatility(self, ticker: str, window: int = 30) -> Optional[float]:
        lr = self._log_returns.get(ticker)
        if lr is None or len(lr) < window:
            return None
        return float(lr.iloc[-window:].std() * np.sqrt(252))

    def rolling_volatility_from_df(self, df: pd.DataFrame, window: int = 30) -> Optional[float]:
        """v5.4 : Calcule la vol à partir d'un DataFrame (pour l'Or avec fallback)."""
        if df is None or df.empty or "Close" not in df.columns:
            return None
        close = df["Close"].dropna()
        if len(close) < window + 1:
            return None
        lr = np.log(close / close.shift(1)).dropna()
        if len(lr) < window:
            return None
        return float(lr.iloc[-window:].std() * np.sqrt(252))

    def rolling_beta(self, ticker: str,
                     benchmark: str = "MWRD.PA", window: int = 60) -> Optional[float]:
        lr_a = self._log_returns.get(ticker)
        lr_b = self._log_returns.get(benchmark)
        if lr_b is None:
            for wt in WORLD_TICKERS:
                lr_b = self._log_returns.get(wt)
                if lr_b is not None:
                    break
        if lr_a is None or lr_b is None:
            return None
        common = lr_a.index.intersection(lr_b.index)
        if len(common) < window:
            return None
        a = lr_a[common].iloc[-window:].values
        b = lr_b[common].iloc[-window:].values
        cov = np.cov(a, b)[0, 1]
        var = np.var(b)
        return float(cov / var) if var > 1e-12 else None

    def rolling_beta_from_df(self, df: pd.DataFrame,
                              benchmark: str = "MWRD.PA", window: int = 60) -> Optional[float]:
        """v5.4 : Calcule le beta à partir d'un DataFrame (pour l'Or avec fallback)."""
        if df is None or df.empty or "Close" not in df.columns:
            return None
        close = df["Close"].dropna()
        if len(close) < window + 1:
            return None
        lr_a = np.log(close / close.shift(1)).dropna()

        lr_b = self._log_returns.get(benchmark)
        if lr_b is None:
            for wt in WORLD_TICKERS:
                lr_b = self._log_returns.get(wt)
                if lr_b is not None:
                    break
        if lr_b is None:
            return None

        common = lr_a.index.intersection(lr_b.index)
        if len(common) < window:
            return None
        a = lr_a[common].iloc[-window:].values
        b = lr_b[common].iloc[-window:].values
        cov = np.cov(a, b)[0, 1]
        var = np.var(b)
        return float(cov / var) if var > 1e-12 else None

    def drawdown_metrics(self, ticker: str, window: int = 252) -> Dict:
        df = self.dm.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns:
            return {"current_dd": None, "max_dd": None}
        close = df["Close"].dropna()
        if len(close) < 10:
            return {"current_dd": None, "max_dd": None}
        recent = close.iloc[-window:]
        peak   = recent.cummax()
        dd     = (recent / peak - 1)
        return {
            "current_dd": float(dd.iloc[-1]) * 100,
            "max_dd":     float(dd.min()) * 100,
        }

    def drawdown_metrics_from_df(self, df: pd.DataFrame, window: int = 252) -> Dict:
        """v5.4 : Calcule les drawdowns à partir d'un DataFrame (pour l'Or avec fallback)."""
        if df is None or df.empty or "Close" not in df.columns:
            return {"current_dd": None, "max_dd": None}
        close = df["Close"].dropna()
        if len(close) < 10:
            return {"current_dd": None, "max_dd": None}
        recent = close.iloc[-window:]
        peak   = recent.cummax()
        dd     = (recent / peak - 1)
        return {
            "current_dd": float(dd.iloc[-1]) * 100,
            "max_dd":     float(dd.min()) * 100,
        }

    def correlation_matrix(self, tickers: List[str], window: int = 60) -> Optional[pd.DataFrame]:
        series_dict = {}
        for tk in tickers:
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                series_dict[tk] = lr.iloc[-window:]
        if len(series_dict) < 2:
            return None
        df_all = pd.concat(series_dict.values(), axis=1)
        df_all.columns = list(series_dict.keys())
        df_all = df_all.dropna()  # v5.4 : .dropna() systématique avant corrélation
        if len(df_all) < 20:
            return None
        return df_all.corr()

    def risk_contribution(self, tickers: List[str], weights: List[float],
                          window: int = 60) -> Dict[str, Dict]:
        valid_tickers, valid_lr, valid_w = [], [], []
        for tk, w in zip(tickers, weights):
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                valid_tickers.append(tk)
                valid_lr.append(lr)
                valid_w.append(w)

        if len(valid_tickers) < 2:
            return {}

        df_all = pd.concat(valid_lr, axis=1)
        df_all.columns = valid_tickers
        df_all = df_all.dropna().iloc[-window:]  # v5.4 : .dropna() systématique
        if len(df_all) < 20:
            return {}

        w  = np.array(valid_w, dtype=float)
        w /= w.sum()

        cov    = df_all.cov().values * 252
        port_v = float(w @ cov @ w)
        port_s = np.sqrt(port_v) if port_v > 0 else 1e-10

        mrc     = cov @ w
        rc      = w * mrc
        total_rc = rc.sum()
        rc_pct  = rc / total_rc * 100 if total_rc > 0 else rc * 0

        result = {}
        for i, tk in enumerate(valid_tickers):
            result[tk] = {
                "weight_pct": w[i] * 100,
                "rc_absolute": float(rc[i]),
                "rc_pct": float(rc_pct[i]),
                "flag": float(rc_pct[i]) > 40,
            }
        return result

    def portfolio_volatility(self, tickers: List[str], weights: List[float],
                             window: int = 60) -> Optional[float]:
        valid_tickers, valid_lr, valid_w = [], [], []
        for tk, w in zip(tickers, weights):
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                valid_tickers.append(tk)
                valid_lr.append(lr)
                valid_w.append(w)
        if len(valid_tickers) < 2:
            return None
        df_all = pd.concat(valid_lr, axis=1)
        df_all.columns = valid_tickers
        df_all = df_all.dropna().iloc[-window:]  # v5.4 : .dropna() systématique
        if len(df_all) < 20:
            return None
        w   = np.array(valid_w) / sum(valid_w)
        cov = df_all.cov().values * 252
        return float(np.sqrt(w @ cov @ w))

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 8 : PORTFOLIO ENGINE — v5.4 : compute_adjusted_benchmark() MWR
# ─────────────────────────────────────────────────────────────────────────────

class PortfolioEngine:
    def __init__(self, dm: DataManager, re: MarketRegimeEngine, qre: QuantRiskEngine):
        self.dm  = dm
        self.re  = re
        self.qre = qre

    # ── v5.4 : Benchmark Cash-Flow Adjusted (MWR) ─────────────────────────
    def compute_adjusted_benchmark(self) -> float:
        """
        Simule l'achat de parts MWRD.PA aux dates exactes des flux réels.
        Applique 0.10% de frais à chaque flux, puis ajustements finaux.
        Retourne la performance % ajustée par rapport au capital investi total.
        """
        flux_data = [
            ("2025-09-17", 7210.0),
            ("2025-10-15",  200.0),
            ("2025-11-12",  100.0),
            ("2025-11-13",  200.0),
            ("2025-11-26",  300.0),
            ("2025-12-15",  200.0),
            ("2026-01-14",  212.0),
            ("2026-02-13",  212.0),
            ("2026-03-06",  400.0),
            ("2026-03-12",  520.0),
            ("2026-03-13",  212.0),
            ("2026-03-27",  750.0),
            ("2026-04-01",  750.0),
        ]

        # Chercher les données MWRD.PA en priorité, puis fallbacks
        df_h = None
        for tk in ["MWRD.PA", "IWDA.AS", "EUNL.DE"]:
            df_h = self.dm.data.get(tk)
            if df_h is not None and not df_h.empty and "Close" in df_h.columns:
                break

        if df_h is None or df_h.empty:
            return 0.0

        close_series = df_h["Close"].dropna()
        total_parts   = 0.0
        total_invested = sum(f[1] for f in flux_data)

        for date_str, amount in flux_data:
            try:
                target_date = pd.to_datetime(date_str)
                # asof() retourne le prix le plus récent <= target_date
                price = float(close_series.asof(target_date))
                if price <= 0 or np.isnan(price):
                    continue
                net_invested  = amount * 0.999  # −0.10% frais
                total_parts  += net_invested / price
            except Exception:
                continue

        if total_parts <= 0 or total_invested <= 0:
            return 0.0

        current_price = float(close_series.iloc[-1])
        # Ajustements finaux : Frais globaux (−31.26€) + Revalorisation fonds euro (+16.23€)
        final_val = (total_parts * current_price) - 31.26 + 16.23
        perf_adj  = ((final_val - total_invested) / total_invested) * 100
        return round(perf_adj, 4)

    def compute_portfolio(self, positions_conf: List[Dict],
                           capital_reel: float, ajustement_pat: float,
                           bonus_fortuneo: float) -> Dict:
        positions_calc = []
        valeur_totale = valeur_veille = 0.0
        val_env = {"PEA": 0.0, "AV": 0.0}
        gan_env = {"PEA": 0.0, "AV": 0.0}

        for pos in positions_conf:
            prix, prev, tk_used = self.dm.get_price_info(pos["tickers"])
            env = pos["enveloppe"]
            if prix is None:
                positions_calc.append({"nom": pos["nom"], "ticker": None, "prix": None,
                    "valeur": 0.0, "perf_pct": None, "var_jour_pct": 0.0,
                    "var_jour_eur": 0.0, "enveloppe": env})
                continue
            valeur     = pos["parts"] * prix
            gain_unit  = prix - pos["prm"]
            perf_pct   = gain_unit / pos["prm"] * 100
            gain_total = gain_unit * pos["parts"]
            var_j_pct  = (prix - prev) / prev * 100 if prev and prev != 0 else 0.0
            var_j_eur  = (prix - prev) * pos["parts"] if prev else 0.0
            positions_calc.append({
                "nom": pos["nom"], "ticker": tk_used, "prix": prix,
                "valeur": valeur, "perf_pct": perf_pct,
                "var_jour_pct": var_j_pct, "var_jour_eur": var_j_eur,
                "enveloppe": env,
            })
            valeur_totale += valeur
            val_env[env]  += valeur
            gan_env[env]  += gain_total
            valeur_veille += pos["parts"] * (prev if prev else prix)

        solde_total  = valeur_totale + ajustement_pat
        gain_reel    = solde_total - capital_reel
        perf_tot_pct = (gain_reel / capital_reel * 100) if capital_reel else 0.0
        perf_j_eur   = valeur_totale - valeur_veille
        perf_j_pct   = perf_j_eur / valeur_veille * 100 if valeur_veille else 0.0

        return {"positions": positions_calc, "valeur_totale": valeur_totale,
                "solde_total": solde_total, "gain_reel": gain_reel,
                "perf_tot_pct": perf_tot_pct, "valeur_veille": valeur_veille,
                "val_env": val_env, "gain_env": gan_env,
                "ajustement_pat": ajustement_pat, "capital_reel": capital_reel,
                "perf_j_eur": perf_j_eur, "perf_j_pct": perf_j_pct}

    def compute_benchmark(self, positions_conf: List[Dict], perf_tot_pct: float) -> Dict:
        """
        v5.4 : Retourne à la fois le benchmark Lump Sum classique ET le benchmark
        Cash-Flow Adjusted (MWR). Le gap affiché utilise le benchmark MWR ajusté.
        """
        bench = next((p for p in positions_conf if p["nom"] == BENCHMARK_NOM), None)
        if not bench:
            return {}
        prix, prev, tk = self.dm.get_price_info(bench["tickers"])
        if not prix:
            return {}
        df_h = self.dm.data.get(tk, pd.DataFrame())
        if df_h.empty:
            for t in bench["tickers"]:
                df_h = self.dm.data.get(t, pd.DataFrame())
                if not df_h.empty: break
        if df_h.empty:
            return {"prix": prix}
        close = df_h["Close"].dropna()
        try:
            start_val = float(close.loc[DATE_DEBUT.strftime("%Y-%m-%d")])
        except KeyError:
            cands     = close.loc[:DATE_DEBUT.strftime("%Y-%m-%d")]
            start_val = float(cands.iloc[-1]) if not cands.empty else float(close.iloc[0])

        # Benchmark Lump Sum classique (gardé pour référence)
        perf_bench_lumpsum = (prix / start_val - 1) * 100 if start_val else None

        # Benchmark MWR Cash-Flow Adjusted (v5.4)
        perf_bench_adj = self.compute_adjusted_benchmark()

        # GAP : performance réelle vs benchmark MWR ajusté (Référence Alpha v5.4)
        gap_adj      = perf_tot_pct - perf_bench_adj if perf_bench_adj != 0 else None
        gap_lumpsum  = perf_tot_pct - perf_bench_lumpsum if perf_bench_lumpsum is not None else None

        perf_bench_j = (prix - prev) / prev * 100 if prev and prev != 0 else None

        return {
            "perf_bench":     perf_bench_lumpsum,   # Lump Sum (référence historique)
            "perf_bench_adj": perf_bench_adj,        # MWR Cash-Flow Adjusted (v5.4)
            "gap":            gap_adj,               # GAP principal = vs MWR ajusté
            "gap_lumpsum":    gap_lumpsum,           # GAP secondaire = vs Lump Sum
            "prix":           prix,
            "perf_bench_j":   perf_bench_j,
        }

    def compute_unified_score(self, ticker: str) -> Dict:
        info    = self.dm.analyze_ticker(ticker)
        details = []
        score   = 0

        rsi_v = info["rsi"] if info else None
        if rsi_v is not None:
            if rsi_v >= 70:   ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Tendu"
            elif rsi_v <= 45: ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Faible"
            else:             ms, mb, md =  1, "bull", f"RSI={rsi_v:.1f} Sain"
        else:                 ms, mb, md =  0, "neut", "RSI indisponible"
        details.append({"name": "Momentum",   "score": ms, "badge": mb, "desc": md})
        score += ms

        if info and info["sma20"] is not None:
            if info["prix"] > info["sma20"]:
                ss, sb, sd = 1, "bull", f"Prix {info['prix']:.2f} > SMA20 {info['sma20']:.2f}"
            else:
                ss, sb, sd = -1, "bear", f"Prix {info['prix']:.2f} < SMA20 {info['sma20']:.2f}"
        else:
            ss, sb, sd = 0, "neut", "SMA20 indisponible"
        details.append({"name": "Structure",  "score": ss, "badge": sb, "desc": sd})
        score += ss

        rs_slope = self.dm.relative_strength_slope(ticker, 14)
        if rs_slope is not None:
            if rs_slope > 0: ls, lb, ld = 2, "bull", f"Pente={rs_slope:+.5f} Leader ✓"
            else:            ls, lb, ld = -2, "bear", f"Pente={rs_slope:.5f} Lagger"
        else:
            ls, lb, ld = 0, "neut", "Données insuffisantes"
        details.append({"name": "Leadership", "score": ls, "badge": lb, "desc": ld})
        score += ls

        return {"total": max(-4, min(4, score)),
                "momentum": ms, "structure": ss, "leadership": ls,
                "details": details, "rsi_raw": rsi_v,
                "adx_raw": info["adx"] if info else None}

    def compute_strategic_score_4c(self, ticker: str, regime: Dict) -> Dict:
        info    = self.dm.analyze_ticker(ticker)

        trend_raw = 0.0
        if info and info["sma20"] and info["prix"]:
            dev = (info["prix"] - info["sma20"]) / info["sma20"]
            trend_raw = max(-1.0, min(1.0, dev * 20))

        macro_raw = regime["confirmed_score"] / 5.0

        rs = self.dm.relative_strength_slope(ticker, 14)
        leader_raw = (1.0 if rs and rs > 0 else -1.0 if rs and rs <= 0 else 0.0)

        vol = self.qre.rolling_volatility(ticker, 30)
        vol_raw = max(-1.0, min(1.0, (0.20 - vol) / 0.10)) if vol is not None else 0.0

        total = (trend_raw * 0.25 + macro_raw * 0.30 +
                 leader_raw * 0.25 + vol_raw * 0.20)

        return {
            "total":      max(-1.0, min(1.0, total)),
            "trend":      trend_raw,
            "macro":      macro_raw,
            "leadership": leader_raw,
            "risk_vol":   vol_raw,
        }

    def compute_confidence_factor(self, tickers: List[str], weights: List[float]) -> float:
        port_vol = self.qre.portfolio_volatility(tickers, weights, 60)
        if port_vol is None: return 0.85
        if port_vol < 0.10:   return 1.00
        elif port_vol < 0.15: return 0.90
        elif port_vol < 0.20: return 0.75
        else:                  return 0.60

    def compute_target_weight(self, nom: str, ticker: str,
                               valeur_totale: float,
                               positions_calc: List[Dict]) -> Dict:
        regime  = self.re.get_full_regime()
        unified = self.compute_unified_score(ticker)
        strat4c = self.compute_strategic_score_4c(ticker, regime)

        base_w = self._get_base_weight(unified["total"], INITIAL_TARGETS.get(nom, 0.25))

        regime_mult = regime["multiplier"]
        ptf_tickers = [p["ticker"] for p in positions_calc if p.get("ticker")]
        ptf_weights = [p["valeur"] / valeur_totale for p in positions_calc
                       if p.get("ticker") and valeur_totale > 0]
        confidence  = self.compute_confidence_factor(ptf_tickers, ptf_weights)

        strat_adj = 1.0 + strat4c["total"] * 0.30

        target = base_w * regime_mult * confidence * strat_adj
        target = max(0.02, min(0.35, target))

        current_val = next((p["valeur"] for p in positions_calc if p["nom"] == nom), 0.0)
        current_pct = current_val / valeur_totale * 100 if valeur_totale > 0 else 0.0
        target_pct  = target * 100
        delta_pct   = current_pct - target_pct
        target_eur  = valeur_totale * target

        if delta_pct >  1.0: action = "RÉDUIRE"
        elif delta_pct < -1.0: action = "RENFORCER"
        else: action = "MAINTENIR"

        return {
            "nom":           nom,
            "unified_score": unified["total"],
            "strat_score":   strat4c["total"],
            "strat4c":       strat4c,
            "base_weight":   base_w,
            "regime_mult":   regime_mult,
            "confidence":    confidence,
            "target_pct":    target_pct,
            "current_pct":   current_pct,
            "current_eur":   current_val,
            "target_eur":    target_eur,
            "delta_pct":     delta_pct,
            "delta_eur":     current_val - target_eur,
            "action":        action,
            "regime_label":  regime["confirmed_label"],
        }

    def _get_base_weight(self, score: int, initial_target: float) -> float:
        if score >= 3:    return initial_target
        elif score >= 1:  return 0.20
        elif score >= -1: return 0.15
        else:             return 0.05

    def evaluate_hydrogen(self, anrj: Optional[Dict]) -> Tuple[str, str]:
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

    def evaluate_em_asia(self, aasi: Optional[Dict]) -> Tuple[str, str]:
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

    def evaluate_sentinelles(self) -> Tuple[str, str, List[Dict]]:
        alerts, rows = [], []
        for name, tickers in SENTINELLES.items():
            info = None
            for tk in tickers:
                info = self.dm.analyze_ticker(tk)
                if info: break
            alerte = ""
            if info and info["sma20"] and info["prix"] < info["sma20"]:
                alerte = "⚠️"
                alerts.append(name)
            rows.append({
                "Sentinelle": name,
                "Prix":  f"{info['prix']:.2f}"  if info else "N/A",
                "SMA20": f"{info['sma20']:.2f}" if (info and info["sma20"]) else "N/A",
                "RSI":   f"{info['rsi']:.1f}"   if (info and info["rsi"])   else "N/A",
                "Alerte": alerte,
            })
        msg = " | ".join([f"⚠️ {a} sous SMA20" for a in alerts]) if alerts else "✅ Sentinelles OK"
        return msg, "orange" if alerts else "green", rows

    def check_leadership_alerts(self) -> List[Dict]:
        alerts = []
        world_close = None
        for wt in WORLD_TICKERS:
            df = self.dm.data.get(wt, pd.DataFrame())
            if not df.empty and "Close" in df.columns:
                world_close = df["Close"].dropna()
                break
        if world_close is None:
            return alerts
        for nom, tk in [("Global Hydrogen", "ANRJ.PA"), ("EM Asia", "AASI.PA")]:
            df = self.dm.data.get(tk, pd.DataFrame())
            if df.empty or "Close" not in df.columns:
                continue
            sc     = df["Close"].dropna()
            common = sc.index.intersection(world_close.index)
            if len(common) < 16:
                continue
            recent = common[-15:]
            s_pf   = (sc[recent].iloc[-1] / sc[recent].iloc[0] - 1) * 100
            w_pf   = (world_close[recent].iloc[-1] / world_close[recent].iloc[0] - 1) * 100
            alerts.append({"nom": nom, "sat_perf": s_pf, "world_perf": w_pf, "gap": s_pf - w_pf})
        return alerts

    def determine_phase(self, gap, anrj, aasi) -> Tuple[str, str]:
        proxies_a  = {tk: self.dm.analyze_ticker(tk) for tk in PROXIES_ANRJ}
        proxies_em = {tk: self.dm.analyze_ticker(tk) for tk in PROXIES_AASI}
        if gap is None:
            return "⏳ Phase indéterminée — Données insuffisantes", "#374151"
        if gap < 0:
            return "📉 Phase 1 : Reconquête — Revenir à l'équilibre vs World AV", "#7F1D1D"
        signals = []
        if anrj and anrj["sma20"] and anrj["prix"] < anrj["sma20"]:
            signals.append("ANRJ<SMA20")
        if aasi and aasi["sma20"] and aasi["prix"] < aasi["sma20"]:
            signals.append("AASI<SMA20")
        ps = sum(1 for v in {**proxies_a, **proxies_em}.values()
                 if v and v.get("sma20") and v["prix"] < v["sma20"])
        if ps >= 2:
            signals.append(f"{ps} proxies<SMA20")
        if signals:
            return f"🔄 Phase 3 : Rotation — Sécuriser les gains ({', '.join(signals)})", "#78350F"
        return "🚀 Phase 2 : Alpha — Battre le MSCI World", "#14532D"

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 9 : PEDAGOGIC ENGINE (v5.3 inchangé)
# ─────────────────────────────────────────────────────────────────────────────

class PedagogicEngine:
    def translate_volatility(self, vol: Optional[float], asset_name: str) -> Dict:
        if vol is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange",
                    "title": "Agitation de l'ETF",
                    "explain": "Donnée indisponible pour le moment.",
                    "scale": [], "action": "Revérifier plus tard."}
        pct = vol * 100
        if pct < 15:
            emoji, level, msg, action = "😌", "green", "L'ETF est calme et stable.", "Aucune vigilance particulière."
        elif pct < 25:
            emoji, level, msg, action = "😐", "orange", "L'ETF bouge normalement.", "Surveillez les niveaux importants."
        else:
            emoji, level, msg, action = "😰", "red", f"L'ETF est agité — des variations brutales sont possibles.", "Réduisez éventuellement la position."
        return {
            "value":   f"{pct:.1f}%",
            "emoji":   emoji, "level":   level,
            "title":   f"Agitation de {asset_name}",
            "explain": f"{msg}\n\nPlus ce chiffre est élevé, plus l'ETF peut perdre ou gagner brusquement en peu de temps.",
            "scale":   [
                {"label": "< 15% — Calme", "cls": "scale-green"},
                {"label": "15-25% — Normal", "cls": "scale-orange"},
                {"label": "> 25% — Risqué", "cls": "scale-red"},
            ],
            "action":  action,
        }

    def translate_beta(self, beta: Optional[float], asset_name: str) -> Dict:
        if beta is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange",
                    "title": "Sensibilité au marché",
                    "explain": "Donnée indisponible.",
                    "scale": [], "action": "Revérifier plus tard."}
        if beta < 0:
            emoji, level = "🔄", "orange"
            msg    = "Cet ETF évolue à contre-courant du marché mondial."
            action = "Position défensive intéressante en période de baisse."
        elif beta < 0.8:
            emoji, level = "🛡️", "green"
            msg    = f"L'ETF bouge {(1-beta)*100:.0f}% moins que le marché mondial."
            action = "Position défensive — protège bien en cas de baisse."
        elif beta < 1.2:
            emoji, level = "⚖️", "green"
            msg    = "L'ETF suit le marché mondial de façon équilibrée."
            action = "Comportement neutre, aucune vigilance particulière."
        elif beta < 1.8:
            emoji, level = "⚡", "orange"
            excess = (beta - 1) * 100
            msg    = f"L'ETF bouge {excess:.0f}% plus violemment que le marché mondial. Si le World baisse de 10%, {asset_name} peut baisser de {beta*10:.0f}%."
            action = "Gardez une position limitée ou utilisez des stops."
        else:
            emoji, level = "🌋", "red"
            msg    = f"L'ETF est très sensible aux mouvements du marché — il amplifie les hausses ET les baisses de façon importante."
            action = "Position risquée — limitez à une part raisonnable du portefeuille."
        return {
            "value":   f"{beta:.2f}×",
            "emoji":   emoji, "level":   level,
            "title":   f"Sensibilité au marché de {asset_name}",
            "explain": msg,
            "scale":   [
                {"label": "< 0.8 — Défensif", "cls": "scale-green"},
                {"label": "0.8-1.2 — Neutre", "cls": "scale-green"},
                {"label": "1.2-1.8 — Offensif", "cls": "scale-orange"},
                {"label": "> 1.8 — Très risqué", "cls": "scale-red"},
            ],
            "action":  action,
        }

    def translate_drawdown(self, current_dd: Optional[float],
                            max_dd: Optional[float], asset_name: str) -> Dict:
        if current_dd is None:
            return {"value": "N/A", "emoji": "❓", "level": "orange",
                    "title": "Recul depuis le sommet",
                    "explain": "Donnée indisponible.",
                    "scale": [], "action": "Revérifier plus tard."}
        abs_dd = abs(current_dd)
        if abs_dd < 3:
            emoji, level = "🏔️", "green"
            msg    = f"{asset_name} est proche de son récent sommet. Bonne santé graphique."
            action = "Aucune alerte — position saine."
        elif abs_dd < 8:
            emoji, level = "📉", "orange"
            msg    = f"{asset_name} a reculé de {abs_dd:.1f}% depuis son dernier sommet. Repli normal."
            action = "Surveillance normale — pas d'action urgente."
        elif abs_dd < 15:
            emoji, level = "⚠️", "orange"
            msg    = f"{asset_name} a reculé de {abs_dd:.1f}% depuis son dernier sommet. Correction significative."
            action = "Vérifiez si votre stop-loss est proche."
        else:
            emoji, level = "🚨", "red"
            msg    = f"{asset_name} a chuté de {abs_dd:.1f}% depuis son sommet récent. Perte importante non récupérée."
            action = "Envisagez de réduire la position ou d'activer le stop-loss."
        max_str = f" | Plus forte baisse 1 an : {abs(max_dd):.1f}%" if max_dd is not None else ""
        return {
            "value":   f"{current_dd:.1f}%",
            "emoji":   emoji, "level":   level,
            "title":   f"Recul depuis le sommet de {asset_name}",
            "explain": msg + max_str,
            "scale":   [
                {"label": "0 à -3% — Sommet", "cls": "scale-green"},
                {"label": "-3 à -8% — Repli normal", "cls": "scale-orange"},
                {"label": "> -8% — Correction", "cls": "scale-red"},
            ],
            "action":  action,
        }

    def translate_regime(self, regime: Dict) -> Dict:
        label = regime["confirmed_label"]
        translations = {
            "Euphorie": {
                "emoji": "🚀", "level": "green",
                "explain": "Les marchés mondiaux sont en pleine euphorie. Les investisseurs achètent massivement.",
                "action": "Bon moment pour maintenir vos positions, mais restez vigilant — les retournements arrivent sans prévenir.",
                "conseil": "Vos ETFs peuvent progresser, mais préparez vos stops.",
            },
            "Expansion": {
                "emoji": "📈", "level": "green",
                "explain": "Les marchés sont en phase de croissance régulière. Contexte globalement favorable.",
                "action": "Maintenez vos positions. Vous pouvez envisager des renforcements si les conditions locales le permettent.",
                "conseil": "Phase idéale pour votre portefeuille Lazy Core + Satellites.",
            },
            "Neutre": {
                "emoji": "⚖️", "level": "orange",
                "explain": "Les marchés sont sans direction claire. Autant de signaux positifs que négatifs.",
                "action": "Réduisez légèrement les positions risquées si vous n'êtes pas à l'aise. Pas d'urgence.",
                "conseil": "Attendez une confirmation avant d'agir.",
            },
            "Stress": {
                "emoji": "😟", "level": "orange",
                "explain": "Les marchés montrent des signes de fatigue. La nervosité augmente.",
                "action": "Réduisez les positions satellites (Hydrogen, EM Asia). Renforcez l'or ou le World.",
                "conseil": "Ce n'est pas le moment d'acheter. Préservez votre capital.",
            },
            "Contraction": {
                "emoji": "🚨", "level": "red",
                "explain": "Crise ou forte baisse des marchés mondiaux. Contexte très défavorable.",
                "action": "Réduisez fortement les satellites. Passez en mode défensif (or, liquidités).",
                "conseil": "Priorité : protéger votre capital, pas gagner de l'argent.",
            },
            "En attente": {
                "emoji": "⏳", "level": "orange",
                "explain": "Les signaux sont contradictoires. Le régime n'est pas encore confirmé.",
                "action": "Attendez 1-2 jours que la situation se clarifie avant d'agir.",
                "conseil": "Ne prenez pas de décision importante dans le flou.",
            },
        }
        info = translations.get(label, translations["En attente"])
        return {"label": label, "score": regime["confirmed_score"],
                "emoji": info["emoji"], "level": info["level"],
                "explain": info["explain"], "action": info["action"],
                "conseil": info["conseil"]}

    def translate_leadership(self, nom: str, weekly_gaps: List[float]) -> Dict:
        if not weekly_gaps:
            return {
                "emoji": "❓", "level": "orange",
                "message": "Données insuffisantes pour évaluer le leadership.",
                "detail": "", "action": "Revérifiez dans quelques jours.",
            }
        pos_weeks  = sum(1 for g in weekly_gaps if g > 0)
        neg_weeks  = sum(1 for g in weekly_gaps if g < 0)
        avg_gap    = sum(weekly_gaps) / len(weekly_gaps)
        n          = len(weekly_gaps)
        consec_neg = 0
        for g in reversed(weekly_gaps):
            if g < 0: consec_neg += 1
            else:     break
        if pos_weeks >= n * 0.6 and avg_gap > 0:
            emoji, level = "🟢", "green"
            msg    = f"🟢 {nom} conserve son leadership face au MSCI World."
            detail = f"{pos_weeks}/{n} semaines positives · Moyenne : {avg_gap:+.1f}%"
            action = f"✅ Conserver la position — {nom} justifie sa place dans le portefeuille."
        elif consec_neg >= 3:
            emoji, level = "🔴", "red"
            msg    = f"🔴 Le MSCI World devient statistiquement plus intéressant que {nom}."
            detail = f"{consec_neg} semaines consécutives de sous-performance"
            action = f"⚠️ Envisagez de réduire {nom} et d'augmenter MSCI World."
        elif neg_weeks > pos_weeks:
            emoji, level = "🟠", "orange"
            msg    = f"🟠 {nom} perd progressivement son avantage face au MSCI World."
            detail = f"{neg_weeks}/{n} semaines négatives · Moyenne : {avg_gap:+.1f}%"
            action = f"👀 Surveillez de près — sans amélioration, envisagez une rotation."
        else:
            emoji, level = "🟡", "orange"
            msg    = f"🟡 {nom} est à égalité avec le MSCI World sur la période."
            detail = f"Performance équivalente · Moyenne : {avg_gap:+.1f}%"
            action = "Maintien raisonnable — suivez l'évolution."
        return {"emoji": emoji, "level": level, "message": msg, "detail": detail, "action": action}

    def get_weekly_performances(self, dm: DataManager,
                                 ticker: str, n_weeks: int = 5) -> Tuple[List[str], List[float], List[float]]:
        world_close = None
        for wt in WORLD_TICKERS:
            df = dm.data.get(wt, pd.DataFrame())
            if not df.empty and "Close" in df.columns:
                world_close = df["Close"].dropna()
                break
        sat_df = dm.data.get(ticker, pd.DataFrame())
        if world_close is None or sat_df.empty or "Close" not in sat_df.columns:
            return [], [], []
        sat_close = sat_df["Close"].dropna()
        common    = sat_close.index.intersection(world_close.index)
        if len(common) < 10:
            return [], [], []
        sat_w   = sat_close[common].resample("W").last()
        world_w = world_close[common].resample("W").last()
        common_w = sat_w.index.intersection(world_w.index)
        if len(common_w) < 2:
            return [], [], []
        sat_w   = sat_w[common_w]
        world_w = world_w[common_w]
        sat_ret   = sat_w.pct_change().dropna() * 100
        world_ret = world_w.pct_change().dropna() * 100
        n = min(n_weeks, len(sat_ret))
        sat_ret   = sat_ret.iloc[-n:]
        world_ret = world_ret.iloc[-n:]
        labels = []
        total  = len(sat_ret)
        for i in range(total):
            if i == total - 1:
                labels.append("En cours")
            else:
                labels.append(f"S-{total - 1 - i}")
        return labels, list(sat_ret.values), list(world_ret.values)

    def translate_simple_score(self, score_raw: int) -> Dict:
        mapping = {-4: 0, -3: 0, -2: 1, -1: 2, 0: 2, 1: 3, 2: 3, 3: 4, 4: 5}
        simple  = mapping.get(max(-4, min(4, score_raw)), 2)
        messages = {
            5: ("⭐⭐⭐⭐⭐", "Momentum très fort", "ring-5",
                "Tout est au vert. L'ETF est en pleine forme.", "Maintenez la position."),
            4: ("⭐⭐⭐⭐☆", "Tendance saine", "ring-4",
                "L'ETF progresse bien et reste au-dessus de ses moyennes.", "Maintenez — éventuellement renforcez."),
            3: ("⭐⭐⭐☆☆", "Situation neutre", "ring-3",
                "L'ETF est stable, sans forte conviction dans un sens ou l'autre.", "Maintenez sans renforcer."),
            2: ("⭐⭐☆☆☆", "Fragilité", "ring-2",
                "L'ETF montre des signes de faiblesse. Quelques alertes à surveiller.", "Soyez prudent — pas de renforcement."),
            1: ("⭐☆☆☆☆", "Risque élevé", "ring-1",
                "L'ETF est clairement en difficulté. Plusieurs indicateurs négatifs.", "Envisagez de réduire la position."),
            0: ("☆☆☆☆☆", "Danger", "ring-0",
                "Situation très dégradée. Risque de pertes importantes.", "Réduction forte recommandée."),
        }
        stars, label, ring_cls, explain, action = messages[simple]
        return {"score": simple, "stars": stars, "label": label,
                "ring_cls": ring_cls, "explain": explain, "action": action}

    def translate_sentinelles(self, sent_rows: List[Dict], sector: str) -> Dict:
        names  = SENTINELLES_HYDROGEN if sector == "hydrogen" else SENTINELLES_EM_ASIA
        alerts = [r for r in sent_rows
                  if r.get("Sentinelle") in names and r.get("Alerte") == "⚠️"]
        total  = sum(1 for r in sent_rows if r.get("Sentinelle") in names)
        if not alerts:
            return {
                "emoji": "🟢", "level": "green",
                "message": "Les leaders du secteur restent solides.",
                "detail": f"Aucune alerte sur {total} valeurs surveillées.",
                "action": "Pas d'action sectorielle requise.",
            }
        elif len(alerts) == 1:
            return {
                "emoji": "🟠", "level": "orange",
                "message": "Les leaders commencent à perdre du momentum.",
                "detail": f"{alerts[0]['Sentinelle']} est sous sa moyenne mobile 20 jours.",
                "action": "Surveillance accrue — pas d'urgence.",
            }
        else:
            names_alert = ", ".join([a["Sentinelle"] for a in alerts])
            return {
                "emoji": "🔴", "level": "red",
                "message": "Les leaders sectoriels décrochent fortement.",
                "detail": f"{names_alert} sous leur moyenne mobile.",
                "action": "Signal négatif pour le secteur — réduction conseillée.",
            }

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 10 : STRATEGIC ENGINE (v5.3 inchangé)
# ─────────────────────────────────────────────────────────────────────────────

class StrategicEngine:
    def __init__(self, dm: DataManager, mre: MarketRegimeEngine, qre: QuantRiskEngine):
        self.dm  = dm
        self.mre = mre
        self.qre = qre

    def compute(self, ticker: str, unified_score: Dict, regime: Dict) -> Dict:
        details = []

        rsi = unified_score.get("rsi_raw")
        if rsi is not None and 45 < rsi < 70:
            mom_score = 1
            mom_label = "✅ L'ETF est en bonne dynamique"
            mom_value = f"RSI {rsi:.0f}"
        elif rsi is not None:
            mom_score = 0
            mom_label = "❌ La dynamique est faible ou tendue"
            mom_value = f"RSI {rsi:.0f}"
        else:
            mom_score = 0
            mom_label = "❓ Donnée indisponible"
            mom_value = "N/A"
        details.append({"dim": "Momentum", "score": mom_score,
                         "label": mom_label, "value": mom_value,
                         "help": "Le RSI mesure la force de la tendance actuelle. Entre 45 et 70 = sain."})

        struct_score = 1 if unified_score.get("structure", -1) > 0 else 0
        info = self.dm.analyze_ticker(ticker)
        if info and info["sma20"] and info["prix"]:
            st_label = ("✅ Prix au-dessus de la moyenne 20 jours" if struct_score == 1
                        else "❌ Prix sous la moyenne 20 jours")
            st_value = f"{info['prix']:.2f}€ vs SMA20 {info['sma20']:.2f}€"
        else:
            st_label = "❓ Donnée indisponible"
            st_value = "N/A"
        details.append({"dim": "Structure", "score": struct_score,
                         "label": st_label, "value": st_value,
                         "help": "Si le prix est au-dessus de sa moyenne sur 20 jours, la tendance court terme est positive."})

        lead_score = 1 if unified_score.get("leadership", -2) > 0 else 0
        rs = self.dm.relative_strength_slope(ticker, 14)
        if rs is not None:
            lead_label = ("✅ L'ETF surperforme le MSCI World" if lead_score == 1
                          else "❌ L'ETF sous-performe le MSCI World")
            lead_value = f"Pente : {rs:+.5f}"
        else:
            lead_label = "❓ Donnée indisponible"
            lead_value = "N/A"
        details.append({"dim": "Leadership", "score": lead_score,
                         "label": lead_label, "value": lead_value,
                         "help": "Compare la performance de l'ETF vs le MSCI World sur 14 jours."})

        reg_score = regime.get("confirmed_score", 0)
        macro_ok  = reg_score >= 1
        macro_s   = 1 if macro_ok else 0
        macro_label = (f"✅ Environnement favorable ({regime['confirmed_label']})"
                       if macro_ok
                       else f"❌ Environnement difficile ({regime['confirmed_label']})")
        details.append({"dim": "Macro", "score": macro_s,
                         "label": macro_label, "value": f"Score {reg_score:+d}/5",
                         "help": "L'environnement économique mondial."})

        vol = self.qre.rolling_volatility(ticker, 30)
        if vol is not None:
            risk_ok = vol < 0.25
            risk_s  = 1 if risk_ok else 0
            risk_label = (f"✅ Agitation acceptable ({vol*100:.1f}%)"
                          if risk_ok else f"❌ ETF très agité ({vol*100:.1f}%)")
            risk_value = f"{vol*100:.1f}% ann."
        else:
            risk_s     = 0
            risk_label = "❓ Donnée indisponible"
            risk_value = "N/A"
        details.append({"dim": "Risque", "score": risk_s,
                         "label": risk_label, "value": risk_value,
                         "help": "Niveau d'agitation de l'ETF. En dessous de 25%, le risque est gérable."})

        total = sum(d["score"] for d in details)

        if total >= 4:
            verdict = "✅ Conditions très favorables — Maintien recommandé"
            verdict_cls = "verdict-green"
        elif total >= 3:
            verdict = "🟡 Conditions correctes — Maintien avec surveillance"
            verdict_cls = "verdict-orange"
        elif total >= 2:
            verdict = "🟠 Conditions mitigées — Prudence conseillée"
            verdict_cls = "verdict-orange"
        else:
            verdict = "🔴 Conditions défavorables — Réduction recommandée"
            verdict_cls = "verdict-red"

        return {"total": total, "details": details,
                "verdict": verdict, "verdict_cls": verdict_cls}

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 11 : FISCAL (v4.1 préservé intégralement)
# ─────────────────────────────────────────────────────────────────────────────

def net_apres_impots(enveloppe: str, montant: float,
                     val_poche: float, gain_poche: float) -> Tuple[float, str]:
    if montant <= 0:       return 0.0, ""
    if montant > val_poche: return 0.0, "⚠️ Montant supérieur à la valeur de la poche"
    ratio_gain   = gain_poche / val_poche if val_poche else 0
    gain_retrait = montant * ratio_gain
    now_tz       = datetime.now(ZoneInfo("Europe/Paris"))
    if enveloppe == "PEA":
        limite = datetime(2031, 4, 1, tzinfo=ZoneInfo("Europe/Paris"))
        if now_tz < limite:
            return 0.0, "⚠️ Retrait PEA impossible avant le 01/04/2031 (fermeture enveloppe)"
        return montant - 0.172 * gain_retrait, ""
    if enveloppe == "AV":
        if now_tz < datetime(2033, 9, 17, tzinfo=ZoneInfo("Europe/Paris")):
            return montant - 0.30 * gain_retrait, ""
        ps = 0.172 * gain_retrait
        ir = 0.128 * max(0, gain_retrait - 9200)
        return montant - ps - ir, ""
    return montant, ""

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 12 : VISUALISATIONS (v5.2 préservées + nouvelles v5.3)
# ─────────────────────────────────────────────────────────────────────────────

_PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E1", family="DM Sans"),
)

def plot_equity_curve(history: pd.DataFrame) -> Optional[go.Figure]:
    if history.empty or "capital_cloture" not in history.columns:
        return None
    df = history.dropna(subset=["capital_cloture"]).copy()
    if len(df) < 2:
        return None
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_dt"]).sort_values("date_dt")
    fig = go.Figure()
    regime_colors = {"Euphorie": "rgba(168,85,247,.10)", "Expansion": "rgba(34,197,94,.10)",
                     "Neutre": "rgba(59,130,246,.08)", "Stress": "rgba(245,158,11,.10)",
                     "Contraction": "rgba(255,49,49,.12)"}
    if "regime" in df.columns:
        prev_regime = None
        x0 = df["date_dt"].iloc[0]
        for i, row in df.iterrows():
            if row.get("regime") != prev_regime and prev_regime is not None:
                col = regime_colors.get(prev_regime, "rgba(255,255,255,.03)")
                fig.add_vrect(x0=x0, x1=row["date_dt"], fillcolor=col, layer="below", line_width=0)
                x0 = row["date_dt"]
            prev_regime = row.get("regime")
        if prev_regime:
            col = regime_colors.get(prev_regime, "rgba(255,255,255,.03)")
            fig.add_vrect(x0=x0, x1=df["date_dt"].iloc[-1], fillcolor=col, layer="below", line_width=0)
    fig.add_trace(go.Scatter(
        x=df["date_dt"], y=df["capital_cloture"].astype(float),
        mode="lines+markers",
        line=dict(color="#D4AF37", width=2.5),
        marker=dict(size=5, color="#D4AF37"),
        name="Capital Clôture",
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>%{y:,.2f}€<extra></extra>",
    ))
    if "perf_cumul" in df.columns and df["perf_cumul"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["date_dt"], y=df["perf_cumul"].astype(float),
            mode="lines", line=dict(color="#3B82F6", width=1.5, dash="dot"),
            name="Perf Cumul (%)", yaxis="y2",
            hovertemplate="%{y:+.2f}%<extra>Perf Cumul</extra>",
        ))
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Évolution de votre capital</b>", font=dict(size=13, color="#6B7585")),
        margin=dict(t=40, b=30, l=60, r=60), height=280,
        legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)", x=0, y=1.15, orientation="h"),
        xaxis=dict(gridcolor="#2E3340", showgrid=True),
        yaxis=dict(gridcolor="#2E3340", showgrid=True, ticksuffix="€", title="Capital (€)"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%", title="Perf (%)"),
    )
    return fig


def plot_weekly_leadership(labels: List[str], sat_perfs: List[float],
                            world_perfs: List[float],
                            sat_name: str, color_sat: str = "#D4AF37") -> go.Figure:
    fig = go.Figure()
    bar_colors_sat = ["#22C55E" if v > 0 else "#FF3131" for v in sat_perfs]
    fig.add_trace(go.Bar(
        x=labels, y=sat_perfs, name=sat_name,
        marker_color=bar_colors_sat, marker_line_width=0,
        text=[f"{v:+.1f}%" for v in sat_perfs], textposition="outside",
        textfont=dict(size=11, color="#CBD5E1"),
        hovertemplate=f"<b>{sat_name}</b><br>%{{x}}: %{{y:+.1f}}%<extra></extra>",
    ))
    bar_colors_world = ["rgba(59,130,246,.7)" if v > 0 else "rgba(59,130,246,.4)" for v in world_perfs]
    fig.add_trace(go.Bar(
        x=labels, y=world_perfs, name="MSCI World",
        marker_color=bar_colors_world, marker_line_width=0,
        text=[f"{v:+.1f}%" for v in world_perfs], textposition="outside",
        textfont=dict(size=11, color="#93C5FD"),
        hovertemplate="<b>MSCI World</b><br>%{x}: %{y:+.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="#4B5563", opacity=0.8)
    fig.update_layout(
        **_PLOTLY_BASE, barmode="group", bargap=0.20, bargroupgap=0.05,
        title=dict(text=f"<b>Leadership hebdomadaire : {sat_name} vs MSCI World</b>",
                   font=dict(size=13, color="#6B7585")),
        margin=dict(t=50, b=40, l=50, r=30), height=300,
        legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)", x=0, y=1.12, orientation="h"),
        xaxis=dict(gridcolor="#2E3340", showgrid=False),
        yaxis=dict(gridcolor="#2E3340", ticksuffix="%", zeroline=False),
    )
    return fig


def plot_correlation_heatmap(corr_df: pd.DataFrame) -> go.Figure:
    short = {"ANRJ.PA": "H₂", "AASI.PA": "EM", "MWRD.PA": "World",
             "DCAM.PA": "W-PEA", "OR-EUR.PA": "Or",
             "GOLD-EUR.PA": "Or", "FGLDA.DE": "Or", "XAD5.MI": "Or"}
    labels = [short.get(c, c) for c in corr_df.columns]
    fig = go.Figure(go.Heatmap(
        z=corr_df.values.round(2), x=labels, y=labels,
        colorscale=[[0,"#FF3131"],[0.5,"#252932"],[1,"#22C55E"]],
        zmid=0, zmin=-1, zmax=1,
        text=corr_df.values.round(2), texttemplate="%{text:.2f}",
        hovertemplate="<b>%{y} / %{x}</b><br>ρ = %{z:.2f}<extra></extra>",
        showscale=True,
        colorbar=dict(tickfont=dict(color="#CBD5E1", size=9),
                      thickness=12, len=0.8, bgcolor="rgba(0,0,0,0)"),
    ))
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Corrélation Pearson (60j)</b>", font=dict(size=12, color="#6B7585")),
        margin=dict(t=40, b=10, l=60, r=20), height=220,
    )
    return fig


def plot_risk_contribution(rc: Dict) -> Optional[go.Figure]:
    if not rc:
        return None
    short = {"ANRJ.PA": "H₂", "AASI.PA": "EM Asia", "MWRD.PA": "MSCI World",
             "DCAM.PA": "World PEA", "OR-EUR.PA": "Or",
             "GOLD-EUR.PA": "Or", "FGLDA.DE": "Or", "XAD5.MI": "Or"}
    names  = [short.get(tk, tk) for tk in rc]
    values = [rc[tk]["rc_pct"] for tk in rc]
    colors = ["#FF3131" if rc[tk]["flag"] else "#007BFF" for tk in rc]
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker_color=colors, marker_line_width=0,
        hovertemplate="%{y}: <b>%{x:.1f}%</b><extra></extra>",
    ))
    fig.add_vline(x=40, line_dash="dash", line_color="#FF3131",
                  annotation_text="Seuil 40%", annotation_font=dict(color="#FF3131", size=9))
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Risk Contribution (%)</b>", font=dict(size=12, color="#6B7585")),
        margin=dict(t=40, b=10, l=80, r=20), height=200,
        xaxis=dict(gridcolor="#2E3340", ticksuffix="%"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    return fig


def plot_weight_indicator(current_pct: float, target_pct: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round(current_pct, 1),
        number={"suffix": "%", "font": {"size": 26, "color": "#CBD5E1",
                                         "family": "Space Mono"}},
        delta={"reference": target_pct, "relative": False,
               "increasing": {"color": "#F97316"},
               "decreasing": {"color": "#22C55E"},
               "suffix": "%", "valueformat": ".1f"},
        title={"text": "Poids Actuel<br><span style='font-size:.8em;color:#6B7585'>vs Cible (or)</span>",
               "font": {"size": 11, "color": "#8892AA"}},
        gauge={
            "axis": {"range": [0, 35], "tickcolor": "#6B7585",
                     "tickfont": {"size": 9}, "nticks": 8},
            "bar":  {"color": "#007BFF", "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [
                {"range": [0,  5],  "color": "rgba(255,49,49,.18)"},
                {"range": [5,  15], "color": "rgba(249,115,22,.12)"},
                {"range": [15, 25], "color": "rgba(34,197,94,.12)"},
                {"range": [25, 35], "color": "rgba(212,175,55,.10)"},
            ],
            "threshold": {"line": {"color": "#D4AF37", "width": 4},
                          "thickness": 0.85, "value": round(target_pct, 1)},
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#CBD5E1", "family": "DM Sans"},
        margin={"t": 50, "b": 10, "l": 20, "r": 20}, height=230,
    )
    return fig


def plot_alpha_bars(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    world_df = None
    for wt in WORLD_TICKERS:
        df = dm.data.get(wt, pd.DataFrame())
        if not df.empty and "Close" in df.columns:
            world_df = df; break
    sat_df = dm.data.get(ticker, pd.DataFrame())
    if world_df is None or sat_df is None or sat_df.empty:
        return None
    wc = world_df["Close"].dropna(); sc = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 17:
        return None
    alpha = ((sc[common[-16:]].pct_change() - wc[common[-16:]].pct_change()) * 100).dropna().iloc[-15:]
    fig = go.Figure(go.Bar(
        x=[d.strftime("%d/%m") for d in alpha.index],
        y=alpha.values,
        marker_color=["#22C55E" if v > 0 else "#FF3131" for v in alpha.values],
        marker_line_width=0,
    ))
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.6)
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text=f"<b>Écart quotidien</b> : {nom} vs MSCI World — 15 derniers jours",
                   font=dict(size=11, color="#6B7585")),
        margin=dict(t=35, b=25, l=55, r=15), height=200, showlegend=False,
        xaxis=dict(gridcolor="#2E3340", showgrid=False),
        yaxis=dict(gridcolor="#2E3340", ticksuffix="%"),
    )
    return fig


def plot_relative_perf(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    world_df = None
    for wt in WORLD_TICKERS:
        df = dm.data.get(wt, pd.DataFrame())
        if not df.empty and "Close" in df.columns:
            world_df = df; break
    sat_df = dm.data.get(ticker, pd.DataFrame())
    if world_df is None or sat_df is None or sat_df.empty:
        return None
    wc = world_df["Close"].dropna(); sc = sat_df["Close"].dropna()
    common = sc.index.intersection(wc.index)
    if len(common) < 20:
        return None
    cutoff   = max(DATE_DEBUT.date(), (datetime.now() - timedelta(days=120)).date())
    common_f = [d for d in common if d.date() >= cutoff] or list(common[-90:])
    ratio    = sc[common_f] / wc[common_f]
    rel      = (ratio / ratio.iloc[0] - 1) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values.clip(min=0),
        fill="tozeroy", fillcolor="rgba(212,175,55,.12)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False))
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values.clip(max=0),
        fill="tozeroy", fillcolor="rgba(255,49,49,.12)",
        line=dict(color="rgba(0,0,0,0)"), showlegend=False))
    fig.add_trace(go.Scatter(x=rel.index, y=rel.values,
        line=dict(color="#D4AF37", width=2), name=f"{nom}/World"))
    if len(rel) >= 14:
        last14 = rel.iloc[-14:]
        fig.add_vrect(x0=last14.index[0], x1=last14.index[-1],
                      fillcolor="rgba(0,123,255,.06)", layer="below", line_width=0)
    fig.add_hline(y=0, line_dash="dot", line_color="#6B7585", opacity=.7)
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text=f"Performance relative : {nom} vs World (base 100)",
                   font=dict(size=11, color="#6B7585")),
        margin=dict(t=20, b=20, l=50, r=20), height=200, showlegend=False,
        xaxis=dict(gridcolor="#2E3340"), yaxis=dict(gridcolor="#2E3340", ticksuffix="%"),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 13 : STREAMLIT UI — v5.4 : sidebar DCA + benchmark MWR + gold fallback
# ─────────────────────────────────────────────────────────────────────────────

class StreamlitUI:
    def __init__(self, dm: DataManager, pm: PersistenceManager,
                 mre: MarketRegimeEngine, qre: QuantRiskEngine,
                 pe: PortfolioEngine, pde: PedagogicEngine,
                 se: StrategicEngine):
        self.dm  = dm
        self.pm  = pm
        self.mre = mre
        self.qre = qre
        self.pe  = pe
        self.pde = pde
        self.se  = se

    @staticmethod
    def _sign(v: float) -> str:
        return "+" if v >= 0 else ""

    # ── SIDEBAR — v5.4 : DCA Persistance ajoutée ─────────────────────────────
    def render_sidebar(self) -> Tuple[bool, List[Dict], float, float, float]:
        st.sidebar.markdown("## ⚙️ Paramètres v5.4")
        mode_direct = st.sidebar.toggle("🔌 Mode Direct (Vue Brute)", value=False,
            help="Désactive tous les ajustements — valeur marchande pure.")
        st.sidebar.markdown("---")

        cap   = st.sidebar.number_input("Capital réel sorti banque (€)",
                    value=st.session_state["cfg_capital_reel"],
                    step=100.0, format="%.2f", key="input_capital_reel")
        adj   = st.sidebar.number_input("Ajustement patrimonial (€)",
                    value=st.session_state["cfg_ajustement_pat"],
                    step=1.0, format="%.2f", key="input_ajustement_pat")
        bonus = st.sidebar.number_input("Bonus Fortuneo (PRM PEA, €)",
                    value=st.session_state["cfg_bonus_fortuneo"],
                    step=10.0, format="%.2f", key="input_bonus_fortuneo")

        if st.sidebar.button("💾 Sauvegarder paramètres", use_container_width=True):
            ok = _save_config(cap, adj, bonus)
            st.session_state["cfg_capital_reel"]   = cap
            st.session_state["cfg_ajustement_pat"] = adj
            st.session_state["cfg_bonus_fortuneo"] = bonus
            st.session_state["save_feedback"] = "✅ Sauvegardé" if ok else "❌ Erreur"
        if st.session_state.get("save_feedback"):
            fb  = st.session_state["save_feedback"]
            cls = "save-box" if fb.startswith("✅") else "alert-box"
            st.sidebar.markdown(f'<div class="{cls}">{fb}</div>', unsafe_allow_html=True)

        st.sidebar.markdown("---")

        # ── v5.4 : Section DCA — Mise à jour Parts & PRM avec persistance JSON ──
        with st.sidebar.expander("📝 MAJ Parts & PRM (DCA)", expanded=False):
            st.caption("Mettez à jour vos positions après un DCA. Les valeurs sont sauvegardées.")
            new_pos_list = []
            for p in st.session_state["positions"]:
                st.markdown(f"**{p['nom']}**")
                c1, c2 = st.columns(2)
                n_parts = c1.number_input(
                    "Parts",
                    value=float(p["parts"]),
                    key=f"dca_parts_{p['nom']}",
                    format="%.4f",
                    step=0.0001,
                )
                n_prm = c2.number_input(
                    "PRM (€)",
                    value=float(p["prm"]),
                    key=f"dca_prm_{p['nom']}",
                    format="%.2f",
                    step=0.01,
                )
                new_pos_list.append({**p, "parts": n_parts, "prm": n_prm})

            if st.button("💾 Sauvegarder les positions", use_container_width=True):
                st.session_state["positions"] = new_pos_list
                ok = _save_positions_to_config(new_pos_list)
                if ok:
                    st.success("✅ Positions enregistrées !")
                else:
                    st.error("❌ Erreur d'écriture JSON")
                st.rerun()

        st.sidebar.markdown("---")

        if self.pm.status == "github":
            st.sidebar.markdown('<div class="persist-ok">🔗 GitHub Gist actif</div>', unsafe_allow_html=True)
        elif self.pm.warning_msg:
            st.sidebar.markdown(f'<div class="persist-warn">⚠️ {self.pm.warning_msg}</div>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<div class="persist-warn">📂 SQLite local</div>', unsafe_allow_html=True)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📦 Positions (session)")
        st.sidebar.caption("Modifiable en live, non persisté. Utilisez 'MAJ Parts & PRM' pour sauvegarder.")

        # Expanders individuels — lisent depuis st.session_state["positions"]
        positions_conf = []
        for pos in st.session_state["positions"]:
            with st.sidebar.expander(pos["nom"]):
                parts = st.number_input("Parts",   value=float(pos["parts"]),
                    step=0.0001, format="%.4f", key=f"p_{pos['nom']}")
                prm   = st.number_input("PRM (€)", value=float(pos["prm"]),
                    step=0.0001, format="%.4f", key=f"r_{pos['nom']}")
                positions_conf.append({**pos, "parts": parts, "prm": prm})

        capital_reel   = cap
        ajustement_pat = 0.0 if mode_direct else adj
        bonus_fortuneo = 0.0 if mode_direct else bonus

        for pos in positions_conf:
            if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0:
                pos["prm"] -= bonus_fortuneo / pos["parts"]

        return mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo

    # ── HEADER ────────────────────────────────────────────────────────────────
    def render_header(self, mode_direct: bool, live_ok: int, live_total: int):
        now = datetime.now(ZoneInfo("Europe/Paris"))
        st.markdown(
            '<div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:.2rem;">'
            '<span style="font-family:Space Mono,monospace;font-size:1.6rem;font-weight:700;color:#D4AF37;">◈</span>'
            '<span style="font-size:1.5rem;font-weight:700;color:#E2E8F0;">COCKPIT DÉCISIONNEL</span>'
            '<span style="font-family:Space Mono,monospace;font-size:.9rem;color:#6B7585;">'
            'v5.4 · PÉDAGOGIQUE</span></div>', unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption(f"Prix live · {now.strftime('%d/%m/%Y %H:%M:%S')} (Paris) · Cache 30s/90s")
        with c2:
            pct = live_ok / live_total * 100 if live_total else 0
            bc  = "#22C55E" if pct >= 80 else "#F97316" if pct >= 50 else "#FF3131"
            tc  = "#0B0E15" if pct >= 80 else "white"
            st.markdown(
                f'<div style="text-align:right;"><span style="background:{bc};color:{tc};'
                f'padding:.2rem .8rem;border-radius:20px;font-size:.72rem;font-weight:700;">'
                f'📡 {live_ok}/{live_total} LIVE</span></div>', unsafe_allow_html=True)
        if mode_direct:
            st.markdown('<div class="mode-direct-banner">🔌 MODE DIRECT ACTIF — Valeur marchande pure</div>',
                        unsafe_allow_html=True)

    # ── BANDEAU RÉGIME ────────────────────────────────────────────────────────
    def render_regime_banner(self, regime: Dict):
        sc    = regime["confirmed_score"]
        label = regime["confirmed_label"]
        css   = regime["confirmed_css"]
        conf  = "✅ Confirmé" if regime["is_confirmed"] else "⏳ En attente"
        s3    = " → ".join([f"{s:+d}" for s in regime["scores_3d"]])

        st.markdown(
            f'<div class="regime-banner {css}">'
            f'<div><span style="font-size:1.1rem;">🌍 Météo des marchés : <b>{label}</b></span>'
            f'<span style="font-size:.82rem;margin-left:1rem;opacity:.8;">{conf}</span></div>'
            f'<div style="font-family:Space Mono,monospace;font-size:1.2rem;">'
            f'Score : <b>{sc:+d}/5</b></div>'
            f'<div style="font-size:.78rem;opacity:.7;">3j : {s3}</div>'
            f'</div>', unsafe_allow_html=True)

        with st.expander("ℹ️ Comment lire la météo des marchés ?", expanded=False):
            reg_trans = self.pde.translate_regime(regime)
            col_exp, col_comp = st.columns([1, 2])
            with col_exp:
                level_color = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}.get(reg_trans["level"], "#6B7585")
                st.markdown(
                    f'<div class="pedagogy-box">'
                    f'<div class="pedagogy-title">Ce que ça signifie</div>'
                    f'<div style="font-size:2rem;text-align:center;margin:.4rem 0;">{reg_trans["emoji"]}</div>'
                    f'<div style="color:{level_color};font-weight:700;margin-bottom:.4rem;">{label}</div>'
                    f'<div>{reg_trans["explain"]}</div>'
                    f'<div style="margin-top:.6rem;padding:.5rem;background:rgba(0,0,0,.2);border-radius:6px;">'
                    f'💡 <b>Que faire ?</b><br>{reg_trans["action"]}</div>'
                    f'</div>', unsafe_allow_html=True)
            with col_comp:
                st.markdown('<div style="font-size:.82rem;color:#6B7585;margin-bottom:.5rem;">Les 5 critères analysés :</div>', unsafe_allow_html=True)
                comp_cols = st.columns(5)
                for i, comp in enumerate(regime.get("components", [])):
                    with comp_cols[i % 5]:
                        bull = comp["bull"]
                        ico  = "🟢" if bull is True else "🔴" if bull is False else "⚪"
                        sc_  = "+1" if bull is True else "−1" if bull is False else "0"
                        st.markdown(
                            f'<div class="card" style="padding:.8rem;text-align:center;">'
                            f'<div style="font-size:1.4rem;">{ico}</div>'
                            f'<div style="font-size:.72rem;color:#6B7585;margin:.2rem 0;">{comp["name"]}</div>'
                            f'<div style="font-family:Space Mono;font-weight:700;'
                            f'color:{"#22C55E" if bull else "#FF3131" if bull is False else "#6B7585"};">'
                            f'{sc_}</div>'
                            f'<div style="font-size:.68rem;color:#4B5563;margin-top:.2rem;">{comp["val"]}</div>'
                            f'</div>', unsafe_allow_html=True)

    # ── COMMAND CENTER — v5.4 : Gap affiché sur benchmark MWR ajusté ─────────
    def render_command_center(self, ptf: Dict, bench: Dict,
                               mode_direct: bool, pm: PersistenceManager):
        st.markdown("## 🚀 Vue d'ensemble du portefeuille")

        perf_j_chain, perf_c_chain, base_cap = pm.compute_daily_performance(ptf["valeur_totale"])

        c1, c2, c3, c4 = st.columns(4)
        s = self._sign

        with c1:
            crd = "card card-purple" if mode_direct else "card card-gold"
            lbl = "Valeur Brute" if mode_direct else "Valeur Totale"
            vj, vjp = ptf["perf_j_eur"], ptf["perf_j_pct"]
            st.markdown(
                f'<div class="{crd}"><div class="kpi-label">{lbl}<span class="live-badge">LIVE</span></div>'
                f'<div class="kpi-value">{ptf["solde_total"]:,.2f}€</div>'
                f'<div class="kpi-delta-{"pos" if vj>=0 else "neg"}">'
                f'{s(vj)}{vj:,.2f}€ ({s(vjp)}{vjp:.2f}%) vs hier</div></div>',
                unsafe_allow_html=True)

        with c2:
            gr  = ptf["gain_reel"]
            clr = "#22C55E" if gr >= 0 else "#FF3131"
            st.markdown(
                f'<div class="card card-blue"><div class="kpi-label">Gain / Perte total</div>'
                f'<div class="kpi-value" style="color:{clr};">{s(gr)}{gr:,.2f}€</div>'
                f'<div class="small">Investi : {ptf["capital_reel"]:,.2f}€</div></div>',
                unsafe_allow_html=True)

        with c3:
            p   = ptf["perf_tot_pct"]
            pc  = "#22C55E" if p >= 0 else "#FF3131"
            # v5.4 : gap principal = vs benchmark MWR ajusté
            gap = bench.get("gap")  # gap vs MWR ajusté
            gap_ls = bench.get("gap_lumpsum")  # gap vs lump sum (référence secondaire)
            gc  = "#22C55E" if (gap or 0) >= 0 else "#FF3131"
            pcc = "#22C55E" if perf_c_chain >= 0 else "#FF3131"
            mwr_adj = bench.get("perf_bench_adj")
            if gap is not None and mwr_adj is not None:
                gap_html = (
                    f'<div class="small">Vs World MWR : '
                    f'<span style="color:{gc};font-weight:700;">{s(gap)}{gap:.2f}%</span>'
                    f'<span class="mwr-badge">MWR</span>'
                    f'</div>'
                )
            elif gap_ls is not None:
                gc_ls = "#22C55E" if gap_ls >= 0 else "#FF3131"
                gap_html = (
                    f'<div class="small">Vs World (LS) : '
                    f'<span style="color:{gc_ls};font-weight:700;">{s(gap_ls)}{gap_ls:.2f}%</span>'
                    f'</div>'
                )
            else:
                gap_html = ""
            st.markdown(
                f'<div class="card card-blue"><div class="kpi-label">Performance</div>'
                f'<div class="kpi-value" style="color:{pc};">{s(p)}{p:.2f}%</div>'
                f'{gap_html}'
                f'<div class="small">Chaîné : <span style="color:{pcc};font-weight:700;">{s(perf_c_chain)}{perf_c_chain:.2f}%</span></div>'
                f'</div>', unsafe_allow_html=True)

        with c4:
            pb    = bench.get("perf_bench_adj")   # v5.4 : afficher le MWR ajusté
            pb_ls = bench.get("perf_bench")        # Lump Sum en tooltip
            pbj   = bench.get("perf_bench_j")
            if pb is not None:
                pbc = "#22C55E" if pb >= 0 else "#FF3131"
                pbj_html = (f'<div class="kpi-delta-{"pos" if pbj>=0 else "neg"}">'
                            f'{s(pbj)}{pbj:.2f}% vs hier</div>' if pbj is not None else "")
                ls_html = (f'<div class="small" style="color:#4B5563;">LS : {s(pb_ls)}{pb_ls:.2f}%</div>'
                           if pb_ls is not None else "")
                body_bench = (
                    f'<div class="kpi-value" style="color:{pbc};">{s(pb)}{pb:.2f}%</div>'
                    f'{pbj_html}{ls_html}'
                )
            else:
                body_bench = '<div class="kpi-value">N/A</div>'
            st.markdown(
                f'<div class="card card-blue">'
                f'<div class="kpi-label">MSCI World MWR<span class="mwr-badge">AJUSTÉ</span>'
                f'<span class="live-badge">LIVE</span></div>'
                f'{body_bench}</div>', unsafe_allow_html=True)

        st.markdown("### 📊 Mes positions")
        col_t, col_p = st.columns([3, 2])
        with col_t:
            rows = []
            for p2 in ptf["positions"]:
                perf_f = f"{s(p2['perf_pct'])}{p2['perf_pct']:.2f}%" if p2["perf_pct"] is not None else "N/A"
                vj_f   = f"{s(p2['var_jour_pct'])}{p2['var_jour_pct']:.2f}%" if p2["var_jour_pct"] else "–"
                vje_f  = f"{s(p2['var_jour_eur'])}{p2['var_jour_eur']:,.2f}€" if p2["var_jour_eur"] else "–"
                prix_f = f"{p2['prix']:.3f}€" if p2["prix"] else "N/A"
                rows.append({"Position": p2["nom"], "Env.": p2["enveloppe"], "Prix": prix_f,
                             "Valeur (€)": f"{p2['valeur']:,.2f}", "Perf.": perf_f,
                             "Δ Jour (%)": vj_f, "Δ Jour (€)": vje_f})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            if not mode_direct:
                st.markdown(
                    f'<div class="info-box">Ajustement patrimonial inclus : +{ptf["ajustement_pat"]:,.2f}€</div>',
                    unsafe_allow_html=True)
        with col_p:
            donut = [p2 for p2 in ptf["positions"] if p2["valeur"] > 0]
            if donut:
                colors_pie = ["#007BFF","#6366F1","#D4AF37","#F97316","#22C55E"]
                fig_pie = go.Figure(go.Pie(
                    labels=[d["nom"] for d in donut], values=[d["valeur"] for d in donut],
                    hole=0.6, textinfo="percent",
                    marker=dict(colors=colors_pie[:len(donut)], line=dict(color="#1C1F26", width=2)),
                ))
                vt = ptf["valeur_totale"]
                fig_pie.update_layout(
                    **_PLOTLY_BASE, margin=dict(t=10,b=10,l=10,r=10), height=270,
                    legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                    annotations=[dict(text=f"{vt:,.0f}€", x=.5, y=.5,
                        font=dict(size=13,color="#D4AF37",family="Space Mono"), showarrow=False)])
                st.plotly_chart(fig_pie, use_container_width=True)

        # v5.4 : Encart explicatif benchmark MWR
        mwr_adj = bench.get("perf_bench_adj")
        if mwr_adj is not None:
            gap = bench.get("gap", 0.0) or 0.0
            gc  = "#22C55E" if gap >= 0 else "#FF3131"
            st.markdown(
                f'<div class="pedagogy-box">'
                f'<div class="pedagogy-title">🆕 v5.4 — Benchmark MWR Cash-Flow Adjusted</div>'
                f'Le "Gap vs World" est désormais calculé en simulant l\'achat de MWRD.PA '
                f'aux mêmes dates et montants que vos flux réels (avec 0.10% de frais). '
                f'<b>World MWR = {s(mwr_adj)}{mwr_adj:.2f}%</b> · '
                f'<b style="color:{gc};">Votre Alpha = {s(gap)}{gap:.2f}%</b>'
                f'</div>', unsafe_allow_html=True)

    # ── EQUITY CURVE ──────────────────────────────────────────────────────────
    def render_equity_curve_section(self, ptf: Dict, regime: Dict,
                                     unified_h: Dict, unified_a: Dict,
                                     positions_conf: List[Dict]):
        st.markdown("## 📈 Historique de votre capital")
        col_eq, col_snap = st.columns([3, 1])

        history = self.pm.load_history()
        with col_eq:
            fig_eq = plot_equity_curve(history)
            if fig_eq:
                st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar": False})
                st.markdown(
                    '<div class="pedagogy-box">'
                    '<div class="pedagogy-title">Ce que montre ce graphique</div>'
                    'La ligne dorée représente l\'évolution réelle de votre capital jour après jour. '
                    'La ligne bleue pointillée montre votre performance cumulée en %. '
                    'Les zones colorées indiquent le régime de marché pendant chaque période.'
                    '</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="card card-orange">'
                    '<div class="kpi-label">Aucun historique enregistré</div>'
                    '<div class="small">Utilisez le bouton "📸 Enregistrer" à droite pour démarrer '
                    'le suivi de votre capital. Faites-le chaque soir de bourse.</div></div>',
                    unsafe_allow_html=True)
            if not history.empty:
                perf_j, perf_c, base_cap = self.pm.compute_daily_performance(ptf["valeur_totale"])
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Jours enregistrés", f"{len(history)}")
                mc2.metric("Base hier (€)", f"{base_cap:,.2f}")
                mc3.metric("Perf du jour", f"{perf_j:+.2f}%")
                mc4.metric("Perf totale", f"{perf_c:+.2f}%")

        with col_snap:
            st.markdown('<div class="card card-green">', unsafe_allow_html=True)
            st.markdown("### 💾 Enregistrer")
            st.caption("Sauvegardez l'état du portefeuille ce soir.")

            vt       = ptf["valeur_totale"]
            pj, pc, _ = self.pm.compute_daily_performance(vt)
            poids_h  = next((p["valeur"]/vt*100 for p in ptf["positions"] if p["nom"]=="Global Hydrogen" and vt>0), 0.0)
            poids_em = next((p["valeur"]/vt*100 for p in ptf["positions"] if p["nom"]=="EM Asia" and vt>0), 0.0)

            st.markdown(f"""
<div style="font-size:.82rem;color:#6B7585;line-height:1.8;">
<b>Capital :</b> {vt:,.2f}€<br>
<b>Aujourd'hui :</b> {pj:+.2f}%<br>
<b>Total :</b> {pc:+.2f}%<br>
<b>Régime :</b> {regime["confirmed_label"]}<br>
<b>H₂ :</b> {poids_h:.1f}% | <b>EM :</b> {poids_em:.1f}%
</div>""", unsafe_allow_html=True)

            if st.button("📸 Enregistrer Snapshot", use_container_width=True, type="primary"):
                ok = self.pm.save_snapshot(
                    capital_cloture=vt, valeur_titres=vt,
                    perf_jour=round(pj, 4), perf_cumul=round(pc, 4),
                    regime=regime["confirmed_label"],
                    score_regime=regime["confirmed_score"],
                    poids_h=round(poids_h, 4), poids_em=round(poids_em, 4)
                )
                if ok:
                    st.success("✅ Enregistré" +
                               (" + GitHub" if self.pm.status == "github" else ""))
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Échec")

            if not history.empty:
                st.markdown("---")
                st.markdown(f'<div class="small">Dernier : {history["date"].iloc[-1]}</div>',
                            unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── LEADERSHIP COMPARISON (v5.3 inchangé) ─────────────────────────────────
    def render_leadership_comparison(self, nom: str, ticker: str,
                                      color_sat: str = "#D4AF37"):
        st.markdown(f"### 📊 {nom} vs MSCI World — Leadership hebdomadaire")
        with st.container():
            st.markdown(
                '<div class="leadership-header">'
                '<div style="font-size:.8rem;color:#6B7585;margin-bottom:.3rem;">POURQUOI CE GRAPHIQUE EST IMPORTANT</div>'
                '<div style="color:#E2E8F0;line-height:1.6;">'
                'Ce graphique compare chaque semaine la performance de votre ETF vs le MSCI World. '
                '<b>Si l\'ETF fait régulièrement moins bien que le World</b>, il perd sa raison d\'être '
                'dans votre portefeuille — autant acheter du MSCI World pur et simple.'
                '</div>'
                '</div>', unsafe_allow_html=True)

            labels, sat_perfs, world_perfs = self.pde.get_weekly_performances(self.dm, ticker)

            if labels and sat_perfs and world_perfs:
                col_chart, col_verdict = st.columns([2, 1])
                with col_chart:
                    fig = plot_weekly_leadership(labels, sat_perfs, world_perfs, nom, color_sat)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                with col_verdict:
                    gaps = [s - w for s, w in zip(sat_perfs, world_perfs)]
                    st.markdown('<div class="kpi-label">COMPARAISON SEMAINE PAR SEMAINE</div>', unsafe_allow_html=True)
                    rows_lead = []
                    for i, (lbl, s_p, w_p) in enumerate(zip(labels, sat_perfs, world_perfs)):
                        gap = s_p - w_p
                        winner = f"🟢 +{gap:.1f}% {nom[:6]}" if gap > 0 else f"🔴 {gap:.1f}% World"
                        rows_lead.append({"Semaine": lbl, f"{nom[:8]}": f"{s_p:+.1f}%",
                                          "World": f"{w_p:+.1f}%", "Résultat": winner})
                    st.dataframe(pd.DataFrame(rows_lead), use_container_width=True, hide_index=True)
                    verdict = self.pde.translate_leadership(nom, gaps)
                    level_color = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}.get(verdict["level"], "#6B7585")
                    level_bg    = {"green": "rgba(34,197,94,.1)", "orange": "rgba(249,115,22,.1)", "red": "rgba(255,49,49,.1)"}.get(verdict["level"], "rgba(107,117,133,.1)")
                    st.markdown(
                        f'<div style="background:{level_bg};border:1px solid {level_color};'
                        f'border-radius:10px;padding:1rem;margin-top:.5rem;">'
                        f'<div style="font-weight:700;font-size:1rem;color:{level_color};">'
                        f'{verdict["message"]}</div>'
                        f'<div style="font-size:.8rem;color:#8892AA;margin:.4rem 0;">{verdict["detail"]}</div>'
                        f'<div style="font-size:.85rem;color:#CBD5E1;margin-top:.5rem;">'
                        f'💡 {verdict["action"]}</div>'
                        f'</div>', unsafe_allow_html=True)
            else:
                st.info("Données hebdomadaires insuffisantes. Revenez après quelques semaines de données.")

    # ── RISK DASHBOARD — v5.4 : Fallback Or systématique ─────────────────────
    def render_risk_dashboard(self, ptf: Dict):
        st.markdown("## ⚠️ Gestion des risques")

        with st.expander("❓ Comment lire les indicateurs de risque ?", expanded=False):
            st.markdown("""
<div class="pedagogy-box">
<div class="pedagogy-title">Guide de lecture des risques</div>
<b>Agitation (Volatilité)</b> : mesure les oscillations quotidiennes de l'ETF.
Plus c'est élevé, plus l'ETF peut monter OU baisser brutalement.<br><br>
<b>Sensibilité (Beta)</b> : si le marché mondial baisse de 10% et que le Beta est 1.5,
votre ETF peut baisser de 15%. Plus le Beta est élevé, plus le risque est amplifié.<br><br>
<b>Recul depuis le sommet (Drawdown)</b> : indique à quelle distance du dernier pic
se trouve l'ETF. -20% signifie qu'il a perdu 20% depuis son sommet récent.
</div>
""", unsafe_allow_html=True)

        st.markdown("### 🔍 Analyse de risque par ETF")

        # v5.4 : récupérer les données Or via le système de fallback
        gold_df, gold_tk_used = self.qre.get_robust_gold_data()

        risk_assets = [
            ("ANRJ.PA",  "Hydrogen",    "#F97316", None),
            ("AASI.PA",  "EM Asia",     "#6366F1", None),
            ("MWRD.PA",  "MSCI World",  "#007BFF", None),
            (gold_tk_used or "OR-EUR.PA", "Or Physique", "#D4AF37", gold_df),
        ]

        cols = st.columns(4)
        for i, (tk, name, color, custom_df) in enumerate(risk_assets):
            with cols[i]:
                # v5.4 : pour l'Or, utiliser les méthodes _from_df si on a un custom_df
                if custom_df is not None:
                    vol  = self.qre.rolling_volatility_from_df(custom_df, 30)
                    beta = self.qre.rolling_beta_from_df(custom_df)
                    dd   = self.qre.drawdown_metrics_from_df(custom_df, 252)
                    gold_note = f"<div style='font-size:.65rem;color:#6B7585;margin-bottom:.3rem;'>Ticker: {gold_tk_used}</div>" if gold_tk_used else ""
                else:
                    vol  = self.qre.rolling_volatility(tk, 30)
                    beta = self.qre.rolling_beta(tk)
                    dd   = self.qre.drawdown_metrics(tk, 252)
                    gold_note = ""

                vol_t  = self.pde.translate_volatility(vol, name)
                beta_t = self.pde.translate_beta(beta, name)
                dd_t   = self.pde.translate_drawdown(dd.get("current_dd"), dd.get("max_dd"), name)

                level_colors = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}

                st.markdown(
                    f'<div class="card" style="border-top:3px solid {color};">'
                    f'<div class="kpi-label">{name}</div>'
                    f'{gold_note}',
                    unsafe_allow_html=True)

                vc = level_colors[vol_t["level"]]
                st.markdown(
                    f'<div class="pedago-metric">'
                    f'<div class="pedago-metric-title">Agitation (Volatilité)</div>'
                    f'<div class="pedago-metric-value" style="color:{vc};">'
                    f'{vol_t["emoji"]} {vol_t["value"]}</div>'
                    f'<div class="pedago-metric-explain">{vol_t["explain"].split(chr(10))[0]}</div>'
                    f'</div>', unsafe_allow_html=True)

                bc = level_colors[beta_t["level"]]
                beta_explain_short = beta_t["explain"][:80] + "..." if len(beta_t["explain"]) > 80 else beta_t["explain"]
                st.markdown(
                    f'<div class="pedago-metric">'
                    f'<div class="pedago-metric-title">Sensibilité au marché (Beta)</div>'
                    f'<div class="pedago-metric-value" style="color:{bc};">'
                    f'{beta_t["emoji"]} {beta_t["value"]}</div>'
                    f'<div class="pedago-metric-explain">{beta_explain_short}</div>'
                    f'</div>', unsafe_allow_html=True)

                dc = level_colors[dd_t["level"]]
                st.markdown(
                    f'<div class="pedago-metric">'
                    f'<div class="pedago-metric-title">Recul depuis le sommet</div>'
                    f'<div class="pedago-metric-value" style="color:{dc};">'
                    f'{dd_t["emoji"]} {dd_t["value"]}</div>'
                    f'<div class="pedago-metric-explain">{dd_t["explain"][:80]}...</div>'
                    f'</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

        # Corrélation et Risk Contribution (expert)
        with st.expander("🔬 Analyse experte : Corrélation & Contribution au risque", expanded=False):
            col_corr, col_rc = st.columns(2)

            # v5.4 : utiliser le ticker Or résolu pour la matrice de corrélation
            gold_corr_tk = gold_tk_used or "OR-EUR.PA"
            tickers_ptf  = ["ANRJ.PA", "AASI.PA", "MWRD.PA", gold_corr_tk]
            positions_map = {p["nom"]: p for p in ptf["positions"]}
            vt = ptf["valeur_totale"]

            with col_corr:
                corr_df = self.qre.correlation_matrix(tickers_ptf, 60)
                if corr_df is not None:
                    fig_c = plot_correlation_heatmap(corr_df)
                    st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})
                    st.markdown(
                        '<div class="pedagogy-box">'
                        'Une corrélation proche de +1 signifie que les deux ETFs bougent ensemble. '
                        'Idéalement, vos actifs ne devraient pas tous monter et baisser en même temps.'
                        '</div>', unsafe_allow_html=True)
                else:
                    st.info("Données insuffisantes (< 60j).")

            with col_rc:
                weights_ptf, valid_tk = [], []
                for tk in tickers_ptf:
                    df = self.dm.data.get(tk, pd.DataFrame())
                    if not df.empty:
                        nom = next((p["nom"] for p in ptf["positions"]
                                    if p.get("ticker") == tk or
                                    (tk == gold_corr_tk and p["nom"] == "Or Physique")), "")
                        val = positions_map.get(nom, {}).get("valeur", 0.0)
                        valid_tk.append(tk)
                        weights_ptf.append(val)
                if valid_tk and sum(weights_ptf) > 0:
                    rc = self.qre.risk_contribution(valid_tk, weights_ptf, 60)
                    if rc:
                        fig_rc = plot_risk_contribution(rc)
                        if fig_rc:
                            st.plotly_chart(fig_rc, use_container_width=True, config={"displayModeBar": False})
                        flags = [tk for tk, v in rc.items() if v["flag"]]
                        if flags:
                            short = {"ANRJ.PA": "Hydrogen", "AASI.PA": "EM Asia",
                                     "MWRD.PA": "MSCI World",
                                     "OR-EUR.PA": "Or", "GOLD-EUR.PA": "Or",
                                     "FGLDA.DE": "Or", "XAD5.MI": "Or"}
                            f_names = ", ".join([short.get(f, f) for f in flags])
                            st.markdown(
                                f'<div class="alert-box">🚨 <b>Trop de risque concentré</b> : '
                                f'{f_names} représente plus de 40% du risque total. '
                                f'Rééquilibrez les poids.</div>', unsafe_allow_html=True)

    # ── SATELLITE CARD PÉDAGOGIQUE (v5.3 inchangé) ────────────────────────────
    def render_satellite_card_pedagogic(self, nom: str, ticker: str,
                                         unified: Dict, target_weight: Dict,
                                         regime: Dict, sent_rows: List[Dict],
                                         sector: str):
        color_map = {"hydrogen": "#F97316", "em_asia": "#6366F1"}
        color = color_map.get(sector, "#D4AF37")

        strat_full   = self.se.compute(ticker, unified, regime)
        simple_score = self.pde.translate_simple_score(unified["total"])

        st.markdown(f'<div class="card" style="border-top:3px solid {color};padding:0;overflow:hidden;">', unsafe_allow_html=True)

        c_score, c_action = st.columns([2, 3])
        with c_score:
            st.markdown(
                f'<div style="padding:1.4rem 1.4rem .8rem 1.4rem;">'
                f'<div class="kpi-label">{nom} — Score Global</div>'
                f'<div class="simple-score-ring {simple_score["ring_cls"]}" style="margin:1rem auto;">'
                f'{strat_full["total"]}/5</div>'
                f'<div style="text-align:center;margin:.4rem 0;">'
                f'<span style="font-size:1.3rem;">{simple_score["stars"]}</span></div>'
                f'<div style="text-align:center;font-weight:700;color:#E2E8F0;font-size:.95rem;">'
                f'{simple_score["label"]}</div>'
                f'<div style="text-align:center;font-size:.82rem;color:#8892AA;margin-top:.3rem;">'
                f'{simple_score["explain"]}</div></div>', unsafe_allow_html=True)

        with c_action:
            st.markdown('<div style="padding:1.4rem 1.4rem .8rem 1.4rem;">', unsafe_allow_html=True)
            st.markdown('<div class="kpi-label">Les 5 critères d\'analyse</div>', unsafe_allow_html=True)
            for detail in strat_full["details"]:
                icon  = "✅" if detail["score"] == 1 else "❌"
                clr   = "#86EFAC" if detail["score"] == 1 else "#FCA5A5"
                st.markdown(
                    f'<div style="display:flex;align-items:flex-start;gap:.5rem;'
                    f'margin:.3rem 0;font-size:.84rem;">'
                    f'<span style="font-size:1rem;flex-shrink:0;">{icon}</span>'
                    f'<div>'
                    f'<span style="color:{clr};font-weight:700;">{detail["dim"]}</span>'
                    f'<span style="color:#6B7585;margin-left:.4rem;font-size:.78rem;">{detail["value"]}</span>'
                    f'<br><span style="color:#8892AA;font-size:.78rem;">{detail["label"]}</span>'
                    f'</div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="{strat_full["verdict_cls"]} verdict-card">'
            f'{strat_full["verdict"]}'
            f'<div style="font-size:.82rem;margin-top:.4rem;opacity:.9;">'
            f'💡 {simple_score["action"]}</div></div>', unsafe_allow_html=True)

        self.render_leadership_comparison(nom, ticker, color)

        sent_verdict = self.pde.translate_sentinelles(sent_rows, sector)
        lv_color = {"green": "#22C55E", "orange": "#F97316", "red": "#FF3131"}.get(sent_verdict["level"], "#6B7585")
        lv_bg    = {"green": "rgba(34,197,94,.1)", "orange": "rgba(249,115,22,.1)", "red": "rgba(255,49,49,.1)"}.get(sent_verdict["level"], "rgba(107,117,133,.1)")
        st.markdown(
            f'<div style="background:{lv_bg};border-left:4px solid {lv_color};'
            f'border-radius:8px;padding:.8rem 1rem;margin:.5rem 0;">'
            f'<b>Santé du secteur :</b> {sent_verdict["emoji"]} {sent_verdict["message"]}<br>'
            f'<span style="font-size:.82rem;color:#8892AA;">{sent_verdict["detail"]}</span><br>'
            f'<span style="font-size:.84rem;color:#CBD5E1;">💡 {sent_verdict["action"]}</span>'
            f'</div>', unsafe_allow_html=True)

        with st.expander("⚙️ Allocation cible & ajustement", expanded=False):
            col_gauge, col_detail = st.columns([1, 2])
            with col_gauge:
                cur_pct = target_weight.get("current_pct", 0.0)
                tgt_pct = target_weight.get("target_pct", 0.0)
                fig_w = plot_weight_indicator(cur_pct, tgt_pct)
                st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})
            with col_detail:
                action  = target_weight.get("action", "MAINTENIR")
                delta_e = target_weight.get("delta_eur", 0.0)
                cur_pct = target_weight.get("current_pct", 0.0)
                tgt_pct = target_weight.get("target_pct", 0.0)
                if action == "RÉDUIRE":
                    st.markdown(
                        f'<div class="arb-sell">'
                        f'<div style="font-size:.72rem;color:#FF3131;letter-spacing:1px;">🚨 ACTION RECOMMANDÉE</div>'
                        f'<div style="font-size:1.1rem;color:#FCA5A5;font-weight:700;">VENDRE {abs(delta_e):,.0f}€</div>'
                        f'<div style="font-size:.82rem;color:#8892AA;margin-top:.3rem;">'
                        f'Votre position est trop importante ({cur_pct:.1f}%) par rapport à la cible ({tgt_pct:.1f}%).</div>'
                        f'</div>', unsafe_allow_html=True)
                elif action == "RENFORCER":
                    st.markdown(
                        f'<div class="arb-buy">'
                        f'<div style="font-size:.72rem;color:#22C55E;letter-spacing:1px;">💡 OPPORTUNITÉ</div>'
                        f'<div style="font-size:1.1rem;color:#86EFAC;font-weight:700;">ACHETER {abs(delta_e):,.0f}€</div>'
                        f'<div style="font-size:.82rem;color:#8892AA;margin-top:.3rem;">'
                        f'Vous êtes en dessous de la cible ({cur_pct:.1f}% vs {tgt_pct:.1f}%).</div>'
                        f'</div>', unsafe_allow_html=True)
                else:
                    st.markdown(
                        f'<div class="arb-neutral">'
                        f'<div style="font-size:.72rem;color:#6B7585;">✅ SITUATION ÉQUILIBRÉE</div>'
                        f'<div style="font-size:1.1rem;color:#CBD5E1;font-weight:600;">MAINTENIR</div>'
                        f'<div style="font-size:.82rem;color:#8892AA;margin-top:.3rem;">'
                        f'Position à {cur_pct:.1f}% — objectif {tgt_pct:.1f}%.</div>'
                        f'</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="margin-top:.8rem;font-size:.8rem;color:#6B7585;">'
                    f'Régime actuel : <b style="color:#CBD5E1;">{target_weight.get("regime_label","N/A")}</b> '
                    f'(Multiplicateur × {target_weight.get("regime_mult", 1.0):.2f})</div>',
                    unsafe_allow_html=True)

        with st.expander(f"📐 Analyse technique détaillée — {nom}", expanded=False):
            fig_a = plot_alpha_bars(self.dm, ticker, nom)
            if fig_a:
                st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})
                st.caption("Chaque barre = journée où l'ETF a fait mieux (vert) ou moins bien (rouge) que le MSCI World.")
            fig_r = plot_relative_perf(self.dm, ticker, nom)
            if fig_r:
                st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})
                st.caption("Courbe au-dessus de 0 = l'ETF surperforme le World depuis le début du suivi.")

    # ── SENTINELLES & MACRO ────────────────────────────────────────────────────
    def render_sentinelles_macro(self, ptf: Dict):
        st.markdown("## 🛰️ Radar Sectoriel & Macro-économie")
        col_s, col_m = st.columns([3, 2])

        s_msg, s_col, sent_rows = self.pe.evaluate_sentinelles()
        with col_s:
            st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
            st.markdown("### 📡 Valeurs de référence sectorielles")
            st.caption("Ces entreprises sont des indicateurs avancés de la santé de vos ETFs.")
            if "OK" in s_msg: st.success(s_msg)
            else:             st.warning(s_msg)
            st.dataframe(pd.DataFrame(sent_rows), use_container_width=True, hide_index=True)
            st.markdown("---")
            st.markdown("#### ⚖️ Poids Satellites actuels")
            vt      = ptf["valeur_totale"]
            anrj_v  = next((p["valeur"] for p in ptf["positions"] if p["nom"]=="Global Hydrogen"), 0)
            aasi_v  = next((p["valeur"] for p in ptf["positions"] if p["nom"]=="EM Asia"), 0)
            poids_s = (anrj_v + aasi_v) / vt * 100 if vt else 0
            delta_ps = poids_s - 45
            st.metric("Hydrogen + EM Asia", f"{poids_s:.1f}%",
                      delta=f"{self._sign(delta_ps)}{delta_ps:.1f}% vs objectif 45%")
            bc = "#FF3131" if poids_s > 45 else "#22C55E"
            st.markdown(
                f'<div style="background:#1C1F26;border-radius:6px;height:8px;">'
                f'<div style="background:{bc};width:{min(poids_s,100):.1f}%;height:8px;border-radius:6px;"></div>'
                f'</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_m:
            st.markdown('<div class="card card-gold">', unsafe_allow_html=True)
            st.markdown("### 🌍 Indicateurs Macro <span class='live-badge'>LIVE</span>",
                        unsafe_allow_html=True)
            st.caption("Ces données donnent le contexte économique mondial.")
            FMT = {"NQ=F":".2f","ES=F":".2f","^TNX":".3f","EURUSD=X":".4f",
                   "BZ=F":".2f","GC=F":".2f","DX-Y.NYB":".2f","MCHI":".2f"}
            SFX = {"^TNX":"%","BZ=F":"$","GC=F":"$"}
            SIGNALS = {"^TNX":     (4.50,  "↑ Défavorable hydro", "↓ OK hydro"),
                       "DX-Y.NYB": (105.0, "↑ Pression EM",       "↓ OK EM")}
            for sym, lbl in MACRO_TICKERS.items():
                info_m = self.dm.live.get(sym, {})
                if info_m.get("prix"):
                    pv, pm2 = info_m["prix"], info_m.get("prev")
                    delta_m = (f'{self._sign((pv-pm2)/pm2*100)}{(pv-pm2)/pm2*100:.2f}%'
                               if pm2 and pm2 != 0 else None)
                    sig   = SIGNALS.get(sym)
                    extra = (f"  {sig[1] if pv > sig[0] else sig[2]}" if sig else "")
                    st.metric(lbl, f"{pv:{FMT.get(sym,'.2f')}}{SFX.get(sym,'')}{extra}",
                              delta=delta_m)
                else:
                    st.metric(lbl, "N/A")
            st.markdown('</div>', unsafe_allow_html=True)

    # ── SIMULATEUR FISCAL ─────────────────────────────────────────────────────
    def render_fiscal_simulator(self, ptf: Dict):
        st.markdown("## 🧮 Simulateur Fiscal")
        st.caption("Calculez le montant net que vous recevrez après impôts si vous vendez.")
        col_pea, col_av = st.columns(2)
        val_env, gan_env = ptf["val_env"], ptf["gain_env"]

        with col_pea:
            st.markdown('<div class="card card-blue"><h4>🏦 PEA</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("PEA", val_env["PEA"], val_env["PEA"], gan_env["PEA"])
            if avert:
                st.warning(avert)
                st.metric("Valeur brute PEA", f"{val_env['PEA']:,.2f}€")
            else:
                st.metric("Net après prélèvements (17.2%)", f"{net:,.2f}€")
            st.caption(f"Gain latent PEA : {self._sign(gan_env['PEA'])}{gan_env['PEA']:,.2f}€")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_av:
            st.markdown('<div class="card card-blue"><h4>🛡️ Assurance-Vie</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("AV", val_env["AV"], val_env["AV"], gan_env["AV"])
            if avert:
                st.warning(avert)
                st.metric("Valeur brute AV", f"{val_env['AV']:,.2f}€")
            else:
                st.metric("Net après fiscalité AV", f"{net:,.2f}€")
            st.caption(f"Gain latent AV : {self._sign(gan_env['AV'])}{gan_env['AV']:,.2f}€")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💸 Simulez un retrait partiel")
        sc1, sc2 = st.columns([2, 1])
        with sc2:
            env_sim = st.selectbox("Enveloppe", ["AV", "PEA"])
        with sc1:
            max_val     = float(max(val_env.get(env_sim, 0), 1000))
            montant_sim = st.slider("Montant à retirer (€)", 0.0, max_val,
                                     min(1000.0, max_val), step=100.0)
        net_sim, avert_sim = net_apres_impots(env_sim, montant_sim,
                                               val_env.get(env_sim, 0), gan_env.get(env_sim, 0))
        if avert_sim:
            st.warning(avert_sim)
        elif montant_sim > 0:
            vp, gp   = val_env.get(env_sim, 0), gan_env.get(env_sim, 0)
            gain_sim = montant_sim * (gp / vp if vp else 0)
            imp_sim  = montant_sim - net_sim
            st.markdown(
                f'<div class="net-box" style="display:flex;gap:2.5rem;flex-wrap:wrap;align-items:center;">'
                f'<div><div class="kpi-label">Vous retirez</div><div class="kpi-value">{montant_sim:,.2f}€</div></div>'
                f'<div style="color:#6B7585;font-size:1.5rem;">→</div>'
                f'<div><div class="kpi-label">Part gains imposables</div><div class="kpi-value" style="color:#D4AF37;">{gain_sim:,.2f}€</div></div>'
                f'<div><div class="kpi-label">Impôts / PS</div><div class="kpi-value" style="color:#FF3131;">{imp_sim:,.2f}€</div></div>'
                f'<div><div class="kpi-label">Vous recevez</div><div class="kpi-value" style="color:#22C55E;">{net_sim:,.2f}€</div></div>'
                f'</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    def render_footer(self, mode_direct: bool, capital: float,
                       score_h: int, score_a: int, regime_label: str,
                       live_ok: int, live_total: int):
        st.markdown("---")
        col_f1, col_f2 = st.columns([4, 1])
        with col_f1:
            s = self._sign
            mode_txt = "🔌 MODE DIRECT" if mode_direct else "Ajust. patrimonial actif"
            persist  = "GitHub Gist + SQLite" if self.pm.status == "github" else "SQLite local"
            st.caption(
                f"◈ Cockpit v5.4 Pédagogique · {mode_txt} · "
                f"Score H={s(score_h)}{score_h}/4 | EM={s(score_a)}{score_a}/4 · "
                f"Régime : {regime_label} · Capital {capital:,.2f}€ · "
                f"Persistance : {persist} · {live_ok}/{live_total} prix live · "
                f"Benchmark : MWR Cash-Flow Adjusted · "
                "Outil personnel — Ne constitue pas un conseil en investissement"
            )
        with col_f2:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 14 : POINT D'ENTRÉE PRINCIPAL — v5.4 : positions depuis session_state
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Session State ─────────────────────────────────────────────────────────
    if "config_loaded" not in st.session_state:
        cfg = _load_config()
        st.session_state["cfg_capital_reel"]   = cfg["capital_reel"]
        st.session_state["cfg_ajustement_pat"] = cfg["ajustement_pat"]
        st.session_state["cfg_bonus_fortuneo"] = cfg["bonus_fortuneo"]
        st.session_state["config_loaded"]      = True
        st.session_state["save_feedback"]      = ""

    # v5.4 : Chargement des positions depuis config_perso.json ou POSITIONS_BASE
    if "positions" not in st.session_state:
        saved_positions = _load_positions_from_config()
        if saved_positions:
            st.session_state["positions"] = saved_positions
        else:
            st.session_state["positions"] = [dict(p) for p in POSITIONS_BASE]

    # ── Instanciation ─────────────────────────────────────────────────────────
    with st.spinner("📡 Chargement des données de marché..."):
        dm = DataManager()
    if not dm.live:
        st.error("❌ Aucun prix live. Vérifiez votre connexion.")
        st.stop()

    pm  = PersistenceManager(static_capital=st.session_state["cfg_capital_reel"])
    mre = MarketRegimeEngine(dm)
    qre = QuantRiskEngine(dm)
    pe  = PortfolioEngine(dm, mre, qre)
    pde = PedagogicEngine()
    se  = StrategicEngine(dm, mre, qre)

    ui  = StreamlitUI(dm, pm, mre, qre, pe, pde, se)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo = \
        ui.render_sidebar()

    # ── Calculs ───────────────────────────────────────────────────────────────
    with st.spinner("⚙️ Calcul des indicateurs..."):
        ptf    = pe.compute_portfolio(positions_conf, capital_reel, ajustement_pat, bonus_fortuneo)
        bench  = pe.compute_benchmark(positions_conf, ptf["perf_tot_pct"])
        regime = mre.get_full_regime()

        anrj_info = dm.analyze_ticker("ANRJ.PA")
        aasi_info = dm.analyze_ticker("AASI.PA")
        h_msg, h_col = pe.evaluate_hydrogen(anrj_info)
        a_msg, a_col = pe.evaluate_em_asia(aasi_info)

        unified_h = pe.compute_unified_score("ANRJ.PA")
        unified_a = pe.compute_unified_score("AASI.PA")

        target_h  = pe.compute_target_weight("Global Hydrogen", "ANRJ.PA",
                                              ptf["valeur_totale"], ptf["positions"])
        target_a  = pe.compute_target_weight("EM Asia", "AASI.PA",
                                              ptf["valeur_totale"], ptf["positions"])

        ld_alerts     = pe.check_leadership_alerts()
        phase_text, phase_color = pe.determine_phase(bench.get("gap"), anrj_info, aasi_info)

        _, _, sent_rows = pe.evaluate_sentinelles()

    live_ok    = sum(1 for v in dm.live.values() if v.get("prix"))
    live_total = len(dm.live)

    # ── Guide pédagogique ─────────────────────────────────────────────────────
    with st.expander("📚 Guide d'utilisation du Cockpit v5.4", expanded=False):
        st.markdown("""
**Bienvenue dans votre Cockpit Décisionnel Pédagogique v5.4**

| Section | Ce qu'elle vous dit | Ce que vous devez faire |
|---------|---------------------|-------------------------|
| 🌍 **Météo des marchés** | Ambiance générale de la Bourse mondiale | Adapte votre niveau de risque |
| 🚀 **Vue d'ensemble** | Valeur totale + Gap vs World MWR ajusté | Suivre votre alpha réel |
| 📊 **Leadership Satellite vs World** | Vaut-il la peine de garder Hydrogen / EM Asia ? | Vendre si le World fait régulièrement mieux |
| ⚠️ **Risques** | Niveau de danger de chaque ETF | Réduire si trop agité ou trop en recul |
| 🛰️ **Radar sectoriel** | Santé des grandes entreprises du secteur | Alerte précoce avant que votre ETF ne chute |
| 🧮 **Simulateur fiscal** | Ce que vous recevrez après impôts | Avant tout retrait ou vente |

**v5.4 — Nouveautés :**
- 🎯 **Benchmark MWR** : le gap vs World est calculé en simulant les mêmes achats que les vôtres (dates + montants réels)
- 🥇 **Or sans N/A** : fallback automatique entre GOLD-EUR.PA → FGLDA.DE → XAD5.MI
- 💾 **Persistance DCA** : mettez à jour parts & PRM dans la sidebar → sauvegardés en JSON

**Règle d'or :** N'agissez que si PLUSIEURS indicateurs pointent dans la même direction.
""")

    # ── Rendu UI ──────────────────────────────────────────────────────────────
    ui.render_header(mode_direct, live_ok, live_total)
    ui.render_regime_banner(regime)

    for al in ld_alerts:
        gv, nom_al, sp, wp = al["gap"], al["nom"], al["sat_perf"], al["world_perf"]
        s = StreamlitUI._sign
        if gv < -5:   cls, ico = "alert-critical", "🚨"
        elif gv < -2: cls, ico = "alert-leadership","⚠️"
        else: continue
        st.markdown(
            f'<div class="{cls}">{ico} <b>ALERTE : {nom_al}</b> — '
            f'{abs(gv):.1f}% en retard sur le World sur 14 jours '
            f'({nom_al} : {s(sp)}{sp:.1f}% | World : {s(wp)}{wp:.1f}%)<br>'
            f'<span style="font-size:.85rem;">→ Vérifiez la section Leadership ci-dessous.</span>'
            f'</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="phase-banner" style="background:{phase_color};color:white;">'
                f'{phase_text}</div>', unsafe_allow_html=True)

    ui.render_command_center(ptf, bench, mode_direct, pm)
    ui.render_equity_curve_section(ptf, regime, unified_h, unified_a, positions_conf)
    ui.render_risk_dashboard(ptf)

    st.markdown("## 🧠 Analyse des ETFs Satellites")

    h_border = "#22C55E" if h_col=="green" else "#F97316" if h_col=="orange" else "#FF3131"
    st.markdown(
        f'<div class="card" style="border-left:4px solid {h_border};margin-bottom:.5rem;">'
        f'<b>🔥 Hydrogen (ANRJ.PA) — Alerte décisionnelle</b><br>'
        f'{h_msg}</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown("### 🔥 Global Hydrogen (ANRJ.PA)")
        ui.render_satellite_card_pedagogic(
            "Global Hydrogen", "ANRJ.PA",
            unified_h, target_h, regime, sent_rows, "hydrogen")

    st.markdown("<br>", unsafe_allow_html=True)

    a_border = "#22C55E" if a_col=="green" else "#F97316" if a_col=="orange" else "#FF3131"
    st.markdown(
        f'<div class="card" style="border-left:4px solid {a_border};margin-bottom:.5rem;">'
        f'<b>🌏 EM Asia (AASI.PA) — Alerte décisionnelle</b><br>'
        f'{a_msg}</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown("### 🌏 EM Asia (AASI.PA)")
        ui.render_satellite_card_pedagogic(
            "EM Asia", "AASI.PA",
            unified_a, target_a, regime, sent_rows, "em_asia")

    ui.render_sentinelles_macro(ptf)
    ui.render_fiscal_simulator(ptf)
    ui.render_footer(mode_direct, capital_reel,
                     unified_h["total"], unified_a["total"],
                     regime["confirmed_label"], live_ok, live_total)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    main()
