import streamlit as st
import pandas as pd
import io
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT & Charge UDL", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #ddd; padding: 10px; text-align: center; }
    td { border: 1px solid #ccc; padding: 8px !important; vertical-align: top; text-align: center; background-color: white; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; }
    .enseignant-name { color: #333; display: block; font-size: 12px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 11px; }
    .separator { border-top: 1px dashed #bbb; margin: 8px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }
    .stat-box { background-color: #e9ecef; border-radius: 5px; padding: 5px; margin-top: 5px; font-weight: bold; color: #1E3A8A; }
    </style>
""", unsafe_allow_html=True)

# --- MOT DE PASSE ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ</h1>", unsafe_allow_html=True)
    pw = st.text_input("Code d'accès :", type="password")
    if pw == "doctorat2026":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- INTERFACE ---
st.markdown("<h1 class='main-title'>🏛️ Gestionnaire d'EDT et des Charges</h1>", unsafe_allow_html=True)
st.markdown("<h5 style='text-align: center; color: #555;'>Département d'électrotechnique - UDL SBA</h5>", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    
    st.header("⚙️ Menu")
    file = st.file_uploader("Charger le fichier Excel", type=['xlsx'])
    if st.button("🚪 Déconnexion"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

if file:
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Nettoyage
    cols_to_fix = ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.replace('\r', ' ').str.strip()

    st.sidebar.markdown("---")
    mode = st.sidebar.radio("Afficher par :", ["Promotion", "Enseignant"])
    
    try:
        if mode == "Promotion":
            options = sorted([str(x) for x in df['Promotion'].unique() if x])
            selection = st.sidebar.selectbox("🎯 Choisir la Promotion :", options)
            df_filtered = df[df['Promotion'] == selection]
        else:
            options = sorted([str(x) for x in df['Enseignants'].unique() if x])
            selection = st.sidebar.selectbox("👤 Choisir l'Enseignant :", options)
            df_filtered = df[df['Enseignants'] == selection]

            # --- ANALYSE DÉTAILLÉE DE LA CHARGE ---
            def analyser_type(titre):
                t = titre.upper()
                if "COURS" in t: return "COURS"
                elif "TD" in t: return "TD"
                elif "TP" in t: return "TP"
                return "AUTRE"

            df_filtered['Type'] = df_filtered['Enseignements'].apply(analyser_type)
            
            # Calcul des volumes horaires
            def calculer_h(row):
                if row['Type'] == "COURS": return 1.5
                return 1.0 # TD et TP
            
            df_filtered['h_val'] = df_filtered.apply(calculer_h, axis=1)
            
            # Statistiques
            nb_cours = len(df_filtered[df_filtered['Type'] == "COURS"])
            nb_td = len(df_filtered[df_filtered['Type'] == "TD"])
            nb_tp = len(df_filtered[df_filtered['Type'] == "TP"])
            charge_totale = df_filtered['h_val'].sum()
            heures_sup = max(0, charge_totale - 9.0)

            # Affichage des statistiques
            st.markdown(f"### 📊 Bilan de l'enseignant : {selection}")
            
            row1_col1, row1_col2, row1_col3 = st.columns(3)
            with row1_col1:
                st.markdown(f"<div class='metric-card'><b>Charge Totale</b><br><h2>{charge_totale} h</h2></div>", unsafe_allow_html=True)
            with row1_col2:
                st.markdown(f"<div class='metric-card'><b>Quota Réglementaire</b><br><h2>9.0 h</h2></div>", unsafe_allow_html=True)
            with row1_col3:
                color = "#d9534f" if heures_sup > 0 else "#28a745"
                st.markdown(f"<div class='metric-card' style='border-color:{color}'><b>Heures Sup</b><br><h2 style='color:{color}'>{heures_sup} h</h2></div>", unsafe_allow_html=True)
            
            st.write("") # Espace
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='stat-box'>📚 Nombre de Cours : {nb_cours}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='stat-box'>📝 Nombre de TD : {nb_td}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='stat-box'>🔬 Nombre de TP : {nb_tp}</div>", unsafe