# =============================================================================
# COCKPIT DÉCISIONNEL BOURSIER v3.0
# Lead Dev: Claude (Anthropic) — Architecture modulaire, yfinance blindé
# =============================================================================

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

# =============================================================================
# ██████╗  BLOC 1 : CONFIGURATION & CSS DARK MODE PREMIUM
# =============================================================================

st.set_page_config(
    page_title="Cockpit Décisionnel v3",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* ── Base Dark ── */
    .stApp { background-color: #0B0E15; }
    section[data-testid="stSidebar"] { background-color: #10131C; border-right: 1px solid #1E2233; }

    /* ── Cards ── */
    .card {
        background: linear-gradient(135deg, #141824 0%, #1A1F30 100%);
        border-radius: 14px; padding: 1.4rem; margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        border: 1px solid #252B3D;
    }
    .card-accent { border-left: 4px solid #3D8BFF; }
    .card-green  { border-left: 4px solid #22C55E; }
    .card-red    { border-left: 4px solid #EF4444; }
    .card-orange { border-left: 4px solid #F97316; }

    /* ── KPIs ── */
    .kpi-value { font-size: 2rem; font-weight: 800; color: #FFFFFF; font-family: 'SF Mono', monospace; }
    .kpi-label { font-size: 0.78rem; color: #8892AA; text-transform: uppercase;
                 letter-spacing: 1.5px; margin-bottom: 0.2rem; }
    .kpi-delta-pos { color: #22C55E; font-size: 0.85rem; font-weight: 600; }
    .kpi-delta-neg { color: #EF4444; font-size: 0.85rem; font-weight: 600; }

    /* ── Verdicts ── */
    .verdict-red    { background: linear-gradient(135deg,#7F1D1D,#991B1B); color:white; padding:1.1rem;
                      border-radius:12px; font-size:1.3rem; font-weight:700; text-align:center; margin:0.75rem 0; }
    .verdict-orange { background: linear-gradient(135deg,#78350F,#92400E); color:white; padding:1.1rem;
                      border-radius:12px; font-size:1.3rem; font-weight:700; text-align:center; margin:0.75rem 0; }
    .verdict-green  { background: linear-gradient(135deg,#14532D,#166534); color:white; padding:1.1rem;
                      border-radius:12px; font-size:1.3rem; font-weight:700; text-align:center; margin:0.75rem 0; }

    /* ── Badges ── */
    .badge { display:inline-block; padding:0.2rem 0.8rem; border-radius:20px;
             font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; }
    .badge-red    { background:#EF4444; color:white; }
    .badge-orange { background:#F97316; color:white; }
    .badge-green  { background:#22C55E; color:#0B0E15; }
    .badge-gray   { background:#374151; color:#D1D5DB; }

    /* ── Phase banner ── */
    .phase-banner {
        padding: 0.8rem 1.2rem; border-radius: 10px; font-weight: 700;
        font-size: 1rem; margin-bottom: 1.2rem; text-align: center;
    }

    /* ── Table ── */
    .stDataFrame { background-color: #141824 !important; }

    /* ── Misc ── */
    h2 { color: #E2E8F0 !important; border-bottom: 1px solid #1E2233; padding-bottom: 0.4rem; }
    h3, h4 { color: #CBD5E1 !important; }
    .small { font-size: 0.82rem; color: #8892AA; }
    .net-box { background:#0D2818; border-left:4px solid #22C55E; border-radius:8px;
               padding:1rem; margin-top:0.75rem; }
    .alert-box { background:#2D1515; border-left:4px solid #EF4444; border-radius:8px;
                 padding:0.75rem 1rem; margin:0.4rem 0; font-size:0.9rem; }
    .info-box { background:#0F1E35; border-left:4px solid #3D8BFF; border-radius:8px;
                padding:0.75rem 1rem; margin:0.4rem 0; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# ██████╗  BLOC 2 : CONFIGURATION DU PORTEFEUILLE
# =============================================================================

POSITIONS_BASE = [
    {"nom": "MSCI World AV",   "tickers": ["MWRD.PA","IWDA.AS","EUNL.DE"], "parts": 36.33,   "prm": 140.41,  "enveloppe": "AV"},
    {"nom": "MSCI World PEA",  "tickers": ["DCAM.PA"],                      "parts": 481.0,   "prm": 5.5937,  "enveloppe": "PEA"},
    {"nom": "Global Hydrogen", "tickers": ["ANRJ.PA"],                      "parts": 4.7701,  "prm": 707.55,  "enveloppe": "AV"},
    {"nom": "EM Asia",         "tickers": ["AASI.PA"],                      "parts": 40.8272, "prm": 49.96,   "enveloppe": "AV"},
    {"nom": "Or Physique",     "tickers": ["CGLD.PA","GOLD.PA"],            "parts": 4.5902,  "prm": 163.39,  "enveloppe": "AV"},
]

BENCHMARK_NOM  = "MSCI World AV"
PROXIES_ANRJ   = ["PLUG", "BE", "NEL.OL"]
PROXIES_AASI   = ["TSM", "005930.KS", "AAXJ"]
MACRO_TICKERS  = {
    "NQ=F":     "Nasdaq 100",
    "ES=F":     "S&P 500",
    "^TNX":     "US 10Y (%)",
    "EURUSD=X": "EUR/USD",
    "BZ=F":     "Brent ($)",
    "GC=F":     "Or ($)",
}
SENTINELLES = {
    "TSMC":       ["TSM"],
    "Samsung":    ["005930.KS"],
    "Air Liquide":["AI.PA"],
    "Bloom Energy":["BE"],
    "SK Hynix":   ["000660.KS"],
}
DATE_DEBUT = datetime(2025, 9, 17)

# =============================================================================
# ██████╗  BLOC 3 : SIDEBAR — PARAMÈTRES DYNAMIQUES
# =============================================================================

st.sidebar.markdown("## ⚙️ Paramètres")
capital_investi = st.sidebar.number_input("Capital investi (€)", value=13956.49, step=100.0, format="%.2f")
bonus_fortuneo  = st.sidebar.number_input("Bonus Fortuneo (€)",  value=160.0,   step=10.0,  format="%.2f")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📦 Positions")

positions_conf = []
for pos in POSITIONS_BASE:
    with st.sidebar.expander(pos["nom"]):
        parts = st.number_input("Parts",   value=float(pos["parts"]), step=0.0001, format="%.4f", key=f"p_{pos['nom']}")
        prm   = st.number_input("PRM (€)", value=float(pos["prm"]),  step=0.0001, format="%.4f", key=f"r_{pos['nom']}")
        positions_conf.append({**pos, "parts": parts, "prm": prm})

# Ajustement PRM PEA (déduction prorata du bonus)
for pos in positions_conf:
    if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0:
        pos["prm"] -= bonus_fortuneo / pos["parts"]

# =============================================================================
# ██████╗  BLOC 4 : DATA ENGINE — TÉLÉCHARGEMENT BLINDÉ YFINANCE
# =============================================================================

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise n'importe quel DataFrame renvoyé par yfinance.
    Gère : MultiIndex colonnes, colonnes vides, noms incohérents.
    Renvoie toujours un DataFrame à colonnes plates avec 'Close' ou DataFrame vide.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # --- CAS 1 : MultiIndex sur les colonnes (yfinance groupe par ticker) ---
    if isinstance(df.columns, pd.MultiIndex):
        try:
            tickers_available = df.columns.get_level_values(1).unique().tolist()
            if tickers_available:
                df = df.xs(tickers_available[0], axis=1, level=1)
        except Exception:
            # Fallback : garder uniquement le premier niveau
            df = df.copy()
            df.columns = df.columns.get_level_values(0)

    # --- CAS 2 : Supprimer colonnes entièrement nulles ---
    df = df.dropna(axis=1, how="all").copy()

    # --- CAS 3 : Harmoniser les noms de colonnes ---
    df.columns = [str(c).strip() for c in df.columns]
    rename_map = {"Adj Close": "Close", "Adj_Close": "Close", "adj close": "Close"}
    df = df.rename(columns=rename_map)

    # Certaines versions de yfinance renvoient 'close' (lowercase)
    lower_map = {c: c.title() for c in df.columns}
    df = df.rename(columns=lower_map)

    if "Close" not in df.columns:
        return pd.DataFrame()

    df = df.dropna(subset=["Close"])
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


@st.cache_data(ttl=90, show_spinner=False)
def load_all_data() -> dict:
    """
    Télécharge tous les tickers en une seule passe groupée,
    puis un fallback ticker par ticker pour les manquants.
    """
    start = (datetime.now() - timedelta(days=520)).strftime("%Y-%m-%d")

    # Construction de la liste complète (sans doublons)
    all_tickers: list = []
    for pos in POSITIONS_BASE:
        all_tickers.extend(pos["tickers"])
    all_tickers.extend(PROXIES_ANRJ)
    all_tickers.extend(PROXIES_AASI)
    all_tickers.extend(list(MACRO_TICKERS.keys()))
    for tlist in SENTINELLES.values():
        all_tickers.extend(tlist)
    all_tickers = list(dict.fromkeys(all_tickers))

    result: dict = {}

    # ── Téléchargement groupé ──────────────────────────────────────────────
    try:
        raw = yf.download(
            all_tickers, start=start,
            group_by="ticker", auto_adjust=True,
            progress=False, threads=True
        )
    except Exception:
        raw = pd.DataFrame()

    if not raw.empty and isinstance(raw.columns, pd.MultiIndex):
        for tk in all_tickers:
            try:
                df = raw[tk].copy()
                df = normalize_df(df)
                if not df.empty:
                    result[tk] = df
            except (KeyError, Exception):
                pass
    elif not raw.empty and len(all_tickers) == 1:
        df = normalize_df(raw.copy())
        if not df.empty:
            result[all_tickers[0]] = df

    # ── Fallback individuel pour les tickers manquants ─────────────────────
    missing = [tk for tk in all_tickers if tk not in result]
    for tk in missing:
        try:
            df = yf.download(tk, start=start, auto_adjust=True, progress=False)
            df = normalize_df(df)
            if not df.empty:
                result[tk] = df
        except Exception:
            pass

    return result


def get_price_info(data: dict, tickers: list) -> tuple:
    """
    Renvoie (prix_actuel, clôture_veille, ticker_utilisé).
    Teste les tickers dans l'ordre et renvoie le premier fonctionnel.
    """
    for tk in tickers:
        df = data.get(tk, pd.DataFrame())
        if df.empty:
            continue
        close = df["Close"].dropna()
        if close.empty:
            continue
        prix = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) >= 2 else None
        return prix, prev, tk
    return None, None, None

# =============================================================================
# ██████╗  BLOC 5 : INDICATEURS TECHNIQUES
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
        high  = df.get("High",  pd.Series(dtype=float)).dropna()
        low   = df.get("Low",   pd.Series(dtype=float)).dropna()
        idx   = close.index.intersection(high.index).intersection(low.index)
        if len(idx) < period + 1:
            return None
        c, h, l = close[idx], high[idx], low[idx]
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        up, down = h.diff(), -l.diff()
        pdm = np.where((up > down) & (up > 0), up, 0.0)
        mdm = np.where((down > up) & (down > 0), down, 0.0)
        atr_s = tr.rolling(period).mean()
        pdi = 100 * pd.Series(pdm, index=idx).rolling(period).mean() / atr_s
        mdi = 100 * pd.Series(mdm, index=idx).rolling(period).mean() / atr_s
        dx  = ((pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)) * 100
        adx_s = dx.rolling(period).mean().dropna()
        return float(adx_s.iloc[-1]) if not adx_s.empty else None
    except Exception:
        return None


def analyze_ticker(data: dict, ticker: str):
    """Analyse technique complète d'un ticker. Retourne un dict ou None."""
    df = data.get(ticker, pd.DataFrame())
    if df.empty or "Close" not in df.columns:
        return None
    close = df["Close"].dropna()
    if close.empty:
        return None
    return {
        "ticker": ticker,
        "prix":   float(close.iloc[-1]),
        "sma20":  sma(close, 20),
        "sma50":  sma(close, 50),
        "rsi":    rsi_indicator(close),
        "adx":    adx_indicator(df),
        "ath30":  float(close.rolling(30, min_periods=1).max().iloc[-1]),
    }

# =============================================================================
# ██████╗  BLOC 6 : CALCULS PORTEFEUILLE
# =============================================================================

def compute_portfolio(positions_conf: list, capital_investi: float,
                      bonus_fortuneo: float, data: dict) -> dict:
    positions_calculees = []
    valeur_totale = 0.0
    valeur_veille = 0.0
    val_env  = {"PEA": 0.0, "AV": 0.0}
    gain_env = {"PEA": 0.0, "AV": 0.0}

    for pos in positions_conf:
        prix, prev, tk_used = get_price_info(data, pos["tickers"])
        env = pos["enveloppe"]

        if prix is None:
            positions_calculees.append({
                "nom": pos["nom"], "ticker": None, "prix": None,
                "valeur": 0.0, "perf_pct": None,
                "var_jour_pct": 0.0, "var_jour_eur": 0.0,
                "enveloppe": env,
            })
            continue

        valeur     = pos["parts"] * prix
        gain_unit  = prix - pos["prm"]
        perf_pct   = gain_unit / pos["prm"] * 100
        gain_total = gain_unit * pos["parts"]

        var_jour_pct = (prix - prev) / prev * 100 if prev and prev != 0 else 0.0
        var_jour_eur = (prix - prev) * pos["parts"] if prev else 0.0

        positions_calculees.append({
            "nom": pos["nom"], "ticker": tk_used, "prix": prix,
            "valeur": valeur, "perf_pct": perf_pct,
            "var_jour_pct": var_jour_pct, "var_jour_eur": var_jour_eur,
            "enveloppe": env,
        })
        valeur_totale   += valeur
        val_env[env]    += valeur
        gain_env[env]   += gain_total
        valeur_veille   += pos["parts"] * (prev if prev else prix)

    capital_net  = capital_investi - bonus_fortuneo
    gain_net     = valeur_totale - capital_net
    perf_tot_pct = gain_net / capital_net * 100 if capital_net else 0.0
    perf_j_eur   = valeur_totale - valeur_veille
    perf_j_pct   = perf_j_eur / valeur_veille * 100 if valeur_veille else 0.0

    return {
        "positions": positions_calculees,
        "valeur_totale": valeur_totale,
        "valeur_veille": valeur_veille,
        "val_env":  val_env,
        "gain_env": gain_env,
        "capital_net":  capital_net,
        "gain_net":     gain_net,
        "perf_tot_pct": perf_tot_pct,
        "perf_j_eur":   perf_j_eur,
        "perf_j_pct":   perf_j_pct,
    }


def compute_benchmark(data: dict, positions_conf: list, perf_tot_pct: float) -> tuple:
    bench_pos = next((p for p in positions_conf if p["nom"] == BENCHMARK_NOM), None)
    if not bench_pos:
        return None, None, None, None
    prix, prev, tk = get_price_info(data, bench_pos["tickers"])
    if not prix or not tk:
        return None, None, None, None

    close = data[tk]["Close"].dropna()
    start_str = DATE_DEBUT.strftime("%Y-%m-%d")
    try:
        start_val = float(close.loc[start_str])
    except KeyError:
        candidates = close.loc[:start_str]
        start_val = float(candidates.iloc[-1]) if not candidates.empty else float(close.iloc[0])

    perf_bench   = (prix / start_val - 1) * 100 if start_val else None
    gap          = perf_tot_pct - perf_bench if perf_bench is not None else None
    perf_bench_j = (prix - prev) / prev * 100 if prev else None
    return perf_bench, gap, prix, perf_bench_j

# =============================================================================
# ██████╗  BLOC 7 : MODULE FISCAL
# =============================================================================

def net_apres_impots(enveloppe: str, montant: float, val_poche: float, gain_poche: float) -> tuple:
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
# ██████╗  BLOC 8 : RÈGLES DÉCISIONNELLES
# =============================================================================

def evaluate_hydrogen(anrj) -> tuple:
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


def evaluate_em_asia(aasi) -> tuple:
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


def evaluate_sentinelles(data: dict) -> tuple:
    alerts = []
    rows   = []
    for name, tickers in SENTINELLES.items():
        info = None
        for tk in tickers:
            info = analyze_ticker(data, tk)
            if info:
                break
        alerte = ""
        if info and info["sma20"] and info["prix"] < info["sma20"]:
            alerte = "⚠️"
            alerts.append(name)
        rows.append({
            "Sentinelle":   name,
            "Prix":         f"{info['prix']:.2f}"   if info else "N/A",
            "SMA20":        f"{info['sma20']:.2f}"  if (info and info["sma20"]) else "N/A",
            "RSI":          f"{info['rsi']:.1f}"    if (info and info["rsi"])   else "N/A",
            "Alerte":       alerte,
        })
    msg = " | ".join([f"⚠️ {a} sous SMA20" for a in alerts]) if alerts else "✅ Sentinelles OK"
    col = "orange" if alerts else "green"
    return msg, col, rows


def decision_finale(h_col, a_col, s_col, h_msg, a_msg, s_msg) -> tuple:
    if "red" in (h_col, a_col):
        msg = h_msg if h_col == "red" else a_msg
        return f"🔴 ACTION REQUISE : {msg}", "red"
    if "orange" in (h_col, a_col, s_col):
        parts = []
        if h_col == "orange": parts.append(h_msg)
        if a_col == "orange": parts.append(a_msg)
        if s_col == "orange": parts.append(s_msg)
        return f"🟡 VIGILANCE : {' | '.join(parts)}", "orange"
    return "🟢 MAINTIEN GLOBAL — Portefeuille en ordre", "green"


def determine_phase(gap, anrj, aasi, proxies_a, proxies_em) -> tuple:
    if gap is None:
        return "⏳ Phase indéterminée — Données insuffisantes", "#374151"
    if gap < 0:
        return "📉 Phase 1 : Reconquête — Revenir à l'équilibre vs World AV", "#7F1D1D"
    signals = []
    if anrj and anrj["sma20"] and anrj["prix"] < anrj["sma20"]:
        signals.append("ANRJ<SMA20")
    if aasi and aasi["sma20"] and aasi["prix"] < aasi["sma20"]:
        signals.append("AASI<SMA20")
    all_proxies = {**proxies_a, **proxies_em}
    proxies_sous = sum(1 for v in all_proxies.values() if v and v.get("sma20") and v["prix"] < v["sma20"])
    if proxies_sous >= 2:
        signals.append(f"{proxies_sous} proxies<SMA20")
    if signals:
        return f"🔄 Phase 3 : Rotation — Sécuriser les gains ({', '.join(signals)})", "#78350F"
    return "🚀 Phase 2 : Alpha — Battre le MSCI World", "#14532D"


def compute_arbitrage(positions_calculees: list, valeur_totale: float, anrj, aasi) -> list:
    actions = []
    if valeur_totale <= 0:
        return actions
    anrj_val = next((p["valeur"] for p in positions_calculees if p["nom"] == "Global Hydrogen"), 0)
    aasi_val = next((p["valeur"] for p in positions_calculees if p["nom"] == "EM Asia"), 0)
    poids_sat = (anrj_val + aasi_val) / valeur_totale * 100

    if anrj and anrj["sma20"] and anrj["prix"] < anrj["sma20"] and anrj_val > 0:
        actions.append(f"🚨 Vendre **{anrj_val * 0.25:,.2f}€** d'ANRJ → renforcer MSCI World AV")
    if aasi and aasi["sma20"] and aasi["prix"] < aasi["sma20"] and aasi_val > 0:
        actions.append(f"🚨 Vendre **{aasi_val * 0.25:,.2f}€** d'AASI → renforcer MSCI World AV")
    if poids_sat > 45:
        excedent = (poids_sat - 45) / 100 * valeur_totale
        actions.append(f"ℹ️ Rééquilibrage : réduire satellites de **{excedent:,.2f}€** (poids actuel {poids_sat:.1f}%)")
    return actions

# =============================================================================
# ██████╗  BLOC 9 : CHARGEMENT DES DONNÉES
# =============================================================================

with st.spinner("🛰️ Chargement des données marché en cours…"):
    DATA = load_all_data()

if not DATA:
    st.error("❌ Aucune donnée récupérée. Vérifiez votre connexion internet.")
    st.stop()

# ── Calcul portefeuille ─────────────────────────────────────────────────────
ptf                 = compute_portfolio(positions_conf, capital_investi, bonus_fortuneo, DATA)
positions_calculees = ptf["positions"]
valeur_totale       = ptf["valeur_totale"]
val_env             = ptf["val_env"]
gain_env            = ptf["gain_env"]

# ── Benchmark ───────────────────────────────────────────────────────────────
perf_bench, gap, bench_prix, perf_bench_j = compute_benchmark(DATA, positions_conf, ptf["perf_tot_pct"])

# ── Analyses techniques ─────────────────────────────────────────────────────
anrj_info  = analyze_ticker(DATA, "ANRJ.PA")
aasi_info  = analyze_ticker(DATA, "AASI.PA")
proxies_a  = {tk: analyze_ticker(DATA, tk) for tk in PROXIES_ANRJ}
proxies_em = {tk: analyze_ticker(DATA, tk) for tk in PROXIES_AASI}

# ── Décisions ───────────────────────────────────────────────────────────────
h_msg, h_col = evaluate_hydrogen(anrj_info)
a_msg, a_col = evaluate_em_asia(aasi_info)
s_msg, s_col, sent_rows = evaluate_sentinelles(DATA)
decision_globale, decision_color = decision_finale(h_col, a_col, s_col, h_msg, a_msg, s_msg)
phase_text, phase_color = determine_phase(gap, anrj_info, aasi_info, proxies_a, proxies_em)
arbitrage_actions = compute_arbitrage(positions_calculees, valeur_totale, anrj_info, aasi_info)

# ── Macro ────────────────────────────────────────────────────────────────────
macro_info = {}
for sym in MACRO_TICKERS:
    df = DATA.get(sym, pd.DataFrame())
    if not df.empty and "Close" in df.columns:
        close = df["Close"].dropna()
        macro_info[sym] = {
            "prix": float(close.iloc[-1]) if not close.empty else None,
            "prev": float(close.iloc[-2]) if len(close) >= 2 else None,
        }
    else:
        macro_info[sym] = None

now = datetime.now(ZoneInfo("Europe/Paris"))

# =============================================================================
# ██████╗  BLOC 10 : HEADER
# =============================================================================

st.title("🛰️ Cockpit Décisionnel v3.0")
st.caption(f"Données temps réel · {now.strftime('%d/%m/%Y à %H:%M')} (Paris) · Cache 90s")

st.markdown(
    f'<div class="phase-banner" style="background-color:{phase_color}; color:white;">'
    f'{phase_text}</div>',
    unsafe_allow_html=True
)

# =============================================================================
# ██████╗  BLOC 11 : SECTION 1 — COMMAND CENTER
# =============================================================================

st.markdown("## 🚀 Command Center")

def sign_str(v):
    return "+" if v >= 0 else ""

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Valeur Totale</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-value">{valeur_totale:,.2f}€</div>', unsafe_allow_html=True)
    clr = "pos" if ptf["perf_j_eur"] >= 0 else "neg"
    st.markdown(
        f'<div class="kpi-delta-{clr}">'
        f'{sign_str(ptf["perf_j_eur"])}{ptf["perf_j_eur"]:,.2f}€ '
        f'({sign_str(ptf["perf_j_pct"])}{ptf["perf_j_pct"]:.2f}%) 24h</div>',
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Gain Net</div>', unsafe_allow_html=True)
    gn = ptf["gain_net"]
    g_clr = "#22C55E" if gn >= 0 else "#EF4444"
    st.markdown(f'<div class="kpi-value" style="color:{g_clr};">{sign_str(gn)}{gn:,.2f}€</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="small">Capital net : {ptf["capital_net"]:,.2f}€</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Performance Totale</div>', unsafe_allow_html=True)
    p = ptf["perf_tot_pct"]
    p_clr = "#22C55E" if p >= 0 else "#EF4444"
    st.markdown(f'<div class="kpi-value" style="color:{p_clr};">{sign_str(p)}{p:.2f}%</div>', unsafe_allow_html=True)
    if gap is not None:
        g_clr2 = "#22C55E" if gap >= 0 else "#EF4444"
        st.markdown(
            f'<div class="small">GAP vs World : <span style="color:{g_clr2};font-weight:700;">'
            f'{sign_str(gap)}{gap:.2f}%</span></div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Benchmark MSCI World</div>', unsafe_allow_html=True)
    if perf_bench is not None:
        pb_clr = "#22C55E" if perf_bench >= 0 else "#EF4444"
        st.markdown(f'<div class="kpi-value" style="color:{pb_clr};">{sign_str(perf_bench)}{perf_bench:.2f}%</div>', unsafe_allow_html=True)
        if perf_bench_j:
            pj_clr = "pos" if perf_bench_j >= 0 else "neg"
            st.markdown(f'<div class="kpi-delta-{pj_clr}">{sign_str(perf_bench_j)}{perf_bench_j:.2f}% 24h</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="kpi-value">N/A</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Tableau positions + donut
st.markdown("### 📊 Positions détaillées")
col_tab, col_pie = st.columns([3, 2])

with col_tab:
    rows = []
    for p in positions_calculees:
        perf_f = f"{sign_str(p['perf_pct'])}{p['perf_pct']:.2f}%" if p["perf_pct"] is not None else "N/A"
        vj_f   = f"{sign_str(p['var_jour_pct'])}{p['var_jour_pct']:.2f}%" if p["var_jour_pct"] else "–"
        vje_f  = f"{sign_str(p['var_jour_eur'])}{p['var_jour_eur']:,.2f}€" if p["var_jour_eur"] else "–"
        prix_f = f"{p['prix']:.3f}€" if p["prix"] else "N/A"
        rows.append({
            "Position":     p["nom"],
            "Env.":         p["enveloppe"],
            "Prix":         prix_f,
            "Valeur (€)":   f"{p['valeur']:,.2f}",
            "Perf.":        perf_f,
            "Var. 24h (%)": vj_f,
            "Var. 24h (€)": vje_f,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with col_pie:
    donut_data = [p for p in positions_calculees if p["valeur"] > 0]
    if donut_data:
        colors = ["#3D8BFF","#6366F1","#22C55E","#F97316","#FACC15"]
        fig = go.Figure(go.Pie(
            labels=[d["nom"] for d in donut_data],
            values=[d["valeur"] for d in donut_data],
            hole=0.55,
            textinfo="percent",
            marker=dict(colors=colors[:len(donut_data)], line=dict(color="#0B0E15", width=2)),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD5E1"), legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
            margin=dict(t=10, b=10, l=10, r=10), height=270,
        )
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# ██████╗  BLOC 12 : SECTION 2 — STRATÉGIE & ARBITRAGE
# =============================================================================

st.markdown("## 📈 Stratégie & Arbitrage")

v_class = {"red": "verdict-red", "orange": "verdict-orange", "green": "verdict-green"}.get(decision_color, "verdict-green")
st.markdown(f'<div class="{v_class}">{decision_globale}</div>', unsafe_allow_html=True)

def render_satellite(title, info, msg, col, proxies):
    card_border = {"red":"card-red","orange":"card-orange","green":"card-green","gray":"card"}.get(col,"card")
    badge_cls   = {"red":"badge-red","orange":"badge-orange","green":"badge-green","gray":"badge-gray"}.get(col,"badge-gray")
    badge_lbl   = {"red":"VENDRE","orange":"VIGILANCE","green":"MAINTENIR","gray":"N/A"}.get(col,"N/A")
    st.markdown(f'<div class="card {card_border}">', unsafe_allow_html=True)
    st.markdown(f"### {title}")
    if info:
        mc = st.columns(4)
        mc[0].metric("Prix",  f"{info['prix']:.2f}€")
        mc[1].metric("SMA20", f"{info['sma20']:.2f}€" if info["sma20"] else "–")
        mc[2].metric("SMA50", f"{info['sma50']:.2f}€" if info["sma50"] else "–")
        mc[3].metric("RSI",   f"{info['rsi']:.1f}"   if info["rsi"]   else "–")
        adx_v = info.get("adx")
        extra = f" · ADX {adx_v:.1f}" if adx_v else ""
        st.markdown(
            f'<span class="badge {badge_cls}">{badge_lbl}</span>'
            f'&nbsp;<span class="small">{msg}{extra}</span>',
            unsafe_allow_html=True
        )
    else:
        st.warning("Données indisponibles")
    st.markdown("**Proxies associés**")
    for tk, prx in proxies.items():
        if prx:
            icon = "🔴" if (prx["sma20"] and prx["prix"] < prx["sma20"]) else "🟢"
            sma_txt = f"SMA20 {prx['sma20']:.2f}" if prx["sma20"] else ""
            rsi_txt = f"RSI {prx['rsi']:.0f}" if prx["rsi"] else ""
            st.markdown(f"{icon} **{tk}** — {prx['prix']:.2f} | {sma_txt} | {rsi_txt}")
        else:
            st.markdown(f"⚪ **{tk}** — N/A")
    st.markdown('</div>', unsafe_allow_html=True)

col_h, col_a = st.columns(2)
with col_h:
    render_satellite("🔬 Hydrogène · ANRJ", anrj_info, h_msg, h_col, proxies_a)
with col_a:
    render_satellite("🌏 EM Asia · AASI",    aasi_info, a_msg, a_col, proxies_em)

# Poids + arbitrages
st.markdown('<div class="card">', unsafe_allow_html=True)
anrj_val  = next((p["valeur"] for p in positions_calculees if p["nom"] == "Global Hydrogen"), 0)
aasi_val  = next((p["valeur"] for p in positions_calculees if p["nom"] == "EM Asia"), 0)
poids_sat = (anrj_val + aasi_val) / valeur_totale * 100 if valeur_totale else 0

col_pw, col_act = st.columns([1, 2])
with col_pw:
    st.markdown("### ⚖️ Poids Satellites")
    delta_poids = poids_sat - 45
    st.metric("ANRJ + AASI", f"{poids_sat:.1f}%",
              delta=f"{sign_str(delta_poids)}{delta_poids:.1f}% vs limite 45%")
    bar_clr = "#EF4444" if poids_sat > 45 else "#22C55E"
    st.markdown(
        f'<div style="background:#1E2233;border-radius:8px;height:10px;">'
        f'<div style="background:{bar_clr};width:{min(poids_sat,100):.1f}%;height:10px;border-radius:8px;"></div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col_act:
    st.markdown("### 🤖 Arbitrages Recommandés")
    if arbitrage_actions:
        for act in arbitrage_actions:
            box = "alert-box" if "🚨" in act else "info-box"
            st.markdown(f'<div class="{box}">{act}</div>', unsafe_allow_html=True)
    else:
        st.success("✅ Aucun arbitrage requis — Maintien en l'état")

# Cible patrimoniale
st.markdown("---")
st.markdown("#### 🎯 Progression vers la Cible 94% World / 6% Or")
val_world = sum(p["valeur"] for p in positions_calculees if "MSCI World" in p["nom"])
val_gold  = sum(p["valeur"] for p in positions_calculees if "Or" in p["nom"])
pw_act = val_world / valeur_totale * 100 if valeur_totale else 0
pg_act = val_gold  / valeur_totale * 100 if valeur_totale else 0
cc1, cc2 = st.columns(2)
cc1.metric("MSCI World",  f"{pw_act:.1f}%", delta=f"{pw_act-94:.1f}% vs cible 94%")
cc2.metric("Or Physique", f"{pg_act:.1f}%", delta=f"{pg_act-6:.1f}% vs cible 6%")
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ██████╗  BLOC 13 : SECTION 3 — SENTINELLES & MACRO
# =============================================================================

st.markdown("## 🛰️ Sentinelles & Macro")
col_sent, col_macro = st.columns([3, 2])

with col_sent:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📡 Sentinelles")
    if "OK" in s_msg:
        st.success(s_msg)
    else:
        st.warning(s_msg)
    st.dataframe(pd.DataFrame(sent_rows), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_macro:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌍 Flash Macro")
    FMT = {"NQ=F": ".2f", "ES=F": ".2f", "^TNX": ".3f", "EURUSD=X": ".4f", "BZ=F": ".2f", "GC=F": ".2f"}
    SFX = {"^TNX": "%", "BZ=F": "$", "GC=F": "$", "NQ=F": "", "ES=F": "", "EURUSD=X": ""}
    for sym, label in MACRO_TICKERS.items():
        info = macro_info.get(sym)
        if info and info["prix"]:
            p_val = info["prix"]
            prev  = info["prev"]
            delta = f'{sign_str((p_val-prev)/prev*100)}{(p_val-prev)/prev*100:.2f}%' if prev and prev != 0 else None
            fmt   = FMT.get(sym, ".2f")
            sfx   = SFX.get(sym, "")
            st.metric(label, f"{p_val:{fmt}}{sfx}", delta=delta)
        else:
            st.metric(label, "N/A")
    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ██████╗  BLOC 14 : SECTION 4 — SIMULATEUR FISCAL
# =============================================================================

st.markdown("## 🧮 Simulateur Fiscal")

col_pea, col_av = st.columns(2)
with col_pea:
    st.markdown('<div class="card">', unsafe_allow_html=True)
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
    st.markdown('<div class="card">', unsafe_allow_html=True)
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
    max_val = float(max(val_env.get(env_sim, 0), 1000))
    montant_sim = st.slider("Montant à retirer (€)", 0.0, max_val, min(1000.0, max_val), step=100.0)

net_sim, avert_sim = net_apres_impots(env_sim, montant_sim, val_env.get(env_sim, 0), gain_env.get(env_sim, 0))
if avert_sim:
    st.warning(avert_sim)
elif montant_sim > 0:
    vp = val_env.get(env_sim, 0)
    gp = gain_env.get(env_sim, 0)
    ratio = gp / vp if vp else 0
    gain_sim   = montant_sim * ratio
    impots_sim = montant_sim - net_sim
    st.markdown(
        f'<div class="net-box" style="display:flex;gap:2.5rem;flex-wrap:wrap;align-items:center;">'
        f'<div><div class="kpi-label">Brut retiré</div><div class="kpi-value">{montant_sim:,.2f}€</div></div>'
        f'<div style="color:#8892AA;font-size:1.5rem;">→</div>'
        f'<div><div class="kpi-label">Part gains</div><div class="kpi-value" style="color:#FACC15;">{gain_sim:,.2f}€</div></div>'
        f'<div><div class="kpi-label">Impôts/PS</div><div class="kpi-value" style="color:#EF4444;">{impots_sim:,.2f}€</div></div>'
        f'<div><div class="kpi-label">Net perçu</div><div class="kpi-value" style="color:#22C55E;">{net_sim:,.2f}€</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# ██████╗  FOOTER
# =============================================================================

st.markdown("---")
col_f1, col_f2 = st.columns([4, 1])
with col_f1:
    st.caption("🛰️ Cockpit Décisionnel v3.0 · Outil personnel — Ne constitue pas un conseil en investissement")
with col_f2:
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()
