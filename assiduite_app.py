import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Plateforme EDT 2026", layout="wide")

# Titre officiel requis
TITRE = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- 2. CONNEXION SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 3. CHARGEMENT ET NETTOYAGE RIGOUREUX ---
@st.cache_data(ttl=60)
def load_and_sync_data():
    # Chargement des deux fichiers
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    df_etud = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    
    # Nettoyage de l'EDT
    df_edt = df_edt.dropna(how='all')
    df_edt['Enseignants'] = df_edt['Enseignants'].astype(str).str.strip()
    df_edt['Promotion'] = df_edt['Promotion'].astype(str).str.strip().str.upper()
    df_edt['Enseignements'] = df_edt['Enseignements'].astype(str).str.strip()
    
    # Nettoyage Étudiants (Nettoyage des noms de colonnes d'abord)
    df_etud.columns = [str(c).strip() for c in df_etud.columns]
    df_etud = df_etud.dropna(how='all')
    
    # Mapping dynamique selon vos noms de colonnes
    df_etud['C_NOM'] = df_etud['Nom'].astype(str).str.strip().str.upper()
    df_etud['C_PRENOM'] = df_etud['Prénom'].astype(str).str.strip().str.title()
    df_etud['C_GROUPE'] = df_etud['Groupe'].astype(str).str.strip().str.upper()
    df_etud['C_SG'] = df_etud['Sous groupe'].astype(str).str.strip().str.upper()
    df_etud['C_PROMO'] = df_etud['Promotion'].astype(str).str.strip().str.upper()
    
    df_etud['DISPLAY_NAME'] = df_etud['C_NOM'] + " " + df_etud['C_PRENOM']
    
    return df_edt, df_etud

# Initialisation
try:
    df_edt, df_etudiants = load_and_sync_data()
except Exception as e:
    st.error(f"Erreur de lecture : Vérifiez que les colonnes 'Nom', 'Prénom', 'Groupe', 'Sous groupe' et 'Promotion' existent. Détail : {e}")
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
    # --- FILTRAGE DYNAMIQUE (EDT) ---
    col_p, col_m = st.columns(2)
    
    with col_p:
        # On récupère les promos de l'enseignant depuis l'EDT
        promos_f = df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique()
        promos_finales = sorted([p for p in promos_f if p != 'NAN' and p != ''])
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", promos_finales)
        
    with col_m:
        # On récupère les matières pour cet enseignant et cette promo
        mats_f = df_edt[(df_edt['Enseignants'] == enseignant_sel) & 
                        (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique()
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", sorted(mats_f))

    # Info séance
    info = df_edt[(df_edt['Enseignants'] == enseignant_sel) & 
                  (df_edt['Promotion'] == promo_sel) & 
                  (df_edt['Enseignements'] == matiere_sel)]
    if not info.empty:
        st.info(f"📍 {info.iloc[0]['Jours']} | {info.iloc[0]['Horaire']} | Lieu: {info.iloc[0]['Lieu']}")

    st.markdown("---")
    st.subheader("📈 État d'Avancement & Appel")
    
    # --- FILTRAGE GROUPES & SOUS-GROUPES (Depuis la liste Étudiants) ---
    df_promo_active = df_etudiants[df_etudiants['C_PROMO'] == promo_sel]
    
    col_g, col_sg = st.columns(2)
    
    with col_g:
        groupes_dispo = sorted(df_promo_active['C_GROUPE'].unique())
        if not groupes_dispo:
            st.warning(f"⚠️ Aucun groupe trouvé pour '{promo_sel}'")
            groupe_sel = None
        else:
            groupe_sel = st.selectbox("👥 Sélectionner le Groupe :", groupes_dispo)
    
    with col_sg:
        if groupe_sel:
            sg_dispo = sorted(df_promo_active[df_promo_active['C_GROUPE'] == groupe_sel]['C_SG'].unique())
            sg_sel = st.selectbox("🔢 Sélectionner le Sous-groupe :", sg_dispo)
        else:
            sg_sel = st.selectbox("🔢 Sélectionner le Sous-groupe :", ["-"])

    # --- SECTION STATISTIQUES ---
    st.markdown("##### 📊 Statistiques de présence")
    c1, c2, c3 = st.columns(3)
    
    eff_p = len(df_promo_active)
    eff_g = len(df_promo_active[df_promo_active['C_GROUPE'] == groupe_sel]) if groupe_sel else 0
    eff_s = len(df_promo_active[(df_promo_active['C_GROUPE'] == groupe_sel) & (df_promo_active['C_SG'] == sg_sel)]) if groupe_sel else 0

    c1.metric("Effectif Promotion", eff_p)
    c2.metric(f"Effectif {groupe_sel if groupe_sel else '-'}", eff_g)
    c3.metric(f"Effectif {sg_sel if groupe_sel else '-'}", eff_s)

    # --- TYPE ET NUMÉRO ---
    st.markdown("<br>", unsafe_allow_html=True)
    col_t, col_n = st.columns(2)
    with col_t:
        type_u = st.selectbox("Type d'unité :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°", "Examen"])
    with col_n:
        num_u = st.number_input("Numéro :", min_value=1, step=1, value=1)

    # --- LISTE D'APPEL ---
    st.markdown("**❌ Sélectionner les ABSENTS :**")
    if groupe_sel:
        df_appel = df_promo_active[(df_promo_active['C_GROUPE'] == groupe_sel) & 
                                   (df_promo_active['C_SG'] == sg_sel)]
        liste_noms = sorted(df_appel['DISPLAY_NAME'].tolist())
        
        absents = st.multiselect(
            "Sélection",
            options=liste_noms,
            label_visibility="collapsed",
            placeholder=f"Liste des {len(liste_noms)} étudiants du {sg_sel}"
        )
    else:
        st.info("Sélectionnez d'abord un groupe.")

    # --- FORMULAIRE FINAL ---
    date_s = st.date_input("📅 Date réelle de la séance :")
    obs = st.text_area("🗒️ Observations (Obligatoire) :")
    sig = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    code_v = st.text_input("🔑 Entrez votre Code Unique :", type="password")

    if st.button("🚀 Valider l'enregistrement", use_container_width=True):
        if not obs or not sig or code_v != "2026":
            st.error("Champs obligatoires ou code incorrect.")
        else:
            try:
                # Logique d'envoi Supabase ici...
                st.success(f"✅ Séance enregistrée ! Absents : {len(absents)} / {eff_s}")
            except Exception as e:
                st.error(f"Erreur : {e}")

with tab_hist:
    st.write("Historique disponible dans la base de données.")
