import streamlit as st
import pandas as pd
import io
import os
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT & Charge UDL", layout="wide")

# --- STYLE CSS (Inclus les règles pour l'impression) ---
st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 20px; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #ddd; padding: 10px; text-align: center; }
    td { border: 1px solid #ccc; padding: 8px !important; vertical-align: top; text-align: center; background-color: white; height: 80px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 13px; }
    .enseignant-name { color: #333; display: block; font-size: 11px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 10px; }
    .separator { border-top: 1px dashed #bbb; margin: 5px 0; }
    
    /* STYLE POUR L'IMPRESSION PDF */
    @media print {
        header, footer, .stSidebar, .stButton, .no-print { display: none !important; }
        .stApp { background-color: white !important; }
        .main-title { font-size: 20pt; }
        table { font-size: 10pt; width: 100% !important; border: 1px solid black !important; }
        th { background-color: #1E3A8A !important; -webkit-print-color-adjust: exact; }
        td { border: 1px solid #000 !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- FONCTION JAVASCRIPT POUR L'IMPRESSION ---
def print_button():
    components.html("""
        <script>
            function printPage() {
                window.print();
            }
        </script>
        <button onclick="printPage()" style="
            background-color: #1E3A8A;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            width: 100%;
            margin-top: 10px;">
            🖨️ Imprimer / Sauvegarder en PDF
        </button>
    """, height=60)

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
    
    if file:
        print_button() # Bouton placé dans la sidebar pour ne pas gêner le tableau
        
    if st.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if file:
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.strip()

    st.sidebar.markdown("---")
    mode = st.sidebar.radio("Afficher par :", ["Promotion", "Enseignant", "🚩 Vérificateur"])
    
    try:
        if mode == "🚩 Vérificateur":
            # (Logique du vérificateur simplifiée pour la lisibilité ici)
            st.subheader("Analyse des conflits...")
            # ... (Gardez votre logique de conflit précédente ici)
        else:
            if mode == "Promotion":
                options = sorted([str(x) for x in df['Promotion'].unique() if x])
                selection = st.sidebar.selectbox("🎯 Choisir la Promotion :", options)
                df_filtered = df[df['Promotion'] == selection].copy()
            else:
                options = sorted([str(x) for x in df['Enseignants'].unique() if x])
                selection = st.sidebar.selectbox("👤 Choisir l'Enseignant :", options)
                df_filtered = df[df['Enseignants'] == selection].copy()

            # --- AFFICHAGE ---
            st.subheader(f"📋 Emploi du Temps : {selection}")
            
            def format_cell(rows):
                items = []
                for _, row in rows.iterrows():
                    local_label = "🏛️" if "AMPHI" in row['Lieu'].upper() else "📍"
                    promo_info = f"<br>({row['Promotion']})" if mode == "Enseignant" else ""
                    html = f"<div><span class='cours-title'>{row['Enseignements']}</span><span class='enseignant-name'>{row['Enseignants']}</span><span class='lieu-name'>{local_label} {row['Lieu']}{promo_info}</span></div>"
                    items.append(html)
                return "<div class='separator'></div>".join(items)

            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
            
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours')
            grid = grid.reindex(index=horaires, columns=jours).fillna("")
            
            # Affichage du tableau HTML
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erreur : {e}")
else:
    st.info("Veuillez charger votre fichier Excel.")