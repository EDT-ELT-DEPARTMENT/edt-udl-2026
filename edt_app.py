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
        .print-footer {{ display: block !important; position: fixed; bottom: 0; font-size: 10px; }}
    }}
    .print-footer {{ display: none; }}
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTIFICATION ---
if "role" not in st.session_state: st.session_state["role"] = None

if not st.session_state["role"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>Accès aux Emplois du Temps S2-2026</h3>", unsafe_allow_html=True)
    
    col_login, _ = st.columns([2, 1])
    with col_login:
        pw = st.text_input("Veuillez entrer le code d'accès :", type="password")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔓 Connexion Enseignant"):
                if pw == "enseignant2026": st.session_state["role"] = "ENSEIGNANT"; st.rerun()
                else: st.error("Code Enseignant incorrect")
        with c2:
            if st.button("🔐 Connexion Administration"):
                if pw == "doctorat2026": st.session_state["role"] = "ADMIN"; st.rerun()
                else: st.error("Code Admin incorrect")
    st.stop()

# --- CHARGEMENT DU FICHIER ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

with st.sidebar:
    st.header(f"👤 {st.session_state['role']}")
    if st.session_state["role"] == "ADMIN":
        st.subheader("⚙️ Administration")
        uploaded_file = st.file_uploader("Mettre à jour l'Excel (ADMIN)", type=['xlsx'])
        if uploaded_file: df = pd.read_excel(uploaded_file)
        elif os.path.exists(NOM_FICHIER_FIXE): df = pd.read_excel(NOM_FICHIER_FIXE)
    else:
        if os.path.exists(NOM_FICHIER_FIXE): df = pd.read_excel(NOM_FICHIER_FIXE)

    st.markdown("---")
    mode_view = st.sidebar.radio("Choisir une Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"])
    
    poste_superieur = False
    if mode_view == "Enseignant":
        st.subheader("👤 Statut Enseignant")
        poste_sup_choice = st.radio("Poste Supérieur (Décharge 50%) ?", ["Non", "Oui"])
        poste_superieur = (poste_sup_choice == "Oui")

    if st.button("🚪 Se déconnecter"):
        st.session_state["role"] = None; st.rerun()

# --- AFFICHAGE DU CONTENU ---
if df is not None:
    st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str} | 🕒 {heure_str}</div>", unsafe_allow_html=True)
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    # --- MESSAGE DE BIENVENUE ---
    if st.session_state["role"] == "ENSEIGNANT":
        st.markdown(f"""
            <div class='welcome-box'>
                <b>👋 Bienvenue, Cher Collègue !</b><br>
                Vous êtes connecté à la plateforme officielle des emplois du temps du <b>Semestre 2 (2026)</b>.<br>
                <i>Note importante : Sélectionnez votre nom à gauche pour visualiser vos statistiques de charge et imprimer votre fiche.</i>
            </div>
        """, unsafe_allow_html=True)

    # Nettoyage des données
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns: df[col] = df[col].fillna("Non défini").astype(str).str.strip()

    jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

    try:
        if mode_view == "Enseignant":
            options = sorted([str(x) for x in df["Enseignants"].unique() if x != "Non défini"])
            selection = st.sidebar.selectbox("Choisir Enseignant :", options)
            df_filtered = df[df["Enseignants"] == selection].copy()

            # --- CALCULS DE CHARGE ET TYPES ---
            def get_type(t):
                t = t.upper()
                if "COURS" in t: return "COURS"
                elif "TD" in t: return "TD"
                elif "TP" in t: return "TP"
                return "AUTRE"

            df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
            df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            df_stats = df_filtered.drop_duplicates(subset=['Jours', 'Horaire'])
            
            charge_reelle = df_stats['h_val'].sum()
            charge_reg = (3.0 if poste_superieur else 6.0)
            h_sup = max(0.0, charge_reelle - charge_reg)

            # Affichage des Statistiques de charge
            st.markdown(f"### 📊 Bilan de charge : M. {selection}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'><b>Charge Réelle</b><br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><b>Charge Réglementaire</b><br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'><b>Heures Sup</b><br><h2>{h_sup} h</h2></div>", unsafe_allow_html=True)
            
            # Affichage du nombre de Cours/TD/TP
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {len(df_stats[df_stats['Type'] == 'COURS'])} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {len(df_stats[df_stats['Type'] == 'TD'])} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {len(df_stats[df_stats['Type'] == 'TP'])} TP</div>", unsafe_allow_html=True)

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

        elif mode_view == "🏢 Planning Salles":
            def get_r(l):
                m = re.search(r'([A-Z0-9]+)', l, re.I)
                return m.group(1).upper() if m else l
            df['L_R'] = df['Lieu'].apply(get_r)
            lieux = sorted([l for l in df['L_R'].unique() if l not in ["Non défini", ""]])
            sel = st.sidebar.selectbox("Choisir Salle/Amphi :", lieux)
            df_filtered = df[df["L_R"] == sel].copy()
            def fmt_l(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><small>{r['Promotion']}</small>" for _, r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_l).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "🚩 Vérificateur":
            dup = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
            err = df[df['Enseignants'] != "Non défini"][dup]
            if err.empty: st.success("✅ Aucun conflit d'horaire.")
            else: st.warning("🚩 Chevauchements détectés :"); st.dataframe(err)

        st.markdown(f"<div class='print-footer'>Document généré le {date_str} à {heure_str} - UDL SBA</div>", unsafe_allow_html=True)
        components.html("<button onclick='window.parent.print()' style='width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:20px;'>🖨️ IMPRIMER CE PLANNING</button>", height=70)

    except Exception as e:
        st.error(f"Erreur d'affichage : {e}")

