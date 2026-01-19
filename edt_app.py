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
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 15px; border-radius: 10px; text-align: center; }
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

            # --- CALCUL DE LA CHARGE (Seulement en mode Enseignant) ---
            st.markdown("---")
            st.subheader(f"📊 Bilan Horaire : {selection}")
            
            # Calcul : On regarde le début du nom de l'enseignement
            def calculer_heures(ligne):
                txt = ligne.upper()
                if "COURS" in txt: return 1.5
                elif "TD" in txt or "TP" in txt: return 1.0
                else: return 1.0 # Par défaut si non spécifié
            
            df_filtered['heures_val'] = df_filtered['Enseignements'].apply(calculer_heures)
            charge_totale = df_filtered['heures_val'].sum()
            heures_sup = max(0, charge_totale - 9.0)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"<div class='metric-card'><b>Charge Hebdo</b><br><h2>{charge_totale} h</h2></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='metric-card'><b>Charge Réglementaire</b><br><h2>9.0 h</h2></div>", unsafe_allow_html=True)
            with col3:
                color = "red" if heures_sup > 0 else "green"
                st.markdown(f"<div class='metric-card' style='border-color:{color}'><b>Heures Sup</b><br><h2 style='color:{color}'>{heures_sup} h</h2></div>", unsafe_allow_html=True)
            st.markdown("---")

        # --- GRILLE ---
        def format_cell(rows):
            items = []
            for _, row in rows.iterrows():
                promo = f"<br>({row['Promotion']})" if mode == "Enseignant" else ""
                html = f"<div class='cell'><span class='cours-title'>{row['Enseignements']}</span><span class='enseignant-name'>{row['Enseignants']}</span><span class='lieu-name'>{row['Lieu']}{promo}</span></div>"
                items.append(html)
            return "<div class='separator'></div>".join(items)

        jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
        horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

        grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours')
        grid = grid.reindex(index=horaires, columns=jours).fillna("")
        
        st.subheader(f"📋 Emploi du temps : {selection}")
        st.write(grid.to_html(escape=False), unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("Veuillez charger votre fichier Excel.")