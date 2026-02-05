import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Plateforme EDT 2026", layout="wide")

# Titre officiel requis par l'utilisateur
TITRE = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- 2. CONNEXION SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 3. CHARGEMENT ET NETTOYAGE DES FICHIERS ---
@st.cache_data(ttl=60)
def load_all_data():
    # Chargement du fichier EDT (Contient les colonnes : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion)
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    
    # Chargement du fichier Étudiants (Contient : Nom, Prénom, Groupe, Sous groupe, Promotion)
    df_etud = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    
    # Nettoyage global
    df_edt = df_edt.dropna(how='all')
    df_etud = df_etud.dropna(how='all')

    # Nettoyage spécifique de l'EDT pour le filtrage
    df_edt['Enseignants'] = df_edt['Enseignants'].astype(str).str.strip()
    df_edt['Promotion'] = df_edt['Promotion'].astype(str).str.strip().str.upper()
    df_edt['Enseignements'] = df_edt['Enseignements'].astype(str).str.strip()
    
    # Nettoyage Étudiants (Index : 0:Nom, 1:Prénom, 2:Groupe, 3:SG, 4:Promotion)
    df_etud['C_NOM'] = df_etud.iloc[:, 0].astype(str).str.strip().str.upper()
    df_etud['C_PRENOM'] = df_etud.iloc[:, 1].astype(str).str.strip().str.title()
    df_etud['C_GROUPE'] = df_etud.iloc[:, 2].astype(str).str.strip()
    df_etud['C_SG'] = df_etud.iloc[:, 3].astype(str).str.strip()
    df_etud['C_PROMO'] = df_etud.iloc[:, 4].astype(str).str.strip().str.upper()
    df_etud['DISPLAY_NAME'] = df_etud['C_NOM'] + " " + df_etud['C_PRENOM']
    
    return df_edt, df_etud

# Initialisation
try:
    df_edt, df_etudiants = load_all_data()
except Exception as e:
    st.error(f"Erreur de lecture des fichiers Excel : {e}")
    st.stop()

# --- 4. INTERFACE UTILISATEUR ---

st.subheader("🔑 Validation Enseignant")
email_prof = st.text_input("Entrez votre Email professionnel :", key="email_prof")

st.markdown(f"#### {TITRE}")

st.subheader("👤 1. Sélectionner l'Enseignant :")
liste_profs = sorted(df_edt['Enseignants'].unique())
enseignant_sel = st.selectbox("Sélection", liste_profs, label_visibility="collapsed")

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    # --- FILTRAGE DYNAMIQUE BASÉ SUR L'EDT ---
    col_p, col_m = st.columns(2)
    
    with col_p:
        # On filtre les promotions où cet enseignant intervient (selon le fichier DATA)
        promos_filtrees = df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique()
        promos_finales = sorted([p for p in promos_filtrees if p != 'NAN'])
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", promos_finales)
        
    with col_m:
        # On filtre les matières de cet enseignant POUR cette promotion spécifique
        matieres_filtrees = df_edt[
            (df_edt['Enseignants'] == enseignant_sel) & 
            (df_edt['Promotion'] == promo_sel)
        ]['Enseignements'].unique()
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", sorted(matieres_filtrees))

    # Affichage des informations de la séance (Horaire, Lieu, Jours)
    info_seance = df_edt[
        (df_edt['Enseignants'] == enseignant_sel) & 
        (df_edt['Promotion'] == promo_sel) & 
        (df_edt['Enseignements'] == matiere_sel)
    ]
    
    if not info_seance.empty:
        st.info(f"📍 {info_seance.iloc[0]['Jours']} | {info_seance.iloc[0]['Horaire']} | Lieu: {info_seance.iloc[0]['Lieu']}")

    st.markdown("---")
    st.subheader("📈 État d'Avancement & Appel")
    
    # --- FILTRES GROUPES & SOUS-GROUPES (Issus de la liste étudiants) ---
    col_g, col_sg = st.columns(2)
    
    df_promo_active = df_etudiants[df_etudiants['C_PROMO'] == promo_sel]
    
    with col_g:
        groupes_dispo = sorted(df_promo_active['C_GROUPE'].unique())
        groupe_sel = st.selectbox("👥 Sélectionner le Groupe :", groupes_dispo)
    
    with col_sg:
        sg_dispo = sorted(df_promo_active[df_promo_active['C_GROUPE'] == groupe_sel]['C_SG'].unique())
        sg_sel = st.selectbox("🔢 Sélectionner le Sous-groupe :", sg_dispo)

    # --- STATISTIQUES NUMÉRIQUES ---
    st.markdown("##### 📊 Statistiques de présence")
    c1, c2, c3 = st.columns(3)
    
    total_p = len(df_promo_active)
    total_g = len(df_promo_active[df_promo_active['C_GROUPE'] == groupe_sel])
    total_s = len(df_promo_active[(df_promo_active['C_GROUPE'] == groupe_sel) & (df_promo_active['C_SG'] == sg_sel)])

    c1.metric("Effectif Promotion", total_p)
    c2.metric(f"Effectif {groupe_sel}", total_g)
    c3.metric(f"Effectif {sg_sel}", total_s)

    # --- TYPE ET NUMÉRO ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_t, col_n = st.columns(2)
    with col_t:
        type_u = st.selectbox("Type d'unité :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°", "Examen"])
    with col_n:
        num_u = st.number_input("Numéro :", min_value=1, step=1)

    # --- LISTE DES ABSENTS ---
    df_appel = df_promo_active[(df_promo_active['C_GROUPE'] == groupe_sel) & (df_promo_active['C_SG'] == sg_sel)]
    liste_noms = sorted(df_appel['DISPLAY_NAME'].tolist())

    st.markdown("**❌ Sélectionner les ABSENTS :**")
    absents_choisis = st.multiselect(
        "Sélection",
        options=liste_noms,
        label_visibility="collapsed",
        placeholder=f"Liste des {len(liste_noms)} étudiants du {sg_sel}"
    )

    # --- VALIDATION FINALE ---
    date_seance = st.date_input("📅 Date réelle de la séance :")
    obs = st.text_area("🗒️ Observations (Obligatoire) :")
    sig = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    code_val = st.text_input("🔑 Entrez votre Code Unique :", type="password")

    if st.button("🚀 Valider l'enregistrement", use_container_width=True):
        if not obs or not sig or code_val != "2026":
            st.error("Champs obligatoires manquants ou code incorrect (2026).")
        else:
            try:
                # Envoi vers la table Supabase
                record = {
                    "enseignant": enseignant_sel,
                    "promotion": promo_sel,
                    "matiere": matiere_sel,
                    "groupe": groupe_sel,
                    "sous_groupe": sg_sel,
                    "absents": ", ".join(absents_choisis),
                    "date": str(date_seance),
                    "observations": obs,
                    "signature": sig,
                    "type_unite": type_u,
                    "num_unite": num_u
                }
                supabase.table("suivi_assiduite_2026").insert(record).execute()
                st.success(f"✅ Enregistrement réussi pour {promo_sel} / {groupe_sel} !")
            except Exception as e:
                st.error(f"Erreur Supabase : {e}")

with tab_hist:
    st.write("Historique des enregistrements (données en temps réel).")
