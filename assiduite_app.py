import streamlit as st
import pandas as pd
import hashlib
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")
TITRE_PLATEFORME = "Plateforme de gestion des enseignements et assiduité des étudiants du département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- Chargement des données (Idem précédent) ---
@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel("dataEDT-ELT-S2-2026.xlsx")
        df_s = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
        df_staff = pd.read_excel("Permanents-Vacataires-ELT2-2025-2026.xlsx")
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip().upper() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', ''], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()

# Préparation Full_N
if 'NOM' in df_etudiants.columns and 'PRÉNOM' in df_etudiants.columns:
    df_etudiants['FULL_N'] = df_etudiants['NOM'] + " " + df_etudiants['PRÉNOM']

# --- AUTHENTIFICATION (Table enseignants_auth) ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# ... [Bloc Login/Signup du message précédent avec key uniques] ...
# Supposons l'utilisateur connecté pour la suite du script :

if not st.session_state["user_data"]:
    # (Affichez vos onglets login/signup ici comme précédemment)
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]

# Correction de l'affichage du nom (évite le None)
nom_o = str(user.get('nom_officiel', '')).strip()
pre_o = str(user.get('prenom_officiel', '')).strip()
nom_complet = f"{nom_o} {pre_o}".strip()
if nom_complet == "": nom_complet = user.get('email')

is_admin = (user['email'] == "milouafarid@gmail.com")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {nom_complet}")
    st.caption(f"Grade : {user.get('grade_enseignant', 'Enseignant')}")
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

# --- INTERFACE PRINCIPALE ---
t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Admin"])

with t_saisie:
    st.markdown(f"#### ⚙️ Séance du {datetime.now().strftime('%d/%m/%Y')}")
    
    # 1. Sélection Enseignant (Admin peut simuler)
    if is_admin:
        ens_actif = st.selectbox("Simuler un enseignant :", sorted(df_edt['ENSEIGNANTS'].unique()))
    else:
        ens_actif = nom_complet

    # 2. Filtres dynamiques basés sur l'EDT
    mask = df_edt['ENSEIGNANTS'].str.contains(ens_actif, na=False, case=False)
    df_profs_edt = df_edt[mask]
    
    col_a, col_b = st.columns(2)
    with col_a:
        charge = st.radio("Régime :", ["Charge Normale", "Heures Suppl."], horizontal=True)
        promo_sel = st.selectbox("🎓 Promotion :", sorted(df_profs_edt['PROMOTION'].unique()) if not df_profs_edt.empty else sorted(df_edt['PROMOTION'].unique()))
    
    with col_b:
        type_s = st.selectbox("Type :", ["Cours", "TD", "TP", "Examen"])
        matieres_dispo = sorted(df_profs_edt[df_profs_edt['PROMOTION'] == promo_sel]['ENSEIGNEMENTS'].unique())
        matiere_sel = st.selectbox("📖 Matière :", matieres_dispo if matieres_dispo else ["Autre"])

    st.divider()
    
    # 3. Liste d'appel
    df_appel = df_etudiants[df_etudiants['PROMOTION'] == promo_sel]
    if not df_appel.empty:
        st.markdown(f"**Liste d'appel ({len(df_appel)} étudiants) :**")
        absents = st.multiselect("Cocher les étudiants ABSENTS :", options=sorted(df_appel['FULL_N'].unique()))
        
        obs = st.text_area("🗒️ Observations / Thème de la séance :")
        
        if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
            # Enregistrement Supabase
            for nom_absent in absents:
                supabase.table("archives_absences").insert({
                    "promotion": promo_sel,
                    "matiere": matiere_sel,
                    "enseignant": nom_complet,
                    "date_seance": str(datetime.now().date()),
                    "etudiant_nom": nom_absent,
                    "note_evaluation": "ABSENCE",
                    "observations": obs
                }).execute()
            st.success(f"✅ Rapport validé. {len(absents)} absences archivées.")
            st.balloons()
    else:
        st.warning("Aucun étudiant trouvé pour cette promotion.")

with t_suivi:
    st.markdown("#### 🔍 Historique d'un étudiant")
    nom_rech = st.selectbox("Rechercher l'étudiant :", ["--"] + sorted(df_etudiants['FULL_N'].unique()), key="rech_suivi")
    if nom_rech != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_rech).execute()
        if res.data:
            df_res = pd.DataFrame(res.data)
            st.table(df_res[['date_seance', 'matiere', 'enseignant', 'note_evaluation']])
        else:
            st.success("Aucune absence enregistrée pour cet étudiant.")

with t_admin:
    if is_admin:
        st.markdown("#### 🛡️ Tableau de bord global")
        res_all = supabase.table("archives_absences").select("*").execute()
        if res_all.data:
            st.dataframe(pd.DataFrame(res_all.data), use_container_width=True)
            if st.button("📥 Télécharger l'archive complète"):
                # Logique export Excel...
                pass
    else:
        st.error("Accès réservé à l'administration.")
