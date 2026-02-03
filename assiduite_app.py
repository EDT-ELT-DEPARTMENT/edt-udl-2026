import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Assiduité ELT - UDL SBA", layout="wide")

# Titre officiel requis par vos instructions
TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- CONNEXION SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erreur de configuration des secrets Supabase. Vérifiez le panneau Settings.")

# --- CHARGEMENT DES SOURCES DE DONNÉES (GitHub) ---
@st.cache_data
def load_all_data():
    # 1. Chargement de l'EDT (Matières, Lieux, Horaires, Promos)
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    
    # 2. Chargement de la liste nominative des étudiants
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    
    # Préparation du nom complet pour l'appel (Nom en MAJUSCULES + Prénom)
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str).str.upper() + " " + df_etudiants['Prénom'].astype(str)
    
    return df_edt, df_etudiants

df_edt, df_etudiants = load_all_data()

# --- INTERFACE UTILISATEUR ---
st.markdown(f"#### {TITRE_OFFICIEL}")
st.header("📝 Registre d'Assiduité Numérique")
st.info("Sélectionnez votre nom pour filtrer automatiquement vos séances, promotions et lieux.")

# --- ÉTAPE 1 : SÉLECTION DE L'ENSEIGNANT ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 1. Sélectionner votre nom (Enseignant) :", ["-- Choisir --"] + liste_profs)

if enseignant_sel != "-- Choisir --":
    
    # --- ÉTAPE 2 : FILTRER LES PROMOTIONS LIÉES À CET ENSEIGNANT ---
    promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
    
    col_p, col_m = st.columns(2)
    
    with col_p:
        promo_sel = st.selectbox("🎓 2. Sélectionner la Promotion :", ["-- Choisir --"] + promos_liees)
    
    if promo_sel != "-- Choisir --":
        
        with col_m:
            # --- ÉTAPE 3 : FILTRER LES MATIÈRES (Enseignant + Promotion) ---
            filtre_seance = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
            matieres_dispo = sorted(df_edt[filtre_seance]['Enseignements'].unique())
            matiere_sel = st.selectbox("📖 3. Sélectionner la Matière :", matieres_dispo)

        # --- ÉTAPE 4 : RÉCUPÉRATION AUTOMATIQUE (Lieu, Jour, Horaire) ---
        # On extrait la ligne précise correspondant au trio Enseignant/Promo/Matière
        infos_ligne = df_edt[(df_edt['Enseignants'] == enseignant_sel) & 
                            (df_edt['Promotion'] == promo_sel) & 
                            (df_edt['Enseignements'] == matiere_sel)].iloc[0]
        
        lieu_auto = infos_ligne['Lieu']
        jour_auto = infos_ligne['Jours']
        horaire_auto = infos_ligne['Horaire']

        # Affichage des informations de planification pour confirmation
        st.success(f"📍 **Détails planifiés :** {jour_auto} à {horaire_auto} | **Lieu :** {lieu_auto}")

        st.divider()

        # --- ÉTAPE 5 : CHARGEMENT DE LA LISTE DES ÉTUDIANTS ---
        # On filtre la liste des étudiants par la promotion choisie
        etudiants_final = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())

        if etudiants_final:
            st.subheader(f"👥 Appel des étudiants : {promo_sel}")
            absents_sel = st.multiselect(
                "❌ Cochez uniquement les étudiants ABSENTS :", 
                options=etudiants_final,
                help="Tapez les premières lettres du nom pour filtrer la liste."
            )
            
            # --- FORMULAIRE D'ENREGISTREMENT FINAL ---
            with st.form("form_final"):
                st.markdown("##### Validation de la séance")
                col_date, col_code = st.columns(2)
                
                with col_date:
                    date_reelle = st.date_input("📅 Date réelle du cours :")
                
                with col_code:
                    code_verif = st.text_input("🔑 Code de validation (2026) :", type="password")
                
                note_obs = st.text_area("🗒️ Thème du cours / Observations :", placeholder="Ex: Suite du chapitre 2, Absence délégué...")

                st.write(f"📊 **Récapitulatif :** {len(absents_sel)} étudiant(s) marqué(s) absent(s).")
                
                btn_envoyer = st.form_submit_button("🚀 ENREGISTRER DANS LA BASE DE DONNÉES", use_container_width=True)

            if btn_envoyer:
                if code_verif == "2026":
                    try:
                        # On concatène les infos de temps et de lieu dans la note ou des colonnes si vous les créez
                        texte_absents = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                        
                        # Construction du pack de données pour Supabase
                        data_payload = {
                            "enseignant": enseignant_sel,
                            "matiere": matiere_sel,
                            "promotion": promo_sel,
                            "absents": texte_absents,
                            "note_etudiant": f"Date: {date_reelle} | Prévu: {jour_auto} {horaire_auto} | Lieu: {lieu_auto} | Obs: {note_obs}"
                        }
                        
                        # Envoi vers la table dédiée
                        supabase.table("suivi_assiduite_2026").insert(data_payload).execute()
                        
                        st.success(f"✅ L'appel pour {matiere_sel} a été enregistré avec succès !")
                        st.balloons()
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'enregistrement : {e}")
                else:
                    st.error("⚠️ Code de validation incorrect. Les données n'ont pas été envoyées.")
        else:
            st.warning(f"⚠️ Aucun étudiant trouvé pour la promotion '{promo_sel}' dans votre fichier Excel.")
else:
    st.write("👋 Veuillez sélectionner votre nom d'enseignant pour afficher vos cours.")
