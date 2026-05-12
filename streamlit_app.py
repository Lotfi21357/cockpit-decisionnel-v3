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

st.markdown("""
<style>  
.stApp {max-width: 100%; padding: 0.5rem;}  
.big-verdict {font-size: 1.8rem !important; font-weight: bold; text-align: center; padding: 0.8rem; border-radius: 1rem; margin: 1rem 0; color: white;}  
.small-text {font-size: 0.85rem; color: #6c757d;}  
</style>  
""", unsafe_allow_html=True)

# ---------- SIDEBAR DYNAMIQUE ----------
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

# ---------- FONCTIONS UTILES ----------
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

def safe_prev(series):
    if series is None: return None
    if isinstance(series, pd.DataFrame): series = series.squeeze()
    if isinstance(series, pd.Series):
        valid = series.dropna()
        return to_float(valid.iloc[-2]) if len(valid) > 1 else safe_last(series)
    return None

def download_ticker(ticker, start):
    try:
        df = yf.download(ticker, start=start, progress=False)
        if not df.empty:
            return df
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)   # Rafraîchissement toutes les minutes
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

# ---------- CHARGEMENT ----------
data = load_all_data()
if not data:
    st.error("Aucune donnée récupérée.")
    st.stop()

# ---------- 100 % LIVE (plus de prix fixes) ----------

# ---------- RÉCUPÉRATION DES TICKERS ET PRIX ----------
ticker_used = {}
latest_prices = {}
prev_prices = {}
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
        prev_prices[used] = safe_prev(data[used]["Close"])
    else:
        latest_prices[pos["nom"]] = None
        prev_prices[pos["nom"]] = None

# ---------- VALEUR DU PORTEFEUILLE ET PERFORMANCES ----------
positions_calculees = []
valeur_totale = 0.0
valeur_veille = 0.0
valeur_par_enveloppe = {"PEA": 0.0, "AV": 0.0}
gain_par_enveloppe = {"PEA": 0.0, "AV": 0.0}

for pos in POSITIONS:
    ticker = ticker_used[pos["nom"]]
    prix = latest_prices.get(ticker)
    prix_veille = prev_prices.get(ticker)
    enveloppe = pos.get("enveloppe", "AV")
    if prix is None or np.isnan(prix):
        positions_calculees.append({
            "nom": pos["nom"],
            "prix": None,
            "valeur": 0.0,
            "perf": None,
            "var_jour": 0.0,
            "var_jour_euro": 0.0
        })
    else:
        valeur = pos["parts"] * prix
        perf = (prix - pos["prm"]) / pos["prm"] * 100

        # Variation journalière (% et €)
        if prix_veille is not None and not np.isnan(prix_veille) and prix_veille != 0:
            var_jour = (prix - prix_veille) / prix_veille * 100
            var_jour_euro = (prix - prix_veille) * pos["parts"]
        else:
            var_jour = 0.0
            var_jour_euro = 0.0

        positions_calculees.append({
            "nom": pos["nom"],
            "prix": prix,
            "valeur": valeur,
            "perf": perf,
            "var_jour": var_jour,
            "var_jour_euro": var_jour_euro
        })
        valeur_totale += valeur
        valeur_par_enveloppe[enveloppe] += valeur
        gain_par_enveloppe[enveloppe] += (prix - pos["prm"]) * pos["parts"]
        if prix_veille is not None and not np.isnan(prix_veille):
            valeur_veille += pos["parts"] * prix_veille
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
    bench_prev = safe_prev(bench_series)
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

# ---------- PRIX DE RATTRAPAGE ----------
prix_rattrapage = None
if gap is not None and gap < 0 and ticker_used.get("Global Hydrogen"):
    valeur_cible = capital_net * (1 + perf_bench/100)
    diff = valeur_cible - valeur_totale
    anrj_parts = next((pos["parts"] for pos in POSITIONS if pos["nom"] == "Global Hydrogen"), None)
    if anrj_parts and anrj_parts > 0:
        anrj_prix_actuel = safe_last(data[ticker_used["Global Hydrogen"]]["Close"]) if ticker_used["Global Hydrogen"] else None
        if anrj_prix_actuel:
            prix_rattrapage = anrj_prix_actuel + (diff / anrj_parts)
else:
    if gap is not None and gap >= 0:
        prix_rattrapage = "Objectif atteint"

