import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import re
import random
import string
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
    st.error("⚠️ Configuration Supabase manquante dans les secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_email_rapport(destinataires, sujet, corps):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = sujet
        msg.attach(MIMEText(corps, 'plain'))
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
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        
        # Nettoyage global et mise en MAJUSCULES
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', ''], '')
        
        # Gestion du staff
        if 'NOM' in df_staff.columns and 'PRÉNOM' in df_staff.columns:
            df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}")
        st.stop()

# --- CHARGEMENT ---
df_edt, df_etudiants, df_staff = load_data()

# --- CRÉATION DU FULL_N ÉTUDIANTS ---
if 'NOM' in df_etudiants.columns and 'PRÉNOM' in df_etudiants.columns:
    df_etudiants['Full_N'] = (df_etudiants['NOM'] + " " + df_etudiants['PRÉNOM']).str.upper().str.strip()
elif 'Nom' in df_etudiants.columns and 'Prénom' in df_etudiants.columns:
    df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()

# --- FONCTION DE COLORATION ---
def color_edt(val):
    if not val or val == "": return ""
    v = str(val).upper()
    if "COURS" in v: return 'background-color: #d1e7dd; color: #084298; font-weight: bold; border: 1px solid #084298;'
    if "TD" in v: return 'background-color: #fff3cd; color: #856404; font-weight: bold; border: 1px solid #856404;'
    if "TP" in v: return 'background-color: #cfe2ff; color: #004085; font-weight: bold; border: 1px solid #004085;'
    return ''

