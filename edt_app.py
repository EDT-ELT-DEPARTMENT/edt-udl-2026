import streamlit as st
import pandas as pd
import io
import os
import glob
import streamlit.components.v1 as components
import re
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
heure_str = now.strftime("%H:%M")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .logo-container {{ display: flex; justify-content: center; margin-bottom: 0px; }}
    .main-title {{ 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }}
    .welcome-box {{
        background-color: #e8f0fe;
        border-left: 5px solid #1E3A8A;
        padding: 15px;
        margin-bottom: 20px;
        border-radius: 5px;
    }}
    .date-badge {{
        background-color: #1E3A8A;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 12px;
        float: right;
    }}
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
        .print-footer {{ display: block !important; position: fixed; bottom: 0; font-size: 10px; }}
    }}
    .print-footer {{ display: none; }}
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTIFICATION DOUBLE ACCÈS ---
if "role" not in st.session_state:
    st.session_state["role"] = None

if not st.session_state["role"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>Accès aux Emplois du Temps S2-2026</h3>", unsafe_allow_html=True)
    
    col_login, _ = st.columns([2, 1])
    with col_login:
        pw = st.text_input("Entrez votre code d'accès :", type="password")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔓 Connexion Enseignant"):
                if pw == "enseignant2026":
                    st.session_state["role"] = "ENSEIGNANT"
                    st.rerun()
                else:
                    st.error("Code Enseignant incorrect")
        with c2:
            if st.button("🔐 Connexion Administration"):
                if pw == "doctorat2026":
                    st.session_state["role"] = "ADMIN"
                    st.rerun()
                else:
                    st.error("Code Admin incorrect")
    st.stop()

# --- CHARGEMENT DU FICHIER ---
excel_files = glob.glob("*.xlsx")
default_file = excel_files[0] if excel_files else None
df = None

with st.sidebar:
    st.header(f"👤 {st.session_state['role']}")
    if st.session_state["role"] == "ADMIN":
        uploaded_file = st.file_uploader("Mettre à jour l'Excel (ADMIN)", type=['xlsx'])
        if uploaded_file: df = pd.read_excel(uploaded_file)
        elif default_file: df = pd.read_excel(default_file)
    else:
        if default_file: df = pd.read_excel(default_file)
    
    st.markdown("---")
    mode_view = st.sidebar.radio("Choisir une Vue :", ["Promotion", "Enseignant", "🏢 Planning par Salle/Amphi (Racine)", "🚩 Vérificateur"])
    if st.button("🚪 Se déconnecter"):
        st.session_state["role"] = None
        st.rerun()

# --- AFFICHAGE DU CONTENU ---
if df is not None:
    st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str} | 🕒 {heure_str}</div>", unsafe_allow_html=True)
    
    if os.path.exists("logo.png"):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("logo.png", width=100)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    if st.session_state["role"] == "ENSEIGNANT":
        st.markdown(f"""
            <div class='welcome-box'>
                <b>👋 Bienvenue, Cher Collègue !</b><br>
                Nous sommes le <b>{nom_jour_fr} {date_str}</b>. Voici l'état actuel des plannings pour le <b>Semestre 2</b>.<br>
                <i>Veuillez sélectionner votre nom à gauche pour imprimer votre fiche officielle.</i>
            </div>
        """, unsafe_allow_html=True)

    # Nettoyage des données (identique au précédent pour la stabilité)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns: df[col] = df[col].fillna("Non défini").astype(str).str.strip()

    jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

    try:
        # Moteur d'affichage par vue
        if mode_view == "Enseignant":
            options = sorted([str(x) for x in df["Enseignants"].unique() if x != "Non défini"])
            selection = st.sidebar.selectbox("Choisir Enseignant :", options)
            df_filtered = df[df["Enseignants"] == selection].copy()
            st.markdown(f"### 📊 Emploi du temps personnalisé : {selection}")
            def fmt_ens(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_ens).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "Promotion":
            options = sorted([str(x) for x in df["Promotion"].unique() if x != "Non défini"])
            selection = st.sidebar.selectbox("Choisir Promotion :", options)
            df_filtered = df[df["Promotion"] == selection].copy()
            def fmt_p(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "🏢 Planning par Salle/Amphi (Racine)":
            # (Logique identique pour les salles)
            pass

        # Footer invisible à l'écran mais visible à l'impression
        st.markdown(f"<div class='print-footer'>Document généré le {date_str} à {heure_str} - UDL SBA</div>", unsafe_allow_html=True)
        components.html("<button onclick='window.parent.print()' style='width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:20px;'>🖨️ IMPRIMER CE PLANNING</button>", height=70)

    except Exception as e:
        st.error(f"Erreur : {e}")
