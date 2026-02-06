import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- 2. INITIALISATION SUPABASE (SÉCURISÉE) ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Erreur de configuration Supabase : {e}")
        return None

supabase = init_connection()

# --- 3. CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel("dataEDT-ELT-S2-2026.xlsx")
        df_s = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
        df_staff = pd.read_excel("Permanents-Vacataires-ELT2-2025-2026.xlsx")
        
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip().upper() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', '<NA>', ''], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur chargement Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()

# --- 4. GESTION DE LA SESSION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    # [Ici vos onglets de login/inscription avec supabase.table("enseignants_auth")...]
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]

# Correction de l'affichage "None"
def clean_val(val):
    v = str(val).strip()
    return "" if v.upper() in ["NONE", "NAN", ""] else v

nom_o = clean_val(user.get('nom_officiel', ''))
pre_o = clean_val(user.get('prenom_officiel', ''))
grade_o = clean_val(user.get('grade_enseignant', 'Enseignant'))
nom_complet = f"{nom_o} {pre_o}".strip() or user.get('email')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {nom_complet}")
    st.info(f"**Grade :** {grade_o}")
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

# --- TABS ---
t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Admin"])

with t_saisie:
    if supabase:
        st.markdown("### 📝 Nouveau Rapport de Séance")
        # [Logique de saisie...]
    else:
        st.error("Base de données non disponible.")

with t_admin:
    is_admin = (user.get('email') == "milouafarid@gmail.com")
    if is_admin:
        st.markdown("#### 🛡️ Tableau de bord global")
        if supabase:
            try:
                # Appel sécurisé
                res_all = supabase.table("archives_absences").select("*").execute()
                if res_all.data:
                    df_all = pd.DataFrame(res_all.data)
                    st.dataframe(df_all, use_container_width=True)
                else:
                    st.info("Aucune donnée dans les archives.")
            except Exception as e:
                st.error(f"Erreur lors de la récupération : {e}")
        else:
            st.error("Supabase n'est pas initialisé.")
    else:
        st.error("Accès restreint.")
