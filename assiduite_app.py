import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Plateforme EDT 2026", layout="wide")

# Titre officiel rappelé systématiquement
TITRE = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- 2. CONNEXION SUPABASE ---
# Assurez-vous que vos secrets sont bien configurés dans Streamlit Cloud
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 3. CHARGEMENT ET NETTOYAGE DES DONNÉES ---
@st.cache_data(ttl=60)
def load_data_complete():
    # Chargement du fichier EDT (Planning)
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    
    # Chargement du fichier Étudiants (Structure: Nom, Prénom, Groupe, Sous groupe, Promotion)
    df_etud = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    
    # Nettoyage des lignes vides
    df_etud = df_etud.dropna(how='all')
    
    # Extraction et nettoyage par index de colonne
    # 0:Nom | 1:Prénom | 2:Groupe | 3:Sous-groupe | 4:Promotion
    df_etud['C_NOM'] = df_etud.iloc[:, 0].astype(str).str.strip().str.upper()
    df_etud['C_PRENOM'] = df_etud.iloc[:, 1].astype(str).str.strip().str.title()
    df_etud['C_GROUPE'] = df_etud.iloc[:, 2].astype(str).str.strip()
    df_etud['C_SG'] = df_etud.iloc[:, 3].astype(str).str.strip()
    df_etud['C_PROMO'] = df_etud.iloc[:, 4].astype(str).str.strip().str.upper()
    
    # NOUVEAU FORMAT D'AFFICHAGE : Nom Prénom (Groupe | Sous-groupe)
    df_etud['DISPLAY_FULL'] = (
        df_etud['C_NOM'] + " " + 
        df_etud['C_PRENOM'] + " (" + 
        df_etud['C_GROUPE'] + " | " + 
        df_etud['C_SG'] + ")"
    )
    
    return df_edt, df_etud

# Initialisation des données
try:
    df_edt, df_etudiants = load_data_complete()
except Exception as e:
    st.error(f"Erreur lors de la lecture des fichiers Excel : {e}")
    st.stop()

# --- 4. INTERFACE UTILISATEUR (ORDRE DEMANDÉ) ---

st.subheader("🔑 Validation Enseignant")
email_prof = st.text_input("Entrez votre Email professionnel :", key="email_prof")

st.markdown(f"#### {TITRE}")

st.subheader("👤 1. Sélectionner l'Enseignant :")
profs_dispo = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("Sélection Enseignant", profs_dispo, label_visibility="collapsed")

# Système d'Onglets
tab_saisie, tab_historique = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    # Ligne Promotion et Matière
    col_p, col_m = st.columns(2)
    
    with col_p:
        # Liste des promotions (ING1, L1MCIL, M1ME...)
        promos_nettoyees = sorted([p for p in df_etudiants['C_PROMO'].unique() if p != 'NAN'])
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", promos_nettoyees)

    with col_m:
        # Matières selon l'enseignant sélectionné
        matieres_enseignant = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Enseignements'].unique())
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", matieres_enseignant)

    # Affichage dynamique 📍
    info = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    if not info.empty:
        st.info(f"📍 {info.iloc[0]['Jours']} | {info.iloc[0]['Horaire']} | Lieu: {info.iloc[0]['Lieu']}")

    st.markdown("---")
    st.subheader("📈 État d'Avancement & Appel")
    
    # Type et Numéro d'unité
    col_t, col_n = st.columns(2)
    with col_t:
        type_u = st.selectbox("Type d'unité :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°", "Examen"])
    with col_n:
        num_u = st.number_input("Numéro :", min_value=1, value=1, step=1)

    # --- LOGIQUE D'APPEL AVEC GROUPE ET SOUS-GROUPE ---
    # On filtre les étudiants de la promotion choisie
    df_promo_active = df_etudiants[df_etudiants['C_PROMO'] == promo_sel]
    liste_etudiants_visibles = sorted(df_promo_active['DISPLAY_FULL'].tolist())

    st.markdown("**❌ Sélectionner les ABSENTS :**")
    
    if not liste_etudiants_visibles:
        st.warning(f"Aucun étudiant trouvé pour {promo_sel}. Vérifiez la 5ème colonne de l'Excel.")
    
    absents_selectionnes = st.multiselect(
        "Sélection des absents",
        options=liste_etudiants_visibles,
        label_visibility="collapsed",
        placeholder="Choose options"
    )

    # Formulaire de validation
    date_reelle = st.date_input("📅 Date réelle de la séance :")
    observations = st.text_area("🗒️ Observations (Obligatoire) :")
    signature = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    code_securite = st.text_input("🔑 Entrez votre Code Unique :", type="password")

    # Bouton de validation
    if st.button("🚀 Valider l'enregistrement", use_container_width=True):
        if not observations or not signature:
            st.error("Les champs Observations et Signature sont obligatoires.")
        elif code_securite != "2026":
            st.error("Code de validation incorrect. Utilisez '2026'.")
        else:
            try:
                # Préparation des données pour l'enregistrement
                data_to_insert = {
                    "enseignant": enseignant_sel,
                    "promotion": promo_sel,
                    "matiere": matiere_sel,
                    "absents": ", ".join(absents_selectionnes),
                    "date": str(date_reelle),
                    "observations": observations,
                    "signature": signature,
                    "email": email_prof
                }
                supabase.table("suivi_assiduite_2026").insert(data_to_insert).execute()
                st.success(f"✅ Séance enregistrée avec succès pour {promo_sel} !")
            except Exception as e:
                st.error(f"Erreur d'enregistrement : {e}")

with tab_historique:
    st.write("L'historique des appels sera extrait de la base Supabase.")
