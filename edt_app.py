import streamlit as st
import pandas as pd
import io
import os
import glob
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .logo-container { display: flex; justify-content: center; margin-bottom: 0px; }
    .main-title { 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 20px; margin-top: 5px;
    }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 85px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 11px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 9px; }
    .separator { border-top: 1px dashed #bbb; margin: 4px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }
    .stat-box { padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }
    .conflit-alert { background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; border: 1px solid #f5c6cb; margin-bottom: 5px; font-size: 14px; }
    .salle-libre { color: #28a745; font-size: 10px; font-weight: bold; display: block; margin: 1px 0; }
    
    @media print {
        @page { size: A4 landscape; margin: 0.5cm; }
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print, button { display: none !important; }
        .stApp { height: auto !important; background-color: white !important; }
        table { page-break-inside: avoid; width: 100% !important; border: 1px solid black !important; }
        th { background-color: #1E3A8A !important; color: white !important; -webkit-print-color-adjust: exact; }
    }
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTIFICATION ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ</h1>", unsafe_allow_html=True)
    pw = st.text_input("Code d'accès :", type="password")
    if pw == "doctorat2026":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- CHARGEMENT DU FICHIER ---
excel_files = glob.glob("*.xlsx")
default_file = excel_files[0] if excel_files else None
df = None

with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("Mettre à jour l'Excel", type=['xlsx'])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
    elif default_file:
        df = pd.read_excel(default_file)
    
    st.markdown("---")
    mode_view = st.sidebar.radio("Vue :", ["Promotion", "Enseignant", "🚩 Vérificateur", "📍 Salles Libres"])
    
    poste_superieur = False
    if mode_view == "Enseignant":
        st.markdown("---")
        st.subheader("👤 Statut Enseignant")
        poste_sup_choice = st.radio("Poste Supérieur (Décharge 50%) ?", ["Non", "Oui"])
        poste_superieur = (poste_sup_choice == "Oui")

if df is not None:
    if os.path.exists("logo.png"):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("logo.png", width=120)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()

    # --- DÉTECTION DES CONFLITS ---
    dup_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
    pot_err_ens = df[df['Enseignants'] != "Non défini"][dup_ens]
    real_err_ens_idx = []
    for name, group in pot_err_ens.groupby(['Jours', 'Horaire', 'Enseignants']):
        if group['Enseignements'].nunique() > 1:
            real_err_ens_idx.extend(group.index.tolist())
    df_err_ens = df.loc[real_err_ens_idx]

    dup_salle = df[df['Lieu'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Lieu'], keep=False)
    pot_err_salle = df[df['Lieu'] != "Non défini"][dup_salle]
    real_err_salle_idx = []
    for name, group in pot_err_salle.groupby(['Jours', 'Horaire', 'Lieu']):
        if group['Enseignements'].nunique() > 1:
            real_err_salle_idx.extend(group.index.tolist())
    df_err_salle = df.loc[real_err_salle_idx]

    jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

    try:
        if mode_view == "🚩 Vérificateur":
            st.subheader("🔍 Analyse des Chevauchements")
            if df_err_ens.empty and df_err_salle.empty:
                st.success("✅ Aucun chevauchement réel détecté.")
            else:
                if not df_err_salle.empty:
                    for _, r in df_err_salle.drop_duplicates(subset=['Jours', 'Horaire', 'Lieu']).iterrows():
                        st.markdown(f"<div class='conflit-alert'>📍 <b>{r['Lieu']}</b> : Plusieurs matières à {r['Horaire']}</div>", unsafe_allow_html=True)
                if not df_err_ens.empty:
                    for _, r in df_err_ens.drop_duplicates(subset=['Jours', 'Horaire', 'Enseignants']).iterrows():
                        st.markdown(f"<div class='conflit-alert' style='background-color:#fff3cd; color:#856404;'>👤 <b>{r['Enseignants']}</b> : Conflit réel le {r['Jours']} à {r