# --- 4. AUTHENTIFICATION & ESPACE ÉTUDIANT ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        st.markdown("### Connexion Enseignant")
        email_log = st.text_input("Email professionnel :").strip().lower()
        pass_log = st.text_input("Code unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("users_enseignants").select("*").eq("email", email_log).execute()
            if res.data and res.data[0]['password_hash'] == hash_pw(pass_log):
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Email ou code incorrect.")

    with t_signup:
        st.markdown("### Créer un compte Enseignant")
        nom_reg = st.selectbox("Sélectionnez votre NOM :", sorted(df_staff['NOM'].unique()))
        prenom_reg = st.selectbox("Sélectionnez votre PRÉNOM :", sorted(df_staff[df_staff['NOM'] == nom_reg]['PRÉNOM'].unique()))
        email_reg = st.text_input("Email :").strip().lower()
        pass_reg = st.text_input("Créer un code unique (chiffres/lettres) :", type="password")
        
        if st.button("S'inscrire", use_container_width=True):
            match = df_staff[(df_staff['NOM'] == nom_reg) & (df_staff['PRÉNOM'] == prenom_reg)]
            if not match.empty:
                grade_reg = str(match.iloc[0]['Grade'])
                statut_reg = str(match.iloc[0]['Qualité'])
                try:
                    supabase.table("users_enseignants").insert({
                        "email": email_reg, "password_hash": hash_pw(pass_reg),
                        "nom_officiel": nom_reg, "prenom_officiel": prenom_reg,
                        "grade_enseignant": grade_reg, "statut_enseignant": statut_reg
                    }).execute()
                    st.success("Compte créé ! Connectez-vous.")
                except:
                    st.error("Cet email est déjà utilisé.")

    with t_forgot:
        st.info("Contactez l'administrateur (milouafarid@gmail.com) pour réinitialiser votre code.")

    with t_student:
        nom_st = st.selectbox("Sélectionner votre nom (Étudiant) :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.info(f"🎓 **Étudiant :** {nom_st} | **Promo :** {profil['Promotion']} | **Groupe :** {profil['Groupe']}")

            st.markdown("#### 📅 Mon Emploi du Temps Hebdomadaire")
            
            def filter_st_edt(row):
                if str(row['Promotion']).upper() != str(profil['Promotion']).upper(): 
                    return False
                ens, code = str(row['Enseignements']).upper(), str(row['Code']).upper()
                if "COURS" in ens: return True
                num_g = re.findall(r'\d+', str(profil['Groupe']))[0] if re.findall(r'\d+', str(profil['Groupe'])) else ""
                if "TD" in ens:
                    if str(profil['Groupe']).upper() in code or (num_g == "1" and "-A" in code) or (num_g == "2" and "-B" in code): 
                        return True
                num_sg = re.findall(r'\d+', str(profil['Sous groupe']))[0] if re.findall(r'\d+', str(profil['Sous groupe'])) else ""
                if "TP" in ens:
                    suff = "A" if num_sg == "1" else "B" if num_sg == "2" else "C" if num_sg == "3" else ""
                    if suff and f"-{suff}" in code: 
                        return True
                return False

            edt_st = df_edt[df_edt.apply(filter_st_edt, axis=1)].copy()
            if not edt_st.empty:
                st.dataframe(edt_st[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']], use_container_width=True)
            else:
                st.warning("Aucun emploi du temps trouvé.")

            st.markdown("#### ❌ Suivi des Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            if res_abs.data:
                df_abs = pd.DataFrame(res_abs.data)
                st.table(df_abs[['matiere', 'date_seance', 'note_evaluation']])
            else:
                st.success("Aucune absence signalée.")

    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user.get('email') == EMAIL_ADMIN_TECH)

nom_session = str(user.get('nom_officiel', '')).strip().upper()
prenom_session = str(user.get('prenom_officiel', '')).strip().upper()
nom_complet_session = f"{nom_session} {prenom_session}" if prenom_session else nom_session

grade_fix = str(user.get('grade_enseignant', '')).strip()
statut_fix = str(user.get('statut_enseignant', 'Permanent')).strip()

# --- SIDEBAR ---
st.sidebar.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom:2px solid #003366;'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {nom_complet_session}")
    if grade_fix: st.success(f"**Grade :** {grade_fix}")
    st.warning(f"**Statut :** {statut_fix}")
    st.divider()
    
    if is_admin:
        liste_profs = sorted([str(x) for x in df_edt['Enseignants'].unique() if x])
        ens_actif = st.selectbox("Simulation (Admin) :", liste_profs, key="unique_admin_sim_key")
    else:
        ens_actif = nom_complet_session

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

# --- INTERFACE PRINCIPALE ---
t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True)
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    date_s = c3.date_input("Date réelle :", value=datetime.now())
    
    mask_ens = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    list_promos = sorted(df_edt[mask_ens]['Promotion'].unique()) if any(mask_ens) else sorted(df_edt['Promotion'].unique())
    p_sel = st.selectbox("🎓 Promotion :", list_promos)
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask_ens & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask_ens) else ["-"])
    
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")
    
    if abs_collective:
        absents_final = eff_liste['Full_N'].tolist()
        type_abs = "Absence Collective"
    else:
        absents_final = st.multiselect("Sélectionner les étudiants absents :", options=eff_liste['Full_N'].tolist())
        type_abs = st.selectbox("Nature :", ["Absence non justifiée", "Absence justifiée", "Exclusion"])

    obs_input = st.text_area("🗒️ Observations générales :")
    code_v = st.text_input("🔑 Code Unique pour validation :", type="password")
    
    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            for name in absents_final:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {nom_complet_session}",
                    "date_seance": str(date_s), "etudiant_nom": name, "note_evaluation": type_abs,
                    "observations": obs_input, "categorie_seance": charge, "type_seance": type_seance
                }).execute()
            
            corps_mail = f"Rapport de {nom_complet_session}\nMatière: {m_sel}\nPromotion: {p_sel}\nAbsents: {len(absents_final)}"
            send_email_rapport([EMAIL_CHEF_DEPT, EMAIL_ADJOINT], f"Rapport - {m_sel}", corps_mail)
            st.success("✅ Rapport archivé et envoyé !"); st.balloons()
        else:
            st.error("Code de validation incorrect.")

with t_suivi:
    st.markdown("### 🔍 Fiche de Suivi Individuelle")
    p_suivi = st.selectbox("1️⃣ Promotion :", sorted(df_etudiants['Promotion'].unique()), key="s_p")
    nom_suivi = st.selectbox("2️⃣ Étudiant :", ["--"] + sorted(df_etudiants[df_etudiants['Promotion'] == p_suivi]['Full_N'].unique()), key="s_n")
    if nom_suivi != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_suivi).execute()
        if res.data: st.table(pd.DataFrame(res.data)[['date_seance', 'matiere', 'note_evaluation', 'enseignant']])

with t_admin:
    if is_admin:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)
    else: st.error("Accès restreint.")