# ---------- INDICATEURS HYDROGÈNE ----------
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

# ---------- INDICATEURS EM ASIA ----------
aasi_series = None
aasi_current = None
if "AASI.PA" in data and not data["AASI.PA"].empty:
    aasi_series = data["AASI.PA"]["Close"].squeeze()
    aasi_current = safe_last(aasi_series)

aasi_sma20 = aasi_sma50 = None
if aasi_series is not None and len(aasi_series) >= 20:
    aasi_sma20 = safe_last(compute_sma(aasi_series, 20))
    aasi_sma50 = safe_last(compute_sma(aasi_series, 50))

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

# ---------- MACRO ----------
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

# ---------- RÈGLES DÉCISIONNELLES ----------
def evaluate_hydrogen():
    if anrj_current is None: return "⚠️ ANRJ manquant", "gray"
    if anrj_current < 706.06: return "🚨 STOP-LOSS : COUPURE 50% VERS WORLD", "red"
    if anrj_current > 812 and anrj_rsi and anrj_rsi > 68: return "💰 TAKE PROFIT 30%", "green"
    if anrj_ath30 and anrj_current < anrj_ath30 * 0.95: return "🔶 ALLÉGEMENT PRÉVENTIF (Protection des gains, -5% ATH 30j)", "orange"
    if anrj_sma20 and anrj_current < anrj_sma20: return "🔶 SOUS SMA20 – ARBITRAGE VERS WORLD", "orange"
    if anrj_sma50 and anrj_current > anrj_sma50: return "✅ MAINTIEN HYDROGÈNE", "green"
    return "ℹ️ SURVEILLANCE", "orange"

def evaluate_em_asia():
    if aasi_current is None: return "⚠️ AASI manquant", "gray"
    if aasi_current > 60.35:
        if aasi_series is not None:
            highest = aasi_series.rolling(50, min_periods=1).max()
            highest_val = safe_last(highest)
            if highest_val and aasi_current < highest_val * 0.92: return "🎯 TRAILING STOP -8% : ARBITRAGE 50%", "red"
        else: return "📈 TRAILING STOP ACTIF", "green"
    if aasi_sma20 and aasi_current < aasi_sma20: return "🔶 SOUS SMA20 – SURVEILLANCE RENFORCÉE", "orange"
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

# ---------- MODULE FISCAL ----------
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

# ---------- INTERFACE ----------
now = datetime.now(ZoneInfo("Europe/Paris"))
st.title("🛰️ Cockpit Décisionnel")
st.caption(f"Données du {now.strftime('%d/%m/%Y %H:%M')} (heure de Paris)")

st.markdown("### 📊 Executive")
col1, col2, col3 = st.columns(3)
# Delta combiné € + %
col1.metric("Valeur totale", f"{valeur_totale:,.2f}€",
            delta=f"{perf_jour_euro:+,.2f}€ ({perf_jour_pct:+.2f}%) (24h)")
col2.metric("Gain net", f"{gain_net:+,.2f}€")
col3.metric("Performance", f"{perf_totale:+.2f}%",
            delta=f"{perf_jour_pct:+.2f}% ({perf_jour_euro:+,.2f}€) (24h)")

if perf_bench is not None:
    col4, col5 = st.columns(2)
    col4.metric(f"Perf. {BENCHMARK_LABEL}", f"{perf_bench:+.2f}%",
                delta=f"{perf_bench_jour:+.2f}% (24h)" if perf_bench_jour is not None else None)
    col5.metric("GAP vs World AV", f"{gap:+.2f}%",
                delta=f"{gap_jour:+.2f}% (24h)" if gap_jour is not None else None)

# Soldes nets estimés
col_pea, col_av = st.columns(2)
for enveloppe, col in [("PEA", col_pea), ("AV", col_av)]:
    val = valeur_par_enveloppe[enveloppe]
    gain = gain_par_enveloppe[enveloppe]
    net, avert = calculer_net_fiscal(enveloppe, val, val, gain)
    col.metric(f"Solde Net Estimé {enveloppe}", f"{net:,.2f}€", help="Retrait total (estimation)")
    if avert:
        col.caption(avert)

# Détail positions
st.markdown("#### Positions")
cols = st.columns(len(positions_calculees))
for i, p in enumerate(positions_calculees):
    with cols[i]:
        prix_str = f"{p['prix']:.2f}€" if p['prix'] is not None else "N/A"
        # Delta = variation journalière en % et €
        delta_str = f"{p['var_jour']:+.2f}% ({p['var_jour_euro']:+.2f}€)"
        st.metric(label=p['nom'], value=prix_str, delta=delta_str)

