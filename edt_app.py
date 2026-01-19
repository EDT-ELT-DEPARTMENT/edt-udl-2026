import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #ddd; padding: 10px; text-align: center; }
    td { border: 1px solid #ccc; padding: 8px !important; vertical-align: top; text-align: center; background-color: white; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; }
    .enseignant-name { color: #333; display: block; font-size: 12px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 11px; }
    .separator { border-top: 1px dashed #bbb; margin: 8px 0; }
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
st.markdown("<h1 class='main-title'>🏛️ Gestionnaire d'Emploi du Temps-Département d'électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Menu")
    file = st.file_uploader("Charger le fichier Excel", type=['xlsx'])
    if st.button("🚪 Déconnexion"):
        st.session_state["auth"] = False
        st.rerun()

if file:
    # 1. Lecture
    df = pd.read_excel(file)
    
    # 2. NETTOYAGE AGRESSIF (Supprime les \n et convertit tout en texte propre)
    df.columns = [str(c).strip() for c in df.columns]
    
    # On s'assure que toutes les colonnes importantes sont traitées comme du texte
    cols_to_fix = ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']
    for col in cols_to_fix:
        if col in df.columns:
            # Remplace les NaN par "Non défini" et supprime les \n
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.replace('\r', ' ').str.strip()

    # 3. FILTRES (Correction du TypeError ici avec list comprehension)
    st.sidebar.markdown("---")
    mode = st.sidebar.radio("Afficher par :", ["Promotion", "Enseignant"])
    
    try:
        if mode == "Promotion":
            # On récupère les valeurs uniques, on s'assure qu'elles sont du texte, et on trie
            options = sorted([str(x) for x in df['Promotion'].unique() if x])
            selection = st.sidebar.selectbox("🎯 Choisir la Promotion :", options)
            df_filtered = df[df['Promotion'] == selection]
        else:
            # Même chose pour les enseignants
            options = sorted([str(x) for x in df['Enseignants'].unique() if x])
            selection = st.sidebar.selectbox("👤 Choisir l'Enseignant :", options)
            df_filtered = df[df['Enseignants'] == selection]

        # 4. CRÉATION DU CONTENU DES CASES
        def format_cell(rows):
            items = []
            for _, row in rows.iterrows():
                promo = f"<br>({row['Promotion']})" if mode == "Enseignant" else ""
                html = f"<div class='cell'> <span class='cours-title'>{row['Enseignements']}</span> <span class='enseignant-name'>{row['Enseignants']}</span> <span class='lieu-name'>{row['Lieu']}{promo}</span> </div>"
                items.append(html)
            return "<div class='separator'></div>".join(items)

        # 5. GRILLE
        jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
        horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

        grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours')
        grid = grid.reindex(index=horaires, columns=jours).fillna("")
        
        st.subheader(f"📋 Emploi du temps : {selection}")
        st.write(grid.to_html(escape=False), unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erreur d'analyse des données : {e}")
        st.info("Vérifiez que votre fichier Excel contient bien les colonnes : Enseignements, Enseignants, Lieu, Promotion, Horaire, Jours")

else:
    st.info("Veuillez charger votre fichier Excel pour activer les options.")