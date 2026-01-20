import streamlit as st
import pandas as pd
import io
import os
import glob
import streamlit.components.v1 as components
import re
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- GESTION DE LA DATE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
heure_str = now.strftime("%H:%M")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS PERSONNALISÉ ---
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
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    
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

# --- SYSTÈME D'AUTHENTIFICATION ---
if "role" not in st.session_state:
    st.session_state["role"] = None

if not st.session_state["role"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>Gestion des Emplois du Temps S2-2026</h3>", unsafe_allow_html=True)
    
    col_login, _ = st.columns([2, 1])
    with col_login:
        pw = st.text_input("Veuillez entrer le code d'accès :", type="password")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔓 Connexion Enseignant"):
                if pw == "enseignant2026":
                    st.session_state["role"] = "ENSEIGNANT"
                    st.rerun()
                else:
                    st.error("Code Enseignant incorrect ❌")
        with c2:
            if st.button("🔐 Connexion Administration"):
                if pw == "doctorat2026":
                    st.session_state["role"] = "ADMIN"
                    st.rerun()
                else:
                    st.error("Code Admin incorrect ❌")
    st.stop()

# --- CONFIGURATION DU FICHIER DE DONNÉES ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx" 
df = None

with st.sidebar:
    st.header(f"👤 {st.session_state['role']}")
    
    # ACCÈS ADMIN : Possibilité de mettre à jour le fichier
    if st.session_state["role"] == "ADMIN":
        st.subheader("⚙️ Administration")
        uploaded_file = st.file_uploader("Mettre à jour l'Excel", type=['xlsx'])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
        elif os.path.exists(NOM_FICHIER_FIXE):
            df = pd.read_excel(NOM_FICHIER_FIXE)
    # ACCÈS ENSEIGNANT : Lecture seule du fichier présent sur GitHub
    else:
        if os.path.exists(NOM_FICHIER_FIXE):
            df = pd.read_excel(NOM_FICHIER_FIXE)
        else:
            st.error(f"Fichier '{NOM_FICHIER_FIXE}' introuvable sur le serveur.")

    st.markdown("---")
    mode_view = st.sidebar.radio("Vue souhaitée :", ["Promotion", "Enseignant", "🏢 Planning par Salle/Amphi", "🚩 Vérificateur"])
    
    if st.button("🚪 Déconnexion"):
        st.session_state["role"] = None
        st.rerun()

# --- TRAITEMENT ET AFFICHAGE ---
if df is not None:
    # Affichage du badge de date
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
                Nous sommes le <b>{nom_jour_fr} {date_str}</b>. Voici l'état actuel des plannings du Semestre 2.<br>
                <i>Veuillez sélectionner votre nom dans le menu à gauche pour imprimer votre fiche.</i>
            </div>
        """, unsafe_allow_html=True)

    # Nettoyage des colonnes
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()

    jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

    try:
        if mode_view == "Enseignant":
            options = sorted([str(x) for x in df["Enseignants"].unique() if x != "Non défini"])
            selection = st.sidebar.selectbox("Sélectionnez votre nom :", options)
            df_filtered = df[df["Enseignants"] == selection].copy()
            
            st.subheader(f"📊 Emploi du temps personnalisé : M. {selection}")
            def fmt_ens(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_ens).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "Promotion":
            options = sorted([str(x) for x in df["Promotion"].unique() if x != "Non défini"])
            selection = st.sidebar.selectbox("Sélectionnez la Promotion :", options)
            df_filtered = df[df["Promotion"] == selection].copy()
            def fmt_p(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "🏢 Planning par Salle/Amphi":
            def get_root(l):
                m = re.search(r'([A-Z0-9]+)', l, re.I)
                return m.group(1).upper() if m else l
            df['Lieu_R'] = df['Lieu'].apply(get_root)
            lieux = sorted([l for l in df['Lieu_R'].unique() if l not in ["Non défini", ""]])
            selection = st.sidebar.selectbox("Sélectionnez le Local :", lieux)
            df_filtered = df[df["Lieu_R"] == selection].copy()
            def fmt_l(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><small>{r['Promotion']}</small>" for _, r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_l).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "🚩 Vérificateur":
            dup = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
            err = df[df['Enseignants'] != "Non défini"][dup]
            if err.empty:
                st.success("✅ Aucun conflit d'horaire détecté.")
            else:
                st.warning("⚠️ Attention : Certains enseignants ont des cours simultanés.")
                st.dataframe(err)

        # Footer pour l'impression
        st.markdown(f"<div class='print-footer'>Généré le {date_str} à {heure_str} - Département Électrotechnique UDL</div>", unsafe_allow_html=True)
        
        # Bouton d'impression
        st.write("")
        components.html("<button onclick='window.parent.print()' style='width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold;'>🖨️ IMPRIMER CE PLANNING (A4 Paysage)</button>", height=70)

    except Exception as e:
        st.error(f"Une erreur est survenue lors du traitement : {e}")
