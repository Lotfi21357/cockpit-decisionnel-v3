# =============================================================================
# COCKPIT DÉCISIONNEL BOURSIER v5.2 — "QUANT-SYSTEM AVEC PERSISTANCE"
# Lead Dev: Claude (Anthropic)
# v4.1 → v5.2 :
#   • Architecture modulaire stricte — 6 classes (DataManager, PersistenceManager,
#     MarketRegimeEngine, QuantRiskEngine, PortfolioEngine, StreamlitUI)
#   • Persistence Layer hybride : SQLite (session) + GitHub Gist CSV (cross-session)
#   • Market Regime Engine : Score −5/+5, 5 labels, confirmation 3 jours anti-whipsaw
#   • Quant Risk Engine : Vol roulante, Beta, Drawdown, Corrélation, Risk Contribution
#   • Portfolio Engine : Score 4 composantes, Dynamic Sizing Matrix, verdict structuré
#   • UI Premium : Equity Curve, Risk Dashboard, Jauges go.Indicator, Bandeau Régime
#   Requis dans requirements.txt : streamlit yfinance pandas numpy plotly PyGithub
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 0 : IMPORTS & PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json, os, sqlite3, io, csv, warnings
from typing import Optional, Dict, List, Tuple
warnings.filterwarnings("ignore")

# PyGithub est optionnel — si absent, le mode Live uniquement est activé
try:
    from github import Github, InputFileContent
    PYGITHUB_OK = True
except ImportError:
    PYGITHUB_OK = False

