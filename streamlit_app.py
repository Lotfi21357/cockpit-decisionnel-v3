import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import warnings
warnings.filterwarnings("ignore")

# ---------- CONFIGURATION ----------
st.set_page_config(page_title="Cockpit Décisionnel", page_icon="🛰️", layout="centered", initial_sidebar_state="expanded")

# ---------- CSS DARK MODE PREMIUM ----------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .card { background-color: #1A1D24; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.3); border: 1px solid #2E3239; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #FFFFFF; }
    .kpi-label { font-size: 0.9rem; color: #B0B5BD; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.25rem; }
    .big-verdict { font-size: 1.4rem !important; font-weight: bold; text-align: center; padding: 1rem; border-radius: 12px; margin: 1rem 0; color: white; }
    .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; }
    .badge-red { background-color: #dc3545; color: white; }
    .badge-orange { background-color: #fd7e14; color: white; }
    .badge-green { background-color: #28a745; color: white; }
    .badge-blue { background-color: #1E90FF; color: white; }
    .badge-gray { background-color: #6c757d; color: white; }
    .net-result { background-color: #1E2F29; padding: 1rem; border-radius: 8px; margin-top: 1rem; border-left: 4px solid #28a745; }
    .stDataFrame { background-color: #1A1D24; color: #FFFFFF; }
    .stMetric label { color: #B0B5BD !important; }
    .stMetric .css-1xarl3l { color: #FFFFFF !important; }
    .stProgress > div > div { background-color: #28a745; }
    h2, h3, h4 { color: #FFFFFF !important; }
    .caption-text { color: #B0B5BD; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR DYNAMIQUE ----------
st.sidebar.title("⚙️ Gestion Dynamique")
capital_investi = st.sidebar.number_input("Capital investi (€)", value=13956.49, step=100.0)
bonus_fortuneo = st.sidebar.number_input("Bonus Fortuneo déjà perçu (€)", value=160.0, step=10.0)
st.sidebar.markdown("---")
st.sidebar.subheader("📦 Positions")

POSITIONS_BASE = [
    {"nom": "MSCI World AV",   "tickers": ["MWRD.PA", "MWRD.L", "IWDA.AS", "EUNL.DE"], "parts": 36.33,   "prm": 140.41,  "enveloppe": "AV"},
    {"nom": "MSCI World PEA",  "tickers": ["DCAM.PA"],                                "parts": 481.0,   "prm": 5.5937,  "enveloppe": "PEA"},
    {"nom": "Global Hydrogen", "tickers": ["ANRJ.PA"],                                "parts": 4.7701,  "prm": 707.55,  "enveloppe": "AV"},
    {"nom": "EM Asia",         "tickers": ["AASI.PA"],                                "parts": 40.8272, "prm": 49.96,   "enveloppe": "AV"},
    {"nom": "Or Physique",     "tickers": ["GOLD-EUR.PA", "CGLD.PA", "GOLD.PA"],      "parts": 4.5902,  "prm": 163.39,  "enveloppe": "AV"},
]

positions_dynamiques = []
for pos in POSITIONS_BASE:
    parts = st.sidebar.number_input(f"Parts {pos['nom']}", value=float(pos["parts"]), step=0.0001, key=f"parts_{pos['nom']}")
    prm = st.sidebar.number_input(f"PRM {pos['nom']}", value=float(pos["prm"]), step=0.0001, key=f"prm_{pos['nom']}")
    positions_dynamiques.append({"nom": pos["nom"], "tickers": pos["tickers"], "parts": parts, "prm": prm, "enveloppe": pos["enveloppe"]})
POSITIONS = positions_dynamiques

for pos in POSITIONS:
    if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0:
        pos["prm"] -= bonus_fortuneo / pos["parts"]

BENCHMARK_LABEL = "MSCI World AV"
EXTRA_TICKERS = ["CW8.PA", "^TNX", "DX-Y.NYB", "BZ=F", "BE", "NVDA", "^SOX"]
FUTURES = ["NQ=F", "ES=F", "GC=F", "EURUSD=X"]
SENTINELLES = {
    "TSMC":         ["TSM", "2330.TW"],
    "Samsung":      ["SSNLF", "005930.KS"],
    "SK Hynix":     ["HXSCL", "000660.KS"],
    "Air Liquide":  ["AI.PA"],
    "Bloom Energy": ["BE"],
}

DATE_DEBUT = datetime(2025, 9, 17)

# ---------- FONCTIONS UTILES ROBUSTES ----------
def to_float(val):
    if val is None: return None
    if isinstance(val, (int, float, np.floating, np.integer)): return float(val)
    if isinstance(val, pd.Series): return float(val.iloc[0]) if not val.empty else None
    if isinstance(val, np.ndarray): return float(val.flat[0]) if val.size > 0 else None
    try: return float(val)
    except: return None

def safe_last(series):
    if series is None: return None
    if isinstance(series, pd.DataFrame): series = series.squeeze()
    if isinstance(series, pd.Series):
        valid = series.dropna()
        return to_float(valid.iloc[-1]) if not valid.empty else None
    if isinstance(series, np.ndarray):
        valid = series[~np.isnan(series)]
        return to_float(valid[-1]) if valid.size > 0 else None
    return to_float(series)

@st.cache_data(ttl=3600, show_spinner=False)
def get_previous_close(ticker):
    try:
        info = yf.Ticker(ticker).info
        return to_float(info.get("previousClose"))
    except:
        return None

@st.cache_data(ttl=60, show_spinner=False)
def download_ticker(ticker, start, interval="1d"):
    try:
        df = yf.download(ticker, start=start, interval=interval, auto_adjust=False, progress=False, threads=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)   # aplatie les MultiIndex
        df = df.rename(columns=str)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                df[col] = np.nan
        df = df.dropna(subset=["Close"])
        return df
    except Exception as e:
        return pd.DataFrame()

def compute_sma(series, window):
    if series is None or len(series) < window: return None
    return series.rolling(window=window).mean()

def compute_rsi(series, period=14):
    """RSI Wilder institutionnel"""
    if series is None or len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_adx(df, period=14):
    """ADX institutionnel basé sur Wilder"""
    if df is None or len(df) < period + 5:
        return None
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    plus_dm = high.diff()
    minus_dm = low.diff() * -1
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di)) * 100
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx

@st.cache_data(ttl=60, show_spinner=False)
def load_all_data():
    start = datetime.now() - timedelta(days=500)
    all_tickers = set()
    for pos in POSITIONS:
        all_tickers.update(pos["tickers"])
    all_tickers.update(EXTRA_TICKERS)
    all_tickers.update(FUTURES)
    for tickers_list in SENTINELLES.values():
        all_tickers.update(tickers_list)
    data = {}
    for t in all_tickers:
        df = download_ticker(t, start)
        if not df.empty:
            data[t] = df
    return data

# ---------- CHARGEMENT DES DONNÉES ----------
data = load_all_data()
if not data:
    st.error("Aucune donnée récupérée.")
    st.stop()

# ---------- RÉCUPÉRATION PRIX PORTEFEUILLE ----------
ticker_used = {}
latest_prices = {}
prev_close_dict = {}
for pos in POSITIONS:
    used = None
    for t in pos["tickers"]:
        if t in data and not data[t].empty:
            used = t
            break
    ticker_used[pos["nom"]] = used
    if used:
        prix = safe_last(data[used]["Close"])
        latest_prices[used] = prix
        prev_close_dict[used] = get_previous_close(used)
    else:
        latest_prices[pos["nom"]] = None
        prev_close_dict[pos["nom"]] = None

# ---------- CALCULS PORTEFEUILLE ----------
positions_calculees = []
valeur_totale = 0.0
valeur_veille = 0.0
valeur_par_enveloppe = {"PEA": 0.0, "AV": 0.0}
gain_par_enveloppe = {"PEA": 0.0, "AV": 0.0}

for pos in POSITIONS:
    ticker = ticker_used[pos["nom"]]
    prix = latest_prices.get(ticker)
    prev_close = prev_close_dict.get(ticker)
    enveloppe = pos.get("enveloppe", "AV")
    if prix is None or np.isnan(prix):
        positions_calculees.append({"nom": pos["nom"], "prix": None, "valeur": 0.0, "perf": None, "var_jour": 0.0, "var_jour_euro": 0.0})
    else:
        valeur = pos["parts"] * prix
        perf = (prix - pos["prm"]) / pos["prm"] * 100
        if prev_close is not None and not np.isnan(prev_close) and prev_close != 0:
            var_jour = (prix - prev_close) / prev_close * 100
            var_jour_euro = (prix - prev_close) * pos["parts"]
        else:
            var_jour = 0.0
            var_jour_euro = 0.0
        positions_calculees.append({"nom": pos["nom"], "prix": prix, "valeur": valeur, "perf": perf, "var_jour": var_jour, "var_jour_euro": var_jour_euro})
        valeur_totale += valeur
        valeur_par_enveloppe[enveloppe] += valeur
        gain_par_enveloppe[enveloppe] += (prix - pos["prm"]) * pos["parts"]
        if prev_close is not None and not np.isnan(prev_close):
            valeur_veille += pos["parts"] * prev_close
        else:
            valeur_veille += valeur

capital_net = capital_investi - bonus_fortuneo
gain_net = valeur_totale - capital_net
perf_totale = (gain_net / capital_net) * 100 if capital_net != 0 else 0
perf_jour_euro = valeur_totale - valeur_veille
perf_jour_pct = (perf_jour_euro / valeur_veille * 100) if valeur_veille != 0 else 0.0

# ---------- BENCHMARK INTERNE ----------
perf_bench = None
gap = None
bench_price = bench_prev = None
bench_ticker = ticker_used.get(BENCHMARK_LABEL)
if bench_ticker and bench_ticker in data and not data[bench_ticker].empty:
    bench_series = data[bench_ticker]["Close"].squeeze()
    bench_price = safe_last(bench_series)
    bench_prev = get_previous_close(bench_ticker)
    if bench_price:
        try:
            start_val = bench_series.loc[DATE_DEBUT.strftime("%Y-%m-%d")]
            start_val = to_float(start_val.iloc[0]) if isinstance(start_val, pd.Series) else to_float(start_val)
        except KeyError:
            start_val = to_float(bench_series.iloc[0])
        if start_val and start_val > 0:
            perf_bench = (bench_price / start_val - 1) * 100
            gap = perf_totale - perf_bench

perf_bench_jour = None
gap_jour = None
if bench_price and bench_prev and bench_prev != 0:
    perf_bench_jour = (bench_price - bench_prev) / bench_prev * 100
    gap_jour = perf_jour_pct - perf_bench_jour if perf_jour_pct is not None else None

# ---------- INDICATEURS TECHNIQUES ----------
anrj_series = None
anrj_current = None
if "ANRJ.PA" in data and not data["ANRJ.PA"].empty:
    anrj_series = data["ANRJ.PA"]["Close"].squeeze()
    anrj_current = safe_last(anrj_series)
    anrj_sma20 = safe_last(compute_sma(anrj_series, 20)) if len(anrj_series) >= 20 else None
    anrj_sma50 = safe_last(compute_sma(anrj_series, 50)) if len(anrj_series) >= 50 else None
    anrj_rsi = safe_last(compute_rsi(anrj_series, 14)) if len(anrj_series) >= 15 else None
    anrj_ath30 = safe_last(anrj_series.rolling(30, min_periods=1).max()) if len(anrj_series) >= 20 else None
else:
    anrj_sma20 = anrj_sma50 = anrj_rsi = anrj_ath30 = None

aasi_current = None
if "AASI.PA" in data and not data["AASI.PA"].empty:
    aasi_series = data["AASI.PA"]["Close"].squeeze()
    aasi_current = safe_last(aasi_series)
    aasi_sma20 = safe_last(compute_sma(aasi_series, 20)) if len(aasi_series) >= 20 else None
    aasi_sma50 = safe_last(compute_sma(aasi_series, 50)) if len(aasi_series) >= 50 else None
else:
    aasi_sma20 = aasi_sma50 = None

# Sentinelles
sentinelle_info = {}
for name, tickers in SENTINELLES.items():
    prix = sma20 = None
    for t in tickers:
        if t in data and not data[t].empty:
            ts = data[t]["Close"].squeeze()
            prix = safe_last(ts)
            if len(ts) >= 20:
                sma20 = safe_last(compute_sma(ts, 20))
            break
    sentinelle_info[name] = {"prix": prix, "sma20": sma20}

# Macro existante
us10y = dxy = brent = None
if "^TNX" in data:
    raw = safe_last(data["^TNX"]["Close"].squeeze())
    us10y = raw / 10 if raw and raw > 20 else raw
if "DX-Y.NYB" in data:
    dxy = safe_last(data["DX-Y.NYB"]["Close"].squeeze())
if "BZ=F" in data:
    brent = safe_last(data["BZ=F"]["Close"].squeeze())

bloom_close = None
if "BE" in data and not data["BE"].empty:
    be_series = data["BE"]["Close"].squeeze()
    bloom_close = safe_last(be_series)

# ---------- MOTEUR DE RÉGIME DE MARCHÉ ----------
def market_regime():
    if perf_bench is None:
        return "UNKNOWN", "gray"
    if gap is not None and gap > 0 and (perf_bench is None or perf_bench > 5):
        return "RISK_ON", "green"
    if gap is not None and gap < 0:
        return "DEFENSIVE", "orange"
    if us10y and us10y > 4.7:
        return "TIGHT_FINANCIAL", "red"
    return "NEUTRAL", "blue"
regime, regime_color = market_regime()

# ---------- MOTEUR DES 4 PHASES ----------
def determine_phase():
    if gap is None:
        return "Indéterminée", "gray"
    weak_signals = False
    if anrj_current and anrj_sma20 and anrj_current < anrj_sma20:
        weak_signals = True
    if aasi_current and aasi_sma20 and aasi_current < aasi_sma20:
        weak_signals = True
    if gap < 0:
        return "PHASE 1 · Reconquête", "#dc3545"
    if gap > 0 and not weak_signals:
        return "PHASE 2 · Alpha", "#28a745"
    if gap > 0 and weak_signals:
        return "PHASE 3 · Rotation", "#fd7e14"
    return "PHASE 4 · Cible Patrimoniale", "#1E90FF"
phase_text, phase_color = determine_phase()

# ---------- RÈGLES DÉCISIONNELLES ----------
def evaluate_hydrogen():
    if anrj_current is None: return "⚠️ ANRJ manquant", "gray"
    if anrj_current < 706.06: return "🚨 STOP-LOSS : COUPURE 50% VERS WORLD", "red"
    if anrj_current > 812 and anrj_rsi and anrj_rsi > 68: return "💰 TAKE PROFIT 30%", "green"
    if anrj_ath30 and anrj_current < anrj_ath30 * 0.95: return "🔶 ALLÉGEMENT PRÉVENTIF", "orange"
    if anrj_sma20 and anrj_current < anrj_sma20: return "🔶 SOUS SMA20 – ARBITRAGE VERS WORLD", "orange"
    if anrj_sma50 and anrj_current > anrj_sma50: return "✅ MAINTIEN HYDROGÈNE", "green"
    return "ℹ️ SURVEILLANCE", "orange"

def evaluate_em_asia():
    if aasi_current is None: return "⚠️ AASI manquant", "gray"
    if aasi_current > 60.35:
        if aasi_series is not None:
            highest = aasi_series.rolling(50, min_periods=1).max()
            highest_val = safe_last(highest)
            if highest_val and aasi_current < highest_val * 0.92: return "🎯 TRAILING STOP -8%", "red"
        else: return "📈 TRAILING STOP ACTIF", "green"
    if aasi_sma20 and aasi_current < aasi_sma20: return "🔶 SOUS SMA20", "orange"
    if aasi_sma50 and aasi_current > aasi_sma50: return "✅ MAINTIEN EM ASIA", "green"
    return "ℹ️ SURVEILLANCE", "orange"

def evaluate_sentinelles():
    alerts = []
    for name, info in sentinelle_info.items():
        if info["prix"] and info["sma20"] and info["prix"] < info["sma20"]:
            alerts.append(f"⚠️ {name} sous SMA20")
    if "BE" in data:
        be_series = data["BE"]["Close"].squeeze()
        if len(be_series) >= 3:
            be_latest = safe_last(be_series)
            be_2d_ago = safe_last(be_series.iloc[:-2]) if len(be_series) > 2 else None
            if be_latest and be_2d_ago and (be_latest / be_2d_ago - 1) < -0.03: alerts.append("⚠️ Bloom Energy -3% en 48h")
    if us10y and us10y > 4.60: alerts.append("⚠️ US10Y > 4.60%")
    if dxy and dxy > 102: alerts.append("⚠️ DXY > 102")
    return " | ".join(alerts) if alerts else "✅ Sentinelles OK", "orange" if alerts else "green"

def decision_finale():
    h_msg, h_col = evaluate_hydrogen()
    a_msg, a_col = evaluate_em_asia()
    s_msg, s_col = evaluate_sentinelles()
    if "red" in [h_col, a_col]:
        msg = h_msg if h_col == "red" else a_msg
        return f"🔴 ACTION REQUISE : {msg}", "red"
    if "orange" in [h_col, a_col, s_col]:
        parties = []
        if h_col == "orange": parties.append(h_msg)
        if a_col == "orange": parties.append(a_msg)
        if s_col == "orange": parties.append(s_msg)
        return f"🟡 VIGILANCE : {' | '.join(parties)}", "orange"
    return "🟢 MAINTIEN GLOBAL", "green"

decision_globale, decision_color = decision_finale()

# ---------- ARBITRAGE INTELLIGENT ----------
valeur_anrj = next((p["valeur"] for p in positions_calculees if p["nom"] == "Global Hydrogen"), 0)
valeur_aasi = next((p["valeur"] for p in positions_calculees if p["nom"] == "EM Asia"), 0)
poids_satellite = (valeur_anrj + valeur_aasi) / valeur_totale * 100 if valeur_totale else 0

def arbitrage_signal():
    actions = []
    satellites = [
        ("Global Hydrogen", anrj_current, anrj_sma20),
        ("EM Asia", aasi_current, aasi_sma20)
    ]
    for nom, prix, sma20 in satellites:
        ligne = next((p for p in positions_calculees if p["nom"] == nom), None)
        if ligne is None or ligne["valeur"] <= 0:
            continue
        valeur = ligne["valeur"]
        trigger = False
        if prix and sma20 and prix < sma20:
            trigger = True
        if gap and gap > 5:
            trigger = True
        if trigger:
            montant = min(valeur * 0.25, max(0, (poids_satellite - 45) / 100 * valeur_totale))
            if montant > 50:
                actions.append(f"🚨 ACTION : Vendre {montant:,.0f}€ de {nom} pour acheter du World AV")
    return actions

arbitrage_actions = arbitrage_signal()

# ---------- MODULE FISCAL ----------
def calculer_net_fiscal(enveloppe, montant, val_poche, gain_poche):
    if montant <= 0: return 0.0, ""
    if montant > val_poche: return 0.0, "Montant supérieur à la valeur"
    ratio = gain_poche / val_poche if val_poche else 0
    gain_retrait = montant * ratio
    aujourdhui = datetime.now(ZoneInfo("Europe/Paris"))
    if enveloppe == "PEA":
        if aujourdhui < datetime(2031, 4, 1, tzinfo=ZoneInfo("Europe/Paris")):
            return 0.0, "⚠️ Retrait PEA impossible avant le 01/04/2031"
        impots = 0.172 * gain_retrait
        return montant - impots, ""
    elif enveloppe == "AV":
        if aujourdhui < datetime(2033, 9, 17, tzinfo=ZoneInfo("Europe/Paris")):
            impots = 0.30 * gain_retrait
            return montant - impots, ""
        else:
            abattement = 9200
            ps = 0.172 * gain_retrait
            ir = 0.128 * max(0, gain_retrait - abattement)
            return montant - ps - ir, ""
    return 0.0, ""

# ---------- INTERFACE PREMIUM ----------
now = datetime.now(ZoneInfo("Europe/Paris"))
st.title("🛰️ Cockpit Décisionnel v3.0 Expert")
st.caption(f"Données en temps réel – {now.strftime('%d/%m/%Y %H:%M')} (heure de Paris)")

# Bandeau régime de marché + phase
st.markdown(f"""
<div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
    <div style="background-color: {phase_color}; color: white; padding: 0.5rem 1rem; border-radius: 8px; font-weight: bold;">
        {phase_text}
    </div>
    <div style="background-color: {regime_color}; color: white; padding: 0.5rem 1rem; border-radius: 8px; font-weight: bold;">
        {regime}
    </div>
</div>
""", unsafe_allow_html=True)

# SECTION 1 : COMMAND CENTER
st.markdown("## 🚀 Command Center")
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="kpi-label">Valeur Totale</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{valeur_totale:,.2f}€</div>', unsafe_allow_html=True)
        st.caption(f"{perf_jour_euro:+,.2f}€ ({perf_jour_pct:+.2f}%) 24h")
    with c2:
        st.markdown('<div class="kpi-label">Gain Net</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{gain_net:+,.2f}€</div>', unsafe_allow_html=True)
        st.caption(f"Capital net : {capital_net:,.2f}€")
    with c3:
        st.markdown('<div class="kpi-label">Performance Totale</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{perf_totale:+.2f}%</div>', unsafe_allow_html=True)
        st.caption(f"{perf_jour_pct:+.2f}% ({perf_jour_euro:+,.2f}€) 24h")
    st.markdown('</div>', unsafe_allow_html=True)

col_bench, col_donut = st.columns([1, 1])
with col_bench:
    st.markdown("### 📊 Benchmark vs " + BENCHMARK_LABEL)
    if perf_bench is not None:
        st.metric("Performance " + BENCHMARK_LABEL, f"{perf_bench:+.2f}%",
                  delta=f"{perf_bench_jour:+.2f}% 24h" if perf_bench_jour else None)
        st.metric("GAP vs World AV", f"{gap:+.2f}%",
                  delta=f"{gap_jour:+.2f}% 24h" if gap_jour else None)
        if gap is not None:
            gap_norm = max(0, min(1, (gap+5)/10))
            st.progress(gap_norm, text=f"Écart : {gap:+.2f}%")
    else:
        st.info("Benchmark indisponible")

with col_donut:
    st.markdown("### 🍩 Répartition")
    donut_data = [p for p in positions_calculees if p["valeur"] > 0]
    if donut_data:
        fig = px.pie(donut_data, values='valeur', names='nom', hole=0.4)
        fig.update_traces(textinfo='percent+label')
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300,
                          paper_bgcolor='#1A1D24', font=dict(color='#FFFFFF'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée")

# SECTION 2 : STRATÉGIE & ARBITRAGE
st.markdown("## 📈 Stratégie & Arbitrage")
st.markdown(f'<div class="big-verdict" style="background-color:{"#dc3545" if decision_color=="red" else "#fd7e14" if decision_color=="orange" else "#28a745"};">{decision_globale}</div>', unsafe_allow_html=True)

colH, colA = st.columns(2)
with colH:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔎 Hydrogène (ANRJ)")
    if anrj_current:
        d1, d2, d3 = st.columns(3)
        d1.metric("Prix", f"{anrj_current:.2f}€")
        d2.metric("SMA20", f"{anrj_sma20:.2f}€" if anrj_sma20 else "N/A")
        d3.metric("RSI", f"{anrj_rsi:.1f}" if anrj_rsi else "N/A")
        msg, col = evaluate_hydrogen()
        status, badge_color = ("Vendre", "red") if "STOP" in msg else ("Surveillance", "orange") if "SOUS" in msg else ("Maintenir", "green")
        st.markdown(f'<span class="badge badge-{badge_color}">{status}</span>', unsafe_allow_html=True)
        st.caption(msg)
    else:
        st.warning("ANRJ indisponible")
    st.markdown('</div>', unsafe_allow_html=True)

with colA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌏 EM Asia (AASI)")
    if aasi_current:
        d1, d2 = st.columns(2)
        d1.metric("Prix", f"{aasi_current:.2f}€")
        d2.metric("SMA20", f"{aasi_sma20:.2f}€" if aasi_sma20 else "N/A")
        msg, col = evaluate_em_asia()
        status, badge_color = ("Vendre", "red") if "TRAILING" in msg else ("Surveillance", "orange") if "SOUS" in msg else ("Maintenir", "green")
        st.markdown(f'<span class="badge badge-{badge_color}">{status}</span>', unsafe_allow_html=True)
        st.caption(msg)
    else:
        st.warning("AASI indisponible")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ⚖️ Poids Satellites & Arbitrage")
st.write(f"ANRJ + EM Asia : {poids_satellite:.1f}% du portefeuille")
st.progress(min(poids_satellite/100, 1.0))
if arbitrage_actions:
    for act in arbitrage_actions:
        st.markdown(f"- {act}")
st.markdown('</div>', unsafe_allow_html=True)

# SECTION 3 : SENTINELLES & FLASH FUTURES
st.markdown("## 🛰️ Sentinelles & Futures")
colS, colM = st.columns([2, 2])
with colS:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📡 Sentinelles")
    s_msg, s_col = evaluate_sentinelles()
    if s_msg != "✅ Sentinelles OK":
        st.warning(s_msg)
    else:
        st.success(s_msg)
    sentinel_rows = []
    for name, info in sentinelle_info.items():
        sentinel_rows.append({"Nom": name, "Prix": f"{info['prix']:.2f}" if info['prix'] else "N/A",
                              "SMA20": f"{info['sma20']:.2f}" if info['sma20'] else "N/A",
                              "Alerte": "⚠️" if (info['prix'] and info['sma20'] and info['prix'] < info['sma20']) else ""})
    if sentinel_rows:
        st.dataframe(pd.DataFrame(sentinel_rows), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

with colM:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ⚡ Flash Futures")
    macro_items = [
        ("Nasdaq Futures", "NQ=F"),
        ("S&P Futures", "ES=F"),
        ("US 10Y", "^TNX"),
        ("EUR/USD", "EURUSD=X"),
        ("Brent", "BZ=F"),
        ("Gold", "GC=F")
    ]
    rows = [st.columns(3), st.columns(3)]  # 2 rangées de 3
    for idx, (label, ticker) in enumerate(macro_items):
        row_idx = idx // 3
        col_idx = idx % 3
        with rows[row_idx][col_idx]:
            if ticker in data:
                close = safe_last(data[ticker]["Close"].squeeze())
                prev = get_previous_close(ticker)
                delta = ((close - prev) / prev * 100) if close and prev else None
                st.metric(label, f"{close:.2f}" if close else "N/A", delta=f"{delta:+.2f}%" if delta else None)
            else:
                st.metric(label, "N/A")
    st.markdown('</div>', unsafe_allow_html=True)

# SECTION 4 : SIMULATEUR FISCAL
st.markdown("## 🧮 Simulateur Fiscal")
col_pea, col_av = st.columns(2)
with col_pea:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🏦 PEA")
    val = valeur_par_enveloppe["PEA"]
    gain = gain_par_enveloppe["PEA"]
    net, avert = calculer_net_fiscal("PEA", val, val, gain)
    st.metric("Solde Net Estimé", f"{net:,.2f}€")
    if avert: st.caption(avert)
    st.markdown('</div>', unsafe_allow_html=True)
with col_av:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🛡️ Assurance-Vie")
    val = valeur_par_enveloppe["AV"]
    gain = gain_par_enveloppe["AV"]
    net, avert = calculer_net_fiscal("AV", val, val, gain)
    st.metric("Solde Net Estimé", f"{net:,.2f}€")
    if avert: st.caption(avert)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 💸 Simuler un retrait")
c1, c2 = st.columns(2)
with c1:
    montant_retrait = st.number_input("Montant à retirer (€)", min_value=0.0, value=1000.0, step=100.0)
with c2:
    enveloppe_retrait = st.selectbox("Enveloppe", ["PEA", "AV"])
net_retrait, avert_retrait = calculer_net_fiscal(enveloppe_retrait, montant_retrait,
                                                 valeur_par_enveloppe.get(enveloppe_retrait, 0.0),
                                                 gain_par_enveloppe.get(enveloppe_retrait, 0.0))
if avert_retrait:
    st.warning(avert_retrait)
else:
    st.markdown(f"""
    <div class="net-result">
        <span style="font-weight:bold; color:#28a745;">Montant net après impôts :</span>
        <span style="font-size:1.5rem; font-weight:bold; color:#FFFFFF; margin-left:0.5rem;">{net_retrait:,.2f}€</span>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("Cockpit Décisionnel · Ne constitue pas un conseil en investissement")
