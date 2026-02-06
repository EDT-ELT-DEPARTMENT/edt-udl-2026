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
    st.error("⚠️ Erreur Supabase. Vérifiez vos secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
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
                df[col] = df[col].astype(str).str.strip()
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

def get_live_grade(user_nom, user_email):
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if not match.empty:
        return match.iloc[0]['Grade']
    return "Enseignant"

def extraire_heure_debut(creneau):
    try:
        return float(creneau.split('-')[0].split('h')[0].strip().replace(':', '.'))
    except: return 99.0

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email :", key="l_email")
        p_log = st.text_input("Code :", type="password", key="l_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Nom :", sorted(df_staff['Full'].unique()))
        info_s = df_staff[df_staff['Full'] == choix].iloc[0]
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Nouveau Code :", type="password")
        if st.button("Créer Compte"):
            try:
                supabase.table("enseignants_auth").insert({"email": reg_mail, "password_hash": hash_pw(reg_pass), "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'], "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']}).execute()
                st.success("Succès !")
            except: st.error("Email déjà pris.")

    with t_student:
        nom_in = st.text_input("Nom Prénom (MAJUSCULES) :").upper().strip()
        if st.button("Voir mon EDT", use_container_width=True):
            df_etudiants['Search'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()
            p = df_etudiants[df_etudiants['Search'] == nom_in]
            if not p.empty:
                info = p.iloc[0]
                st.success(f"Dossier : {nom_in} ({info['Promotion']})")
                edt = df_edt[df_edt['Promotion'] == info['Promotion']].copy()
                if not edt.empty:
                    edt['tri'] = edt['Horaire'].apply(extraire_heure_debut)
                    edt = edt.sort_values('tri')
                    st.table(edt.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(list(dict.fromkeys(x))), sort=False))
            else: st.error("Inconnu.")
    st.stop()

# --- 5. INTERFACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
current_grade = get_live_grade(user['nom_officiel'], user['email'])

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}\n**{current_grade}**")
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin :", sorted(df_edt['Enseignants'].unique()))
    else: enseignant_vue = user['nom_officiel']
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("Séance :", ["Cours", "TD", "TP", "Examen"])
    reg_s = c2.selectbox("Régime :", ["Charge Horaire", "Heures Supp"])
    date_s = c3.date_input("Date :", value=datetime.now())
    
    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    m_sel = st.selectbox("Matière :", sorted(df_edt[mask & (df_edt['Promotion']==p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    g_sel = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    df_appel = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)].copy()
    df_appel['Full'] = (df_appel['Nom'] + " " + df_appel['Prénom']).str.upper().str.strip()
    
    abs_coll = st.checkbox("🚩 ABSENCE COLLECTIVE")
    absents = df_appel['Full'].tolist() if abs_coll else st.multiselect("❌ Absents :", options=df_appel['Full'].tolist())
    
    et_noter = st.selectbox("📝 Noter :", ["Aucun"] + df_appel['Full'].tolist())
    v_note = st.text_input("Note/Obs (ex: +1) :", "0")
    code_v = st.text_input("🔑 Code Validation :", type="password")

    if st.button("🚀 VALIDER", use_container_width=True):
        if hash_pw(code_v) == user['password_hash']:
            meta = {"promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_grade} {user['nom_officiel']}", "date_seance": str(date_s), "categorie_seance": cat_s}
            for ab in absents:
                r = meta.copy(); r.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                supabase.table("archives_absences").insert(r).execute()
            if et_noter != "Aucun":
                rn = meta.copy(); rn.update({"etudiant_nom": et_noter, "note_evaluation": v_note})
                supabase.table("archives_absences").insert(rn).execute()
            st.success("✅ Archivé !")
        else: st.error("Code erroné.")

with tab_suivi:
    st.markdown("### 🔍 Suivi Individuel")
    df_etudiants['Search_Full'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()
    et_search = st.selectbox("🎯 Étudiant :", ["--"] + sorted(df_etudiants['Search_Full'].unique()))
    
    if et_search != "--":
        # Récupération exacte via SQL (on force le filtre sur le nom nettoyé)
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_search).execute()
        
        if res.data:
            df_res = pd.DataFrame(res.data)
            
            # Métriques
            abs_count = len(df_res[df_res['note_evaluation'] == 'ABSENCE'])
            st.metric("Total Absences", abs_count)
            
            # Tableau
            st.table(df_res[['date_seance', 'matiere', 'enseignant', 'note_evaluation']])
            
            # Export
            buf = io.BytesIO()
            df_res.to_excel(buf, index=False)
            st.download_button("📥 Télécharger Fiche Excel", buf.getvalue(), f"Suivi_{et_search}.xlsx")
        else:
            st.info(f"Aucune donnée enregistrée pour {et_search}.")

with tab_hist:
    st.markdown("### 📜 Registre Global")
    all_res = supabase.table("archives_absences").select("*").execute()
    if all_res.data:
        df_glob = pd.DataFrame(all_res.data)
        st.dataframe(df_glob, use_container_width=True)
        buf_g = io.BytesIO(); df_glob.to_excel(buf_g, index=False)
        st.download_button("📊 Exporter Tout", buf_g.getvalue(), "Archives_Globales.xlsx")