st.set_page_config(
    page_title="Cockpit v5.2 · Quant System",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 : CSS — DESIGN SYSTEM INSTITUTIONNEL (DARK MODE)
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
.main .block-container { padding-top: 1.5rem; max-width: 1400px; }

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
.status-maintain   { background:linear-gradient(135deg,#2D3F1F,#344A22); color:#86EFAC;
                     padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-lighten    { background:linear-gradient(135deg,#3B3208,#453B0A); color:#FDE68A;
                     padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-vigilance  { background:linear-gradient(135deg,#3B2008,#47260A); color:#FDBA74;
                     padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-reduce     { background:linear-gradient(135deg,#3B0F0F,#4A1414); color:#FCA5A5;
                     padding:.8rem 1.2rem; border-radius:8px; font-weight:700; font-size:1rem; text-align:center; }
.status-exit       { background:linear-gradient(135deg,#2D0505,#3A0808); color:#FF3131;
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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2 : CONSTANTES & CONFIGURATION (Préservées intégralement de v4.1)
# ─────────────────────────────────────────────────────────────────────────────

POSITIONS_BASE: List[Dict] = [
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
_DB_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local.db")

# Cibles initiales satellites (v4.1)
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

# Tickers supplémentaires pour le Regime Engine
REGIME_TICKERS = ["SPY", "QQQ", "^VIX", "^TNX", "DX-Y.NYB", "ES=F", "NQ=F"]

SENTINELLES: Dict[str, List[str]] = {
    "TSMC":        ["TSM"],
    "Samsung":     ["005930.KS"],
    "Air Liquide": ["AI.PA"],
    "Bloom Energy":["BE"],
    "SK Hynix":    ["000660.KS"],
}

DATE_DEBUT = datetime(2025, 9, 17)

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 : FONCTIONS CACHÉES (module-level — obligatoire pour @st.cache_data)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise un DataFrame yfinance : supprime MultiIndex, ffill, valide 'Close'."""
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
    """Retourne (prix_live, prev_close) pour un ticker."""
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
    """Charge tous les prix live (cache 30s)."""
    all_tickers = []
    for pos in POSITIONS_BASE:
        all_tickers.extend(pos["tickers"])
    all_tickers.extend(list(MACRO_TICKERS.keys()))
    all_tickers.extend(REGIME_TICKERS)
    all_tickers.extend(PROXIES_ANRJ + PROXIES_AASI)
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
    """Charge 600j d'historique pour tous les tickers (cache 90s)."""
    start = (datetime.now() - timedelta(days=600)).strftime("%Y-%m-%d")
    all_tickers = []
    for pos in POSITIONS_BASE:
        all_tickers.extend(pos["tickers"])
    all_tickers.extend(PROXIES_ANRJ + PROXIES_AASI)
    all_tickers.extend(list(MACRO_TICKERS.keys()))
    all_tickers.extend(REGIME_TICKERS)
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

    # Fallback individuel pour les tickers manquants
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
            return {**defaults, **{k: float(v) for k, v in data.items() if k in defaults}}
    except Exception:
        pass
    return defaults


def _save_config(capital_reel: float, ajustement_pat: float, bonus_fortuneo: float) -> bool:
    try:
        payload = {"capital_reel": round(capital_reel, 2),
                   "ajustement_pat": round(ajustement_pat, 2),
                   "bonus_fortuneo": round(bonus_fortuneo, 2)}
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 : PERSISTENCE MANAGER (SQLite local + GitHub Gist CSV)
# ─────────────────────────────────────────────────────────────────────────────

# Colonnes du CSV persistant
_CSV_COLS = ["date", "capital_cloture", "valeur_titres",
             "perf_jour", "perf_cumul", "regime", "score_regime",
             "poids_h", "poids_em"]

class PersistenceManager:
    """
    Gestion de la persistance hybride :
    - SQLite  : cache de session rapide (local.db)
    - GitHub Gist : stockage cross-session (history.csv)

    Configuration dans st.secrets :
        GITHUB_TOKEN = "ghp_xxxx"
        GIST_ID      = "abc123def456" (Gist contenant history.csv)

    Fallback silencieux si token absent ou réseau défaillant.
    """

    def __init__(self, static_capital: float):
        self.static_capital  = static_capital
        self._github_ok      = False
        self._gist           = None
        self._github_warning = ""
        self._history_cache: Optional[pd.DataFrame] = None

        # ── Initialisation SQLite ──────────────────────────────────────────
        try:
            self._conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
            self._init_db()
        except Exception as e:
            # Fallback in-memory
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._init_db()

        # ── Initialisation GitHub ──────────────────────────────────────────
        if PYGITHUB_OK:
            try:
                token   = st.secrets.get("GITHUB_TOKEN", "")
                gist_id = st.secrets.get("GIST_ID", "")
                if token and gist_id:
                    gh          = Github(token)
                    self._gist  = gh.get_gist(gist_id)
                    self._github_ok = True
                    # Télécharger l'historique au démarrage
                    self._sync_from_github()
            except Exception as e:
                self._github_warning = f"GitHub Gist indisponible : {str(e)[:80]}"
        else:
            self._github_warning = "PyGithub non installé — mode SQLite uniquement."

    def _init_db(self):
        """Crée la table SQLite si elle n'existe pas."""
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
        """Télécharge history.csv depuis le Gist et peuple SQLite."""
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
        """Pousse le DataFrame historique complet en CSV sur le Gist."""
        if not self._gist:
            return
        try:
            buf  = io.StringIO()
            df.to_csv(buf, index=False, columns=_CSV_COLS)
            csv_content = buf.getvalue()
            self._gist.edit(files={"history.csv": InputFileContent(csv_content)})
        except Exception:
            pass  # Échec silencieux — la session locale continue

    def save_snapshot(self, capital_cloture: float, valeur_titres: float,
                      perf_jour: float, perf_cumul: float, regime: str,
                      score_regime: int, poids_h: float, poids_em: float) -> bool:
        """
        Sauvegarde un snapshot :
        1. Écrit dans SQLite
        2. Pousse asynchronement vers GitHub Gist
        Retourne True si SQLite ok (GitHub est best-effort).
        """
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
            self._history_cache = None  # invalide le cache
            # Push GitHub (best-effort)
            if self._github_ok:
                self._push_to_github(self.load_history())
            return True
        except Exception:
            return False

    def load_history(self) -> pd.DataFrame:
        """Retourne l'historique complet sous forme de DataFrame (colonnes = _CSV_COLS)."""
        if self._history_cache is not None:
            return self._history_cache
        try:
            df = pd.read_sql("SELECT * FROM snapshots ORDER BY date ASC", self._conn)
            # S'assurer que toutes les colonnes sont présentes
            for col in _CSV_COLS:
                if col not in df.columns:
                    df[col] = None
            self._history_cache = df[_CSV_COLS].copy()
            return self._history_cache
        except Exception:
            return pd.DataFrame(columns=_CSV_COLS)

    def get_last_snapshot(self) -> Optional[Dict]:
        """Retourne le dernier snapshot ou None si historique vide."""
        hist = self.load_history()
        if hist.empty:
            return None
        row = hist.iloc[-1]
        return {c: row[c] for c in _CSV_COLS}

    def get_initial_capital(self) -> float:
        """
        Capital de base pour le calcul de performance cumulée :
        - Premier snapshot disponible (chaînage)
        - Sinon, capital statique configuré
        """
        hist = self.load_history()
        if not hist.empty and hist["capital_cloture"].notna().any():
            return float(hist["capital_cloture"].dropna().iloc[0])
        return self.static_capital

    def compute_daily_performance(self, current_value: float) -> Tuple[float, float, float]:
        """
        Retourne (perf_jour_pct, perf_cumul_pct, base_capital_hier).
        - perf_jour  = (current / dernier_snapshot) - 1
        - perf_cumul = (current / premier_snapshot) - 1
        Ne recalcule JAMAIS depuis le capital de départ fixe.
        """
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
        """Statut du layer de persistance pour l'affichage UI."""
        if self._github_ok:
            return "github"
        if self._github_warning:
            return "warn"
        return "local"

    @property
    def warning_msg(self) -> str:
        return self._github_warning

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 5 : DATA MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class DataManager:
    """
    Gère l'accès aux données de marché :
    - Prix live (fast_info → info fallback)
    - Historique 600j (yfinance bulk download)
    - Log returns (obligatoire pour tous les calculs de risque)
    """

    def __init__(self):
        self.live: Dict[str, Dict]         = _cached_live_prices()
        self.data: Dict[str, pd.DataFrame] = _cached_historical_data()
        self._log_returns_cache: Optional[Dict[str, pd.Series]] = None

    def get_price_info(self, tickers: List[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Retourne (prix, prev_close, ticker_utilisé) pour une liste de tickers fallback."""
        for tk in tickers:
            info = self.live.get(tk, {})
            prix = info.get("prix")
            prev = info.get("prev")
            if prix and float(prix) > 0:
                return float(prix), float(prev) if prev else None, tk
        return None, None, None

    def compute_log_returns(self) -> Dict[str, pd.Series]:
        """
        Calcule les rendements logarithmiques journaliers pour tous les actifs.
        Formula : ln(P_t / P_{t-1})
        Obligatoire pour tous les calculs de risque ultérieurs.
        """
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
        """Pente de (Actif / MSCI World) sur N jours. >0 = leadership."""
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
# MODULE 6 : MARKET REGIME ENGINE
# ─────────────────────────────────────────────────────────────────────────────

# Mapping score → label
_REGIME_LABELS = [
    (4,  5,  "Euphorie",    "regime-euphorie",    "#A855F7"),
    (2,  3,  "Expansion",   "regime-expansion",   "#22C55E"),
    (0,  1,  "Neutre",      "regime-neutre",      "#3B82F6"),
    (-3,-1,  "Stress",      "regime-stress",      "#F59E0B"),
    (-5,-4,  "Contraction", "regime-contraction", "#FF3131"),
]

# Multiplicateurs régime pour le sizing dynamique
REGIME_MULTIPLIERS = {
    "Euphorie":    1.00,
    "Expansion":   1.00,
    "Neutre":      0.85,
    "Stress":      0.70,
    "Contraction": 0.20,
}

class MarketRegimeEngine:
    """
    Calcule le régime de marché global via 5 indicateurs macro :
    Score −5 → +5 sur 5 composantes (chacune ±1) :
      +1 Trend     : ES=F (ou SPY) > SMA200
      +1 Breadth   : QQQ (ou NQ=F) > SMA50
      +1 Volatility: ^VIX < 20
      +1 Rates     : ^TNX < SMA20
      +1 Liquidity : DX-Y.NYB < SMA50

    Anti-whipsaw : le régime est "confirmé" seulement si les 3 derniers
    jours glissants donnent le même label.
    """

    def __init__(self, dm: DataManager):
        self.dm = dm

    def _compute_score_at(self, offset: int = 0) -> int:
        """
        Calcule le score régime à un offset de jours dans le passé.
        offset=0 → aujourd'hui, offset=1 → hier, etc.
        """
        score = 0
        data  = self.dm.data

        def _get_close(tickers: List[str]) -> Optional[pd.Series]:
            for tk in tickers:
                df = data.get(tk, pd.DataFrame())
                if not df.empty and "Close" in df.columns:
                    cl = df["Close"].dropna()
                    if len(cl) > offset + 10:
                        return cl.iloc[:len(cl) - offset] if offset > 0 else cl
            return None

        # ── 1. Trend : S&P 500 > SMA200 ──────────────────────────────────────
        cl = _get_close(["ES=F", "SPY"])
        if cl is not None and len(cl) >= 201:
            score += 1 if float(cl.iloc[-1]) > float(cl.rolling(200).mean().iloc[-1]) else -1

        # ── 2. Breadth : Nasdaq > SMA50 ───────────────────────────────────────
        cl = _get_close(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51:
            score += 1 if float(cl.iloc[-1]) > float(cl.rolling(50).mean().iloc[-1]) else -1

        # ── 3. Volatility : VIX < 20 ─────────────────────────────────────────
        cl = _get_close(["^VIX"])
        if cl is not None:
            score += 1 if float(cl.iloc[-1]) < 20 else -1

        # ── 4. Rates : US10Y < SMA20 ──────────────────────────────────────────
        cl = _get_close(["^TNX"])
        if cl is not None and len(cl) >= 21:
            score += 1 if float(cl.iloc[-1]) < float(cl.rolling(20).mean().iloc[-1]) else -1

        # ── 5. Liquidity : DXY < SMA50 ────────────────────────────────────────
        cl = _get_close(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51:
            score += 1 if float(cl.iloc[-1]) < float(cl.rolling(50).mean().iloc[-1]) else -1

        return max(-5, min(5, score))

    def _score_to_label(self, score: int) -> Tuple[str, str, str]:
        """(label, css_class, hex_color)"""
        for lo, hi, label, css, color in _REGIME_LABELS:
            if lo <= score <= hi:
                return label, css, color
        return "Neutre", "regime-neutre", "#3B82F6"

    def get_full_regime(self) -> Dict:
        """
        Calcule le régime avec confirmation 3 jours (anti-whipsaw).
        Retourne un dict complet pour l'UI et les engines.
        """
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
            confirmed      = True
            conf_label     = label_0
            conf_css       = css_0
            conf_color     = color_0
            conf_score     = current_score
        elif labels_3d[0] == labels_3d[1]:
            # 2/3 confirmé
            confirmed  = True
            conf_label = label_0
            conf_css   = css_0
            conf_color = color_0
            conf_score = current_score
        else:
            confirmed  = False
            conf_label = "En attente"
            conf_css   = "regime-pending"
            conf_color = "#6B7585"
            conf_score = current_score

        # Détail des 5 composantes
        components = self._get_component_details()

        return {
            "current_score":   current_score,
            "confirmed_score": conf_score,
            "confirmed_label": conf_label,
            "confirmed_css":   conf_css,
            "confirmed_color": conf_color,
            "is_confirmed":    confirmed,
            "scores_3d":       scores_3d,
            "labels_3d":       labels_3d,
            "components":      components,
            "multiplier":      REGIME_MULTIPLIERS.get(conf_label, 0.85),
        }

    def _get_component_details(self) -> List[Dict]:
        """Retourne le détail des 5 composantes pour l'affichage."""
        data   = self.dm.data
        detail = []

        def _last(tks): 
            for tk in tks:
                df = data.get(tk, pd.DataFrame())
                if not df.empty and "Close" in df.columns:
                    cl = df["Close"].dropna()
                    if not cl.empty: return cl
            return None

        # Trend
        cl = _last(["ES=F", "SPY"])
        if cl is not None and len(cl) >= 201:
            sma = float(cl.rolling(200).mean().iloc[-1])
            v   = float(cl.iloc[-1])
            detail.append({"name": "Trend (SMA200)",    "bull": v > sma,  "val": f"{v:.1f} vs {sma:.1f}"})
        else:
            detail.append({"name": "Trend (SMA200)",    "bull": None, "val": "N/A"})

        # Breadth
        cl = _last(["QQQ", "NQ=F"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1])
            v   = float(cl.iloc[-1])
            detail.append({"name": "Breadth (SMA50)",   "bull": v > sma,  "val": f"{v:.1f} vs {sma:.1f}"})
        else:
            detail.append({"name": "Breadth (SMA50)",   "bull": None, "val": "N/A"})

        # VIX
        cl = _last(["^VIX"])
        if cl is not None:
            v = float(cl.iloc[-1])
            detail.append({"name": "Volatilité (VIX)",  "bull": v < 20, "val": f"{v:.2f} (seuil 20)"})
        else:
            detail.append({"name": "Volatilité (VIX)",  "bull": None, "val": "N/A"})

        # Rates
        cl = _last(["^TNX"])
        if cl is not None and len(cl) >= 21:
            sma = float(cl.rolling(20).mean().iloc[-1])
            v   = float(cl.iloc[-1])
            detail.append({"name": "Taux (US10Y SMA20)","bull": v < sma, "val": f"{v:.3f}% vs {sma:.3f}%"})
        else:
            detail.append({"name": "Taux (US10Y SMA20)","bull": None, "val": "N/A"})

        # Liquidity
        cl = _last(["DX-Y.NYB"])
        if cl is not None and len(cl) >= 51:
            sma = float(cl.rolling(50).mean().iloc[-1])
            v   = float(cl.iloc[-1])
            detail.append({"name": "Liquidité (DXY)",   "bull": v < sma, "val": f"{v:.2f} vs {sma:.2f}"})
        else:
            detail.append({"name": "Liquidité (DXY)",   "bull": None, "val": "N/A"})

        return detail

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 7 : QUANT RISK ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class QuantRiskEngine:
    """
    Calculs de risque quantitatifs pour chaque satellite et le portefeuille global :
    - Volatilité roulante annualisée (30j, log returns)
    - Beta roulant 60j vs MSCI World
    - Drawdown courant + Max Drawdown (252j)
    - Matrice de corrélation Pearson (60j)
    - Risk Contribution par actif (Risk Parity logic)
    - Flag si un actif contribue > 40% du risque global
    """

    def __init__(self, dm: DataManager):
        self.dm          = dm
        self._log_returns = dm.compute_log_returns()

    def rolling_volatility(self, ticker: str, window: int = 30) -> Optional[float]:
        """Volatilité annualisée : std(log_returns, 30j) × √252."""
        lr = self._log_returns.get(ticker)
        if lr is None or len(lr) < window:
            return None
        return float(lr.iloc[-window:].std() * np.sqrt(252))

    def rolling_beta(self, ticker: str,
                     benchmark: str = "MWRD.PA", window: int = 60) -> Optional[float]:
        """Beta roulant 60j : Cov(actif, benchmark) / Var(benchmark)."""
        lr_a = self._log_returns.get(ticker)
        lr_b = self._log_returns.get(benchmark)
        if lr_b is None:
            # Essayer d'autres tickers World
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

    def drawdown_metrics(self, ticker: str, window: int = 252) -> Dict:
        """
        Retourne current_drawdown et max_drawdown sur la fenêtre (252j par défaut).
        Drawdown = (prix_actuel / peak_historique) - 1
        """
        df = self.dm.data.get(ticker, pd.DataFrame())
        if df.empty or "Close" not in df.columns:
            return {"current_dd": None, "max_dd": None}
        close = df["Close"].dropna()
        if len(close) < 10:
            return {"current_dd": None, "max_dd": None}
        recent  = close.iloc[-window:]
        peak    = recent.cummax()
        dd      = (recent / peak - 1)
        return {
            "current_dd": float(dd.iloc[-1]) * 100,
            "max_dd":     float(dd.min()) * 100,
        }

    def correlation_matrix(self, tickers: List[str], window: int = 60) -> Optional[pd.DataFrame]:
        """
        Matrice de corrélation Pearson sur les log returns (60j).
        Retourne None si données insuffisantes.
        """
        series_dict = {}
        for tk in tickers:
            lr = self._log_returns.get(tk)
            if lr is not None and len(lr) >= window:
                series_dict[tk] = lr.iloc[-window:]
        if len(series_dict) < 2:
            return None
        df_all = pd.concat(series_dict.values(), axis=1)
        df_all.columns = list(series_dict.keys())
        df_all = df_all.dropna()
        if len(df_all) < 20:
            return None
        return df_all.corr()

    def risk_contribution(self, tickers: List[str], weights: List[float],
                          window: int = 60) -> Dict[str, Dict]:
        """
        Calcule la contribution marginale au risque de chaque actif.
        Basé sur Risk Parity : RC_i = w_i × (Σw)_i / σ_portefeuille
        Flag si un actif contribue > 40% du risque total.
        """
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
        df_all = df_all.dropna().iloc[-window:]
        if len(df_all) < 20:
            return {}

        w  = np.array(valid_w, dtype=float)
        w /= w.sum()  # normalise à 1

        cov    = df_all.cov().values * 252  # annualisé
        port_v = float(w @ cov @ w)
        port_s = np.sqrt(port_v) if port_v > 0 else 1e-10

        mrc        = cov @ w                        # marginal risk contribution
        rc         = w * mrc                         # risk contribution absolue
        total_rc   = rc.sum()
        rc_pct     = rc / total_rc * 100 if total_rc > 0 else rc * 0

        result = {}
        for i, tk in enumerate(valid_tickers):
            result[tk] = {
                "weight_pct":   w[i] * 100,
                "rc_absolute":  float(rc[i]),
                "rc_pct":       float(rc_pct[i]),
                "flag":         float(rc_pct[i]) > 40,
            }
        return result

    def portfolio_volatility(self, tickers: List[str], weights: List[float],
                             window: int = 60) -> Optional[float]:
        """Volatilité annualisée du portefeuille pondéré."""
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
        df_all = df_all.dropna().iloc[-window:]
        if len(df_all) < 20:
            return None
        w   = np.array(valid_w) / sum(valid_w)
        cov = df_all.cov().values * 252
        return float(np.sqrt(w @ cov @ w))

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 8 : PORTFOLIO ENGINE (Préservation logique v4.1 + Dynamic Sizing v5.2)
# ─────────────────────────────────────────────────────────────────────────────

class PortfolioEngine:
    """
    Calculs de portefeuille et décisions d'allocation :
    - compute_portfolio()         : valorisation live (v4.1 préservée)
    - compute_benchmark()         : performance vs MSCI World (v4.1 préservée)
    - compute_unified_score()     : Score 3 couches −4/+4 (v4.1 préservée)
    - compute_strategic_score_4c(): Score 4 composantes (v5.2)
    - compute_confidence_factor() : Ajustement par volatilité (v5.2)
    - compute_target_weight()     : Dynamic Sizing Matrix (v5.2)
    - compute_strategic_arb()     : Verdict structuré (v4.1+v5.2)
    """

    def __init__(self, dm: DataManager, re: MarketRegimeEngine, qre: QuantRiskEngine):
        self.dm  = dm
        self.re  = re
        self.qre = qre

    # ── CALCUL PORTEFEUILLE (v4.1 préservé intégralement) ──────────────────────
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
            valeur       = pos["parts"] * prix
            gain_unit    = prix - pos["prm"]
            perf_pct     = gain_unit / pos["prm"] * 100
            gain_total   = gain_unit * pos["parts"]
            var_j_pct    = (prix - prev) / prev * 100 if prev and prev != 0 else 0.0
            var_j_eur    = (prix - prev) * pos["parts"] if prev else 0.0
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
        close    = df_h["Close"].dropna()
        try:
            start_val = float(close.loc[DATE_DEBUT.strftime("%Y-%m-%d")])
        except KeyError:
            cands     = close.loc[:DATE_DEBUT.strftime("%Y-%m-%d")]
            start_val = float(cands.iloc[-1]) if not cands.empty else float(close.iloc[0])
        perf_bench   = (prix / start_val - 1) * 100 if start_val else None
        gap          = perf_tot_pct - perf_bench if perf_bench is not None else None
        perf_bench_j = (prix - prev) / prev * 100 if prev and prev != 0 else None
        return {"perf_bench": perf_bench, "gap": gap,
                "prix": prix, "perf_bench_j": perf_bench_j}

    # ── SCORE UNIFIÉ v4.1 (3 couches, −4/+4) ──────────────────────────────────
    def compute_unified_score(self, ticker: str) -> Dict:
        info    = self.dm.analyze_ticker(ticker)
        details = []
        score   = 0

        # Couche 1 : Momentum (RSI)
        rsi_v = info["rsi"] if info else None
        if rsi_v is not None:
            if rsi_v >= 70:   ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Tendu"
            elif rsi_v <= 45: ms, mb, md = -1, "bear", f"RSI={rsi_v:.1f} Faible"
            else:             ms, mb, md =  1, "bull", f"RSI={rsi_v:.1f} Sain"
        else:                 ms, mb, md =  0, "neut", "RSI indisponible"
        details.append({"name": "Momentum",   "score": ms, "badge": mb, "desc": md})
        score += ms

        # Couche 2 : Structure (prix vs SMA20)
        if info and info["sma20"] is not None:
            if info["prix"] > info["sma20"]:
                ss, sb, sd = 1, "bull", f"Prix {info['prix']:.2f} > SMA20 {info['sma20']:.2f}"
            else:
                ss, sb, sd = -1, "bear", f"Prix {info['prix']:.2f} < SMA20 {info['sma20']:.2f}"
        else:
            ss, sb, sd = 0, "neut", "SMA20 indisponible"
        details.append({"name": "Structure",  "score": ss, "badge": sb, "desc": sd})
        score += ss

        # Couche 3 : Leadership (pente RS 14j)
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

    # ── SCORE STRATÉGIQUE 4 COMPOSANTES (v5.2) ─────────────────────────────────
    def compute_strategic_score_4c(self, ticker: str, regime: Dict) -> Dict:
        """
        Score stratégique pondéré : −1 → +1
        • Trend       25% (structure SMA20 normalisée)
        • Macro/Régime 30% (score régime / 5 normalisé)
        • Leadership   25% (pente RS normalisée)
        • Risk/Vol     20% (inverse de la volatilité)
        """
        info    = self.dm.analyze_ticker(ticker)
        lr_data = self.dm.compute_log_returns()

        # Trend (25%) : prix vs SMA20 → ±1 normalisé
        trend_raw = 0.0
        if info and info["sma20"] and info["prix"]:
            dev = (info["prix"] - info["sma20"]) / info["sma20"]
            trend_raw = max(-1.0, min(1.0, dev * 20))  # amplification ×20

        # Macro/Régime (30%) : score_regime / 5 → ±1
        macro_raw = regime["confirmed_score"] / 5.0

        # Leadership (25%) : pente RS → ±1
        rs = self.dm.relative_strength_slope(ticker, 14)
        if rs is not None:
            leader_raw = 1.0 if rs > 0 else -1.0
        else:
            leader_raw = 0.0

        # Risk/Vol (20%) : vol < 15% = +1, 15-25% = linéaire, > 25% = −1
        vol = self.qre.rolling_volatility(ticker, 30)
        if vol is not None:
            vol_raw = max(-1.0, min(1.0, (0.20 - vol) / 0.10))
        else:
            vol_raw = 0.0

        total = (trend_raw * 0.25 + macro_raw * 0.30 +
                 leader_raw * 0.25 + vol_raw * 0.20)

        return {
            "total":      max(-1.0, min(1.0, total)),
            "trend":      trend_raw,
            "macro":      macro_raw,
            "leadership": leader_raw,
            "risk_vol":   vol_raw,
            "weights":    {"Trend": 0.25, "Macro/Régime": 0.30,
                           "Leadership": 0.25, "Risque/Vol": 0.20},
        }

    def compute_confidence_factor(self, tickers: List[str],
                                   weights: List[float]) -> float:
        """
        Facteur de confiance 0.5 → 1.0 basé sur la volatilité globale.
        Vol < 10%  → 1.0
        Vol 10-15% → 0.90
        Vol 15-20% → 0.75
        Vol > 20%  → 0.60
        """
        port_vol = self.qre.portfolio_volatility(tickers, weights, 60)
        if port_vol is None:
            return 0.85
        if port_vol < 0.10:   return 1.00
        elif port_vol < 0.15: return 0.90
        elif port_vol < 0.20: return 0.75
        else:                  return 0.60

    # ── DYNAMIC SIZING MATRIX (v5.2) ───────────────────────────────────────────
    def compute_target_weight(self, nom: str, ticker: str,
                               valeur_totale: float,
                               positions_calc: List[Dict]) -> Dict:
        """
        Target_Weight = Base_Weight × Régime_Multiplier × Confidence_Factor × (1 + adj)
        Clamp : [2%, 35%]
        Produit le verdict : Poids Actuel | Poids Cible | Action | Δ%
        """
        regime  = self.re.get_full_regime()
        unified = self.compute_unified_score(ticker)
        strat4c = self.compute_strategic_score_4c(ticker, regime)

        # Base weight (logique v4.1)
        base_w = self._get_base_weight(unified["total"], INITIAL_TARGETS.get(nom, 0.25))

        # Multiplicateurs
        regime_mult = regime["multiplier"]
        tickers_all = [pos["tickers"][0] for pos in POSITIONS_BASE if pos.get("valeur", 0) > 0]
        weights_all = [pos["valeur"] / valeur_totale for pos in positions_calc
                       if pos["valeur"] > 0 and pos.get("ticker")]
        # Confidence
        ptf_tickers = [p["ticker"] for p in positions_calc if p.get("ticker")]
        ptf_weights = [p["valeur"] / valeur_totale for p in positions_calc
                       if p.get("ticker") and valeur_totale > 0]
        confidence  = self.compute_confidence_factor(ptf_tickers, ptf_weights)

        # Ajustement score stratégique (±30%)
        strat_adj = 1.0 + strat4c["total"] * 0.30

        target = base_w * regime_mult * confidence * strat_adj
        target = max(0.02, min(0.35, target))

        # Poids actuel
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
        """Matrice de base selon score unifié −4/+4 (v4.1 préservée)."""
        if score >= 3:   return initial_target
        elif score >= 1: return 0.20
        elif score >= -1:return 0.15
        else:            return 0.05

    # ── RÈGLES DÉCISIONNELLES SATELLITES (v4.1 préservées) ────────────────────
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
# MODULE 9 : FISCAL (v4.1 préservé intégralement)
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
# MODULE 10 : VISUALISATIONS (Graphiques réutilisables)
# ─────────────────────────────────────────────────────────────────────────────

_PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E1", family="DM Sans"),
)

def plot_equity_curve(history: pd.DataFrame) -> Optional[go.Figure]:
    """Courbe d'équité avec fond coloré par régime."""
    if history.empty or "capital_cloture" not in history.columns:
        return None
    df = history.dropna(subset=["capital_cloture"]).copy()
    if len(df) < 2:
        return None
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date_dt"]).sort_values("date_dt")

    fig = go.Figure()

    # Fond coloré par régime
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
        # Dernier segment
        if prev_regime:
            col = regime_colors.get(prev_regime, "rgba(255,255,255,.03)")
            fig.add_vrect(x0=x0, x1=df["date_dt"].iloc[-1], fillcolor=col, layer="below", line_width=0)

    # Ligne equity
    fig.add_trace(go.Scatter(
        x=df["date_dt"], y=df["capital_cloture"].astype(float),
        mode="lines+markers",
        line=dict(color="#D4AF37", width=2.5),
        marker=dict(size=5, color="#D4AF37"),
        name="Capital Clôture",
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>%{y:,.2f}€<extra></extra>",
    ))

    # Perf cumulée en secondary axis si disponible
    if "perf_cumul" in df.columns and df["perf_cumul"].notna().any():
        fig.add_trace(go.Scatter(
            x=df["date_dt"], y=df["perf_cumul"].astype(float),
            mode="lines", line=dict(color="#3B82F6", width=1.5, dash="dot"),
            name="Perf Cumul (%)", yaxis="y2",
            hovertemplate="%{y:+.2f}%<extra>Perf Cumul</extra>",
        ))

    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Courbe d'Équité — Capital Clôture</b>",
                   font=dict(size=13, color="#6B7585")),
        margin=dict(t=40, b=30, l=60, r=60),
        height=280,
        legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)", x=0, y=1.15, orientation="h"),
        xaxis=dict(gridcolor="#2E3340", showgrid=True),
        yaxis=dict(gridcolor="#2E3340", showgrid=True, ticksuffix="€", title="Capital (€)"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    ticksuffix="%", title="Perf (%)"),
    )
    return fig


def plot_correlation_heatmap(corr_df: pd.DataFrame) -> go.Figure:
    """Heatmap de corrélation Pearson (60j) — labels courts."""
    short = {"ANRJ.PA": "H₂", "AASI.PA": "EM", "MWRD.PA": "World",
             "DCAM.PA": "W-PEA", "OR-EUR.PA": "Or"}
    labels = [short.get(c, c) for c in corr_df.columns]
    fig = go.Figure(go.Heatmap(
        z=corr_df.values.round(2), x=labels, y=labels,
        colorscale=[[0,"#FF3131"],[0.5,"#252932"],[1,"#22C55E"]],
        zmid=0, zmin=-1, zmax=1,
        text=corr_df.values.round(2),
        texttemplate="%{text:.2f}",
        hovertemplate="<b>%{y} / %{x}</b><br>ρ = %{z:.2f}<extra></extra>",
        showscale=True,
        colorbar=dict(tickfont=dict(color="#CBD5E1", size=9),
                      thickness=12, len=0.8, bgcolor="rgba(0,0,0,0)"),
    ))
    fig.update_layout(
        **_PLOTLY_BASE,
        title=dict(text="<b>Corrélation Pearson (60j)</b>",
                   font=dict(size=12, color="#6B7585")),
        margin=dict(t=40, b=10, l=60, r=20), height=220,
    )
    return fig


def plot_risk_contribution(rc: Dict) -> Optional[go.Figure]:
    """Barres horizontales des contributions au risque."""
    if not rc:
        return None
    short = {"ANRJ.PA": "H₂", "AASI.PA": "EM Asia", "MWRD.PA": "MSCI World",
             "DCAM.PA": "World PEA", "OR-EUR.PA": "Or"}
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
        title=dict(text="<b>Risk Contribution (%)</b>",
                   font=dict(size=12, color="#6B7585")),
        margin=dict(t=40, b=10, l=80, r=20), height=200,
        xaxis=dict(gridcolor="#2E3340", ticksuffix="%"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
    )
    return fig


def plot_weight_indicator(current_pct: float, target_pct: float) -> go.Figure:
    """Jauge go.Indicator : Poids Actuel vs Cible."""
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
        margin={"t": 50, "b": 10, "l": 20, "r": 20},
        height=230,
    )
    return fig


def plot_alpha_bars(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    """Alpha quotidien (actif vs MSCI World) — 15 derniers jours."""
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
        title=dict(text=f"<b>Alpha quotidien</b> : {nom} vs MSCI World — 15j",
                   font=dict(size=11, color="#6B7585")),
        margin=dict(t=35, b=25, l=55, r=15), height=200, showlegend=False,
        xaxis=dict(gridcolor="#2E3340", showgrid=False),
        yaxis=dict(gridcolor="#2E3340", ticksuffix="%"),
    )
    return fig


def plot_relative_perf(dm: DataManager, ticker: str, nom: str) -> Optional[go.Figure]:
    """Performance relative actif vs MSCI World depuis DATE_DEBUT."""
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
        title=dict(text=f"Perf relative : {nom} vs World",
                   font=dict(size=11, color="#6B7585")),
        margin=dict(t=20, b=20, l=50, r=20), height=200, showlegend=False,
        xaxis=dict(gridcolor="#2E3340"), yaxis=dict(gridcolor="#2E3340", ticksuffix="%"),
    )
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 11 : STREAMLIT UI (Orchestrateur de rendu)
# ─────────────────────────────────────────────────────────────────────────────

class StreamlitUI:
    """
    Sépare strictement la logique de rendu de la logique métier.
    Chaque méthode render_* correspond à une section de l'interface.
    """

    def __init__(self, dm: DataManager, pm: PersistenceManager,
                 mre: MarketRegimeEngine, qre: QuantRiskEngine,
                 pe: PortfolioEngine):
        self.dm  = dm
        self.pm  = pm
        self.mre = mre
        self.qre = qre
        self.pe  = pe

    # ── STATIC HELPER ──────────────────────────────────────────────────────────
    @staticmethod
    def _sign(v: float) -> str:
        return "+" if v >= 0 else ""

    # ── SIDEBAR ────────────────────────────────────────────────────────────────
    def render_sidebar(self) -> Tuple[bool, List[Dict], float, float, float]:
        """
        Rendu de la sidebar. Retourne :
        (mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo)
        """
        st.sidebar.markdown("## ⚙️ Paramètres v5.2")
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
            st.session_state["save_feedback"] = "✅ Paramètres sauvegardés" if ok else "❌ Erreur d'écriture"
        if st.session_state.get("save_feedback"):
            fb  = st.session_state["save_feedback"]
            cls = "save-box" if fb.startswith("✅") else "alert-box"
            st.sidebar.markdown(f'<div class="{cls}">{fb}</div>', unsafe_allow_html=True)

        # Persistance status
        st.sidebar.markdown("---")
        if self.pm.status == "github":
            st.sidebar.markdown('<div class="persist-ok">🔗 Persistance GitHub Gist active</div>', unsafe_allow_html=True)
        elif self.pm.warning_msg:
            st.sidebar.markdown(f'<div class="persist-warn">⚠️ {self.pm.warning_msg}</div>', unsafe_allow_html=True)
        else:
            st.sidebar.markdown('<div class="persist-warn">📂 SQLite local uniquement</div>', unsafe_allow_html=True)

        # Positions
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📦 Positions")
        positions_conf = []
        for pos in POSITIONS_BASE:
            with st.sidebar.expander(pos["nom"]):
                parts = st.number_input("Parts",   value=float(pos["parts"]),
                    step=0.0001, format="%.4f", key=f"p_{pos['nom']}")
                prm   = st.number_input("PRM (€)", value=float(pos["prm"]),
                    step=0.0001, format="%.4f", key=f"r_{pos['nom']}")
                positions_conf.append({**pos, "parts": parts, "prm": prm})

        # Ajustements
        capital_reel   = cap
        ajustement_pat = 0.0 if mode_direct else adj
        bonus_fortuneo = 0.0 if mode_direct else bonus

        for pos in positions_conf:
            if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0:
                pos["prm"] -= bonus_fortuneo / pos["parts"]

        return mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo

    # ── HEADER ─────────────────────────────────────────────────────────────────
    def render_header(self, mode_direct: bool, live_ok: int, live_total: int):
        now = datetime.now(ZoneInfo("Europe/Paris"))
        st.markdown(
            '<div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:.2rem;">'
            '<span style="font-family:Space Mono,monospace;font-size:1.6rem;font-weight:700;color:#D4AF37;">◈</span>'
            '<span style="font-size:1.5rem;font-weight:700;color:#E2E8F0;">COCKPIT DÉCISIONNEL</span>'
            '<span style="font-family:Space Mono,monospace;font-size:.9rem;color:#6B7585;">'
            'v5.2 · QUANT-SYSTEM</span></div>', unsafe_allow_html=True)

        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption(f"Prix live · {now.strftime('%d/%m/%Y %H:%M:%S')} (Paris) · Cache 30s/90s")
        with c2:
            pct   = live_ok / live_total * 100 if live_total else 0
            bc    = "#22C55E" if pct >= 80 else "#F97316" if pct >= 50 else "#FF3131"
            tc    = "#0B0E15" if pct >= 80 else "white"
            st.markdown(f'<div style="text-align:right;">'
                        f'<span class="badge" style="background:{bc};color:{tc};padding:.2rem .8rem;'
                        f'border-radius:20px;font-size:.72rem;font-weight:700;">'
                        f'📡 {live_ok}/{live_total} LIVE</span></div>', unsafe_allow_html=True)
        if mode_direct:
            st.markdown('<div class="mode-direct-banner">🔌 MODE DIRECT ACTIF — Valeur marchande pure</div>',
                        unsafe_allow_html=True)

    # ── BANDEAU RÉGIME (Élément central de v5.2) ──────────────────────────────
    def render_regime_banner(self, regime: Dict):
        sc    = regime["confirmed_score"]
        label = regime["confirmed_label"]
        css   = regime["confirmed_css"]
        conf  = "✅ Confirmé (3j)" if regime["is_confirmed"] else "⏳ En attente de confirmation"
        s3    = " → ".join([f"{s:+d}" for s in regime["scores_3d"]])

        st.markdown(
            f'<div class="regime-banner {css}">'
            f'<div><span style="font-size:1.1rem;">🌍 Régime : <b>{label}</b></span>'
            f'<span style="font-size:.82rem;margin-left:1rem;opacity:.8;">{conf}</span></div>'
            f'<div style="font-family:Space Mono,monospace;font-size:1.2rem;">'
            f'Score : <b>{sc:+d}/5</b></div>'
            f'<div style="font-size:.78rem;opacity:.7;">3j : {s3}</div>'
            f'</div>', unsafe_allow_html=True)

        # Détail des 5 composantes (expander)
        with st.expander("📊 Détail des 5 indicateurs du régime", expanded=False):
            cols = st.columns(5)
            for i, comp in enumerate(regime.get("components", [])):
                with cols[i % 5]:
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

    # ── COMMAND CENTER (KPIs) ──────────────────────────────────────────────────
    def render_command_center(self, ptf: Dict, bench: Dict,
                               mode_direct: bool, pm: PersistenceManager):
        st.markdown("## 🚀 Command Center")

        # Performance chaînée v5.2
        perf_j_chain, perf_c_chain, base_cap = pm.compute_daily_performance(ptf["valeur_totale"])

        c1, c2, c3, c4 = st.columns(4)
        s = self._sign

        with c1:
            crd = "card card-purple" if mode_direct else "card card-gold"
            lbl = "Valeur Titres Brute" if mode_direct else "Solde Total Portefeuille"
            vj, vjp = ptf["perf_j_eur"], ptf["perf_j_pct"]
            st.markdown(
                f'<div class="{crd}"><div class="kpi-label">{lbl}<span class="live-badge">LIVE</span></div>'
                f'<div class="kpi-value">{ptf["solde_total"]:,.2f}€</div>'
                f'<div class="kpi-delta-{"pos" if vj>=0 else "neg"}">'
                f'{s(vj)}{vj:,.2f}€ ({s(vjp)}{vjp:.2f}%) vs veille</div></div>',
                unsafe_allow_html=True)

        with c2:
            lbl2 = "Gain Boursier Brut" if mode_direct else "Gain Réel Patrimonial"
            gr   = ptf["gain_reel"]
            clr  = "#22C55E" if gr >= 0 else "#FF3131"
            st.markdown(
                f'<div class="card card-blue"><div class="kpi-label">{lbl2}</div>'
                f'<div class="kpi-value" style="color:{clr};">{s(gr)}{gr:,.2f}€</div>'
                f'<div class="small">Capital réel : {ptf["capital_reel"]:,.2f}€</div></div>',
                unsafe_allow_html=True)

        with c3:
            p    = ptf["perf_tot_pct"]
            pc   = "#22C55E" if p >= 0 else "#FF3131"
            gap  = bench.get("gap")
            gc   = "#22C55E" if (gap or 0) >= 0 else "#FF3131"
            body = (f'<div class="small">GAP vs World : '
                    f'<span style="color:{gc};font-weight:700;">{s(gap)}{gap:.2f}%</span></div>'
                    if gap is not None else "")
            # Perf chaînée
            pcc  = "#22C55E" if perf_c_chain >= 0 else "#FF3131"
            st.markdown(
                f'<div class="card card-blue"><div class="kpi-label">Performance Totale</div>'
                f'<div class="kpi-value" style="color:{pc};">{s(p)}{p:.2f}%</div>'
                f'{body}'
                f'<div class="small" style="margin-top:.2rem;">Perf chaînée : '
                f'<span style="color:{pcc};font-weight:700;">{s(perf_c_chain)}{perf_c_chain:.2f}%</span>'
                f' | J : {s(perf_j_chain)}{perf_j_chain:.2f}%</div></div>',
                unsafe_allow_html=True)

        with c4:
            pb   = bench.get("perf_bench")
            pbj  = bench.get("perf_bench_j")
            if pb is not None:
                pbc = "#22C55E" if pb >= 0 else "#FF3131"
                pbj_html = (f'<div class="kpi-delta-{"pos" if pbj>=0 else "neg"}">'
                            f'{s(pbj)}{pbj:.2f}% vs veille</div>' if pbj is not None else "")
                body_bench = (f'<div class="kpi-value" style="color:{pbc};">{s(pb)}{pb:.2f}%</div>'
                              f'{pbj_html}')
            else:
                body_bench = '<div class="kpi-value">N/A</div>'
            st.markdown(
                f'<div class="card card-blue"><div class="kpi-label">Benchmark MSCI World'
                f'<span class="live-badge">LIVE</span></div>'
                f'{body_bench}</div>', unsafe_allow_html=True)

        # ── Tableau positions + donut ──────────────────────────────────────────
        st.markdown("### 📊 Positions détaillées")
        col_t, col_p = st.columns([3, 2])
        with col_t:
            rows = []
            for p2 in ptf["positions"]:
                perf_f = f"{s(p2['perf_pct'])}{p2['perf_pct']:.2f}%" if p2["perf_pct"] is not None else "N/A"
                vj_f   = f"{s(p2['var_jour_pct'])}{p2['var_jour_pct']:.2f}%" if p2["var_jour_pct"] else "–"
                vje_f  = f"{s(p2['var_jour_eur'])}{p2['var_jour_eur']:,.2f}€" if p2["var_jour_eur"] else "–"
                prix_f = f"{p2['prix']:.3f}€" if p2["prix"] else "N/A"
                rows.append({"Position": p2["nom"], "Env.": p2["enveloppe"], "Prix live": prix_f,
                             "Valeur (€)": f"{p2['valeur']:,.2f}", "Perf.": perf_f,
                             "Δ Jour (%)": vj_f, "Δ Jour (€)": vje_f})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            if not mode_direct:
                st.markdown(
                    f'<div class="info-box">Ajust. patrimonial : +{ptf["ajustement_pat"]:,.2f}€ → '
                    f'Solde total : <b>{ptf["solde_total"]:,.2f}€</b></div>', unsafe_allow_html=True)
        with col_p:
            donut = [p2 for p2 in ptf["positions"] if p2["valeur"] > 0]
            if donut:
                colors_pie = ["#007BFF","#6366F1","#D4AF37","#F97316","#22C55E"]
                fig_pie = go.Figure(go.Pie(
                    labels=[d["nom"] for d in donut], values=[d["valeur"] for d in donut],
                    hole=0.6, textinfo="percent",
                    marker=dict(colors=colors_pie[:len(donut)],
                                line=dict(color="#1C1F26", width=2)),
                ))
                vt = ptf["valeur_totale"]
                fig_pie.update_layout(
                    **_PLOTLY_BASE, margin=dict(t=10,b=10,l=10,r=10), height=270,
                    legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                    annotations=[dict(text=f"{vt:,.0f}€", x=.5, y=.5,
                        font=dict(size=13,color="#D4AF37",family="Space Mono"), showarrow=False)])
                st.plotly_chart(fig_pie, use_container_width=True)

    # ── EQUITY CURVE & SNAPSHOT ────────────────────────────────────────────────
    def render_equity_curve_section(self, ptf: Dict, regime: Dict,
                                     unified_h: Dict, unified_a: Dict,
                                     positions_conf: List[Dict]):
        st.markdown("## 📈 Equity Curve & Persistance")
        col_eq, col_snap = st.columns([3, 1])

        history = self.pm.load_history()
        with col_eq:
            fig_eq = plot_equity_curve(history)
            if fig_eq:
                st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown(
                    '<div class="card card-orange">'
                    '<div class="kpi-label">Aucune donnée historique</div>'
                    '<div class="small">Utilisez le bouton "Enregistrer Snapshot" pour démarrer '
                    'le suivi de votre courbe d\'équité.</div></div>', unsafe_allow_html=True)
            if not history.empty:
                perf_j, perf_c, base_cap = self.pm.compute_daily_performance(ptf["valeur_totale"])
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Snapshots enregistrés", f"{len(history)}")
                mc2.metric("Base J-1 (€)", f"{base_cap:,.2f}")
                mc3.metric("Perf Jour (chaîné)", f"{perf_j:+.2f}%")
                mc4.metric("Perf Cumul (chaîné)", f"{perf_c:+.2f}%")

        with col_snap:
            st.markdown('<div class="card card-green">', unsafe_allow_html=True)
            st.markdown("### 💾 Snapshot")
            st.caption("Enregistre l'état du portefeuille.")

            vt      = ptf["valeur_totale"]
            pj, pc, _ = self.pm.compute_daily_performance(vt)
            poids_h = next((p["valeur"]/vt*100 for p in ptf["positions"] if p["nom"]=="Global Hydrogen" and vt>0), 0.0)
            poids_em= next((p["valeur"]/vt*100 for p in ptf["positions"] if p["nom"]=="EM Asia" and vt>0), 0.0)

            st.markdown(f"""
<div style="font-size:.82rem;color:#6B7585;line-height:1.8;">
<b>Valeur :</b> {vt:,.2f}€<br>
<b>Perf J :</b> {pj:+.2f}%<br>
<b>Perf Cumul :</b> {pc:+.2f}%<br>
<b>Régime :</b> {regime["confirmed_label"]}<br>
<b>Poids H₂ :</b> {poids_h:.1f}%<br>
<b>Poids EM :</b> {poids_em:.1f}%
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
                    st.success("✅ Snapshot sauvegardé" +
                               (" + GitHub Gist" if self.pm.status == "github" else " (SQLite)"))
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Échec de sauvegarde")

            if not history.empty:
                st.markdown("---")
                st.markdown(f'<div class="small">Dernier snapshot : {history["date"].iloc[-1]}</div>',
                            unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ── RISK DASHBOARD ─────────────────────────────────────────────────────────
    def render_risk_dashboard(self, ptf: Dict):
        st.markdown("## ⚠️ Risk Dashboard")
        col_corr, col_rc = st.columns(2)

        # Tickers avec valeur > 0
        tickers_ptf  = ["ANRJ.PA", "AASI.PA", "MWRD.PA", "OR-EUR.PA"]
        positions_map = {p["nom"]: p for p in ptf["positions"]}
        vt = ptf["valeur_totale"]

        # Matrice de corrélation
        with col_corr:
            st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
            corr_df = self.qre.correlation_matrix(tickers_ptf, 60)
            if corr_df is not None:
                fig_c = plot_correlation_heatmap(corr_df)
                st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Données insuffisantes pour la corrélation (< 60j).")
            st.markdown('</div>', unsafe_allow_html=True)

        # Risk Contribution
        with col_rc:
            st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
            weights_ptf = []
            valid_tk    = []
            for tk in tickers_ptf:
                df = self.dm.data.get(tk, pd.DataFrame())
                if not df.empty:
                    nom = next((p["nom"] for p in ptf["positions"] if p.get("ticker") == tk), "")
                    val = positions_map.get(nom, {}).get("valeur", 0.0)
                    valid_tk.append(tk)
                    weights_ptf.append(val)
            if valid_tk and sum(weights_ptf) > 0:
                rc = self.qre.risk_contribution(valid_tk, weights_ptf, 60)
                if rc:
                    fig_rc = plot_risk_contribution(rc)
                    if fig_rc:
                        st.plotly_chart(fig_rc, use_container_width=True, config={"displayModeBar": False})
                    # Flags
                    flags = [tk for tk, v in rc.items() if v["flag"]]
                    if flags:
                        short = {"ANRJ.PA": "H₂", "AASI.PA": "EM Asia",
                                 "MWRD.PA": "MSCI World", "OR-EUR.PA": "Or"}
                        f_names = ", ".join([short.get(f, f) for f in flags])
                        st.markdown(
                            f'<div class="alert-box">🚨 <b>Concentration de risque</b> : '
                            f'{f_names} contribue > 40% du risque total → Recalibrer les poids.</div>',
                            unsafe_allow_html=True)
                else:
                    st.info("Calcul risk contribution indisponible.")
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Métriques de risque par actif ─────────────────────────────────────
        st.markdown("### 📐 Métriques de Risque Individuelles")
        risk_cols = st.columns(4)
        for i, (tk, lbl) in enumerate([("ANRJ.PA","H₂ Hydrogen"),("AASI.PA","EM Asia"),
                                        ("MWRD.PA","MSCI World"),("OR-EUR.PA","Or")]):
            with risk_cols[i]:
                vol   = self.qre.rolling_volatility(tk, 30)
                beta  = self.qre.rolling_beta(tk)
                dd    = self.qre.drawdown_metrics(tk, 252)
                st.markdown(
                    f'<div class="card">'
                    f'<div class="kpi-label">{lbl}</div>'
                    f'<div style="display:grid;gap:.4rem;margin-top:.5rem;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:.82rem;">'
                    f'<span style="color:#6B7585;">Vol 30j (ann.)</span>'
                    f'<span style="color:{"#FF3131" if vol and vol>0.25 else "#22C55E" if vol and vol<0.15 else "#F97316"};font-weight:700;">'
                    f'{"N/A" if vol is None else f"{vol*100:.1f}%"}</span></div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:.82rem;">'
                    f'<span style="color:#6B7585;">Beta (60j)</span>'
                    f'<span style="color:#CBD5E1;font-weight:600;">'
                    f'{"N/A" if beta is None else f"{beta:.2f}"}</span></div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:.82rem;">'
                    f'<span style="color:#6B7585;">DD courant</span>'
                    f'<span style="color:{"#FF3131" if dd["current_dd"] and dd["current_dd"]<-5 else "#F97316" if dd["current_dd"] and dd["current_dd"]<-2 else "#22C55E"};font-weight:600;">'
                    f'{"N/A" if dd["current_dd"] is None else f"{dd["current_dd"]:+.1f}%"}</span></div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:.82rem;">'
                    f'<span style="color:#6B7585;">Max DD (252j)</span>'
                    f'<span style="color:#FCA5A5;font-weight:600;">'
                    f'{"N/A" if dd["max_dd"] is None else f"{dd["max_dd"]:.1f}%"}</span></div>'
                    f'</div></div>', unsafe_allow_html=True)

    # ── SATELLITE CARD v5.2 (3 colonnes) ──────────────────────────────────────
    def render_satellite_card(self, nom: str, ticker: str,
                               unified: Dict, target_weight: Dict,
                               regime: Dict):
        """
        3 colonnes :
        1. Score Stratégique (Unifié v4.1 + 4 composantes v5.2)
        2. Jauges de Risque (Vol, Beta, Drawdown)
        3. Action (go.Indicator Poids Actuel vs Cible)
        """
        total = unified["total"]
        if total >= 3:   score_cls, card_cls = "score-pos",  "card-gold"
        elif total >= 0: score_cls, card_cls = "score-neut", "card-orange"
        else:            score_cls, card_cls = "score-neg",  "card-red"

        status_label, status_cls = self._get_status_label(total)
        s4c = target_weight.get("strat4c", {})

        st.markdown(f'<div class="card {card_cls}" style="padding:0;overflow:hidden;">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1.2, 0.9, 0.9])

        # ── Colonne 1 : Score Stratégique ────────────────────────────────────
        with col1:
            sign = "+" if total > 0 else ""
            st.markdown(
                f'<div style="padding:1.4rem;">'
                f'<div class="kpi-label">{nom} — Score Stratégique</div>'
                f'<div style="margin:.4rem 0 .8rem 0;">'
                f'<span class="score-badge {score_cls}">{sign}{total}/4</span></div>',
                unsafe_allow_html=True)

            # Tableau 3 couches v4.1
            badge_map = {"bull": "BULL", "neut": "NEUTRE", "bear": "BEAR"}
            rows_html = ""
            for layer in unified["details"]:
                vs   = f"{'+' if layer['score']>0 else ''}{layer['score']}" if layer['score']!=0 else "0"
                clr  = "#22C55E" if layer['score']>0 else "#FF3131" if layer['score']<0 else "#6B7585"
                rows_html += (
                    f'<tr><td class="col-name">{layer["name"]}</td>'
                    f'<td class="col-badge"><span class="bg-{layer["badge"]}">'
                    f'{badge_map[layer["badge"]]}</span></td>'
                    f'<td class="col-val"><span style="color:{clr};">{vs}</span>'
                    f' <span style="color:#6B7585;font-size:.75rem;">— {layer["desc"]}</span>'
                    f'</td></tr>'
                )
            st.markdown(
                f'<table class="score-table"><thead><tr>'
                f'<th>CRITÈRE</th><th style="text-align:center">SIGNAL</th><th>VALEUR</th>'
                f'</tr></thead><tbody>{rows_html}</tbody></table>',
                unsafe_allow_html=True)

            # Score 4 composantes v5.2 (si disponible)
            if s4c:
                st.markdown('<div style="margin-top:.8rem;"><div class="kpi-label" style="margin-top:.5rem;">Score Stratégique 4C (v5.2)</div>', unsafe_allow_html=True)
                comp_names = {"trend": "Trend", "macro": "Macro/Rég.", "leadership": "Leadership", "risk_vol": "Risque/Vol"}
                comp_w     = {"trend": 25, "macro": 30, "leadership": 25, "risk_vol": 20}
                for key, lbl in comp_names.items():
                    v   = s4c.get(key, 0)
                    w   = comp_w[key]
                    clr = "#22C55E" if v > 0.1 else "#FF3131" if v < -0.1 else "#F97316"
                    bar_w = abs(v) * 50
                    bar_clr = "#22C55E" if v >= 0 else "#FF3131"
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:.5rem;margin:.2rem 0;font-size:.78rem;">'
                        f'<span style="color:#6B7585;width:80px;">{lbl} ({w}%)</span>'
                        f'<div style="background:#2E3340;border-radius:4px;height:6px;width:80px;position:relative;">'
                        f'<div style="position:absolute;{"right:50%" if v<0 else "left:50%"};'
                        f'width:{bar_w}px;height:6px;background:{bar_clr};border-radius:4px;"></div>'
                        f'<div style="position:absolute;left:50%;width:1px;height:6px;background:#6B7585;"></div>'
                        f'</div>'
                        f'<span style="color:{clr};font-weight:700;font-family:Space Mono;font-size:.72rem;">'
                        f'{v:+.2f}</span></div>', unsafe_allow_html=True)
                tot4c = s4c.get("total", 0)
                tc_clr = "#22C55E" if tot4c > 0.1 else "#FF3131" if tot4c < -0.1 else "#F97316"
                st.markdown(
                    f'<div style="font-size:.8rem;margin-top:.4rem;font-family:Space Mono;'
                    f'color:{tc_clr};font-weight:700;">Score total : {tot4c:+.2f}/1</div></div>',
                    unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # ── Colonne 2 : Jauges de Risque ─────────────────────────────────────
        with col2:
            st.markdown('<div style="padding:1.4rem;">', unsafe_allow_html=True)
            st.markdown('<div class="kpi-label">Jauges de Risque</div>', unsafe_allow_html=True)

            vol  = self.qre.rolling_volatility(ticker, 30)
            beta = self.qre.rolling_beta(ticker)
            dd   = self.qre.drawdown_metrics(ticker, 252)

            def _risk_row(label, value, unit, warn_hi, bad_hi, reverse=False):
                if value is None:
                    cls_, v_ = "risk-ok", "N/A"
                else:
                    is_bad  = value > bad_hi if not reverse else value < bad_hi
                    is_warn = value > warn_hi if not reverse else value < warn_hi
                    cls_ = "risk-flag" if is_bad or is_warn else "risk-ok"
                    v_   = f"{value:.2f}{unit}"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'margin:.4rem 0;font-size:.82rem;">'
                    f'<span style="color:#6B7585;">{label}</span>'
                    f'<span class="{cls_}">{v_}</span></div>',
                    unsafe_allow_html=True)

            _risk_row("Vol 30j ann.",     vol * 100 if vol else None,     "%", 20.0, 30.0)
            _risk_row("Beta 60j",         beta,                           "",   1.3,  1.8)
            _risk_row("DD Courant",       abs(dd["current_dd"]) if dd["current_dd"] else None, "%", 5.0, 10.0)
            _risk_row("Max DD (252j)",    abs(dd["max_dd"]) if dd["max_dd"] else None,          "%", 15.0, 25.0)

            # Régime multiplier
            rm  = target_weight.get("regime_mult", 1.0)
            cf  = target_weight.get("confidence", 1.0)
            rmc = "#22C55E" if rm >= 1.0 else "#F97316" if rm >= 0.7 else "#FF3131"
            cfc = "#22C55E" if cf >= 0.9 else "#F97316" if cf >= 0.75 else "#FF3131"
            st.markdown("<div style='margin-top:.8rem;'>", unsafe_allow_html=True)
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;font-size:.78rem;margin:.2rem 0;">'
                f'<span style="color:#6B7585;">Rég. Multiplier</span>'
                f'<span style="color:{rmc};font-weight:700;">{rm:.2f}×</span></div>'
                f'<div style="display:flex;justify-content:space-between;font-size:.78rem;margin:.2rem 0;">'
                f'<span style="color:#6B7585;">Confidence Factor</span>'
                f'<span style="color:{cfc};font-weight:700;">{cf:.2f}</span></div>',
                unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

        # ── Colonne 3 : Action go.Indicator ──────────────────────────────────
        with col3:
            st.markdown('<div style="padding:1.4rem;">', unsafe_allow_html=True)
            st.markdown('<div class="kpi-label">Allocation Cible</div>', unsafe_allow_html=True)

            cur_pct = target_weight.get("current_pct", 0.0)
            tgt_pct = target_weight.get("target_pct", 0.0)
            action  = target_weight.get("action", "MAINTENIR")
            delta_e = target_weight.get("delta_eur", 0.0)

            fig_w = plot_weight_indicator(cur_pct, tgt_pct)
            st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})

            # Verdict
            if action == "RÉDUIRE":
                st.markdown(
                    f'<div class="arb-sell">'
                    f'<div style="font-size:.72rem;color:#FF3131;letter-spacing:1px;">🚨 ACTION</div>'
                    f'<div style="font-size:1.1rem;color:#FCA5A5;font-weight:700;">RÉDUIRE {abs(delta_e):,.0f}€</div>'
                    f'<div style="font-size:.75rem;color:#8892AA;">{cur_pct:.1f}% → {tgt_pct:.1f}%</div>'
                    f'</div>', unsafe_allow_html=True)
            elif action == "RENFORCER":
                st.markdown(
                    f'<div class="arb-buy">'
                    f'<div style="font-size:.72rem;color:#22C55E;letter-spacing:1px;">💡 OPPORTUNITÉ</div>'
                    f'<div style="font-size:1.1rem;color:#86EFAC;font-weight:700;">RENFORCER {abs(delta_e):,.0f}€</div>'
                    f'<div style="font-size:.75rem;color:#8892AA;">{cur_pct:.1f}% → {tgt_pct:.1f}%</div>'
                    f'</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="arb-neutral">'
                    f'<div style="font-size:.72rem;color:#6B7585;">✅ STATU QUO</div>'
                    f'<div style="font-size:1.1rem;color:#CBD5E1;font-weight:600;">MAINTENIR</div>'
                    f'<div style="font-size:.75rem;color:#8892AA;">{cur_pct:.1f}% ≈ {tgt_pct:.1f}%</div>'
                    f'</div>', unsafe_allow_html=True)

            # Verdict structuré
            st.markdown(
                f'<div style="background:#1C1F26;border:1px solid #2E3340;border-radius:8px;'
                f'padding:.6rem;margin-top:.6rem;font-size:.76rem;font-family:Space Mono,monospace;">'
                f'<span style="color:#6B7585;">Actuel :</span> {cur_pct:.1f}%<br>'
                f'<span style="color:#6B7585;">Cible  :</span> <span style="color:#D4AF37;">{tgt_pct:.1f}%</span><br>'
                f'<span style="color:#6B7585;">Δ      :</span> {self._sign(delta_e)}{delta_e:,.0f}€</div>',
                unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # close card

        # Verdict décisionnel v4.1 + Alpha Bars + Perf Relative
        st.markdown(
            f'<div style="text-align:center;margin:.5rem 0;">'
            f'<div class="{status_cls}" style="display:inline-block;min-width:300px;">'
            f'{status_label}</div></div>', unsafe_allow_html=True)

        fig_a = plot_alpha_bars(self.dm, ticker, nom)
        if fig_a:
            st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})
        fig_r = plot_relative_perf(self.dm, ticker, nom)
        if fig_r:
            st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})

    @staticmethod
    def _get_status_label(score: int) -> Tuple[str, str]:
        if score >= 3:   return "MAINTIEN TOTAL",         "status-maintain"
        elif score >= 1: return "ALLÈGEMENT LÉGER",       "status-lighten"
        elif score >= -1:return "VIGILANCE",              "status-vigilance"
        elif score >= -2:return "RÉDUCTION PARTIELLE",    "status-reduce"
        else:            return "SORTIE / RÉDUCTION FORTE","status-exit"

    # ── SENTINELLES & MACRO (v4.1 préservé) ───────────────────────────────────
    def render_sentinelles_macro(self, ptf: Dict):
        st.markdown("## 🛰️ Sentinelles & Flash Macro")
        col_s, col_m = st.columns([3, 2])

        s_msg, s_col, sent_rows = self.pe.evaluate_sentinelles()
        with col_s:
            st.markdown('<div class="card card-blue">', unsafe_allow_html=True)
            st.markdown("### 📡 Sentinelles sectorielles")
            if "OK" in s_msg: st.success(s_msg)
            else:             st.warning(s_msg)
            st.dataframe(pd.DataFrame(sent_rows), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### ⚖️ Poids Satellites vs Cible")
            vt       = ptf["valeur_totale"]
            anrj_v   = next((p["valeur"] for p in ptf["positions"] if p["nom"]=="Global Hydrogen"), 0)
            aasi_v   = next((p["valeur"] for p in ptf["positions"] if p["nom"]=="EM Asia"), 0)
            poids_s  = (anrj_v + aasi_v) / vt * 100 if vt else 0
            delta_ps = poids_s - 45
            st.metric("ANRJ + AASI", f"{poids_s:.1f}%",
                      delta=f"{self._sign(delta_ps)}{delta_ps:.1f}% vs 45%")
            bc = "#FF3131" if poids_s > 45 else "#22C55E"
            st.markdown(
                f'<div style="background:#1C1F26;border-radius:6px;height:8px;">'
                f'<div style="background:{bc};width:{min(poids_s,100):.1f}%;height:8px;border-radius:6px;"></div>'
                f'</div>', unsafe_allow_html=True)

            st.markdown("#### 🎯 Cible 94% World / 6% Or")
            vw = sum(p["valeur"] for p in ptf["positions"] if "MSCI World" in p["nom"])
            vg = sum(p["valeur"] for p in ptf["positions"] if "Or" in p["nom"])
            c_w, c_g = st.columns(2)
            c_w.metric("MSCI World",  f"{vw/vt*100:.1f}%" if vt else "N/A",
                       delta=f"{(vw/vt*100-94 if vt else 0):.1f}% vs 94%")
            c_g.metric("Or Physique", f"{vg/vt*100:.1f}%" if vt else "N/A",
                       delta=f"{(vg/vt*100-6 if vt else 0):.1f}% vs 6%")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_m:
            st.markdown('<div class="card card-gold">', unsafe_allow_html=True)
            st.markdown("### 🌍 Flash Macro <span class='live-badge'>LIVE</span>",
                        unsafe_allow_html=True)
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
                    sig     = SIGNALS.get(sym)
                    extra   = (f"  {sig[1] if pv > sig[0] else sig[2]}" if sig else "")
                    st.metric(lbl, f"{pv:{FMT.get(sym,'.2f')}}{SFX.get(sym,'')}{extra}",
                              delta=delta_m)
                else:
                    st.metric(lbl, "N/A")
            st.markdown('</div>', unsafe_allow_html=True)

    # ── SIMULATEUR FISCAL (v4.1 préservé) ─────────────────────────────────────
    def render_fiscal_simulator(self, ptf: Dict):
        st.markdown("## 🧮 Simulateur Fiscal")
        col_pea, col_av = st.columns(2)
        val_env, gan_env = ptf["val_env"], ptf["gain_env"]

        with col_pea:
            st.markdown('<div class="card card-blue"><h4>🏦 PEA</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("PEA", val_env["PEA"], val_env["PEA"], gan_env["PEA"])
            if avert: st.warning(avert); st.metric("Valeur brute PEA", f"{val_env['PEA']:,.2f}€")
            else:     st.metric("Net après PS 17.2%", f"{net:,.2f}€")
            st.caption(f"Gain latent PEA : {self._sign(gan_env['PEA'])}{gan_env['PEA']:,.2f}€")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_av:
            st.markdown('<div class="card card-blue"><h4>🛡️ Assurance-Vie</h4>', unsafe_allow_html=True)
            net, avert = net_apres_impots("AV", val_env["AV"], val_env["AV"], gan_env["AV"])
            if avert: st.warning(avert); st.metric("Valeur brute AV", f"{val_env['AV']:,.2f}€")
            else:     st.metric("Net après fiscalité AV", f"{net:,.2f}€")
            st.caption(f"Gain latent AV : {self._sign(gan_env['AV'])}{gan_env['AV']:,.2f}€")
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
                                               val_env.get(env_sim, 0), gan_env.get(env_sim, 0))
        if avert_sim:
            st.warning(avert_sim)
        elif montant_sim > 0:
            vp, gp   = val_env.get(env_sim, 0), gan_env.get(env_sim, 0)
            gain_sim = montant_sim * (gp / vp if vp else 0)
            imp_sim  = montant_sim - net_sim
            st.markdown(
                f'<div class="net-box" style="display:flex;gap:2.5rem;flex-wrap:wrap;align-items:center;">'
                f'<div><div class="kpi-label">Brut retiré</div><div class="kpi-value">{montant_sim:,.2f}€</div></div>'
                f'<div style="color:#6B7585;font-size:1.5rem;">→</div>'
                f'<div><div class="kpi-label">Part gains</div><div class="kpi-value" style="color:#D4AF37;">{gain_sim:,.2f}€</div></div>'
                f'<div><div class="kpi-label">Impôts/PS</div><div class="kpi-value" style="color:#FF3131;">{imp_sim:,.2f}€</div></div>'
                f'<div><div class="kpi-label">Net perçu</div><div class="kpi-value" style="color:#22C55E;">{net_sim:,.2f}€</div></div>'
                f'</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── FOOTER ─────────────────────────────────────────────────────────────────
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
                f"◈ Cockpit v5.2 Quant-System · {mode_txt} · "
                f"Score H={s(score_h)}{score_h}/4 | EM={s(score_a)}{score_a}/4 · "
                f"Régime : {regime_label} · Capital {capital:,.2f}€ · "
                f"Persistance : {persist} · {live_ok}/{live_total} prix live · "
                "Outil personnel — Ne constitue pas un conseil en investissement"
            )
        with col_f2:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 12 : POINT D'ENTRÉE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Initialisation Session State ──────────────────────────────────────────
    if "config_loaded" not in st.session_state:
        cfg = _load_config()
        st.session_state["cfg_capital_reel"]   = cfg["capital_reel"]
        st.session_state["cfg_ajustement_pat"] = cfg["ajustement_pat"]
        st.session_state["cfg_bonus_fortuneo"] = cfg["bonus_fortuneo"]
        st.session_state["config_loaded"]      = True
        st.session_state["save_feedback"]      = ""

    # ── Instanciation des Engines ──────────────────────────────────────────────
    with st.spinner("📡 Récupération des prix en direct..."):
        dm = DataManager()
    if not dm.live:
        st.error("❌ Aucun prix live. Vérifiez votre connexion.")
        st.stop()

    # PersistenceManager (utilise le capital de la config comme base initiale)
    pm  = PersistenceManager(static_capital=st.session_state["cfg_capital_reel"])
    mre = MarketRegimeEngine(dm)
    qre = QuantRiskEngine(dm)
    pe  = PortfolioEngine(dm, mre, qre)
    ui  = StreamlitUI(dm, pm, mre, qre, pe)

    # ── Sidebar ────────────────────────────────────────────────────────────────
    mode_direct, positions_conf, capital_reel, ajustement_pat, bonus_fortuneo = \
        ui.render_sidebar()

    # ── Calculs Cœur ──────────────────────────────────────────────────────────
    with st.spinner("⚙️ Calculs quantitatifs en cours..."):
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

    live_ok    = sum(1 for v in dm.live.values() if v.get("prix"))
    live_total = len(dm.live)

    # ── Expander Méthodologie ─────────────────────────────────────────────────
    with st.expander("ℹ️ Méthodologie v5.2", expanded=False):
        st.markdown("""
### Architecture v5.2 — 6 Modules

| Module | Rôle |
|--------|------|
| **DataManager** | Données live + historique 600j, log returns |
| **PersistenceManager** | SQLite session + GitHub Gist CSV cross-session |
| **MarketRegimeEngine** | Score −5/+5, 5 labels, confirmation 3j anti-whipsaw |
| **QuantRiskEngine** | Vol 30j, Beta 60j, Drawdown, Corrélation, Risk Contribution |
| **PortfolioEngine** | Score unifié 3 couches + Score 4 composantes + Dynamic Sizing |
| **StreamlitUI** | Rendu pur, zéro logique métier |

### Dynamic Sizing Matrix
```
Target = Base_Weight × Régime_Multiplier × Confidence_Factor × (1 + ScoreStrat × 0.30)
```
| Régime | Multiplier | Conf. Vol<10% | Conf. Vol>20% |
|--------|-----------|--------------|--------------|
| Euphorie / Expansion | 1.00 | 1.00 | 0.60 |
| Neutre | 0.85 | 1.00 | 0.60 |
| Stress | 0.70 | 1.00 | 0.60 |
| Contraction | 0.20 | 1.00 | 0.60 |

### Score Unifié v4.1 (−4/+4) — Inchangé
| Couche | Indicateur | Bull | Bear | Poids |
|--------|-----------|------|------|-------|
| Momentum | RSI 14j | 45<RSI<70 → +1 | RSI≥70 ou ≤45 → −1 | ±1 |
| Structure | Prix vs SMA20 | Prix>SMA20 → +1 | Prix<SMA20 → −1 | ±1 |
| Leadership | Pente RS 14j | Pente>0 → +2 | Pente<0 → −2 | ±2 |
""")

    # ── Rendu UI ───────────────────────────────────────────────────────────────
    ui.render_header(mode_direct, live_ok, live_total)
    ui.render_regime_banner(regime)

    # Alertes Leadership
    for al in ld_alerts:
        gv, nom_al, sp, wp = al["gap"], al["nom"], al["sat_perf"], al["world_perf"]
        s = StreamlitUI._sign
        if gv < -5:   cls, ico = "alert-critical", "🚨"
        elif gv < -2: cls, ico = "alert-leadership","⚠️"
        else: continue
        st.markdown(
            f'<div class="{cls}">{ico} <b>ALERTE LEADERSHIP : {nom_al}</b> — '
            f'Sous-performance de <b>{abs(gv):.1f}%</b> vs World 14j '
            f'({nom_al} : {s(sp)}{sp:.1f}% | World : {s(wp)}{wp:.1f}%)</div>',
            unsafe_allow_html=True)

    # Phase banner
    st.markdown(f'<div class="phase-banner" style="background:{phase_color};color:white;">'
                f'{phase_text}</div>', unsafe_allow_html=True)

    ui.render_command_center(ptf, bench, mode_direct, pm)
    ui.render_equity_curve_section(ptf, regime, unified_h, unified_a, positions_conf)
    ui.render_risk_dashboard(ptf)

    st.markdown("## 🧠 Score Unifié — Satellites")
    st.markdown("### 🔥 Global Hydrogen (ANRJ.PA)")
    st.markdown(
        f'<div class="alert-box" style="background:#2D1515;border-left:4px solid '
        f'{"#22C55E" if h_col=="green" else "#F97316" if h_col=="orange" else "#FF3131"};">'
        f'{h_msg}</div>', unsafe_allow_html=True)
    ui.render_satellite_card("Global Hydrogen", "ANRJ.PA", unified_h, target_h, regime)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🌏 EM Asia (AASI.PA)")
    st.markdown(
        f'<div class="alert-box" style="background:#2D1515;border-left:4px solid '
        f'{"#22C55E" if a_col=="green" else "#F97316" if a_col=="orange" else "#FF3131"};">'
        f'{a_msg}</div>', unsafe_allow_html=True)
    ui.render_satellite_card("EM Asia", "AASI.PA", unified_a, target_a, regime)

    ui.render_sentinelles_macro(ptf)
    ui.render_fiscal_simulator(ptf)
    ui.render_footer(mode_direct, capital_reel,
                     unified_h["total"], unified_a["total"],
                     regime["confirmed_label"], live_ok, live_total)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:   # Streamlit exécute toujours le module
    main()
