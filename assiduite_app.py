import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import random
import string
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 EMAILS ADMINISTRATION
EMAIL_CHEF_DEPT = "chef.department.elt.fge@gmail.com"
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur de configuration Supabase.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'NAN'], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

def get_staff_info(user_nom, user_email):
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    if not match.empty:
        g = match.iloc[0].get('Grade', 'Enseignant')
        s = match.iloc[0].get('Qualité', 'Permanent')
        return g, s
    return "Enseignant", "Permanent"

def extraire_heure_debut(creneau):
    try:
        return float(creneau.split('-')[0].split('h')[0].strip().replace(':', '.'))
    except: return 99.0

# --- FONCTION D'INSERTION SÉCURISÉE ---
def safe_insert(table_name, data_dict):
    """Tente d'insérer les données, et réessaie avec moins de colonnes en cas d'erreur API."""
    try:
        return supabase.table(table_name).insert(data_dict).execute()
    except Exception:
        # Si ça échoue, on retire les colonnes récentes (statut, regime) qui pourraient manquer en SQL
        cols_a_retirer = ["statut_enseignant", "regime_heure", "observations", "categorie_seance"]
        for col in cols_a_retirer:
            data_dict.pop(col, None)
        return supabase.table(table_name).insert(data_dict).execute()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié"])
    
    with t_login:
        email_log = st.text_input("Email :", key="log_email")
        pass_log = st.text_input("Code Unique :", type="password", key="log_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Nom :", sorted(df_staff['Full_S'].unique()))
        info_s = df_staff[df_staff['Full_S'] == choix].iloc[0]
        st.info(f"Grade : {info_s['Grade']} | Statut : {info_s['Qualité']}")
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Code :", type="password")
        if st.button("Valider"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'],
                    "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']
                }).execute()
                st.success("Compte créé.")
            except: st.error("Erreur insertion.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
current_grade, current_statut = get_staff_info(user['nom_officiel'], user['email'])

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}\n**{current_grade}** ({current_statut})")
    st.divider()
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
        st.divider()
        if st.button("🗑️ VIDER LES ARCHIVES"):
            st.session_state["confirm_reset"] = True
        if st.session_state.get("confirm_reset"):
            confirm_p = st.text_input("Code pour confirmer :", type="password")
            if st.button("OUI, TOUT SUPPRIMER"):
                if hash_pw(confirm_p) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base vidée.")
                    st.session_state["confirm_reset"] = False
                    st.rerun()
    else: enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("Séance :", ["Cours", "TD", "TP", "Examen"])
    reg_s = c2.selectbox("Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("Date :", value=datetime.now())

    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    m_sel = st.selectbox("Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])

    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    g_sel = st.selectbox("Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    sg_sel = st.selectbox("Sous-groupe :", sorted(df_p_full[df_p_full['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p_full.empty else ["SG1"])

    df_appel = df_p_full[(df_p_full['Groupe']==g_sel) & (df_p_full['Sous groupe']==sg_sel)].copy()
    df_appel['Full_S'] = (df_appel['Nom'].fillna('') + " " + df_appel['Prénom'].fillna('')).str.upper().str.strip()
    liste_etudiants = df_appel['Full_S'].tolist()

    col_abs, col_note = st.columns(2)
    with col_abs:
        abs_coll = st.checkbox("🚩 ABSENCE COLLECTIVE")
        absents_sel = liste_etudiants if abs_coll else st.multiselect("❌ Absents :", options=liste_etudiants)
    with col_note:
        et_a_noter = st.selectbox("📝 Noter un étudiant :", ["Aucun"] + liste_etudiants)
        val_note = st.text_input("Valeur :", "0")

    obs_txt = st.text_area("🗒️ Observations :")
    code_v = st.text_input("🔑 Code Validation :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            meta = {
                "promotion": p_sel, "matiere": m_sel, 
                "enseignant": f"{current_grade} {user['nom_officiel']}", 
                "statut_enseignant": current_statut,
                "date_seance": str(date_s), "regime_heure": reg_s,
                "categorie_seance": cat_s, "observations": obs_txt
            }
            # Utilisation de safe_insert pour éviter les erreurs API
            for ab in absents_sel:
                r = meta.copy(); r.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                safe_insert("archives_absences", r)
            if et_a_noter != "Aucun":
                rn = meta.copy(); rn.update({"etudiant_nom": et_a_noter, "note_evaluation": val_note})
                safe_insert("archives_absences", rn)
            st.success("✅ Séance archivée.")
            st.balloons()
        else: st.error("Code incorrect.")

with tab_suivi:
    df_etudiants['Full_S'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()
    et_search = st.selectbox("🎯 Étudiant :", ["--"] + sorted(df_etudiants['Full_S'].unique()))
    if et_search != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_search).execute()
        if res.data:
            df_res = pd.DataFrame(res.data)
            st.table(df_res[['date_seance', 'matiere', 'enseignant', 'note_evaluation']])
            buf = io.BytesIO(); df_res.to_excel(buf, index=False)
            st.download_button("📥 Télécharger Excel", buf.getvalue(), f"Suivi_{et_search}.xlsx")

with tab_hist:
    all_res = supabase.table("archives_absences").select("*").execute()
    if all_res.data:
        df_glob = pd.DataFrame(all_res.data)
        st.dataframe(df_glob, use_container_width=True)
        buf_g = io.BytesIO(); df_glob.to_excel(buf_g, index=False)
        st.download_button("📊 Exporter tout", buf_g.getvalue(), "Archives.xlsx")