# Feu tricolore
bg = {"red": "#dc3545", "orange": "#fd7e14", "green": "#28a745"}[decision_color]
st.markdown(f"<div class='big-verdict' style='background-color:{bg};'>{decision_globale}</div>", unsafe_allow_html=True)

# Simulation de retrait fiscal
st.sidebar.markdown("---")
st.sidebar.subheader("🧮 Simulation retrait fiscal")
montant_retrait = st.sidebar.number_input("Montant à retirer (€)", min_value=0.0, value=1000.0, step=100.0)
enveloppe_retrait = st.sidebar.selectbox("Enveloppe", ["PEA", "AV"])
valeur_poche = valeur_par_enveloppe.get(enveloppe_retrait, 0.0)
gain_poche = gain_par_enveloppe.get(enveloppe_retrait, 0.0)
net_retrait, avert_retrait = calculer_net_fiscal(enveloppe_retrait, montant_retrait, valeur_poche, gain_poche)
st.sidebar.markdown(f"**Net après impôts :** {net_retrait:,.2f} €")
if avert_retrait:
    st.sidebar.warning(avert_retrait)

# Score de risque
st.markdown("#### ⚖️ Poids Satellites")
jauge = poids_satellite / 100
st.progress(min(jauge, 1.0))
st.write(f"ANRJ + EM Asia : {poids_satellite:.1f}% du portefeuille")
if alerte_risque:
    st.warning("⚠️ Poids satellites > 45% – Exposition élevée aux thématiques")

# Détails Hydrogène
st.subheader("🔎 Hydrogène (ANRJ)")
if anrj_current:
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("ANRJ", f"{anrj_current:.2f}€")
    d2.metric("SMA20", f"{anrj_sma20:.2f}€" if anrj_sma20 else "N/A")
    d3.metric("ATH 30j", f"{anrj_ath30:.2f}€" if anrj_ath30 else "N/A")
    d4.metric("RSI", f"{anrj_rsi:.1f}" if anrj_rsi else "N/A")
    st.caption(evaluate_hydrogen()[0])
else:
    st.warning("ANRJ indisponible")

# Détails EM Asia
st.subheader("🌏 EM Asia (AASI)")
if aasi_current:
    e1, e2 = st.columns(2)
    e1.metric("AASI", f"{aasi_current:.2f}€")
    e2.metric("SMA20", f"{aasi_sma20:.2f}€" if aasi_sma20 else "N/A")
    st.caption(evaluate_em_asia()[0])
else:
    st.warning("AASI indisponible")

# Sentinelles
st.subheader("🛰️ Sentinelles")
s_msg, s_col = evaluate_sentinelles()
st.caption(s_msg)
sentinel_rows = []
for name, info in sentinelle_info.items():
    prix = info["prix"]
    sma20 = info["sma20"]
    sentinel_rows.append({"Nom": name, "Dernier": f"{prix:.2f}" if prix else "N/A", "SMA20": f"{sma20:.2f}" if sma20 else "N/A"})
if sentinel_rows:
    st.dataframe(pd.DataFrame(sentinel_rows), use_container_width=True, hide_index=True)

# Macro
st.subheader("🧭 Macro")
m1, m2, m3, m4 = st.columns(4)
m1.metric("US 10Y", f"{us10y:.2f}%" if us10y else "N/A")
m2.metric("DXY", f"{dxy:.2f}" if dxy else "N/A")
m3.metric("Brent", f"{brent:.2f}$" if brent else "N/A")
m4.metric("Bloom Energy", f"{bloom_close:.2f}$" if bloom_close else "N/A")

# ---------- DIAGRAMME DE RÉPARTITION (donut) ----------
st.subheader("📊 Répartition du Portefeuille")
donut_data = [p for p in positions_calculees if p["valeur"] > 0]
if donut_data:
    fig = px.pie(
        donut_data,
        values='valeur',
        names='nom',
        hole=0.4,
        title="Allocation actuelle"
    )
    fig.update_traces(textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune donnée de répartition disponible.")

st.markdown("---")
st.caption("Cockpit Décisionnel · Ne constitue pas un conseil en investissement")
