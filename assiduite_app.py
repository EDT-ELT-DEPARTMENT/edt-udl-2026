import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURATION ---
st.set_page_config(page_title="Assiduité ELT", layout="wide")
TITRE = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data
def load_data():
    # Chargement de l'EDT pour les profs/matières
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    # Chargement des étudiants
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str) + " " + df_etudiants['Prénom'].astype(str)
    return df_edt, df_etudiants

df_edt, df_etudiants = load_data()

st.markdown(f"### {TITRE}")
st.header("📝 Registre d'Assiduité Numérique")

# --- LOGIQUE DE FILTRAGE HORS FORMULAIRE POUR RÉACTIVITÉ ---

col1, col2 = st.columns(2)

with col1:
    # 1. Sélection Enseignant
    liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
    enseignant_sel = st.selectbox("👤 Choisir Enseignant :", ["-- Sélectionner --"] + liste_profs)

with col2:
    # 2. Filtrage des Matières selon l'Enseignant choisi
    if enseignant_sel != "-- Sélectionner --":
        matieres_dispo = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Enseignements'].unique())
    else:
        matieres_dispo = []
    matiere_sel = st.selectbox("📖 Matière (Filtrée) :", matieres_dispo)

col3, col4 = st.columns(2)

with col3:
    # 3. Sélection Promotion
    liste_promos = sorted(df_etudiants['Promotion'].dropna().unique())
    promo_sel = st.selectbox("🎓 Promotion :", ["-- Sélectionner --"] + liste_promos)

with col4:
    date_jour = st.date_input("📅 Date :")

st.divider()

# --- SÉLECTION DES ÉTUDIANTS ---
if promo_sel != "-- Sélectionner --":
    # Filtrer les étudiants de la promo choisie
    liste_etudiants_promo = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())
    
    # Multiselect qui s'affiche seulement si une promo est choisie
    absents_sel = st.multiselect(f"❌ Sélectionner les étudiants ABSENTS de {promo_sel} :", liste_etudiants_promo)
else:
    st.info("💡 Veuillez sélectionner une promotion pour afficher la liste des étudiants.")
    absents_sel = []

# --- VALIDATION DANS UN FORMULAIRE ---
with st.form("validation_appel"):
    note_obs = st.text_area("🗒️ Observations / Thème de la séance :")
    code_verif = st.text_input("🔑 Code Validation :", type="password")
    
    submit = st.form_submit_button("🚀 Valider l'appel et enregistrer", use_container_width=True)

if submit:
    if code_verif == "2026" and enseignant_sel != "-- Sélectionner --" and promo_sel != "-- Sélectionner --":
        try:
            liste_absents_txt = ", ".join(absents_sel) if absents_sel else "Aucun absent"
            
            data = {
                "enseignant": enseignant_sel,
                "matiere": matiere_sel,
                "promotion": promo_sel,
                "absents": liste_absents_txt,
                "note_etudiant": f"Date: {date_jour} | Obs: {note_obs}"
            }
            
            supabase.table("suivi_assiduite_2026").insert(data).execute()
            st.success(f"✅ Appel enregistré pour {matiere_sel} ({promo_sel}).")
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.error("❌ Veuillez remplir tous les champs et vérifier le code.")
