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
st.set_page_config(page_title="Cockpit Décisionnel", page_icon="🛰️", layout="wide", initial_sidebar_state="expanded")

# ---------- CSS DARK MODE PREMIUM ----------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .card { background-color: #1A1D24; border-radius:12px; padding:1.2rem; margin-bottom:1rem; border:1px solid #2E3239; }
    .kpi-value { font-size:2rem; font-weight:700; color:#FFFFFF; }
    .kpi-label { font-size:0.9rem; color:#B0B5BD; text-transform:uppercase; letter-spacing:0.5px; }
    .big-verdict { font-size:1.4rem !important; font-weight:bold; text-align:center; padding:1rem; border-radius:12px; margin:1rem 0; color:white; }
    .badge { display:inline-block; padding:0.25rem 0.75rem; border-radius:20px; font-size:0.8rem; font-weight:600; text-transform:uppercase; }
    .badge-red { background-color:#dc3545; }
    .badge-orange { background-color:#fd7e14; }
    .badge-green { background-color:#28a745; }
    h2, h3, h4 { color:#FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
st.sidebar.title("⚙️ Paramètres")
capital_investi = st.sidebar.number_input("Capital investi (€)", value=13956.49)
bonus_fortuneo = st.sidebar.number_input("Bonus Fortuneo (€)", value=160.0)

POSITIONS_BASE = [
    {"nom": "MSCI World AV",   "tickers": ["MWRD.PA"], "parts": 36.33,   "prm": 140.41,  "env": "AV"},
    {"nom": "MSCI World PEA",  "tickers": ["DCAM.PA"], "parts": 481.0,   "prm": 5.5937,  "env": "PEA"},
    {"nom": "Global Hydrogen", "tickers": ["ANRJ.PA"], "parts": 4.7701,  "prm": 707.55,  "env": "AV"},
    {"nom": "EM Asia",         "tickers": ["AASI.PA"], "parts": 40.8272, "prm": 49.96,   "env": "AV"},
    {"nom": "Or Physique",     "tickers": ["SGLD.PA"], "parts": 4.5902,  "prm": 163.39,  "env": "AV"},
]

# ---------- LOGIQUE DE NETTOYAGE DES DONNÉES (CORRECTION TECHNIQUE) ----------
def clean_df(df):
    """Force le DataFrame à avoir des colonnes simples et sans MultiIndex"""
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

@st.cache_data(ttl=300)
def fetch_data(ticker_list):
    data_map = {}
    for t in ticker_list:
        try:
            # On télécharge 1 par 1 pour éviter les erreurs de MultiIndex groupés
            d = yf.download(t, period="2y", interval="1d", progress=False, auto_adjust=True)
            d = clean_df(d)
            if not d.empty:
                data_map[t] = d
        except:
            continue
    return data_map

# Initialisation des Tickers
ALL_TICKERS = ["MWRD.PA", "DCAM.PA", "ANRJ.PA", "AASI.PA", "SGLD.PA", 
               "PLUG", "BE", "NEL.OL", "TSM", "005930.KS", "AAXJ", 
               "NQ=F", "ES=F", "GC=F", "^TNX", "EURUSD=X"]

data = fetch_data(ALL_TICKERS)

# ---------- CALCULS ----------
valeur_totale = 0
positions_calculees = []

for pos in POSITIONS_BASE:
    t = pos["tickers"][0]
    prm = pos["prm"]
    if pos["nom"] == "MSCI World PEA":
        prm -= (bonus_fortuneo / pos["parts"])
    
    current_price = data[t]['Close'].iloc[-1] if t in data else 0
    valeur = pos["parts"] * current_price
    valeur_totale += valeur
    perf = ((current_price - prm) / prm) * 100 if prm != 0 else 0
    
    positions_calculees.append({
        "nom": pos["nom"],
        "prix": current_price,
        "valeur": valeur,
        "perf": perf,
        "poids": 0 # calculé après
    })

# Calcul des poids et arbitrage
valeur_satellites = 0
for p in positions_calculees:
    p["poids"] = (p["valeur"] / valeur_totale * 100) if valeur_totale > 0 else 0
    if p["nom"] in ["Global Hydrogen", "EM Asia"]:
        valeur_satellites += p["valeur"]

# ---------- INTERFACE ----------
st.title("🛰️ Cockpit Décisionnel Expert")

# INDICATEUR DE PHASE
gap_world = next((p["perf"] for p in positions_calculees if p["nom"] == "MSCI World AV"), 0)
ma_perf_totale = ((valeur_totale - (capital_investi - bonus_fortuneo)) / (capital_investi - bonus_fortuneo)) * 100
gap_vs_world = ma_perf_totale - gap_world

if gap_vs_world < 0:
    phase = "PHASE 1 : RECONQUÊTE (Objectif : Rattraper le World)"
    color = "#dc3545"
elif gap_vs_world > 0 and (valeur_satellites/valeur_totale*100) > 10:
    phase = "PHASE 2/3 : ALPHA & ROTATION (Objectif : Sécuriser les profits)"
    color = "#fd7e14"
else:
    phase = "PHASE 4 : PATRIMOINE (Cible 94% World / 6% Gold)"
    color = "#28a745"

st.markdown(f'<div style="background-color:{color}; color:white; padding:1rem; border-radius:10px; text-align:center; font-weight:bold;">{phase}</div>', unsafe_allow_html=True)

# COMMAND CENTER
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Valeur Totale", f"{valeur_totale:,.2f} €")
with c2:
    st.metric("Gain Net", f"{valeur_totale - capital_investi:,.2f} €", delta=f"{ma_perf_totale:.2f}%")
with c3:
    st.metric("GAP vs World", f"{gap_vs_world:+.2f}%", delta_color="normal")

# ARBITRAGE
st.markdown("### 🚨 Ordres d'Arbitrage")
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if gap_vs_world > 0:
        # Suggestion de vente si le World est battu
        anrj_val = next(p["valeur"] for p in positions_calculees if p["nom"] == "Global Hydrogen")
        st.write(f"✅ World Battu ! Suggestion : Vendre **{anrj_val * 0.20:,.2f} €** de Hydrogen pour acheter du World.")
    else:
        st.write("ℹ️ Conserver les positions satellites tant que le World n'est pas battu.")
    st.markdown('</div>', unsafe_allow_html=True)

# REPARTITION
st.markdown("### 🍩 Répartition Réelle")
fig = px.pie(positions_calculees, values='valeur', names='nom', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
st.plotly_chart(fig, use_container_width=True)

st.info("💡 Le MSCI World PEA est calculé avec PRM ajusté du Bonus Fortuneo. Affichage : 5.594 (3 décimales).")
