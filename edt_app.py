import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Générateur EDT UDL", layout="wide")

st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'Times New Roman'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    
    /* Style du tableau type "Grille Universitaire" */
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #ddd; padding: 12px; text-align: center; }
    td { border: 1px solid #ccc; padding: 10px !important; vertical-align: top; text-align: center; background-color: white; min-width: 150px; }
    
    /* Style pour les multi-cours dans une case */
    .cell-item { font-size: 13px; margin-bottom: 5px; }
    .separator { border-top: 1px dashed #bbb; margin: 8px 0; }
    .cours-title { color: #1E3A8A; font-weight: bold; }
    .enseignant-name { color: #333; }
    .lieu-name { color: #666; font-style: italic; }
    </style>
""", unsafe_allow_html=True)

# --- PROTECTION PAR MOT DE PASSE ---
if "auth_edt" not in st.session_state:
    st.session_state["auth_edt"] = False

def check_password():
    if st.session_state["pw_input"] == "doctorat2026": # Même mot de passe que votre autre appli
        st.session_state["auth_edt"] = True
    else:
        st.error("Mot de passe incorrect")

if not st.session_state["auth_edt"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ GÉNÉRATEUR EDT</h1>", unsafe_allow_html=True)
    st.text_input("Code d'accès :", type="password", key="pw_input", on_change=check_password)
    st.stop()

# --- LOGIQUE D'AFFICHAGE ---
st.markdown("<h1 class='main-title'>🏛️ Consultation des Emplois du Temps</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Administration")
    file = st.file_uploader("Charger le fichier Excel (.xlsx)", type=['xlsx'])
    st.markdown("---")
    if st.button("🚪 Déconnexion"):
        st.session_state["auth_edt"] = False
        st.rerun()

if file:
    df = pd.read_excel(file)
    df.columns = [c.strip() for c in df.columns]

    # --- FILTRES ---
    mode = st.radio("Afficher par :", ["Promotion (Étudiants)", "Enseignant (Planning Pro)"], horizontal=True)
    
    if mode == "Promotion (Étudiants)":
        target = st.selectbox("Sélectionnez la Promotion :", sorted(df['Promotion'].unique()))
        df_view = df[df['Promotion'] == target]
    else:
        target = st.selectbox("Sélectionnez l'Enseignant :", sorted(df['Enseignants'].unique()))
        df_view = df[df['Enseignants'] == target]

    # --- FORMATAGE DE LA CELLULE (Exactement comme votre exemple) ---
    def format_edt_cell(rows):
        items = []
        for _, row in rows.iterrows():
            content = f"""
            <div class='cell-item'>
                <span class='cours-title'>{row['Enseignements']}</span><br>
                <span class='enseignant-name'>{row['Enseignants']}</span><br>
                <span class='lieu-name'>{row['Lieu']}</span>
            </div>
            """
            items.append(content)
        return "<div class='separator'></div>".join(items)

    # --- CRÉATION DE LA GRILLE ---
    jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

    # Pivot avec notre fonction de formatage personnalisée
    grid = df_view.groupby(['Horaire', 'Jours']).apply(format_edt_cell).unstack('Jours')
    
    # Réorganisation
    grid = grid.reindex(index=horaires, columns=jours).fillna("")

    # Affichage final
    st.markdown(f"### 📋 Emploi du temps actuel : **{target}**")
    st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    # Export
    buf = io.BytesIO()
    grid.to_excel(buf)
    st.download_button("📥 Télécharger en Excel", buf.getvalue(), f"EDT_{target}.xlsx")

else:
    st.info("Veuillez importer le fichier Excel dans la barre latérale pour générer la vue.")