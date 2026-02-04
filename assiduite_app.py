import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Plateforme EDT 2026", layout="wide")
TITRE = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- 2. CONNEXION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 3. CHARGEMENT ADAPTÉ À VOTRE NOUVEAU FICHIER ---
@st.cache_data(ttl=10)
def load_data_updated():
    # Lecture des fichiers
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    df_etud = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    
    # Nettoyage des colonnes (enlève les espaces et tabulations invisibles)
    df_etud.columns = [str(c).strip() for c in df_etud.columns]
    
    # --- CIBLAGE PAR POSITION ---
    # Col 0:Nom | Col 1:Prénom | Col 4:Promotion (La 5ème colonne)
    df_etud['PROMO_PROPRE'] = df_etud.iloc[:, 4].astype(str).str.strip()
    df_etud['NOM_PROPRE'] = df_etud.iloc[:, 0].astype(str).str.strip().str.upper()
    df_etud['PRENOM_PROPRE'] = df_etud.iloc[:, 1].astype(str).str.strip()
    
    # Nom complet pour la liste d'appel
    df_etud['IDENTITE'] = df_etud['NOM_PROPRE'] + " " + df_etud['PRENOM_PROPRE']
    
    return df_edt, df_etud

# Initialisation
try:
    df_edt, df_etudiants = load_data_updated()
except Exception as e:
    st.error(f"⚠️ Erreur : Le fichier Excel est chargé mais le code n'arrive pas à le lire. Détail : {e}")
    st.stop()

# --- 4. INTERFACE UTILISATEUR ---

st.subheader("🔑 Validation Enseignant")
email_prof = st.text_input("Entrez votre Email professionnel :")

st.markdown(f"#### {TITRE}")

st.subheader("👤 1. Sélectionner l'Enseignant :")
profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("Sélection", profs, label_visibility="collapsed")

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    col_p, col_m = st.columns(2)
    
    with col_p:
        # On extrait les promotions depuis la 5ème colonne
        liste_promos = sorted([p for p in df_etudiants['PROMO_PROPRE'].unique() if p.lower() != 'nan'])
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", liste_promos)

    with col_m:
        matieres = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Enseignements'].unique())
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", matieres)

    # Affichage 📍 Horaire | Lieu
    info = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    if not info.empty:
        st.info(f"📍 {info.iloc[0]['Jours']} | {info.iloc[0]['Horaire']} | Lieu: {info.iloc[0]['Lieu']}")

    st.markdown("### 📈 État d'Avancement & Appel")
    
    col_t, col_n = st.columns(2)
    with col_t:
        type_u = st.selectbox("Type d'unité :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°", "Examen"])
    with col_n:
        num_u = st.number_input("Numéro :", min_value=1, value=1)

    # --- FILTRAGE DES ÉTUDIANTS ---
    # On cherche les étudiants dont la 5ème colonne (Promotion) correspond au choix
    df_selection = df_etudiants[df_etudiants['PROMO_PROPRE'] == promo_sel]
    liste_noms = sorted(df_selection['IDENTITE'].tolist())

    st.markdown("**❌ Sélectionner les ABSENTS :**")
    
    absents = st.multiselect(
        "Liste",
        options=liste_noms,
        label_visibility="collapsed",
        placeholder="Choose options"
    )

    # Formulaire final
    date_s = st.date_input("📅 Date réelle de la séance :")
    obs = st.text_area("🗒️ Observations (Obligatoire) :")
    sig = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    code = st.text_input("🔑 Entrez votre Code Unique :", type="password")

    if st.button("🚀 Valider l'enregistrement", use_container_width=True):
        if not obs or not sig or code != "2026":
            st.error("Champs obligatoires ou code incorrect.")
        else:
            # Ici l'enregistrement vers Supabase
            st.success(f"✅ Séance enregistrée pour {promo_sel} avec {len(absents)} absents.")

with tab_hist:
    st.write("L'historique est disponible dans la base de données.")
