import streamlit as st
import pandas as pd
import os
import re
import hashlib
from datetime import datetime
from supabase import create_client
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- FONCTION SÉCURITÉ ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
heure_str = now.strftime("%H:%M")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS (VERSION ORIGINALE) ---
st.markdown(f"""
    <style>
    .logo-container {{ display: flex; justify-content: center; margin-bottom: 0px; }}
    .main-title {{ 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }}
    .welcome-box {{
        background-color: #e8f0fe; border-left: 5px solid #1E3A8A;
        padding: 15px; margin-bottom: 20px; border-radius: 5px;
    }}
    .date-badge {{
        background-color: #1E3A8A; color: white; padding: 5px 15px;
        border-radius: 20px; font-size: 12px; float: right;
    }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    .stat-box {{ padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }}
    
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    
    @media print {{
        @page {{ size: A4 landscape; margin: 0.5cm; }}
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print, button {{ display: none !important; }}
        .stApp {{ height: auto !important; background-color: white !important; }}
        table {{ page-break-inside: avoid; width: 100% !important; border: 1px solid black !important; }}
        th {{ background-color: #1E3A8A !important; color: white !important; -webkit-print-color-adjust: exact; }}
    }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU FICHIER ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None
if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns: df[col] = df[col].fillna("Non défini").astype(str).str.strip()

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["🔑 Connexion", "📝 Inscription Enseignant", "🛡️ Administration"])
    
    with tab1:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")

    with tab2:
        st.info("L'inscription lie votre email à votre nom officiel dans l'EDT.")
        new_em = st.text_input("Email professionnel")
        if df is not None:
            noms_list = sorted([n for n in df['Enseignants'].unique() if n != "Non défini"])
            new_nom = st.selectbox("Sélectionnez votre nom officiel", noms_list)
        new_ps = st.text_input("Créez un mot de passe", type="password")
        if st.button("S'inscrire"):
            try:
                supabase.table("enseignants_auth").insert({"email": new_em, "nom_officiel": new_nom, "password_hash": hash_pw(new_ps)}).execute()
                st.success("Inscription validée ! Vous pouvez vous connecter.")
            except: st.error("Email déjà utilisé ou erreur de base de données.")

    with tab3:
        pw_admin = st.text_input("Code Administrateur", type="password")
        if st.button("Accès Administration"):
            if pw_admin == "doctorat2026":
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}
                st.rerun()
    st.stop()

# --- ESPACE CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    if is_admin:
        mode_view = st.radio("Choisir une Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"])
        poste_superieur = st.checkbox("Simuler Poste Supérieur (3h)")
    else:
        mode_view = "Personnel"
        poste_superieur = st.checkbox("Poste Supérieur (Décharge 50%)")
    
    if st.button("🚪 Se déconnecter"):
        st.session_state["user_data"] = None; st.rerun()

# --- AFFICHAGE ---
st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str} | 🕒 {heure_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

if df is not None:
    # --- VUE ENSEIGNANT (PERSONNEL OU ADMIN) ---
    if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
        cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
        df_filtered = df[df["Enseignants"] == cible].copy()

        if mode_view == "Personnel":
            st.markdown(f"<div class='welcome-box'><b>👋 Bienvenue, M. {cible} !</b><br>Note importante : Voici votre planning personnel et vos statistiques de charge.</div>", unsafe_allow_html=True)

        def get_type(t):
            t = str(t).upper()
            if "COURS" in t: return "COURS"
            elif "TD" in t: return "TD"
            elif "TP" in t: return "TP"
            return "AUTRE"

        df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
        df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
        df_stats = df_filtered.drop_duplicates(subset=['Jours', 'Horaire'])
        
        charge_reelle = df_stats['h_val'].sum()
        c_reg = 3.0 if poste_superieur else 6.0
        h_sup = charge_reelle - c_reg
        
        st.markdown(f"### 📊 Bilan de charge : {cible}")
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-card'><b>Charge Réelle</b><br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><b>Charge Réglementaire</b><br><h2>{c_reg} h</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><b>Heures Sup</b><br><h2>{h_sup} h</h2></div>", unsafe_allow_html=True)
        
        s1, s2, s3 = st.columns(3)
        s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {len(df_stats[df_stats['Type'] == 'COURS'])} COURS</div>", unsafe_allow_html=True)
        s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {len(df_stats[df_stats['Type'] == 'TD'])} TD</div>", unsafe_allow_html=True)
        s3.markdown(f"<div class='
