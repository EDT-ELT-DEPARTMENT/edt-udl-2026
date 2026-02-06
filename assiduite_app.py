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
    st.error("⚠️ Erreur de configuration Supabase. Vérifiez vos secrets Streamlit.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires) if isinstance(destinataires, list) else destinataires
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

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
    """Récupère le Grade et le Statut (Qualité) en temps réel."""
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    
    if not match.empty:
        g = match.iloc[0].get('Grade', 'Enseignant')
        s = match.iloc[0].get('Qualité', 'Permanent') # Permanent ou Vacataire
        return g, s
    return "Enseignant", "Permanent"

def extraire_heure_debut(creneau):
    try:
        h_part = creneau.split('-')[0].split('h')[0].strip()
        return float(h_part.replace(':', '.'))
    except: return 99.0

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        email_log = st.text_input("Email :", key="login_email")
        pass_log = st.text_input("Code Unique :", type="password", key="login_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Email ou code incorrect.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full'].unique()))
        info_s = df_staff[df_staff['Full'] == choix].iloc[0]
        st.info(f"Profil : {info_s['NOM']} | Grade : {info_s['Grade']} | Statut : {info_s['Qualité']}")
        reg_mail = st.text_input("Confirmez votre Email :", value=info_s['Email'])
        reg_pass = st.text_input("Créez votre Code Unique :", type="password")
        if st.button("Valider Inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'],
                    "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']
                }).execute()
                st.success("Compte créé avec succès !")
            except: st.error("Erreur : Email déjà utilisé.")

    with t_student:
        st.subheader("🎓 Portail Étudiant")
        nom_in = st.text_input("Nom et Prénom (MAJUSCULES) :").upper().strip()
        if st.button("Consulter ma fiche", use_container_width=True):
            df_etudiants['Search_Full'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()
            profil = df_etudiants[df_etudiants['Search_Full'] == nom_in]
            if not profil.empty:
                p = profil.iloc[0]
                st.success(f"✅ Dossier trouvé : {nom_in}")
                # Affichage Emploi du Temps trié
                edt_raw = df_edt[df_edt['Promotion'] == p['Promotion']].copy()
                if not edt_raw.empty:
                    edt_raw['tri_h'] = edt_raw['Horaire'].apply(extraire_heure_debut)
                    edt_raw = edt_raw.sort_values(by='tri_h')
                    pivot = edt_raw.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(list(dict.fromkeys(x))), sort=False)
                    st.table(pivot)
            else: st.error("Étudiant non reconnu.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE (ENSEIGNANTS) ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# RÉCUPÉRATION DU GRADE ET DU STATUT (PERMANENT/VACATAIRE)
current_grade, current_statut = get_staff_info(user['nom_officiel'], user['email'])

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    st.markdown(f"**Enseignant :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {current_grade}")
    st.markdown(f"**Statut :** {current_statut}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
    else: 
        enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    reg_s = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("📅 Date réelle :", value=datetime.now())

    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])

    st.divider()
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    g_sel = st.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    sg_sel = st.selectbox("🔢 Sous-groupe :", sorted(df_p_full[df_p_full['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p_full.empty else ["SG1"])

    df_appel = df_p_full[(df_p_full['Groupe']==g_sel) & (df_p_full['Sous groupe']==sg_sel)].copy()
    df_appel['Full'] = (df_appel['Nom'] + " " + df_appel['Prénom']).str.upper().strip()
    
    col_abs, col_note = st.columns(2)
    with col_abs:
        abs_coll = st.checkbox("🚩 SIGNALER ABSENCE COLLECTIVE")
        absents_sel = df_appel['Full'].tolist() if abs_coll else st.multiselect("❌ Absents :", options=df_appel['Full'].tolist())
    with col_note:
        et_a_noter = st.selectbox("📝 Noter un étudiant :", ["Aucun"] + df_appel['Full'].tolist())
        val_note = st.text_input("Valeur (ex: +1 ou Note) :", "0")

    obs_txt = st.text_area("🗒️ Observations :")
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            # Préparation des données avec Statut et Grade
            meta = {
                "promotion": p_sel, 
                "matiere": m_sel, 
                "enseignant": f"{current_grade} {user['nom_officiel']}", 
                "statut_enseignant": current_statut,
                "date_seance": str(date_s),
                "regime_heure": reg_s,
                "categorie_seance": cat_s,
                "observations": obs_txt
            }
            
            for ab in absents_sel:
                r = meta.copy()
                r.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                supabase.table("archives_absences").insert(r).execute()
            
            if et_a_noter != "Aucun":
                rn = meta.copy()
                rn.update({"etudiant_nom": et_a_noter, "note_evaluation": val_note})
                supabase.table("archives_absences").insert(rn).execute()
                
            send_mail([EMAIL_CHEF_DEPT, user['email']], f"Rapport {m_sel}", f"Séance validée par {user['nom_officiel']} ({current_statut})")
            st.success("✅ Séance archivée avec succès.")
            st.balloons()
        else: st.error("Code incorrect.")

with tab_suivi:
    df_etudiants['Search_Full'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().strip()
    et_search = st.selectbox("🎯 Rechercher un étudiant :", ["-- Sélectionner --"] + sorted(df_etudiants['Search_Full'].unique()))
    if et_search != "-- Sélectionner --":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_search).execute()
        if res.data:
            df_res = pd.DataFrame(res.data)
            st.table(df_res[['date_seance', 'matiere', 'enseignant', 'note_evaluation']])
            buf = io.BytesIO(); df_res.to_excel(buf, index=False)
            st.download_button("📥 Télécharger Fiche Excel", buf.getvalue(), f"Suivi_{et_search}.xlsx")
        else: st.info("Aucune donnée.")

with tab_hist:
    all_res = supabase.table("archives_absences").select("*").execute()
    if all_res.data:
        df_glob = pd.DataFrame(all_res.data)
        st.dataframe(df_glob, use_container_width=True)
        buf_g = io.BytesIO(); df_glob.to_excel(buf_g, index=False)
        st.download_button("📊 Exporter toute la base", buf_g.getvalue(), "Archives_Globales.xlsx")
