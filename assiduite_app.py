import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import random
import string
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

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
    st.error("⚠️ Erreur Supabase : Vérifiez vos Secrets Streamlit.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_notification_admin(details):
    destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT, EMAIL_ADMIN_TECH]
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Système EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = f"Rapport de Séance : {details['matiere']} - {details['promotion']}"
        corps = f"Rapport validé par {details['enseignant']}\nPromotion: {details['promotion']}\nAbsents: {details['nb_absents']}"
        msg.attach(MIMEText(corps, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except:
        pass

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'NAN', 'none'], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()
df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "🎓 Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email :")
        p_log = st.text_input("Code Unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Votre nom :", sorted(df_staff['Full_S'].unique()))
        inf_s = df_staff[df_staff['Full_S'] == choix_nom].iloc[0]
        st.info(f"Profil détecté : {inf_s['Grade']} | {inf_s['Qualité']}")
        reg_e = st.text_input("Email :", value=inf_s['Email'])
        reg_p = st.text_input("Créer Code Unique :", type="password")
        if st.button("Valider l'inscription"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf_s['NOM'], "prenom_officiel": inf_s['PRÉNOM'],
                "statut_enseignant": inf_s['Qualité'], "grade_enseignant": inf_s['Grade']
            }).execute()
            st.success("Compte créé !")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# Correction Grade si None
grade_display = user.get('grade_enseignant')
if not grade_display or grade_display == "" or grade_display == "None":
    grade_display = "Enseignant"

with st.sidebar:
    st.markdown(f"### 👤 Profil Enseignant")
    st.markdown(f"**Nom :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {grade_display}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        ens_actif = st.selectbox("Simuler un enseignant :", sorted(df_edt['Enseignants'].unique()))
    else:
        ens_actif = user['nom_officiel']

    if st.button("🔄 Actualiser"): st.rerun()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET 1 : SAISIE AVEC STATISTIQUES NUMÉRIQUES ---
with t_saisie:
    c1, c2, c3 = st.columns(3)
    type_s = c1.selectbox("Séance :", ["Cours", "TD", "TP", "Examen"])
    date_s = c3.date_input("Date :", value=datetime.now())
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    # Données de la promotion
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    
    col_g, col_sg = st.columns(2)
    g_sel = col_g.selectbox("Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    df_g = df_p_full[df_p_full['Groupe'] == g_sel]
    sg_sel = col_sg.selectbox("Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["SG1"])
    
    # --- AFFICHAGE NUMÉRIQUE DES EFFECTIFS ---
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_p_full))
    m2.metric(f"Effectif Groupe {g_sel}", len(df_g))
    m3.metric(f"Effectif S-Groupe {sg_sel}", len(df_g[df_g['Sous groupe'] == sg_sel]))
    st.markdown("---")

    m_sel = st.selectbox("Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])
    
    df_appel = df_g[df_g['Sous groupe'] == sg_sel]
    abs_sel = st.multiselect("❌ Sélectionner les Absents :", options=df_appel['Full_N'].tolist())
    
    obs = st.text_area("Observations :")
    code_v = st.text_input("🔑 Code Unique :", type="password")
    
    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            details = {
                "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_display} {user['nom_officiel']}",
                "date_seance": str(date_s), "nb_absents": len(abs_sel), "statut": user.get('statut_enseignant', 'Permanent')
            }
            for student in abs_sel:
                supabase.table("archives_absences").insert({**details, "etudiant_nom": student, "note_evaluation": "ABSENCE", "observations": obs}).execute()
            
            send_notification_admin(details)
            st.success("Rapport validé et archivé !"); st.balloons()
        else: st.error("Code incorrect.")

# --- ONGLET 2 : SUIVI ÉTUDIANT ---
with t_suivi:
    st.markdown("### 🔍 Suivi Individuel")
    etudiant_search = st.selectbox("Rechercher un étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    
    if etudiant_search != "--":
        info = df_etudiants[df_etudiants['Full_N'] == etudiant_search].iloc[0]
        
        # Calcul des effectifs pour cet étudiant
        eff_p = len(df_etudiants[df_etudiants['Promotion'] == info['Promotion']])
        eff_g = len(df_etudiants[(df_etudiants['Promotion'] == info['Promotion']) & (df_etudiants['Groupe'] == info['Groupe'])])
        
        c_i1, c_i2, c_i3 = st.columns(3)
        c_i1.metric("Promo", info['Promotion'])
        c_i2.metric("Groupe", info['Groupe'])
        c_i3.metric("Sous-groupe", info['Sous groupe'])
        
        res_sql = supabase.table("archives_absences").select("*").eq("etudiant_nom", etudiant_search).eq("note_evaluation", "ABSENCE").execute()
        if res_sql.data:
            st.table(pd.DataFrame(res_sql.data)[['date_seance', 'matiere', 'enseignant']])
        else:
            st.success("Aucune absence.")

# --- ONGLET 3 : PANNEAU ADMIN ---
with t_admin:
    if is_admin:
        st.markdown("### 🛡️ Registre Global")
        res_glob = supabase.table("archives_absences").select("*").execute()
        if res_glob.data:
            df_all = pd.DataFrame(res_glob.data)
            st.dataframe(df_all, use_container_width=True)
            
            buf = io.BytesIO()
            df_all.to_excel(buf, index=False)
            st.download_button("📥 Télécharger Excel Global", buf.getvalue(), "Archives_2026.xlsx")
    else:
        st.error("Accès réservé.")
