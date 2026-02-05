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
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_CHEF_ADJOINT = "nass_ka@yahoo.fr"
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP (GMAIL)
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur de configuration Supabase. Vérifiez vos Secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body, is_html=False):
    """Fonction d'envoi d'email robuste"""
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
    except Exception as e:
        st.error(f"Erreur d'envoi email : {e}")
        return False

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
        st.error(f"Erreur de lecture des fichiers Excel : {e}")
        st.stop()

# --- CHARGEMENT DES DONNÉES ---
df_edt, df_etudiants, df_staff = load_data()

def get_live_grade(user_nom, user_email):
    """Récupère le grade exact (Pr, MCA...) dans le fichier Staff"""
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    if not match.empty:
        g = match.iloc[0]['Grade']
        return g if g != "" else "Enseignant"
    return "Enseignant"

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None
if "maintenance_mode" not in st.session_state:
    st.session_state["maintenance_mode"] = False

# --- 4. AUTHENTIFICATION & RÉCUPÉRATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié"])
    
    with t_login:
        email_log = st.text_input("Email professionnel :", key="login_email")
        pass_log = st.text_input("Code Unique :", type="password", key="login_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full_Name'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_Name'].unique()))
        info = df_staff[df_staff['Full_Name'] == choix].iloc[0]
        st.info(f"Vérification : {info['NOM']} {info['PRÉNOM']} | Grade : **{info['Grade']}**")
        
        reg_mail = st.text_input("Confirmez votre Email :", value=info['Email'])
        reg_pass = st.text_input("Créez votre Code Unique :", type="password")
        if st.button("Valider l'inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info['NOM'], "prenom_officiel": info['PRÉNOM'],
                    "statut_enseignant": info['Qualité'], "grade_enseignant": info['Grade']
                }).execute()
                st.success("Compte créé avec succès !")
            except:
                st.error("Erreur : Email déjà enregistré.")

    with t_forgot:
        f_email = st.text_input("Email du compte :")
        if st.button("M'envoyer un nouveau code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_code = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_code)}).eq("email", f_email).execute()
                
                body_forgot = f"Votre nouveau Code Unique pour la plateforme UDL est : {new_code}\n\nSécurité : Changez-le dès votre connexion."
                if send_mail(f_email, "Récupération de Code - UDL", body_forgot):
                    st.success(f"Un code temporaire a été envoyé à {f_email}")
                else:
                    st.error("Erreur lors de l'envoi de l'email.")
            else:
                st.error("Cet email n'existe pas dans notre base.")
    st.stop()

# --- 5. LOGIQUE ADMINISTRATIVE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

if st.session_state["maintenance_mode"] and not is_admin:
    st.warning("🚧 La plateforme est actuellement en maintenance pour mise à jour des EDTs.")
    st.stop()

# --- 6. INTERFACE PRINCIPALE ---
st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    # Grade dynamique depuis Excel
    current_grade = get_live_grade(user['nom_officiel'], user['email'])
    st.markdown(f"**Enseignant :** {user['nom_officiel']} {user.get('prenom_officiel', '')}")
    st.markdown(f"**Grade :** {current_grade}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        enseignant_vue = st.selectbox("Vue Admin - Enseignant :", sorted(df_edt['Enseignants'].unique()))
        
        # BOUTON MAINTENANCE
        if st.checkbox("⚙️ Activer Maintenance"):
            if st.button("CONFIRMER MAINTENANCE"):
                st.session_state["maintenance_mode"] = True
                st.warning("Maintenance activée !")
        
        # BOUTON RESET
        st.divider()
        if st.button("🚨 Vider toutes les Archives"):
            st.session_state["reset_trigger"] = True
        if st.session_state.get("reset_trigger"):
            confirm_reset_pw = st.text_input("Code Admin pour RESET :", type="password")
            if st.button("CONFIRMER SUPPRESSION DÉFINITIVE"):
                if hash_pw(confirm_reset_pw) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Toutes les données ont été effacées.")
                    st.session_state["reset_trigger"] = False
                else:
                    st.error("Code incorrect.")
    else:
        enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

# --- 7. ONGLETS ---
tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

with tab_saisie:
    # Infos Séance
    c1, c2, c3 = st.columns(3)
    cat_seance = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    regime_seance = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_seance = c3.date_input("📅 Date réelle :")

    # Sélection Promotion et Matière
    cp, cm = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    list_promos = sorted(df_edt[mask]['Promotion'].unique())
    promo_sel = cp.selectbox("🎓 Promotion :", list_promos if list_promos else sorted(df_edt['Promotion'].unique()))
    
    list_mats = sorted(df_edt[mask & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
    matiere_sel = cm.selectbox("📖 Matière :", list_mats if list_mats else ["-"])

    # Affichage EDT
    res_edt = df_edt[(df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    if not res_edt.empty:
        st.info(f"📍 Lieu : **{res_edt.iloc[0]['Lieu']}** | 🕒 Horaire : **{res_edt.iloc[0]['Horaire']}** | 🗓️ Jour prévu : **{res_edt.iloc[0]['Jours']}**")

    st.markdown("---")
    st.markdown("### 📈 Appel & Participation (Effectifs Numériques)")
    
    # Statistiques Numériques
    df_p_full = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    col_g, col_sg = st.columns(2)
    gr_sel = col_g.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["-"])
    df_gr = df_p_full[df_p_full['Groupe'] == gr_sel]
    sg_sel = col_sg.selectbox("🔢 Sous-groupe :", sorted(df_gr['Sous groupe'].unique()) if not df_gr.empty else ["-"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_p_full))
    m2.metric(f"Groupe
