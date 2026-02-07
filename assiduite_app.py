import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Fichiers sources
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# --- 2. CONNEXION SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Erreur Supabase : {e}")
        return None

supabase = init_connection()

# --- 3. CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur lecture Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

# Préparation Nom Complet
if 'Nom' in df_etudiants.columns:
    df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper()
else:
    df_etudiants['Full_N'] = (df_etudiants['NOM'] + " " + df_etudiants['PRÉNOM']).str.upper()

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    with st.container():
        e_log = st.text_input("Email Professionnel :", key="auth_email")
        p_log = st.text_input("Code Unique :", type="password", key="auth_pass")
        if st.button("Se connecter", use_container_width=True, key="auth_btn"):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).execute()
            if res.data and res.data[0]['password_hash'] == hashlib.sha256(str.encode(p_log)).hexdigest():
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

# Barre latérale (Sidebar)
with st.sidebar:
    st.markdown(f"### 👤 {user.get('nom_officiel', 'Enseignant')}")
    st.markdown(f"**Grade :** {user.get('grade_enseignant', 'N/A')}")
    st.markdown(f"**Statut :** Permanent")
    st.divider()
    
    # SOLUTION DUPLICATE ID : On force une clé unique
    if is_admin:
        ens_actif = st.selectbox(
            "Vue Simulation (Admin) :", 
            sorted(df_edt['Enseignants'].unique()),
            key="admin_sim_selectbox" 
        )
    else:
        ens_actif = user.get('nom_officiel', '')

    if st.button("🚪 Déconnexion", key="logout_sidebar"):
        st.session_state["user_data"] = None
        st.rerun()

# --- ONGLES ---
t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True, key="radio_regime")
    
    col1, col2 = st.columns(2)
    type_seance = col1.selectbox("Type :", ["Cours", "TD", "TP", "Examen"], key="sel_type")
    date_s = col2.date_input("Date réelle :", value=datetime.now(), key="date_saisie")
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()), key="sel_promo")
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    c_g, c_sg = st.columns(2)
    g_sel = c_g.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()), key="sel_group")
    sg_sel = c_sg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()), key="sel_sgroup")
    
    # Métriques d'effectif
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promo", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"S-Groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    
    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()), key="sel_matiere")

    st.divider()
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    absents = st.multiselect("Sélectionner les absents :", options=eff_liste['Full_N'].tolist(), key="multi_absents")
    nature_abs = st.selectbox("Nature :", ["Absence non justifiée", "Absence justifiée", "Exclusion"], key="sel_nature")

    st.markdown("### 📝 Notation / Participation")
    etudiant_note = st.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist(), key="sel_cible_note")
    critere = st.selectbox("Critère :", ["Test", "Participation", "Interrogation"], key="sel_critere")
    val_note = st.text_input("Note ou Observation :", key="input_note")

    obs_gen = st.text_area("🗒️ Observations générales :", key="area_obs")
    code_v = st.text_input("🔑 Confirmer avec votre Code Unique :", type="password", key="input_confirm")
    
    if st.button("🚀 VALIDER LE RAPPORT", type="primary", use_container_width=True, key="btn_valider"):
        # Logique de validation ici
        st.success("Rapport enregistré avec succès !")

with t_suivi:
    st.subheader("🔍 Suivi des dossiers")
    search = st.selectbox("Rechercher un étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()), key="search_etudiant")

with t_admin:
    if is_admin:
        st.subheader("🛡️ Administration")
        st.write("Registre global des absences.")
    else:
        st.warning("Accès restreint.")
