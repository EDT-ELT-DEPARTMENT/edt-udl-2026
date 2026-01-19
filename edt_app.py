import streamlit as st
import pandas as pd
import io
import os
import glob
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT & Charge UDL", layout="wide")

# --- STYLE CSS (Interface & Impression Page Unique) ---
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

    @media print {
        @page { size: A4 landscape; margin: 0.5cm; }
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print, button { display: none !important; }
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
    if os.path.exists("logo.png"): st.image("logo.png")
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("Mettre à jour l'Excel", type=['xlsx'])
    
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
    elif default_file:
        df = pd.read_excel(default_file)
        st.sidebar.info(f"📁 Source par défaut : {default_file}")
    
    if st.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if df is not None:
    st.markdown("<h1 class='main-title'>🏛️ Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.strip()

    # --- LOGIQUE DE CONFLIT AVANCÉE ---
    
    # 1. Conflit Enseignant : Ignorer si c'est la même matière dans le même lieu (Matière commune)
    dup_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
    potential_err_ens = df[df['Enseignants'] != "Non défini"][dup_ens]
    
    real_err_ens_idx = []
    for name, group in potential_err_ens.groupby(['Jours', 'Horaire', 'Enseignants']):
        # Erreur si l'enseignant est sur deux matières différentes OU deux lieux différents au même moment
        if len(group[['Enseignements', 'Lieu']].drop_duplicates()) > 1:
            real_err_ens_idx.extend(group.index.tolist())
    df_err_ens = df.loc[real_err_ens_idx]

    # 2. Conflit de Lieu : Ignorer si c'est la même matière (Matière commune ou Co-enseignement)
    dup_salle = df[df['Lieu'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Lieu'], keep=False)
    potential_err_salle = df[df['Lieu'] != "Non défini"][dup_salle]
    
    real_err_salle_idx = []
    for name, group in potential_err_salle.groupby(['Jours', 'Horaire', 'Lieu']):
        # Erreur si le lieu contient deux matières différentes au même moment
        if len(group[['Enseignements']].drop_duplicates()) > 1:
            real_err_salle_idx.extend(group.index.tolist())
    df_err_salle = df.loc[real_err_salle_idx]

    st.sidebar.markdown("---")
    mode_view = st.sidebar.radio("Vue :", ["Promotion", "Enseignant", "🚩 Vérificateur"])
    
    try:
        if mode_view == "🚩 Vérificateur":
            st.subheader("🔍 Analyse des Chevauchements")
            if df_err_ens.empty and df_err_salle.empty:
                st.success("✅ Aucun conflit. Les séances partagées (matières communes ou co-enseignement) sont autorisées.")
            else:
                if not df_err_salle.empty:
                    for _, r in df_err_salle.drop_duplicates(subset=['Jours', 'Horaire', 'Lieu']).iterrows():
                        st.markdown(f"<div class='conflit-alert'>📍 <b>{r['Lieu']}</b> : Conflit de matières ({r['Jours']} à {r['Horaire']})</div>", unsafe_allow_html=True)
                if not df_err_ens.empty:
                    for _, r in df_err_ens.drop_duplicates(subset=['Jours', 'Horaire', 'Enseignants']).iterrows():
                        st.markdown(f"<div class='conflit-alert' style='background-color:#fff3cd; color:#856404;'>👤 <b>{r['Enseignants']}</b> : Conflit de lieu ou de matière ({r['Jours']} à {r['Horaire']})</div>", unsafe_allow_html=True)

        else:
            col_target = "Promotion" if mode_view == "Promotion" else "Enseignants"
            options = sorted([str(x) for x in df[col_target].unique() if x and x != "Non défini"])
            selection = st.sidebar.selectbox(f"Choisir {mode_view} :", options)
            df_filtered = df[df[col_target] == selection].copy()

            if mode_view == "Enseignant":
                def get_type(t):
                    t = t.upper()
                    if "COURS" in t: return "COURS"
                    elif "TD" in t: return "TD"
                    elif "TP" in t: return "TP"
                    return "AUTRE"
                df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
                df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
                # On ne compte la charge qu'une fois par créneau (évite de doubler pour les matières communes)
                c_tot = df_filtered.drop_duplicates(subset=['Jours', 'Horaire'])['h_val'].sum()
                
                st.markdown(f"### 📊 Bilan : {selection}")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='metric-card'><b>Charge Réelle</b><br><h2>{c_tot} h</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'><b>Quota</b><br><h2>9.0 h</h2></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='metric-card' style='border-color:{'#d9534f' if c_tot > 9 else '#28a745'}'><b>Heures Sup</b><br><h2>{max(0, c_tot-9)} h</h2></div>", unsafe_allow_html=True)

            # --- BOUTON IMPRESSION ---
            components.html("""
                <button onclick="window.parent.print()" style="background-color: #28a745; color: white; padding: 12px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; width: 100%; font-family: sans-serif;">
                    🖨️ Imprimer l'EDT (Une seule page A4 Paysage)
                </button>
            """, height=55)

            # --- GRILLE ---
            def format_cell(rows):
                items = []
                for idx, row in rows.iterrows():
                    is_err = "border: 2px solid red; background:#fff0f0;" if idx in df_err_ens.index or idx in df_err_salle.index else ""
                    icon = "🏛️" if "AMPHI" in row['Lieu'].upper() else "📍"
                    # En mode Promotion, on affiche le prof. En mode Enseignant, on affiche la Promo.
                    label_extra = f"<br>({row['Promotion']})" if mode_view == "Enseignant" else f"<br><span class='enseignant-name'>{row['Enseignants']}</span>"
                    html = f"<div style='{is_err} padding:4px;'><span class='cours-title'>{row['Enseignements']}</span>{label_extra}<span class='lieu-name'>{icon} {row['Lieu']}</span></div>"
                    items.append(html)
                return "<div class='separator'></div>".join(items)

            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    except Exception as e: st.error(f"Erreur : {e}")