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

# ---------- CSS PREMIUM (cartes, badges, couleurs) ----------
st.markdown("""
<style>
    /* Fond général */
    .stApp {
        background-color: #f4f6f9;
    }
    /* Carte blanche */
    .card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    /* KPI executive */
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E2A3A;
    }
    .kpi-label {
        font-size: 0.9rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Bannières */
    .big-verdict {
        font-size: 1.4rem !important;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
        color: white;
    }
    /* Badge de statut */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-red { background-color: #dc3545; color: white; }
    .badge-orange { background-color: #fd7e14; color: white; }
    .badge-green { background-color: #28a745; color: white; }
    .badge-gray { background-color: #6c757d; color: white; }
    .small-text { font-size: 0.85rem; color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR DYNAMIQUE (réglages portefeuille) ----------
st.sidebar.title("⚙️ Gestion Dynamique")

capital_investi = st.sidebar.number_input(
    "Capital investi (€)",
    value=13956.49,
    step=100.0
)

bonus_fortuneo = st.sidebar.number_input(
    "Bonus Fortuneo déjà perçu (€)",
    value=160.0,
    step=10.0,
    help="Somme déjà reçue (ex. 160 €). Modifie‐la pour simuler le prochain bonus (ex. 320 €)."
)

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
    parts = st.sidebar.number_input(
        f"Parts {pos['nom']}",
        value=float(pos["parts"]),
        step=0.0001,
        key=f"parts_{pos['nom']}"
    )
    prm = st.sidebar.number_input(
        f"PRM {pos['nom']}",
        value=float(pos["prm"]),
        step=0.0001,
        key=f"prm_{pos['nom']}"
    )
    positions_dynamiques.append({
        "nom": pos["nom"],
        "tickers": pos["tickers"],
        "parts": parts,
        "prm": prm,
        "enveloppe": pos["enveloppe"]
    })

POSITIONS = positions_dynamiques

# -- Bonus Fortuneo : réduction du PRM de MSCI World PEA --
for pos in POSITIONS:
    if pos["nom"] == "MSCI World PEA" and pos["parts"] > 0:
        reduction_par_part = bonus_fortuneo / pos["parts"]
        pos["prm"] = pos["prm"] - reduction_par_part

BENCHMARK_LABEL = "MSCI World AV"
EXTRA_TICKERS = ["CW8.PA", "^TNX", "DX-Y.NYB", "BZ=F", "BE", "NVDA", "^SOX"]
SENTINELLES = {
    "TSMC":         ["TSM", "2330.TW"],
    "Samsung":      ["SSNLF", "005930.KS"],
    "SK Hynix":     ["HXSCL", "000660.KS"],
    "Air Liquide":  ["AI.PA"],
    "Bloom Energy": ["BE"],
}

DATE_DEBUT = datetime(2025, 9, 17)

# ---------- FONCTIONS UTILES (inchangées) ----------
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
    try:
        df = yf.download(ticker, start=start, progress=False)
        if not df.empty:
            return df
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_previous_close(ticker):
    try:
        info = yf.Ticker(ticker).info
        return to_float(info.get("previousClose"))
    except:
        return None

@st.cache_data(ttl=60, show_spinner=False)
def load_all_data():
    start = datetime.now() - timedelta(days=500)
    data = {}
    for pos in POSITIONS:
        for t in pos["tickers"]:
            df = download_ticker(t, start)
            if not df.empty:
                data[t] = df
                break
    for t in EXTRA_TICKERS:
        if t not in data:
            df = download_ticker(t, start)
            if not df.empty:
                data[t] = df
    for name, tickers in SENTINELLES.items():
        for t in tickers:
            if t not in data:
                df = download_ticker(t, start)
                if not df.empty:
                    data[t] = df
                    break
    if "EURUSD=X" not in data:
        eur = download_ticker("EURUSD=X", start)
        if not eur.empty:
            data["EURUSD=X"] = eur
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

# ---------- CHARGEMENT DES DONNÉES ----------
data = load_all_data()
if not data:
    st.error("Aucune donnée récupérée.")
    st.stop()

# ---------- RÉCUPÉRATION DES TICKERS ET PRIX ----------
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

# ---------- CALCULS DU PORTEFEUILLE ----------
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
        positions_calculees.append({
            "nom": pos["nom"], "prix": None, "valeur": 0.0,
            "perf": None, "var_jour": 0.0, "var_jour_euro": 0.0
        })
    else:
        valeur = pos["parts"] * prix
        perf = (prix - pos["prm"]) / pos["prm"] * 100

        if prev_close is not None and not np.isnan(prev_close) and prev_close != 0:
            var_jour = (prix - prev_close) / prev_close * 100
            var_jour_euro = (prix - prev_close) * pos["parts"]
        else:
            var_jour = 0.0
            var_jour_euro = 0.0

        positions_calculees.append({
            "nom": pos["nom"], "prix": prix, "valeur": valeur,
            "perf": perf, "var_jour": var_jour, "var_jour_euro": var_jour_euro
        })
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
bench_price = None
bench_prev = None

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
    if perf_jour_pct is not None:
        gap_jour = perf_jour_pct - perf_bench_jour

# ---------- INDICATEURS TECHNIQUES ----------
anrj_series = None
anrj_current = None
if "ANRJ.PA" in data and not data["ANRJ.PA"].empty:
    anrj_series = data["ANRJ.PA"]["Close"].squeeze()
    anrj_current = safe_last(anrj_series)

anrj_sma20 = anrj_sma50 = anrj_rsi = anrj_ath30 = None
if anrj_series is not None and len(anrj_series) >= 20:
    anrj_sma20 = safe_last(compute_sma(anrj_series, 20))
    anrj_sma50 = safe_last(compute_sma(anrj_series, 50))
    anrj_rsi = safe_last(compute_rsi(anrj_series, 14))
    ath30_series = anrj_series.rolling(30, min_periods=1).max()
    anrj_ath30 = safe_last(ath30_series)

aasi_series = None
aasi_current = None
if "AASI.PA" in data and not data["AASI.PA"].empty:
    aasi_series = data["AASI.PA"]["Close"].squeeze()
    aasi_current = safe_last(aasi_series)

aasi_sma20 = aasi_sma50 = None
if aasi_series is not None and len(aasi_series) >= 20:
    aasi_sma20 = safe_last(compute_sma(aasi_series, 20))
    aasi_sma50 = safe_last(compute_sma(aasi_series, 50))

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

# Macro
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

# ---------- RÈGLES DÉCISIONNELLES (inchangées) ----------
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
    tsmc = sentinelle_info.get("TSMC")
    if tsmc and tsmc["prix"] and tsmc["sma20"] and tsmc["prix"] < tsmc["sma20"]: alerts.append("⚠️ TSMC sous SMA20")
    sam = sentinelle_info.get("Samsung")
    if sam and sam["prix"] and sam["sma20"] and sam["prix"] < sam["sma20"]: alerts.append("⚠️ Samsung sous SMA20")
    al = sentinelle_info.get("Air Liquide")
    if al and al["prix"] and al["sma20"] and al["prix"] < al["sma20"]: alerts.append("⚠️ Air Liquide sous SMA20")
    if "BE" in data:
        be_series = data["BE"]["Close"].squeeze()
        if len(be_series) >= 3:
            be_latest = safe_last(be_series)
            be_2d_ago = safe_last(be_series.iloc[:-2]) if len(be_series) > 2 else None
            if be_latest and be_2d_ago and (be_latest / be_2d_ago - 1) < -0.03: alerts.append("⚠️ Bloom Energy -3% en 48h")
    if us10y and us10y > 4.60: alerts.append("⚠️ US10Y > 4.60%")
    if dxy and dxy > 102: alerts.append("⚠️ DXY > 102")
    if alerts: return " | ".join(alerts), "orange"
    return "✅ Sentinelles OK", "green"

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

# Score de risque satellite
valeur_anrj = next((p["valeur"] for p in positions_calculees if p["nom"] == "Global Hydrogen"), 0)
valeur_aasi = next((p["valeur"] for p in positions_calculees if p["nom"] == "EM Asia"), 0)
poids_satellite = (valeur_anrj + valeur_aasi) / valeur_totale * 100 if valeur_totale > 0 else 0
alerte_risque = poids_satellite > 45

# ---------- MODULE FISCAL (inchangé) ----------
def calculer_net_fiscal(enveloppe, montant_retrait, valeur_poche, gain_poche):
    if montant_retrait <= 0:
        return 0.0, ""
    if montant_retrait > valeur_poche:
        return 0.0, "Montant supérieur à la valeur du portefeuille."
    ratio_gain = gain_poche / valeur_poche if valeur_poche != 0 else 0
    gain_retrait = montant_retrait * ratio_gain
    aujourdhui = datetime.now(ZoneInfo("Europe/Paris"))
    
    if enveloppe == "PEA":
        seuil_pea = datetime(2031, 4, 1, tzinfo=ZoneInfo("Europe/Paris"))
        if aujourdhui < seuil_pea:
            return 0.0, "⚠️ Retrait PEA impossible avant le 01/04/2031 (clôture du plan si retrait)."
        impots = 0.172 * gain_retrait
        net = montant_retrait - impots
        return net, ""
    
    elif enveloppe == "AV":
        maturite = datetime(2033, 9, 17, tzinfo=ZoneInfo("Europe/Paris"))
        if aujourdhui < maturite:
            impots = 0.30 * gain_retrait
            net = montant_retrait - impots
            return net, ""
        else:
            abattement = 9200
            ps = 0.172 * gain_retrait
            ir = 0.128 * max(0, gain_retrait - abattement)
            impots = ps + ir
            net = montant_retrait - impots
            return net, ""
    else:
        return 0.0, "Enveloppe inconnue"

# ---------- NOUVELLE INTERFACE PREMIUM ----------
now = datetime.now(ZoneInfo("Europe/Paris"))
st.title("🛰️ Cockpit Décisionnel")
st.caption(f"Données en temps réel – {now.strftime('%d/%m/%Y %H:%M')} (heure de Paris)")

# ======================= SECTION 1 : COMMAND CENTER =======================
st.markdown("## 🚀 Command Center")
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # Ligne de KPIs
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="kpi-label">Valeur Totale</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{valeur_totale:,.2f}€</div>', unsafe_allow_html=True)
        st.caption(f"{perf_jour_euro:+,.2f}€ ({perf_jour_pct:+.2f}%) 24h")
    with col2:
        st.markdown(f'<div class="kpi-label">Gain Net</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{gain_net:+,.2f}€</div>', unsafe_allow_html=True)
        st.caption(f"Capital net : {capital_net:,.2f}€")
    with col3:
        st.markdown(f'<div class="kpi-label">Performance Totale</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="kpi-value">{perf_totale:+.2f}%</div>', unsafe_allow_html=True)
        st.caption(f"{perf_jour_pct:+.2f}% ({perf_jour_euro:+,.2f}€) 24h")
    st.markdown('</div>', unsafe_allow_html=True)

# Sous-section Benchmark + Donut
col_bench, col_donut = st.columns([1, 1])
with col_bench:
    st.markdown("### 📊 Benchmark vs " + BENCHMARK_LABEL)
    if perf_bench is not None:
        st.metric(label="Performance " + BENCHMARK_LABEL, value=f"{perf_bench:+.2f}%",
                  delta=f"{perf_bench_jour:+.2f}% 24h" if perf_bench_jour else None)
        st.metric(label="GAP vs World AV", value=f"{gap:+.2f}%",
                  delta=f"{gap_jour:+.2f}% 24h" if gap_jour else None)
        # Barre de progression du GAP
        if gap is not None:
            gap_norm = (gap + 5) / 10   # normalise entre -5% et +5%
            gap_norm = max(0, min(1, gap_norm))
            st.progress(gap_norm, text=f"Écart par rapport au World AV : {gap:+.2f}%")
    else:
        st.info("Données benchmark indisponibles")

with col_donut:
    st.markdown("### 🍩 Répartition")
    donut_data = [p for p in positions_calculees if p["valeur"] > 0]
    if donut_data:
        fig = px.pie(donut_data, values='valeur', names='nom', hole=0.4)
        fig.update_traces(textinfo='percent+label')
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée")

# ======================= SECTION 2 : STRATÉGIE & ARBITRAGE =======================
st.markdown("## 📈 Stratégie & Arbitrage")

# Feu tricolore géant
bg_color = {"red": "#dc3545", "orange": "#fd7e14", "green": "#28a745"}[decision_color]
st.markdown(f"""
<div class="big-verdict" style="background-color:{bg_color}; margin-bottom:1.5rem;">
    {decision_globale}
</div>
""", unsafe_allow_html=True)

# Badge de statut (utilitaire)
def get_status_badge(msg):
    if "MAINTIEN" in msg.upper(): return "Maintenir", "green"
    if "TAKE PROFIT" in msg.upper(): return "Vendre (Take Profit)", "green"
    if "STOP-LOSS" in msg.upper(): return "Vendre (Stop)", "red"
    if "ALLÉGEMENT" in msg.upper() or "ARBITRAGE" in msg.upper(): return "Alléger", "orange"
    if "SOUS SMA20" in msg.upper(): return "Surveillance", "orange"
    if "TRAILING STOP" in msg.upper(): return "Vendre (Trailing)", "red"
    if "SURVEILLANCE" in msg.upper(): return "Surveillance", "orange"
    return "Neutre", "gray"

# Analyse Hydrogène & EM Asia côte à côte
colH, colA = st.columns(2)

with colH:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔎 Hydrogène (ANRJ)")
    if anrj_current:
        d1, d2, d3 = st.columns(3)
        d1.metric("Prix", f"{anrj_current:.2f}€")
        d2.metric("SMA20", f"{anrj_sma20:.2f}€" if anrj_sma20 else "N/A")
        d3.metric("RSI", f"{anrj_rsi:.1f}" if anrj_rsi else "N/A")
        # Badge de statut
        msg, col = evaluate_hydrogen()
        status, badge_color = get_status_badge(msg)
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
        status, badge_color = get_status_badge(msg)
        st.markdown(f'<span class="badge badge-{badge_color}">{status}</span>', unsafe_allow_html=True)
        st.caption(msg)
    else:
        st.warning("AASI indisponible")
    st.markdown('</div>', unsafe_allow_html=True)

# Poids satellites (carte séparée)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ⚖️ Poids Satellites")
st.write(f"ANRJ + EM Asia : {poids_satellite:.1f}% du portefeuille")
st.progress(min(poids_satellite/100, 1.0))
if alerte_risque:
    st.warning("⚠️ Poids satellites > 45% – Exposition élevée aux thématiques")
st.markdown('</div>', unsafe_allow_html=True)

# ======================= SECTION 3 : SENTINELLES & MACRO =======================
st.markdown("## 🛰️ Sentinelles & Macro")

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
        prix = info["prix"]
        sma20 = info["sma20"]
        alert = ""
        if prix and sma20 and prix < sma20:
            alert = "⚠️"
        sentinel_rows.append({
            "Nom": name,
            "Prix": f"{prix:.2f}" if prix else "N/A",
            "SMA20": f"{sma20:.2f}" if sma20 else "N/A",
            "Statut": alert
        })
    if sentinel_rows:
        st.dataframe(pd.DataFrame(sentinel_rows), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

with colM:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌍 Flash Macro")
    st.metric("🛢️ Brent", f"{brent:.2f}$" if brent else "N/A")
    st.metric("💵 DXY", f"{dxy:.2f}" if dxy else "N/A")
    st.metric("📈 US 10Y", f"{us10y:.2f}%" if us10y else "N/A")
    st.metric("🔋 Bloom Energy", f"{bloom_close:.2f}$" if bloom_close else "N/A")
    st.markdown('</div>', unsafe_allow_html=True)

# ======================= SECTION 4 : SIMULATEUR FISCAL =======================
st.markdown("## 🧮 Simulateur Fiscal")

# Soldes nets estimés en haut de la section
col_pea, col_av = st.columns(2)
with col_pea:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🏦 PEA")
    val = valeur_par_enveloppe["PEA"]
    gain = gain_par_enveloppe["PEA"]
    net, avert = calculer_net_fiscal("PEA", val, val, gain)
    st.metric("Solde Net Estimé", f"{net:,.2f}€", help="Retrait total (estimation)")
    if avert:
        st.caption(avert)
    st.markdown('</div>', unsafe_allow_html=True)

with col_av:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### 🛡️ Assurance-Vie")
    val = valeur_par_enveloppe["AV"]
    gain = gain_par_enveloppe["AV"]
    net, avert = calculer_net_fiscal("AV", val, val, gain)
    st.metric("Solde Net Estimé", f"{net:,.2f}€", help="Retrait total (estimation)")
    if avert:
        st.caption(avert)
    st.markdown('</div>', unsafe_allow_html=True)

# Formulaire de simulation
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 💸 Simuler un retrait")
col_form1, col_form2 = st.columns(2)
with col_form1:
    montant_retrait = st.number_input("Montant à retirer (€)", min_value=0.0, value=1000.0, step=100.0)
with col_form2:
    enveloppe_retrait = st.selectbox("Enveloppe", ["PEA", "AV"])
valeur_poche = valeur_par_enveloppe.get(enveloppe_retrait, 0.0)
gain_poche = gain_par_enveloppe.get(enveloppe_retrait, 0.0)
net_retrait, avert_retrait = calculer_net_fiscal(enveloppe_retrait, montant_retrait, valeur_poche, gain_poche)
if avert_retrait:
    st.warning(avert_retrait)
else:
    st.markdown(f"""
    <div style="background:#e9f7ef; padding:1rem; border-radius:8px; margin-top:1rem;">
        <span style="font-weight:bold; color:#28a745;">Montant net après impôts :</span>
        <span style="font-size:1.5rem; font-weight:bold; color:#1E2A3A;"> {net_retrait:,.2f}€</span>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Pied de page
st.markdown("---")
st.caption("Cockpit Décisionnel · Ne constitue pas un conseil en investissement")
