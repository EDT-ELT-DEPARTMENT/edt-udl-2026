import streamlit as st
import pandas as pd
import io
import os
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT & Charge UDL", layout="wide")

# --- STYLE CSS (Interface & Impression Page Unique) ---
st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 80px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 11px; }
    .enseignant-name { color: #333; display: block; font-size: 10px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 9px; }
    .separator { border-top: 1px dashed #bbb; margin: 4px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; }
    .stat-box { background-color: #e9ecef; border-radius: 5px; padding: 8px; margin-top: 5px; font-weight: bold; color: #1E3A8A; text-align: center; font-size: 13px; border: 1px solid #ccc; }
    .conflit-alert { background-color: #ffcccc; color: #cc0000; padding: 10px; border-radius: 5px; border-left: 5px solid #cc0000; margin-bottom: 8px; font-size: 14px; }

    @media print {
        @page { size: A4 landscape; margin: 1cm; }
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print, .stMarkdown button { 
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

# --- AUTHENTIFICATION ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ</h1>", unsafe_allow_html=True)
    pw = st.text_input("Code d'accès du département :", type="password")
    if pw == "doctorat2026":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- HEADER ---
st.markdown("<h1 class='main-title'>🏛️ Plateforme de getion des emplois du temps-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png")
    st.header("⚙️ Gestion")
    file = st.file_uploader("Charger l'EDT (Excel)", type=['xlsx'])
    if st.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if file:
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Normalisation
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.strip()

    # --- ANALYSE GLOBALE DES CONFLITS ---
    mask_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
    df_err_ens = df[df['Enseignants'] != "Non défini"][mask_ens]
    mask_salle = df[df['Lieu'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Lieu'], keep=False)
    df_err_salle = df[df['Lieu'] != "Non défini"][mask_salle]

    st.sidebar.markdown("---")
    mode_view = st.sidebar.radio("Affichage :", ["Promotion", "Enseignant", "🚩 Vérificateur de Conflits"])
    
    try:
        if mode_view == "🚩 Vérificateur de Conflits":
            st.subheader("🔍 Analyse des Salles, Amphis et Enseignants")
            if df_err_ens.empty and df_err_salle.empty:
                st.success("✅ Aucun conflit détecté dans l'emploi du temps.")
            else:
                if not df_err_salle.empty:
                    for _, r in df_err_salle.iterrows():
                        icon = "🏛️ Amphi" if "AMPHI" in r['Lieu'].upper() else "📍 Salle"
                        st.markdown(f"<div class='conflit-alert'>{icon} <b>{r['Lieu']}</b> : Double occupation le {r['Jours']} à {r['Horaire']}</div>", unsafe_allow_html=True)
                if not df_err_ens.empty:
                    for _, r in df_err_ens.iterrows():
                        st.markdown(f"<div class='conflit-alert' style='background-color:#fff3cd; color:#856404;'>👤 <b>{r['Enseignants']}</b> : Deux cours simultanés le {r['Jours']} à {r['Horaire']}</div>", unsafe_allow_html=True)

        else:
            col_target = "Promotion" if mode_view == "Promotion" else "Enseignants"
            options = sorted([str(x) for x in df[col_target].unique() if x])
            selection = st.sidebar.selectbox(f"Sélectionner {mode_view} :", options)
            df_filtered = df[df[col_target] == selection].copy()

            if mode_view == "Enseignant":
                # --- CALCULS DE CHARGE ET SÉANCES ---
                def get_type(t):
                    t = t.upper()
                    if "COURS" in t: return "COURS"
                    elif "TD" in t: return "TD"
                    elif "TP" in t: return "TP"
                    return "AUTRE"
                
                df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
                df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
                
                c_tot = df_filtered['h_val'].sum()
                h_sup = max(0, c_tot - 9.0)
                
                st.markdown(f"### 📊 Bilan de charge : {selection}")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='metric-card'><b>Charge Hebdomadaire</b><br><h2>{c_tot} h</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'><b>Quota (9h)</b><br><h2>9.0 h</h2></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='metric-card' style='border-color:{'#d9534f' if h_sup > 0 else '#28a745'}'><b>Heures Sup</b><br><h2 style='color:{'#d9534f' if h_sup > 0 else '#28a745'}'>{h_sup} h</h2></div>", unsafe_allow_html=True)
                
                s1, s2, s3 = st.columns(3)
                s1.markdown(f"<div class='stat-box'>📚 Cours : {len(df_filtered[df_filtered['Type']=='COURS'])}</div>", unsafe_allow_html=True)
                s2.markdown(f"<div class='stat-box'>📝 TD : {len(df_filtered[df_filtered['Type']=='TD'])}</div>", unsafe_allow_html=True)
                s3.markdown(f"<div class='stat-box'>🔬 TP : {len(df_filtered[df_filtered['Type']=='TP'])}</div>", unsafe_allow_html=True)

            # --- BOUTON IMPRESSION PDF SÉCURISÉ ---
            st.markdown("---")
            components.html(
                """
                <button onclick="window.parent.print()" style="
                    background-color: #28a745; color: white; padding: 12px; 
                    border: none; border-radius: 5px; font-weight: bold; 
                    cursor: pointer; width: 100%; font-family: sans-serif; font-size: 16px;">
                    📥 Télécharger / Imprimer cet emploi du temps (Une seule page A4)
                </button>
                """, height=60
            )

            # --- GRILLE D'AFFICHAGE ---
            def format_cell(rows):
                items = []
                for _, row in rows.iterrows():
                    is_err = "border: 2px solid red; background:#fff0f0;" if row.name in df_err_ens.index or row.name in df_err_salle.index else ""
                    local_icon = "🏛️" if "AMPHI" in row['Lieu'].upper() else "📍"
                    p_info = f"<br>({row['Promotion']})" if mode_view == "Enseignant" else ""
                    html = f"<div style='{is_err} padding:4px; border-radius:3px;'><span class='cours-title'>{row['Enseignements']}</span><span class='enseignant-name'>{row['Enseignants']}</span><span class='lieu-name'>{local_icon} {row['Lieu']}{p_info}</span></div>"
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
    st.info("Veuillez charger le fichier Excel des emplois du temps.")