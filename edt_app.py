import streamlit as st
import pandas as pd
import io
import os
import glob
import streamlit.components.v1 as components

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EDT & Charge UDL", layout="wide")

# --- STYLE CSS (Design, Interface & Impression Page Unique) ---
st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 85px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 11px; }
    .enseignant-name { color: #333; display: block; font-size: 10px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 9px; }
    .separator { border-top: 1px dashed #bbb; margin: 4px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }
    .stat-box { background-color: #e9ecef; border-radius: 5px; padding: 8px; margin-top: 5px; font-weight: bold; color: #1E3A8A; text-align: center; font-size: 13px; border: 1px solid #ccc; }
    .conflit-alert { background-color: #ffcccc; color: #cc0000; padding: 10px; border-radius: 5px; border-left: 5px solid #cc0000; margin-bottom: 8px; font-size: 14px; }

    /* STYLE IMPRESSION FORCEE SUR UNE PAGE A4 PAYSAGE */
    @media print {
        @page { size: A4 landscape; margin: 0.5cm; }
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print, button { 
            display: none !important; 
        }
        .stApp { height: auto !important; background-color: white !important; }
        .main .block-container { padding: 0 !important; max-width: 100% !important; }
        table { page-break-inside: avoid; width: 100% !important; font-size: 10pt !important; border: 1px solid black !important; }
        th { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; background-color: #1E3A8A !important; color: white !important; }
        td { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; border: 1px solid black !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- SYSTÈME D'AUTHENTIFICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ</h1>", unsafe_allow_html=True)
    pw = st.text_input("Code d'accès du département :", type="password")
    if pw == "doctorat2026":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- RECHERCHE AUTOMATIQUE DU FICHIER EXCEL ---
# Cherche n'importe quel fichier .xlsx dans le dossier (ex: dataEDT-ELT-S2-2026.xlsx)
excel_files = glob.glob("*.xlsx")
default_file = excel_files[0] if excel_files else None
df = None

# --- INTERFACE BARRE LATÉRALE ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png")
    st.header("⚙️ Configuration")
    
    uploaded_file = st.file_uploader("Mettre à jour le fichier Excel", type=['xlsx'])
    
    # Priorité : 1. Fichier chargé manuellement / 2. Fichier présent sur GitHub
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Fichier temporaire chargé")
    elif default_file:
        df = pd.read_excel(default_file)
        st.info(f"📁 Source : {default_file}")
    
    if st.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- LOGIQUE DE L'APPLICATION ---
if df is not None:
    st.markdown("<h1 class='main-title'>🏛️ Plateforme de getion des EDTs-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    # Nettoyage des colonnes
    df.columns = [str(c).strip() for c in df.columns]
    cols_needed = ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']
    for col in cols_needed:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.strip()

    # --- DÉTECTION DES CONFLITS (Global) ---
    mask_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
    df_err_ens = df[df['Enseignants'] != "Non défini"][mask_ens]
    
    mask_salle = df[df['Lieu'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Lieu'], keep=False)
    df_err_salle = df[df['Lieu'] != "Non défini"][mask_salle]

    st.sidebar.markdown("---")
    mode_view = st.sidebar.radio("Afficher par :", ["Promotion", "Enseignant", "🚩 Vérificateur de Conflits"])
    
    try:
        if mode_view == "🚩 Vérificateur de Conflits":
            st.subheader("🔍 Analyse des Salles, Amphis et Enseignants")
            if df_err_ens.empty and df_err_salle.empty:
                st.success("✅ Aucun chevauchement détecté dans l'emploi du temps.")
            else:
                if not df_err_salle.empty:
                    for _, r in df_err_salle.iterrows():
                        label = "🏛️ Amphi" if "AMPHI" in r['Lieu'].upper() else "📍 Salle"
                        st.markdown(f"<div class='conflit-alert'>{label} <b>{r['Lieu']}</b> : Double occupation le {r['Jours']} à {r['Horaire']}</div>", unsafe_allow_html=True)
                if not df_err_ens.empty:
                    for _, r in df_err_ens.iterrows():
                        st.markdown(f"<div class='conflit-alert' style='background-color:#fff3cd; color:#856404;'>👤 <b>{r['Enseignants']}</b> : Conflit horaire le {r['Jours']} à {r['Horaire']}</div>", unsafe_allow_html=True)

        else:
            col_target = "Promotion" if mode_view == "Promotion" else "Enseignants"
            options = sorted([str(x) for x in df[col_target].unique() if x and x != "Non défini"])
            selection = st.sidebar.selectbox(f"Choisir {mode_view} :", options)
            df_filtered = df[df[col_target] == selection].copy()

            if mode_view == "Enseignant":
                # --- CALCULS DE CHARGE ---
                def get_type(t):
                    t = t.upper()
                    if "COURS" in t: return "COURS"
                    elif "TD" in t: return "TD"
                    elif "TP" in t: return "TP"
                    return "AUTRE"
                
                df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
                df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
                
                charge_totale = df_filtered['h_val'].sum()
                heures_sup = max(0, charge_totale - 9.0)
                
                st.markdown(f"### 📊 Bilan de charge : {selection}")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='metric-card'><b>Charge Hebdomadaire</b><br><h2>{charge_totale} h</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'><b>Quota Statutaire</b><br><h2>9.0 h</h2></div>", unsafe_allow_html=True)
                color_sup = "#d9534f" if heures_sup > 0 else "#28a745"
                c3.markdown(f"<div class='metric-card' style='border-color:{color_sup}'><b>Heures Sup</b><br><h2 style='color:{color_sup}'>{heures_sup} h</h2></div>", unsafe_allow_html=True)
                
                s1, s2, s3 = st.columns(3)
                s1.markdown(f"<div class='stat-box'>📚 Cours : {len(df_filtered[df_filtered['Type']=='COURS'])}</div>", unsafe_allow_html=True)
                s2.markdown(f"<div class='stat-box'>📝 TD : {len(df_filtered[df_filtered['Type']=='TD'])}</div>", unsafe_allow_html=True)
                s3.markdown(f"<div class='stat-box'>🔬 TP : {len(df_filtered[df_filtered['Type']=='TP'])}</div>", unsafe_allow_html=True)

            # --- BOUTON IMPRESSION PDF (SÉCURISÉ & OPTIMISÉ) ---
            st.markdown("---")
            components.html(
                """
                <button onclick="window.parent.print()" style="
                    background-color: #28a745; color: white; padding: 12px; 
                    border: none; border-radius: 5px; font-weight: bold; 
                    cursor: pointer; width: 100%; font-family: sans-serif; font-size: 16px;">
                    🖨️ Télécharger / Imprimer en PDF (Format A4 Paysage)
                </button>
                """, height=60
            )

            # --- GÉNÉRATION DU TABLEAU ---
            def format_cell(rows):
                items = []
                for _, row in rows.iterrows():
                    is_err = "border: 2px solid red; background:#fff0f0;" if row.name in df_err_ens.index or row.name in df_err_salle.index else ""
                    icon = "🏛️" if "AMPHI" in row['Lieu'].upper() else "📍"
                    p_info = f"<br>({row['Promotion']})" if mode_view == "Enseignant" else ""
                    html = f"<div style='{is_err} padding:4px; border-radius:3px;'><span class='cours-title'>{row['Enseignements']}</span><span class='enseignant-name'>{row['Enseignants']}</span><span class='lieu-name'>{icon} {row['Lieu']}{p_info}</span></div>"
                    items.append(html)
                return "<div class='separator'></div>".join(items)

            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
            
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours')
            grid = grid.reindex(index=horaires, columns=jours).fillna("")
            
            st.subheader(f"📋 Emploi du Temps : {selection}")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erreur d'affichage : {e}")
else:
    st.warning("⚠️ Aucun fichier Excel trouvé. Veuillez déposer votre fichier .xlsx sur GitHub ou le charger ici.")