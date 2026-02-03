import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURATION ---
st.set_page_config(page_title="Assiduité ELT - UDL", layout="wide")
TITRE = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Connexion Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CHARGEMENT DES SOURCES ---
@st.cache_data
def load_all_data():
    # Fichier 1 : EDT pour lier Enseignant -> Promotion -> Matière
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    
    # Fichier 2 : Liste des étudiants pour les noms
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    # Création du nom complet pour l'affichage
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str).str.upper() + " " + df_etudiants['Prénom'].astype(str)
    
    return df_edt, df_etudiants

df_edt, df_etudiants = load_all_data()

# --- INTERFACE ---
st.markdown(f"#### {TITRE}")
st.header("📝 Registre d'Assiduité par Cascade")
st.info("La liste des promotions et des matières se filtre automatiquement selon l'enseignant choisi.")

# --- ÉTAPE 1 : SÉLECTION DE L'ENSEIGNANT ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 1. Sélectionner l'Enseignant :", ["-- Faire un choix --"] + liste_profs)

if enseignant_sel != "-- Faire un choix --":
    
    # --- ÉTAPE 2 : FILTRER LES PROMOTIONS DE CET ENSEIGNANT ---
    # On cherche dans le fichier EDT les promos liées à cet enseignant
    promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
    
    col1, col2 = st.columns(2)
    
    with col1:
        promo_sel = st.selectbox("🎓 2. Promotion concernée :", ["-- Choisir Promotion --"] + promos_liees)
    
    if promo_sel != "-- Choisir Promotion --":
        
        with col2:
            # --- ÉTAPE 3 : FILTRER LES MATIÈRES (Enseignant + Promotion) ---
            # On cherche les matières que ce prof donne à CETTE promo spécifique
            filtre_matiere = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
            matieres_dispo = sorted(df_edt[filtre_matiere]['Enseignements'].unique())
            matiere_sel = st.selectbox("📖 3. Matière / Module :", matieres_dispo)

        st.divider()

        # --- ÉTAPE 4 : CHARGER LA LISTE DES ÉTUDIANTS ---
        # On filtre le fichier des étudiants selon la promotion sélectionnée
        etudiants_final = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())

        if etudiants_final:
            st.subheader(f"👥 Liste d'appel : {promo_sel}")
            absents_sel = st.multiselect(
                "❌ Cochez les étudiants ABSENTS :", 
                options=etudiants_final,
                help="Vous pouvez taper le nom pour chercher plus vite."
            )
            
            # --- FORMULAIRE FINAL POUR L'ENVOI ---
            with st.form("envoi_assiduite"):
                date_seance = st.date_input("📅 Date de la séance :")
                note_obs = st.text_area("🗒️ Thème traité / Observations :", placeholder="Ex: TD n°2, chapitre asservissement...")
                
                st.write(f"**Récapitulatif :** {len(absents_sel)} étudiant(s) absent(s) sur {len(etudiants_final)}.")
                
                code_verif = st.text_input("🔑 Code de validation (2026) :", type="password")
                
                btn_valider = st.form_submit_button("🚀 Enregistrer l'assiduité dans Supabase", use_container_width=True)

            if btn_valider:
                if code_verif == "2026":
                    try:
                        # Préparation du texte des absents
                        texte_absents = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                        
                        data_insert = {
                            "enseignant": enseignant_sel,
                            "matiere": matiere_sel,
                            "promotion": promo_sel,
                            "absents": texte_absents,
                            "note_etudiant": f"Date: {date_seance} | Obs: {note_obs}"
                        }
                        
                        supabase.table("suivi_assiduite_2026").insert(data_insert).execute()
                        st.success(f"✅ Succès ! L'appel pour le cours de {matiere_sel} a été enregistré.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erreur technique : {e}")
                else:
                    st.error("⚠️ Code de validation incorrect.")
        else:
            st.warning(f"⚠️ Aucun étudiant trouvé dans le fichier Excel pour la promotion '{promo_sel}'.")

else:
    st.write("👉 Veuillez sélectionner un enseignant pour commencer l'appel.")
