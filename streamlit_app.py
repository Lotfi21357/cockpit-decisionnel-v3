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
    .card { background-color: #1A1D24; border-radius:12px; padding:1.2rem; margin-bottom:1rem; box-shadow:0 2px 8px rgba(0,0,0,0.3); border:1px solid #2E3239; }
    .kpi-value { font-size:2rem; font-weight:700; color:#FFFFFF; }
    .kpi-label { font-size:0.9rem; color:#B0B5BD; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:0.25rem; }
    .big-verdict { font-size:1.4rem !important; font-weight:bold; text-align:center; padding:1rem; border-radius:12px; margin:1rem 0; color:white; }
    .badge { display:inline-block; padding:0.25rem 0.75rem; border-radius:20px; font-size:0.8rem; font-weight:600; text-transform:uppercase; }
    .badge-red { background-color:#dc3545; color:white; }
    .badge-orange { background-color:#fd7e14; color:white; }
    .badge-green { background-color:#28a745; color:white; }
    .badge-gray { background-color:#6c757d; color:white; }
    .small-text { font-size:0.85rem; color:#B0B5BD; }
    .stDataFrame { background-color:#1A1D24; color:#FFFFFF; }
    .stMetric label { color:#B0B5BD !important; }
    .stMetric .css-1xarl3l { color:#FFFFFF !important; }
    .stProgress > div > div { background-color:#28a745; }
    .net-result { background-color:#1E2F29; padding:1rem; border-radius:8px; margin-top:1rem; border-left:4px solid #28a745; }
    .caption-text { color:#B0B5BD; }
    h2, h3, h4 { color:#FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
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
    {"nom": "Or Physique",     "tickers": ["SGLD.PA", "CGLD.PA", "GOLD.PA"],          "parts": 4.5902,  "prm": 163.39,  "enveloppe": "AV"},
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
EXTRA_TICKERS = ["CW8.PA", "^TNX", "BZ=F", "BE", "NVDA", "^SOX"]
PROXIES_ANRJ = ["PLUG", "BE", "NEL.OL"]
PROXIES_AASI = ["TSM", "005930.KS", "AAXJ"]
FUTURES = ["NQ=F", "ES=F", "EURUSD=X", "GC=F"]

SENTINELLES = {
    "TSMC": ["TSM", "2330.TW"],
    "Samsung": ["005930.KS", "SSNLF"],
    "SK Hynix": ["000660.KS", "HXSCL"],
    "Air Liquide": ["AI.PA"],
    "Bloom Energy": ["BE"],
}

DATE_DEBUT = datetime(2025, 9, 17)

# ---------- FONCTIONS UTILES ----------
@st.cache_data(ttl=60, show_spinner=False)
def get_previous_close(ticker):
    try:
        info = yf.Ticker(ticker).info
        return float(info.get("previousClose")) if info.get("previousClose") else None
    except:
        return None

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

def download_ticker(ticker, start):
    """Télécharge et retourne un DataFrame propre (sans MultiIndex, colonnes simples)."""
    try:
        df = yf.download(ticker, start=start, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        # Si yfinance renvoie un MultiIndex (un seul ticker), on aplatit
        if isinstance(df.columns, pd.MultiIndex):
            # On garde le premier niveau (Close, High, Low, etc.) et on supprime le nom du ticker
            df.columns = df.columns.droplevel(1)
        # Au cas où ce serait une Series, on la convertit en DataFrame
        if isinstance(df, pd.Series):
            df = df.to_frame(name='Close')
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def load_all_data():
    start = datetime.now() - timedelta(days=500)
    data = {}
    all_pos_tickers = [t for pos in POSITIONS for t in pos["tickers"]]
    all_tickers = all_pos_tickers + EXTRA_TICKERS + [t for prox in [PROXIES_ANRJ, PROXIES_AASI] for t in prox] + FUTURES
    for name, tickers in SENTINELLES.items():
        all_tickers.extend(tickers)
    all_tickers = list(set(all_tickers))

    for t in all_tickers:
        df = download_ticker(t, start)
        if not df.empty:
            data[t] = df
    return data

def compute_sma(series, window):
    if series is None or len(series) < window: return None
    return series.rolling(window=window).mean()

def compute_rsi(series, period=14):
    if series is None or len(series) < period+1: return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    avg_loss.replace(0, np.nan, inplace=True)
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_adx(high, low, close, period=14):
    """Simplifié: renvoie l'ADX lissé"""
    if len(close) < period+1:
        return None
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()
    return safe_last(adx)

def analyze_proxy(ticker, data_dict):
    if ticker not in data_dict or data_dict[ticker].empty:
        return None
    # Convertir en DataFrame standard (même si c'était une Series)
    df = pd.DataFrame(data_dict[ticker].copy())
    # S'assurer que 'Close' existe
    if 'Close' not in df.columns:
        return None
    close = df['Close'].squeeze()
    if len(close) < 20:
        return None
    sma20 = safe_last(compute_sma(close, 20))
    rsi = safe_last(compute_rsi(close, 14))
    # ADX seulement si High/Low disponibles
    adx = None
    if 'High' in df.columns and 'Low' in df.columns:
        high = df['High'].squeeze()
        low = df['Low'].squeeze()
        adx = compute_adx(high, low, close)
    return {"prix": safe_last(close), "sma20": sma20, "rsi": rsi, "adx": adx}

# ---------- CHARGEMENT ----------
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

# ---------- CALCUL PORTEFEUILLE ----------
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
        if prev_close and not np.isnan(prev_close) and prev_close != 0:
            var_jour = (prix - prev_close) / prev_close * 100
            var_jour_euro = (prix - prev_close) * pos["parts"]
        else:
            var_jour = 0.0
            var_jour_euro = 0.0
        positions_calculees.append({"nom": pos["nom"], "prix": prix, "valeur": valeur, "perf": perf, "var_jour": var_jour, "var_jour_euro": var_jour_euro})
        valeur_totale += valeur
        valeur_par_enveloppe[enveloppe] += valeur
        gain_par_enveloppe[enveloppe] += (prix - pos["prm"]) * pos["parts"]
        if prev_close and not np.isnan(prev_close):
            valeur_veille += pos["parts"] * prev_close
        else:
            valeur_veille += valeur

capital_net = capital_investi - bonus_fortuneo
gain_net = valeur_totale - capital_net
perf_totale = (gain_net / capital_net) * 100 if capital_net != 0 else 0
perf_jour_euro = valeur_totale - valeur_veille
perf_jour_pct = (perf_jour_euro / valeur_veille * 100) if valeur_veille != 0 else 0.0

# ---------- BENCHMARK ----------
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
anrj_current = anrj_sma20 = anrj_sma50 = anrj_rsi = anrj_ath30 = None
if "ANRJ.PA" in data and not data["ANRJ.PA"].empty:
    anrj_series = data["ANRJ.PA"]["Close"].squeeze()
    anrj_current = safe_last(anrj_series)
    if len(anrj_series) >= 20:
        anrj_sma20 = safe_last(compute_sma(anrj_series, 20))
        anrj_sma50 = safe_last(compute_sma(anrj_series, 50))
        anrj_rsi = safe_last(compute_rsi(anrj_series, 14))
        anrj_ath30 = safe_last(anrj_series.rolling(30, min_periods=1).max())

aasi_current = aasi_sma20 = aasi_sma50 = None
if "AASI.PA" in data and not data["AASI.PA"].empty:
    aasi_series = data["AASI.PA"]["Close"].squeeze()
    aasi_current = safe_last(aasi_series)
    if len(aasi_series) >= 20:
        aasi_sma20 = safe_last(compute_sma(aasi_series, 20))
        aasi_sma50 = safe_last(compute_sma(aasi_series, 50))

# Proxies analyse
proxies_anrj_data = {t: analyze_proxy(t, data) for t in PROXIES_ANRJ}
proxies_aasi_data = {t: analyze_proxy(t, data) for t in PROXIES_AASI}

# ---------- SENTINELLES ----------
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

# ---------- MACRO (FUTURES) ----------
macro_data = {}
for sym in ["NQ=F", "ES=F", "GC=F", "BZ=F", "^TNX", "EURUSD=X"]:
    if sym in data and not data[sym].empty:
        price = safe_last(data[sym]["Close"].squeeze())
        prev = get_previous_close(sym)
        macro_data[sym] = {"price": price, "prev_close": prev}
    else:
        macro_data[sym] = None

# ---------- RÈGLES DÉCISIONNELLES ----------
def evaluate_hydrogen():
    if anrj_current is None: return "⚠️ ANRJ manquant", "gray"
    if anrj_current < 706.06: return "🚨 STOP-LOSS", "red"
    if anrj_current > 812 and anrj_rsi and anrj_rsi > 68: return "💰 TAKE PROFIT 30%", "green"
    if anrj_ath30 and anrj_current < anrj_ath30 * 0.95: return "🔶 ALLÉGEMENT PRÉVENTIF", "orange"
    if anrj_sma20 and anrj_current < anrj_sma20: return "🔶 SOUS SMA20", "orange"
    if anrj_sma50 and anrj_current > anrj_sma50: return "✅ MAINTIEN", "green"
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
    if aasi_sma50 and aasi_current > aasi_sma50: return "✅ MAINTIEN", "green"
    return "ℹ️ SURVEILLANCE", "orange"

def evaluate_sentinelles():
    alerts = []
    for name, info in sentinelle_info.items():
        if info["prix"] and info["sma20"] and info["prix"] < info["sma20"]:
            alerts.append(f"⚠️ {name} sous SMA20")
    for name, prox in [("Hydrogène", proxies_anrj_data), ("EM Asia", proxies_aasi_data)]:
        count_under = sum(1 for v in prox.values() if v and v.get("sma20") and v["prix"] < v["sma20"])
        if count_under >= 2:
            alerts.append(f"⚠️ {name} : {count_under}/3 proxies sous SMA20")
    return " | ".join(alerts) if alerts else "✅ Sentinelles OK", "orange" if alerts else "green"

def decision_finale():
    h_msg, h_col = evaluate_hydrogen()
    a_msg, a_col = evaluate_em_asia()
    s_msg, s_col = evaluate_sentinelles()
    if "red" in [h_col, a_col]:
        msg = h_msg if h_col == "red" else a_msg
        return f"🔴 ACTION REQUISE : {msg}", "red"
    if "orange" in [h_col, a_col, s_col]:
        parts = []
        if h_col=="orange": parts.append(h_msg)
        if a_col=="orange": parts.append(a_msg)
        if s_col=="orange": parts.append(s_msg)
        return f"🟡 VIGILANCE : {' | '.join(parts)}", "orange"
    return "🟢 MAINTIEN GLOBAL", "green"

decision_globale, decision_color = decision_finale()

# ---------- PHASES ----------
def determine_phase(gap):
    if gap is None: return "Données insuffisantes", "#6c757d"
    if gap < 0:
        return "Phase 1 : Reconquête – Revenir à l'équilibre vs World AV", "#dc3545"
    else:
        signals = []
        if anrj_sma20 and anrj_current and anrj_current < anrj_sma20:
            signals.append("ANRJ sous SMA20")
        if aasi_sma20 and aasi_current and aasi_current < aasi_sma20:
            signals.append("AASI sous SMA20")
        for prox in proxies_anrj_data.values():
            if prox and prox.get("sma20") and prox["prix"] < prox["sma20"]:
                signals.append(f"Proxy {prox['prix']:.2f}<SMA20")
                break
        for prox in proxies_aasi_data.values():
            if prox and prox.get("sma20") and prox["prix"] < prox["sma20"]:
                signals.append(f"Proxy {prox['prix']:.2f}<SMA20")
                break
        if signals:
            return "Phase 3 : Rotation – Sécuriser les gains (signaux faibles)", "#fd7e14"
        return "Phase 2 : Alpha – Battre le World", "#28a745"

phase_text, phase_color = determine_phase(gap)

# ---------- ARBITRAGE AUTOMATIQUE ----------
def compute_arbitrage():
    actions = []
    if gap is None: return actions
    poids = poids_satellite if 'poids_satellite' in locals() else 0
    for pos_info in [{"nom": "Global Hydrogen", "valeur": valeur_anrj},
                     {"nom": "EM Asia", "valeur": valeur_aasi}]:
        if pos_info["valeur"] <= 0: continue
        if pos_info["nom"] == "Global Hydrogen" and anrj_sma20 and anrj_current and anrj_current < anrj_sma20:
            sell_amount = pos_info["valeur"] * 0.25
            actions.append(f"🚨 ACTION : Vendre {sell_amount:,.2f}€ de {pos_info['nom']} pour acheter du MSCI World AV")
        if pos_info["nom"] == "EM Asia" and aasi_sma20 and aasi_current and aasi_current < aasi_sma20:
            sell_amount = pos_info["valeur"] * 0.25
            actions.append(f"🚨 ACTION : Vendre {sell_amount:,.2f}€ de {pos_info['nom']} pour acheter du MSCI World AV")
    if poids > 45:
        excedent = (poids - 45) / 100 * valeur_totale
        actions.append(f"ℹ️ RÉÉQUILIBRAGE : Réduire satellites de {excedent:,.2f}€ pour rester sous 45%")
    return actions

arbitrage_actions = compute_arbitrage()

# ---------- MODULE FISCAL ----------
def calculer_net_fiscal(enveloppe, montant, val_poche, gain_poche):
    if montant <= 0: return 0.0, ""
    if montant > val_poche: return 0.0, "Montant supérieur à la valeur"
    ratio = gain_poche / val_poche if val_poche else 0
    gain_retrait = montant * ratio
    aujourdhui = datetime.now(ZoneInfo("Europe/Paris"))
    if enveloppe == "PEA":
        if aujourdhui < datetime(2031,4,1, tzinfo=ZoneInfo("Europe/Paris")):
            return 0.0, "⚠️ Retrait PEA impossible avant le 01/04/2031"
        impots = 0.172 * gain_retrait
        return montant - impots, ""
    elif enveloppe == "AV":
        if aujourdhui < datetime(2033,9,17, tzinfo=ZoneInfo("Europe/Paris")):
            impots = 0.30 * gain_retrait
            return montant - impots, ""
        else:
            abattement = 9200
            ps = 0.172 * gain_retrait
            ir = 0.128 * max(0, gain_retrait - abattement)
            return montant - ps - ir, ""
    return 0.0, ""

# ---------- INTERFACE ----------
now = datetime.now(ZoneInfo("Europe/Paris"))
st.title("🛰️ Cockpit Décisionnel v2.0 Expert")
st.caption(f"Données en temps réel – {now.strftime('%d/%m/%Y %H:%M')} (heure de Paris)")

st.markdown(f"""
<div style="background-color:{phase_color}; color:white; padding:0.75rem; border-radius:8px; text-align:center; font-weight:bold; margin-bottom:1rem;">
    {phase_text}
</div>
""", unsafe_allow_html=True)

# SECTION 1
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

col_b, col_d = st.columns([1, 1])
with col_b:
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
with col_d:
    st.markdown("### 🍩 Répartition")
    donut_data = [p for p in positions_calculees if p["valeur"] > 0]
    if donut_data:
        fig = px.pie(donut_data, values='valeur', names='nom', hole=0.4)
        fig.update_traces(textinfo='percent+label')
        fig.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=300,
                          paper_bgcolor='#1A1D24', font=dict(color='#FFFFFF'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée")

# SECTION 2
st.markdown("## 📈 Stratégie & Arbitrage")
st.markdown(f'<div class="big-verdict" style="background-color:{"#dc3545" if decision_color=="red" else "#fd7e14" if decision_color=="orange" else "#28a745"};">{decision_globale}</div>', unsafe_allow_html=True)

colH, colA = st.columns(2)
with colH:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔎 Hydrogène (ANRJ)")
    if anrj_current:
        c1,c2,c3 = st.columns(3)
        c1.metric("Prix", f"{anrj_current:.2f}€")
        c2.metric("SMA20", f"{anrj_sma20:.2f}€" if anrj_sma20 else "N/A")
        c3.metric("RSI", f"{anrj_rsi:.1f}" if anrj_rsi else "N/A")
        msg, col = evaluate_hydrogen()
        status, bcol = ("Vendre", "red") if "STOP" in msg or "TAKE PROFIT" in msg else ("Surveillance", "orange") if "SOUS" in msg else ("Maintenir", "green")
        st.markdown(f'<span class="badge badge-{bcol}">{status}</span>', unsafe_allow_html=True)
        st.caption(msg)
        st.markdown("**Proxies**")
        for name, prox in proxies_anrj_data.items():
            if prox:
                st.write(f"{name}: {prox['prix']:.2f} | SMA20: {prox['sma20']:.2f}" if prox['sma20'] else f"{name}: {prox['prix']:.2f}")
    else:
        st.warning("ANRJ indisponible")
    st.markdown('</div>', unsafe_allow_html=True)

with colA:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌏 EM Asia (AASI)")
    if aasi_current:
        c1,c2 = st.columns(2)
        c1.metric("Prix", f"{aasi_current:.2f}€")
        c2.metric("SMA20", f"{aasi_sma20:.2f}€" if aasi_sma20 else "N/A")
        msg, col = evaluate_em_asia()
        status, bcol = ("Vendre", "red") if "TRAILING" in msg else ("Surveillance", "orange") if "SOUS" in msg else ("Maintenir", "green")
        st.markdown(f'<span class="badge badge-{bcol}">{status}</span>', unsafe_allow_html=True)
        st.caption(msg)
        st.markdown("**Proxies**")
        for name, prox in proxies_aasi_data.items():
            if prox:
                st.write(f"{name}: {prox['prix']:.2f} | SMA20: {prox['sma20']:.2f}" if prox['sma20'] else f"{name}: {prox['prix']:.2f}")
    else:
        st.warning("AASI indisponible")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ⚖️ Poids Satellites & Arbitrage")
valeur_anrj = next((p["valeur"] for p in positions_calculees if p["nom"]=="Global Hydrogen"), 0)
valeur_aasi = next((p["valeur"] for p in positions_calculees if p["nom"]=="EM Asia"), 0)
poids_satellite = (valeur_anrj + valeur_aasi) / valeur_totale * 100 if valeur_totale else 0
st.write(f"ANRJ + EM Asia : {poids_satellite:.1f}% du portefeuille")
st.progress(min(poids_satellite/100, 1.0))
if arbitrage_actions:
    for act in arbitrage_actions:
        st.markdown(f"- {act}")
st.markdown('</div>', unsafe_allow_html=True)

# SECTION 3
st.markdown("## 🛰️ Sentinelles & Macro Futures")
colS, colM = st.columns([2, 1])
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
    st.markdown("### 🌍 Flash Macro (Temps réel)")
    nq = macro_data.get("NQ=F")
    es = macro_data.get("ES=F")
    if nq:
        var_nq = (nq['price'] - nq['prev_close']) / nq['prev_close'] * 100 if nq['prev_close'] else 0
        st.metric("Nasdaq 100", f"{nq['price']:.2f}", delta=f"{var_nq:+.2f}%")
    else: st.metric("Nasdaq 100", "N/A")
    if es:
        var_es = (es['price'] - es['prev_close']) / es['prev_close'] * 100 if es['prev_close'] else 0
        st.metric("S&P 500", f"{es['price']:.2f}", delta=f"{var_es:+.2f}%")
    else: st.metric("S&P 500", "N/A")
    tnx = macro_data.get("^TNX")
    if tnx:
        st.metric("US 10Y", f"{tnx['price']:.2f}%")
    else: st.metric("US 10Y", "N/A")
    eurusd = macro_data.get("EURUSD=X")
    if eurusd:
        st.metric("EUR/USD", f"{eurusd['price']:.4f}")
    else: st.metric("EUR/USD", "N/A")
    brent = macro_data.get("BZ=F")
    if brent:
        st.metric("Brent", f"{brent['price']:.2f}$")
    else: st.metric("Brent", "N/A")
    gold = macro_data.get("GC=F")
    if gold:
        var_gold = (gold['price'] - gold['prev_close']) / gold['prev_close'] * 100 if gold['prev_close'] else 0
        st.metric("Or (GC=F)", f"{gold['price']:.2f}$", delta=f"{var_gold:+.2f}%")
    else: st.metric("Or", "N/A")
    st.markdown('</div>', unsafe_allow_html=True)

# SECTION 4
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
