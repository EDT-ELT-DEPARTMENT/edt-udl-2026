import streamlit as st
import pandas as pd
import hashlib
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des enseignements et assiduité des étudiants du département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Fichiers sources
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 CONFIGURATION EMAILS
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_CHEF_DEPT = "chef.department.elt.fge@gmail.com"
EMAIL_ADJOINT = "milouafarid@gmail.com"
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Configuration Supabase manquante."); st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_email_rapport(destinataires, sujet, corps):
    try:
        msg = MIMEMultipart(); msg['From'] = EMAIL_SENDER
        msg['To'] = ", ".join(destinataires); msg['Subject'] = sujet
        msg.attach(MIMEText(corps, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls(); server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg); server.quit()
        return True
    except: return False

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip().upper() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', ''], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()

# Préparation colonne Full_N
if 'NOM' in df_etudiants.columns and 'PRÉNOM' in df_etudiants.columns:
    df_etudiants['FULL_N'] = df_etudiants['NOM'] + " " + df_etudiants['PRÉNOM']

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email :").strip().lower()
        p_log = st.text_input("Code :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).execute()
            if res.data and res.data[0]['password_hash'] == hash_pw(p_log):
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")

    with t_signup:
        nom_reg = st.selectbox("NOM :", sorted(df_staff['NOM'].unique()))
        prenom_reg = st.selectbox("PRÉNOM :", sorted(df_staff[df_staff['NOM'] == nom_reg]['PRÉNOM'].unique()))
        email_reg = st.text_input("Email :").strip().lower()
        pass_reg = st.text_input("Code secret :", type="password")
        if st.button("S'inscrire", use_container_width=True):
            match = df_staff[(df_staff['NOM'] == nom_reg) & (df_staff['PRÉNOM'] == prenom_reg)]
            supabase.table("enseignants_auth").insert({
                "email": email_reg, "password_hash": hash_pw(pass_reg),
                "nom_officiel": nom_reg, "prenom_officiel": prenom_reg,
                "grade_enseignant": str(match.iloc[0].get('GRADE', 'N/A')),
                "statut_enseignant": str(match.iloc[0].get('QUALITÉ', 'PERMANENT'))
            }).execute()
            st.success("Compte créé !")

    with t_student:
        nom_st = st.selectbox("Nom Étudiant :", ["--"] + sorted(df_etudiants['FULL_N'].unique().tolist()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['FULL_N'] == nom_st].iloc[0]
            st.info(f"🎓 {nom_st} | Promo : {profil['PROMOTION']} | Groupe : {profil['GROUPE']}")
            edt_st = df_edt[df_edt['PROMOTION'] == profil['PROMOTION']]
            st.dataframe(edt_st[['ENSEIGNEMENTS', 'CODE', 'ENSEIGNANTS', 'HORAIRE', 'JOURS', 'LIEU']], use_container_width=True)
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            if res_abs.data: st.table(pd.DataFrame(res_abs.data)[['date_seance', 'matiere', 'note_evaluation']])
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
nom_complet = f"{user['nom_officiel']} {user['prenom_officiel']}"
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.sidebar.markdown(f"### 👤 {nom_complet}")
st.sidebar.info(f"Grade: {user.get('grade_enseignant', 'N/A')}")
if st.sidebar.button("🚪 Déconnexion"):
    st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Admin"])

with t_saisie:
    st.markdown("### ⚙️ Détails de la Séance")
    col1, col2 = st.columns(2)
    charge = col1.radio("Régime :", ["Charge Normale", "Heures Suppl."], horizontal=True)
    date_s = col2.date_input("Date :", value=datetime.now())
    
    # Filtres dynamiques
    ens_actif = nom_complet if not is_admin else st.selectbox("Admin: Simuler Enseignant", sorted(df_edt['ENSEIGNANTS'].unique()))
    df_p = df_edt[df_edt['ENSEIGNANTS'].str.contains(ens_actif, na=False)]
    
    promo = st.selectbox("🎓 Promotion :", sorted(df_p['PROMOTION'].unique()) if not df_p.empty else ["-"])
    matiere = st.selectbox("📖 Matière :", sorted(df_p[df_p['PROMOTION'] == promo]['ENSEIGNEMENTS'].unique()) if not df_p.empty else ["-"])
    
    # Liste étudiants
    df_eff = df_etudiants[df_etudiants['PROMOTION'] == promo]
    absents = st.multiselect("❌ Étudiants Absents :", options=sorted(df_eff['FULL_N'].unique()))
    obs = st.text_area("🗒️ Observations :")
    
    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        for name in absents:
            supabase.table("archives_absences").insert({
                "promotion": promo, "matiere": matiere, "enseignant": nom_complet,
                "date_seance": str(date_s), "etudiant_nom": name, "note_evaluation": "Absence",
                "observations": obs
            }).execute()
        
        # Envoi Mail
        send_email_rapport([EMAIL_CHEF_DEPT], f"Rapport {matiere} - {promo}", f"Enseignant: {nom_complet}\nDate: {date_s}\nAbsents: {len(absents)}")
        st.success("Rapport archivé et envoyé !")

with t_suivi:
    nom_rech = st.selectbox("Rechercher un étudiant :", ["--"] + sorted(df_etudiants['FULL_N'].unique()))
    if nom_rech != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_rech).execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)
        else: st.success("Aucune absence.")

with t_admin:
    if is_admin:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data))
    else: st.error("Accès Admin requis.")
