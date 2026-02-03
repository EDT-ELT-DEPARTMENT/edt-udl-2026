import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Suivi Assiduité - UDL-SBA", layout="wide")

# Titre officiel
st.markdown("### Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
st.header("📝 Registre de Suivi de l'Assiduité")

# Connexion Supabase (utilisez vos secrets Streamlit)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- FORMULAIRE D'ENREGISTREMENT ---
with st.container():
    st.info("Veuillez remplir les informations de la séance ci-dessous.")
    
    with st.form("form_assiduite"):
        col1, col2 = st.columns(2)
        
        with col1:
            enseignant = st.text_input("👤 Nom de l'Enseignant :")
            promotion = st.selectbox("🎓 Promotion :", ["L2 ELT", "L3 ELT", "M1 RE", "M2 RE", "M1 EP", "M2 EP", "ING 1", "ING 2"])
        
        with col2:
            matiere = st.text_input("📖 Matière / Module :")
            date_seance = st.date_input("📅 Date de la séance :", datetime.now())

        st.markdown("---")
        absents = st.text_area("❌ Liste des étudiants absents :", placeholder="Ex: Nom Prénom (Matricule), ...")
        note = st.text_area("🗒️ Observations / Notes sur l'étudiant :", placeholder="Commentaires éventuels sur le déroulement...")

        code_verif = st.text_input("🔑 Code Validation :", type="password")
        
        submit = st.form_submit_button("🚀 Valider et Envoyer à la Base de Données", use_container_width=True)

if submit:
    if code_verif == "2026":
        try:
            # Mapping exact avec vos colonnes Supabase : enseignant, matiere, promotion, absents, note_etudiant
            payload = {
                "enseignant": enseignant,
                "matiere": matiere,
                "promotion": promotion,
                "absents": absents,
                "note_etudiant": note
            }
            
            supabase.table("suivi_assiduite_2026").insert(payload).execute()
            st.success("✅ Données enregistrées avec succès dans la table 'suivi_assiduite_2026' !")
        except Exception as e:
            st.error(f"❌ Erreur de connexion : {e}")
    else:
        st.error("⚠️ Code de validation incorrect.")

# --- VUE ADMINISTRATION (OPTIONNELLE) ---
st.divider()
if st.checkbox("🔍 Afficher l'historique des saisies"):
    admin_code = st.text_input("Code Admin :", type="password")
    if admin_code == "admin2026":
        res = supabase.table("suivi_assiduite_2026").select("*").execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)