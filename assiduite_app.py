import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Assiduité - Département Electrotechnique", layout="wide")

# Titre officiel requis
TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Connexion Supabase via Secrets
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erreur de configuration des secrets Supabase.")

# Interface
st.image("logo.PNG", width=70) if "logo.PNG" else None
st.markdown(f"### {TITRE_OFFICIEL}")
st.header("📝 Registre d'Assiduité des Étudiants")

# Formulaire de saisie
with st.container():
    with st.form("form_assiduite", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            ens = st.text_input("👤 Nom de l'Enseignant :")
            prom = st.selectbox("🎓 Promotion :", ["L2 ELT", "L3 ELT", "M1 RE", "M2 RE", "M1 EP", "M2 EP", "ING 1", "ING 2"])
        
        with col2:
            mat = st.text_input("📖 Matière / Module :")
            # Note: La colonne 'date' n'est pas dans votre capture, on peut l'inclure dans 'note_etudiant' ou l'ignorer
            date_info = datetime.now().strftime("%d/%m/%Y %H:%M")

        st.markdown("---")
        abs_list = st.text_area("❌ Liste des étudiants absents :", placeholder="Ex: Etudiant A, Etudiant B...")
        note_obs = st.text_area("🗒️ Observations sur la séance :", placeholder="Remarques éventuelles...")

        # Code de sécurité pour éviter les envois erronés
        code_secu = st.text_input("🔑 Code de validation :", type="password")
        
        btn_submit = st.form_submit_button("🚀 Enregistrer la séance", use_container_width=True)

if btn_submit:
    if code_secu == "2026":
        if ens and mat and prom:
            try:
                # Mapping strict avec vos colonnes Supabase
                data_to_insert = {
                    "enseignant": ens,
                    "matiere": mat,
                    "promotion": prom,
                    "absents": abs_list,
                    "note_etudiant": f"[{date_info}] {note_obs}"
                }
                
                supabase.table("suivi_assiduite_2026").insert(data_to_insert).execute()
                st.success(f"✅ Séance enregistrée avec succès pour {prom} !")
                st.balloons()
            except Exception as e:
                st.error(f"❌ Erreur lors de l'insertion : {e}")
        else:
            st.warning("Veuillez remplir les champs obligatoires (Enseignant, Matière, Promotion).")
    else:
        st.error("⚠️ Code de validation incorrect.")

# --- NAVIGATION RAPIDE ---
st.sidebar.markdown("---")
st.sidebar.info("💡 Cette application est liée au portail principal.")
# Remplacez l'URL ci-dessous par l'URL de votre application EDT
if st.sidebar.button("📅 Retour à l'Emploi du Temps"):
    st.sidebar.write("Lien : [Cliquez ici pour l'EDT](votre-lien-edt-streamlit)")