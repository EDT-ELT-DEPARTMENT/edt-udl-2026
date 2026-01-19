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
    .main-title { 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 20px; margin-top: 10px;
    }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 85px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 11px; }
    .enseignant-name { color: #333; display: block; font-size: 10px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 9px; }
    .separator { border-top: 1px dashed #bbb; margin: 4px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }
    .stat-box { padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; }
    .badge-poste { background-color: #1E3A8A; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin-bottom: 10px; display: inline-block; }
    
    @media print {
        @page { size: A4 landscape; margin: 0.5cm; }
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print, button { display: none !important; }
        .stApp { height: auto !important; background-color: white !important; }
        .main .block-container { padding: 0 !important; max-width: 100% !important; }
        table { page-break-inside: avoid; width: 100% !important; font-size: 10pt !important; border: 1px solid black !important; }
        th { background-color: #1E3A8A !important; color: white !important; }
        td { border: 1px solid black !important; }
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
    mode_view = st.sidebar.radio("Vue :", ["Promotion", "Enseignant", "🚩 Vérificateur"])
    
    poste_superieur = False
    if mode_view == "Enseignant":
        st.markdown("---")
        st.subheader("👤 Statut Enseignant")
        poste_sup_choice = st.radio("Poste Supérieur (Décharge 50%) ?", ["Non", "Oui"])
        poste_superieur = True if poste_sup_choice == "Oui" else False

if df is not None:
    # LOGO ET TITRE
    if os.path.exists("logo.png"):
        col_l1, col_l2, col_l3 = st.columns([1, 1, 1])
        with col_l2: st.image("logo.png", width=120)
    
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()

    try:
        if mode_view == "Enseignant":
            options = sorted([str(x) for x in df["Enseignants"].unique() if x and x != "Non défini"])
            selection = st.sidebar.selectbox(f"Choisir Enseignant :", options)
            df_filtered = df[df["Enseignants"] == selection].copy()

            # --- CALCULS ---
            def get_type(t):
                t = t.upper()
                if "COURS" in t: return "COURS"
                elif "TD" in t: return "TD"
                elif "TP" in t: return "TP"
                return "AUTRE"

            df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
            df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            
            # Unicité par créneau (pour les amphis/matières communes)
            df_stats = df_filtered.drop_duplicates(subset=['Jours', 'Horaire'])
            
            charge_reelle = df_stats['h_val'].sum()
            charge_reglementaire = 3.0 if poste_superieur else 6.0
            h_sup = charge_reelle - charge_reglementaire
            
            # Nombre de séances
            n_cours = len(df_stats[df_stats['Type'] == "COURS"])
            n_td = len(df_stats[df_stats['Type'] == "TD"])
            n_tp = len(df_stats[df_stats['Type'] == "TP"])

            # --- AFFICHAGE BILAN ---
            st.markdown(f"### 📊 Bilan de charge : {selection}")
            if poste_superieur:
                st.markdown("<span class='badge-poste'>🛡️ Poste Supérieur (Décharge appliquée)</span>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'><b>Charge Réelle</b><br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><b>Charge Réglementaire</b><br><h2>{charge_reglementaire} h</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'><b>Heures Sup</b><br><h2>{h_sup} h</h2></div>", unsafe_allow_html=True)
            
            st.write("") # Espace
            
            # --- AFFICHAGE NOMBRE DE COURS, TD, TP ---
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {n_cours} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {n_td} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {n_tp} TP</div>", unsafe_allow_html=True)
            
            st.write("---")
            
            # GRILLE
            def format_cell(rows):
                items = []
                for idx, row in rows.iterrows():
                    icon = "🏛️" if "AMPHI" in row['Lieu'].upper() else "📍"
                    html = f"<div><span class='cours-title'>{row['Enseignements']}</span><br>({row['Promotion']})<br><span class='lieu-name'>{icon} {row['Lieu']}</span></div>"
                    items.append(html)
                return "<div class='separator'></div>".join(items)

            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9