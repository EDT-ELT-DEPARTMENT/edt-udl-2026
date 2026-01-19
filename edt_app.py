import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Générateur EDT UDL", layout="wide")

# --- STYLE CSS (Formatage du tableau et des cellules) ---
st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'Times New Roman'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    
    /* Style du tableau type "Grille Universitaire" */
    table { width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #ddd; padding: 12px; text-align: center; width: 15%; }
    td { border: 1px solid #ccc; padding: 8px !important; vertical-align: top; text-align: center; background-color: white; overflow: hidden; }
    
    /* Formatage du contenu des cases */
    .cell-container { display: flex; flex-direction: column; gap: 5px; }
    .cours-title { color: #1E3A8A; font-weight: bold; font-size: 13px; line-height: 1.2; }
    .enseignant-name { color: #333; font-size: 12px; }
    .lieu-name { color: #666; font-style: italic; font-size: 11px; }
    .separator { border-top: 1px dashed #bbb; margin: 8px 0; }
    .conflit-tag { color: #d9534f; font-weight: bold; font-size: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- SYSTÈME D'AUTHENTIFICATION ---
if "auth_edt" not in st.session_state:
    st.session_state["auth_edt"] = False

def check_password():
    if st.session_state["pw_input"] == "doctorat2026":
        st.session_state["auth_edt"] = True
    else:
        st.error("Mot de passe incorrect")

if not st.session_state["auth_edt"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ GÉNÉRATEUR EDT</h1>", unsafe_allow_html=True)
    st.text_input("Veuillez saisir le code d'accès :", type="password", key="pw_input", on_change=check_password)
    st.stop()

# --- CHARGEMENT ET NETTOYAGE DES DONNÉES ---
st.markdown("<h1 class='main-title'>🏛️ Consultation des Emplois du Temps</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Administration")
    file = st.file_uploader("Importer le fichier Excel (.xlsx)", type=['xlsx'])
    if st.button("🚪 Déconnexion"):
        st.session_state["auth_edt"] = False
        st.rerun()

if file:
    # Lecture et nettoyage immédiat des \n et espaces
    df = pd.read_excel(file)
    df.columns = [c.strip() for c in df.columns]
    
    # NETTOYAGE CRUCIAL : Supprime les \n qui s'affichent dans votre Excel
    df = df.replace(r'\n', ' ', regex=True).replace(r'\r', ' ', regex=True)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].str.strip()

    # --- OPTIONS DE VUE ---
    st.sidebar.markdown("---")
    mode = st.sidebar.radio("Mode d'affichage :", ["Par Promotion (Étudiants)", "Par Enseignant (Planning Pro)"])
    
    if mode == "Par Promotion (Étudiants)":
        option_list = sorted(df['Promotion'].unique())
        selection = st.sidebar.selectbox("🎯 Choisir la Promotion :", option_list)
        df_filtered = df[df['Promotion'] == selection]
    else:
        option_list = sorted(df['Enseignants'].unique())
        selection = st.sidebar.selectbox("👤 Choisir l'Enseignant :", option_list)
        df_filtered = df[df['Enseignants'] == selection]

    # --- FONCTION DE GÉNÉRATION DE CASE (Format HTML) ---
    def format_cell(rows):
        items = []
        for _, row in rows.iterrows():
            conflit = "<span class='conflit-tag'>⚠️ CONFLIT</span><br>" if "⚠" in str(row.get('Chevauchement', '')) else ""
            # Si mode enseignant, on ajoute la promo dans la case
            promo_info = f"<br>({row['Promotion']})" if mode == "Par Enseignant (Planning Pro)" else ""
            
            cell_html = f"""
            <div class='cell-container'>
                {conflit}
                <span class='cours-title'>{row['Enseignements']}</span>
                <span class='enseignant-name'>{row['Enseignants']}</span>
                <span class='lieu-name'>{row['Lieu']}{promo_info}</span>
            </div>
            """
            items.append(cell_html)
        return "<div class='separator'></div>".join(items)

    # --- CONSTRUCTION DE LA GRILLE ---
    jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires_ordre = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

    try:
        # Groupement par horaire et jour
        grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours')
        
        # Réorganiser selon l'ordre officiel
        grid = grid.reindex(index=horaires_ordre, columns=jours_ordre).fillna("")

        st.markdown(f"### 📋 Résultats pour : **{selection}**")
        st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        # --- EXPORT ---
        st.sidebar.markdown("---")
        output = io.BytesIO()
        grid.to_excel(output)
        st.sidebar.download_button(label="📥 Télécharger l'EDT (.xlsx)", data=output.getvalue(), file_name=f"EDT_{selection}.xlsx")

    except Exception as e:
        st.error(f"Erreur lors de la création du tableau : {e}")

else:
    st.info("👋 Veuillez charger le fichier Excel des enseignements dans le menu à gauche pour générer les vues.")