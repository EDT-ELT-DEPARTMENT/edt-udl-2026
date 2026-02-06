import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import random
import string
import segno  # Bibliothèque pour la génération du QR Code
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

# 🔑 CONFIGURATION SMTP
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur de configuration Supabase. Vérifiez vos secrets Streamlit.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    """Hachage pour sécuriser les codes."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body, is_html=False):
    """Envoi de mail via Gmail."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires) if isinstance(destinataires, list) else destinataires
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

@st.cache_data
def load_data():
    """Chargement des fichiers Excel."""
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

def get_live_grade(user_nom, user_email):
    """Récupère le grade actuel dans le fichier staff."""
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    if not match.empty:
        g = match.iloc[0]['Grade']
        return g if g != "" else "Enseignant"
    return "Enseignant"

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION & ESPACE ÉTUDIANT ---
if not st.session_state["user_data"]:
    st.markdown(f"<h3 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h3>", unsafe_allow_html=True)
    t_login, t_signup, t_student = st.tabs(["🔐 Connexion Enseignant", "📝 Inscription", "🎓 Espace Étudiant"])
    
    with t_login:
        email_log = st.text_input("Email :", key="auth_email")
        pass_log = st.text_input("Code Unique :", type="password", key="auth_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full'].unique()))
        info_s = df_staff[df_staff['Full'] == choix].iloc[0]
        st.info(f"Profil : {info_s['NOM']} | Grade : {info_s['Grade']}")
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Code Unique à créer :", type="password")
        if st.button("Valider Inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'],
                    "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']
                }).execute()
                st.success("Inscription réussie !")
            except: st.error("Erreur d'inscription.")

    with t_student:
        st.subheader("🎓 Portail Étudiant")
        nom_in = st.text_input("Entrez votre NOM et PRÉNOM (Majuscules) :").upper().strip()
        if st.button("Consulter ma fiche", use_container_width=True):
            if nom_in:
                df_etudiants['Full'] = df_etudiants['Nom'] + " " + df_etudiants['Prénom']
                profil = df_etudiants[df_etudiants['Full'] == nom_in]
                if not profil.empty:
                    p = profil.iloc[0]
                    st.success(f"✅ Dossier trouvé : {nom_in}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Promotion", p['Promotion'])
                    c2.metric("Groupe", p['Groupe'])
                    c3.metric("Sous-Groupe", p['Sous groupe'])
                    
                    st.markdown("#### 📅 Votre Emploi du Temps")
                    edt_p = df_edt[df_edt['Promotion'] == p['Promotion']]
                    st.dataframe(edt_p[['Enseignements', 'Enseignants', 'Horaire', 'Jours', 'Lieu']], use_container_width=True)
                    
                    st.markdown("#### 🚩 Suivi des Absences")
                    res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_in).execute()
                    if res_abs.data:
                        df_res = pd.DataFrame(res_abs.data)
                        st.table(df_res[['date_seance', 'matiere', 'enseignant']])
                    else:
                        st.info("Aucune absence enregistrée.")
                else: st.error("Nom non reconnu.")
    st.stop()

# --- 5. INTERFACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    current_g = get_live_grade(user['nom_officiel'], user['email'])
    st.markdown(f"**Enseignant :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {current_g}")
    
    st.divider()
    st.markdown("### 📱 QR Code Étudiant")
    app_url = "https://edt-udl-2026.streamlit.app" 
    qr = segno.make(app_url)
    buf_qr = io.BytesIO()
    qr.save(buf_qr, kind='png', scale=5)
    st.image(buf_qr.getvalue(), caption="Scan pour les absences")
    
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
    else:
        enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

# --- ONGLETS PRINCIPAUX ---
tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    # --- PARTIE INFOS SÉANCE ---
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    reg_s = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("📅 Date réelle :", value=datetime.now())

    cp, cm = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    list_promos = sorted(df_edt[mask]['Promotion'].unique())
    p_sel = cp.selectbox("🎓 Promotion :", list_promos if list_promos else sorted(df_edt['Promotion'].unique()))
    list_mats = sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique())
    m_sel = cm.selectbox("📖 Matière :", list_mats if list_mats else ["-"])

    st.divider()
    
    # --- PARTIE AFFICHAGE NUMÉRIQUE (MÉTRIQUES) ---
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p_full[df_p_full['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p_full.empty else ["SG1"])

    # Calcul des effectifs pour l'affichage numérique
    count_promo = len(df_p_full)
    count_groupe = len(df_p_full[df_p_full['Groupe'] == g_sel])
    count_sg = len(df_p_full[(df_p_full['Groupe'] == g_sel) & (df_p_full['Sous groupe'] == sg_sel)])

    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", count_promo)
    m2.metric(f"Effectif Groupe {g_sel}", count_groupe)
    m3.metric(f"Effectif S-Groupe {sg_sel}", count_sg)

    # --- APPEL ---
    df_appel = df_p_full[(df_p_full['Groupe']==g_sel) & (df_p_full['Sous groupe']==sg_sel)].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    
    absents = st.multiselect("❌ Marquer les Absents :", options=df_appel['Full'].tolist())
    code_v = st.text_input("🔑 Code Unique pour valider :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            for ab in absents:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_g} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": ab, "note_evaluation": "ABSENCE",
                    "categorie_seance": cat_s, "regime_heure": reg_s
                }).execute()
            st.success("Séance archivée avec succès.")
        else: st.error("Code incorrect.")

with tab_suivi:
    st.markdown("### 🔍 Fiche et Suivi Individuel")
    df_etudiants['Search_Full'] = df_etudiants['Nom'] + " " + df_etudiants['Prénom']
    et_sel = st.selectbox("🎯 Rechercher
