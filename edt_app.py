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
    .conflit-alert { background-color: #ffcccc; color: #cc0000; padding: 10px; border-radius: 5px; border-left: 5px solid #cc0000; margin-bottom: 10px; font-size: 14px; }
    .badge-salle { background-color: #1E3A8A; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
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

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    st.header("⚙️ Menu Principal")
    file = st.file_uploader("Charger le fichier Excel", type=['xlsx'])
    if st.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if file:
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Nettoyage et normalisation des Lieux (Salles/Amphis)
    cols_to_fix = ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.replace('\r', ' ').str.strip()

    # --- DÉTECTION DES CONFLITS ---
    # 1. Conflit Enseignant
    mask_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
    df_err_ens = df[df['Enseignants'] != "Non défini"][mask_ens]
    
    # 2. Conflit Local (Salle ou Amphi)
    mask_salle = df[df['Lieu'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Lieu'], keep=False)
    df_err_salle = df[df['Lieu'] != "Non défini"][mask_salle]

    st.sidebar.markdown("---")
    mode = st.sidebar.radio("Afficher par :", ["Promotion", "Enseignant", "🚩 Vérificateur de Salles/Amphis"])
    
    try:
        if mode == "🚩 Vérificateur de Salles/Amphis":
            st.subheader("🔍 Analyse de l'occupation des locaux")
            
            if df_err_ens.empty and df_err_salle.empty:
                st.success("✅ Félicitations ! Aucun chevauchement de salle ou d'enseignant.")
            else:
                if not df_err_salle.empty:
                    st.error(f"⚠️ {len(df_err_salle)//2} Conflit(s) de Salle/Amphi détecté(s) :")
                    for _, r in df_err_salle.iterrows():
                        type_local = "🏛️ Amphi" if "AMPHI" in r['Lieu'].upper() else "📍 Salle"
                        st.markdown(f"<div class='conflit-alert'><b>{type_local} {r['Lieu']}</b> : Double occupation le {r['Jours']} à {r['Horaire']} ({r['Enseignements']})</div>", unsafe_allow_html=True)
                
                if not df_err_ens.empty:
                    st.warning(f"⚠️ {len(df_err_ens)//2} Enseignant(s) en conflit horaire :")
                    for _, r in df_err_ens.iterrows():
                        st.markdown(f"<div class='conflit-alert' style='background-color:#fff3cd; border-color:#ffeeba; color:#856404;'>👤 <b>{r['Enseignants']}</b> : Présent dans deux endroits le {r['Jours']} à {r['Horaire']}</div>", unsafe_allow_html=True)

        else:
            # --- VUES STANDARDS ---
            if mode == "Promotion":
                options = sorted([str(x) for x in df['Promotion'].unique() if x])
                selection = st.sidebar.selectbox("🎯 Choisir la Promotion :", options)
                df_filtered = df[df['Promotion'] == selection].copy()
            else:
                options = sorted([str(x) for x in df['Enseignants'].unique() if x])
                selection = st.sidebar.selectbox("👤 Choisir l'Enseignant :", options)
                df_filtered = df[df['Enseignants'] == selection].copy()

                # Calcul Charge
                df_filtered['Type'] = df_filtered['Enseignements'].apply(lambda x: "COURS" if "COURS" in x.upper() else ("TD" if "TD" in x.upper() else "TP"))
                df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
                charge = df_filtered['h_val'].sum()
                st.info(f"📊 Charge hebdomadaire de {selection} : **{charge}h** (Heures Sup: {max(0, charge-9)}h)")

            # --- GRILLE ---
            def format_cell(rows):
                items = []
                for _, row in rows.iterrows():
                    color_style = "border: 2px solid #cc0000; background: #fff5f5;" if row.name in df_err_ens.index or row.name in df_err_salle.index else ""
                    local_label = "🏛️" if "AMPHI" in row['Lieu'].upper() else "📍"
                    promo = f"<br>({row['Promotion']})" if mode == "Enseignant" else ""
                    html = f"<div style='{color_style} padding:5px; border-radius:3px;'><span class='cours-title'>{row['Enseignements']}</span><span class='enseignant-name'>{row['Enseignants']}</span><span class='lieu-name'>{local_label} {row['Lieu']}{promo}</span></div>"
                    items.append(html)
                return "<div class='separator'></div>".join(items)

            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours')
            grid = grid.reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("Veuillez charger votre fichier Excel.")