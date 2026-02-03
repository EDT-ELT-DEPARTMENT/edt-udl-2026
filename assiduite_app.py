import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURATION & TITRE ---
st.set_page_config(page_title="Assiduité ELT", layout="wide")
TITRE = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CHARGEMENT DES DONNÉES EXCEL (Depuis GitHub) ---
@st.cache_data
def load_data():
    # Chargement des matières et enseignants
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    # Chargement de la liste des étudiants
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    # Création d'une colonne Nom Complet
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str) + " " + df_etudiants['Prénom'].astype(str)
    return df_edt, df_etudiants

df_edt, df_etudiants = load_data()

# --- INTERFACE ---
st.markdown(f"### {TITRE}")
st.header("📝 Registre d'Assiduité Numérique")

with st.form("form_assiduite"):
    col1, col2 = st.columns(2)
    
    with col1:
        # Liste déroulante des enseignants depuis votre Excel
        liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
        enseignant_sel = st.selectbox("👤 Enseignant :", liste_profs)
        
        # Liste des promotions
        liste_promos = sorted(df_etudiants['Promotion'].dropna().unique())
        promo_sel = st.selectbox("🎓 Promotion :", liste_promos)

    with col2:
        # Liste des matières
        liste_matieres = sorted(df_edt['Enseignements'].dropna().unique())
        matiere_sel = st.selectbox("📖 Matière :", liste_matieres)
        
        date_jour = st.date_input("📅 Date de la séance :")

    st.divider()
    
    # --- SÉLECTION DES ABSENTS ---
    # On filtre les étudiants selon la promotion choisie
    etudiants_promo = df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist()
    absents_sel = st.multiselect("❌ Sélectionner les étudiants ABSENTS :", etudiants_promo)
    
    note_obs = st.text_area("🗒️ Observations / Thème de la séance :")
    
    code_verif = st.text_input("🔑 Code Validation :", type="password")
    
    submit = st.form_submit_button("🚀 Valider l'appel et enregistrer", use_container_width=True)

if submit:
    if code_verif == "2026":
        try:
            # Préparation des données pour Supabase
            # On transforme la liste des absents en texte séparé par des virgules
            liste_absents_txt = ", ".join(absents_sel)
            
            data = {
                "enseignant": enseignant_sel,
                "matiere": matiere_sel,
                "promotion": promo_sel,
                "absents": liste_absents_txt,
                "note_etudiant": f"Date: {date_jour} | Obs: {note_obs}"
            }
            
            supabase.table("suivi_assiduite_2026").insert(data).execute()
            st.success(f"✅ Appel enregistré ! {len(absents_sel)} étudiant(s) marqué(s) absent(s).")
        except Exception as e:
            st.error(f"Erreur lors de l'envoi : {e}")
    else:
        st.error("❌ Code incorrect.")