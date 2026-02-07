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
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Erreur Configuration Supabase : {e}")
        return None

supabase = init_connection()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def clean_val(val):
    """ Nettoie les valeurs pour éviter l'affichage de 'None' ou 'nan' """
    v = str(val).strip()
    if v.upper() in ["NONE", "NAN", "<NA>", ""]:
        return ""
    return v

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
    except Exception:
        return False

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        
        # Nettoyage et uniformisation des colonnes
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'none', 'NAN'], '')
        
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}")
        st.stop()

# Chargement initial
df_edt, df_etudiants, df_staff = load_data()

# Préparation colonne Full_N (Étudiants)
if 'Nom' in df_etudiants.columns and 'Prénom' in df_etudiants.columns:
    df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()
else:
    df_etudiants['Full_N'] = (df_etudiants['NOM'] + " " + df_etudiants['PRÉNOM']).str.upper().str.strip()

# --- 4. AUTHENTIFICATION & ESPACES PUBLICS ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :", key="log_e").strip().lower()
        p_log = st.text_input("Code Unique :", type="password", key="log_p")
        if st.button("Se connecter", use_container_width=True):
            if supabase:
                res = supabase.table("enseignants_auth").select("*").eq("email", e_log).execute()
                if res.data and res.data[0]['password_hash'] == hash_pw(p_log):
                    st.session_state["user_data"] = res.data[0]
                    st.rerun()
                else:
                    st.error("Email ou code incorrect.")

    with t_signup:
        if 'NOM' in df_staff.columns:
            df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
            choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()))
            inf = df_staff[df_staff['Full_S'] == choix].iloc[0]
            
            st.info(f"Profil détecté : {inf.get('Grade', 'N/A')} | {inf.get('Qualité', 'N/A')}")
            reg_e = st.text_input("Confirmer votre Email :", value=inf.get('Email', ''))
            reg_p = st.text_input("Créer votre Code Unique :", type="password", key="reg_p_key")
            
            if st.button("Valider Inscription", use_container_width=True):
                try:
                    supabase.table("enseignants_auth").insert({
                        "email": reg_e.lower(), 
                        "password_hash": hash_pw(reg_p),
                        "nom_officiel": str(inf['NOM']), 
                        "prenom_officiel": str(inf['PRÉNOM']),
                        "statut_enseignant": str(inf.get('Qualité', 'Permanent')), 
                        "grade_enseignant": str(inf.get('Grade', 'Enseignant'))
                    }).execute()
                    st.success("✅ Compte créé ! Connectez-vous.")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    with t_forgot:
        f_email = st.text_input("Email d'inscription :", key="forgot_e")
        if st.button("Récupérer mon code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_email_rapport([f_email], "Votre nouveau code UDL", f"Votre nouveau code d'accès est : {new_c}")
                st.success("Nouveau code généré et envoyé par email.")
            else:
                st.error("Email inconnu.")

    with t_student:
        nom_st = st.selectbox("Sélectionner votre nom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.info(f"🎓 {profil['Promotion']} | Groupe {profil['Groupe']} | {profil['Sous groupe']}")
            
            st.markdown("### ❌ Mes Absences & Évaluations")
            if supabase:
                res_st = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
                if res_st.data:
                    df_std = pd.DataFrame(res_st.data)
                    st.table(df_std[['date_seance', 'matiere', 'note_evaluation']])
                else:
                    st.success("Aucune absence signalée.")
    st.stop()

# --- 5. ESPACE ENSEIGNANT (CONNECTÉ) ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
nom_affiche = clean_val(user.get('nom_officiel', ''))
prenom_affiche = clean_val(user.get('prenom_officiel', ''))
grade_affiche = clean_val(user.get('grade_enseignant', 'Enseignant'))

st.markdown(f"<h4 style='text-align:center; border-bottom: 2px solid #003366; padding-bottom: 10px;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {nom_affiche} {prenom_affiche}")
    st.markdown(f"**Grade :** {grade_affiche}")
    st.markdown(f"**Statut :** {clean_val(user.get('statut_enseignant', 'Permanent'))}")
    st.divider()
    ens_actif = st.selectbox("Vue Simulation (Admin) :", sorted(df_edt['Enseignants'].unique())) if is_admin else nom_affiche
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET SAISIE ---
with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True)
    
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    date_s = c3.date_input("Date réelle :", value=datetime.now())
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promo", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"S-Groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    
    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["Matière libre"])
    
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    absents_final = st.multiselect("Sélectionner les absents :", options=eff_liste['Full_N'].tolist())
    type_abs = st.selectbox("Nature :", ["Absence non justifiée", "Absence justifiée", "Exclusion"])

    st.divider()
    st.markdown("### 📝 Notation / Participation")
    cn1, cn2, cn3 = st.columns(3)
    etudiant_note = cn1.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist())
    critere = cn2.selectbox("Critère :", ["Test", "Participation", "Interrogation"])
    valeur = cn3.text_input("Note ou Observation :")

    obs = st.text_area("🗒️ Observations générales (Thème du cours, etc.) :")
    code_v = st.text_input("🔑 Confirmer avec votre Code Unique :", type="password")
    
    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            try:
                # 1. Insertion Absences
                for name in absents_final:
                    supabase.table("archives_absences").insert({
                        "date_seance": str(date_s), "promotion": str(p_sel), "matiere": str(m_sel),
                        "etudiant_nom": str(name), "note_evaluation": str(type_abs),
                        "observations": f"{charge} | {type_seance} | Grp: {g_sel}",
                        "enseignant": f"{grade_affiche} {nom_affiche}", "categorie_seance": str(charge),
                        "lieu_seance": str(m_sel), "grade_enseignant": str(grade_affiche)
                    }).execute()
                
                # 2. Insertion Note
                if etudiant_note != "Aucun":
                    supabase.table("archives_absences").insert({
                        "date_seance": str(date_s), "promotion": str(p_sel), "matiere": str(m_sel),
                        "etudiant_nom": str(etudiant_note), "note_evaluation": f"{critere}: {valeur}",
                        "observations": str(obs), "enseignant": f"{grade_affiche} {nom_affiche}",
                        "categorie_seance": str(charge), "lieu_seance": str(m_sel)
                    }).execute()
                
                st.success("✅ Rapport archivé !"); st.balloons()
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
        else:
            st.error("Code incorrect.")

# --- ONGLET SUIVI ---
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
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Erreur Configuration Supabase : {e}")
        return None

supabase = init_connection()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def clean_val(val):
    v = str(val).strip()
    if v.upper() in ["NONE", "NAN", "<NA>", ""]:
        return ""
    return v

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'none', 'NAN'], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

# Préparation Full_N
if 'Nom' in df_etudiants.columns and 'Prénom' in df_etudiants.columns:
    df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()
else:
    df_etudiants['Full_N'] = (df_etudiants['NOM'] + " " + df_etudiants['PRÉNOM']).str.upper().str.strip()

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :", key="log_e").strip().lower()
        p_log = st.text_input("Code Unique :", type="password", key="log_p")
        if st.button("Se connecter", use_container_width=True):
            if supabase:
                res = supabase.table("enseignants_auth").select("*").eq("email", e_log).execute()
                if res.data and res.data[0]['password_hash'] == hash_pw(p_log):
                    st.session_state["user_data"] = res.data[0]
                    st.rerun()
                else:
                    st.error("Email ou code incorrect.")
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
nom_affiche = clean_val(user.get('nom_officiel', ''))
prenom_affiche = clean_val(user.get('prenom_officiel', ''))
grade_affiche = clean_val(user.get('grade_enseignant', 'Enseignant'))
tel_affiche = clean_val(user.get('telephone', '')) # On récupère le tel si dispo

st.markdown(f"<h4 style='text-align:center; border-bottom: 2px solid #003366; padding-bottom: 10px;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {nom_affiche} {prenom_affiche}")
    st.markdown(f"**Grade :** {grade_affiche}")
    st.divider()
    ens_actif = st.selectbox("Vue Simulation (Admin) :", sorted(df_edt['Enseignants'].unique())) if is_admin else nom_affiche
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET SAISIE ---
with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True)
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    date_s = c3.date_input("Date réelle :", value=datetime.now())
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["Matière libre"])
    
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    absents_final = st.multiselect("Sélectionner les absents :", options=eff_liste['Full_N'].tolist())
    type_abs = st.selectbox("Nature :", ["Absence non justifiée", "Absence justifiée", "Exclusion"])

    st.markdown("### 📝 Notation / Participation")
    etudiant_note = st.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist())
    critere = st.selectbox("Critère :", ["Test", "Participation", "Interrogation"])
    valeur = st.text_input("Note ou Observation :")

    obs_gen = st.text_area("🗒️ Observations générales :")
    code_v = st.text_input("🔑 Code Unique :", type="password")
    
    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            try:
                # 1. Insertion des Absences
                for name in absents_final:
                    supabase.table("archives_absences").insert({
                        # Nouvelles colonnes
                        "date_seance": str(date_s),
                        "promotion": str(p_sel),
                        "matiere": str(m_sel),
                        "etudiant_nom": str(name),
                        "note_evaluation": str(type_abs),
                        "observations": f"{charge} | {type_seance} | Grp: {g_sel}",
                        "enseignant": f"{grade_affiche} {nom_affiche}",
                        "categorie_seance": str(charge),
                        # Anciennes colonnes conservées (pour compatibilité)
                        "lieu_seance": str(m_sel),
                        "jour_nom": str(date_s.strftime("%A")),
                        "statut_enseignant": str(user.get('statut_enseignant', 'Permanent')),
                        "grade_enseignant": str(grade_affiche),
                        "tel_enseignant": str(tel_affiche)
                    }).execute()
                
                # 2. Insertion de la Note
                if etudiant_note != "Aucun":
                    supabase.table("archives_absences").insert({
                        "date_seance": str(date_s),
                        "promotion": str(p_sel),
                        "matiere": str(m_sel),
                        "etudiant_nom": str(etudiant_note),
                        "note_evaluation": f"{critere}: {valeur}",
                        "observations": str(obs_gen),
                        "enseignant": f"{grade_affiche} {nom_affiche}",
                        "categorie_seance": str(charge),
                        "lieu_seance": str(m_sel),
                        "grade_enseignant": str(grade_affiche)
                    }).execute()
                
                st.success("✅ Rapport validé et archivé !"); st.balloons()
            except Exception as e:
                st.error(f"❌ Erreur d'archivage : {e}")
        else:
            st.error("🔑 Code incorrect.")

# --- ONGLET SUIVI ---
with t_suivi:
    st.subheader("🔍 Suivi Étudiant")
    mask_ens = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    ses_promos = sorted(df_edt[mask_ens]['Promotion'].unique())

    if not ses_promos:
        st.warning("Aucune promotion assignée.")
    else:
        df_access = df_etudiants[df_etudiants['Promotion'].isin(ses_promos)]
        search = st.selectbox("Rechercher un étudiant :", ["--"] + sorted(df_access['Full_N'].unique()), key="search_suivi")
        
        if search != "--":
            res = supabase.table("archives_absences").select("*").eq("etudiant_nom", search).execute()
            if res.data:
                df_res = pd.DataFrame(res.data)
                # Affichage des colonnes spécifiques au suivi assiduité
                cols_to_show = ['date_seance', 'matiere', 'note_evaluation', 'observations', 'enseignant']
                st.dataframe(df_res[cols_to_show], use_container_width=True)
            else:
                st.success(f"✅ Aucun incident enregistré pour {search}.")

# --- ONGLET ADMIN ---
with t_admin:
    if is_admin:
        st.subheader("🛡️ Registre Global")
        res_admin = supabase.table("archives_absences").select("*").execute()
        if res_admin.data:
            st.dataframe(pd.DataFrame(res_admin.data), use_container_width=True)

# --- ONGLET ADMIN ---
with t_admin:
    if is_admin:
        st.subheader("🛡️ Registre Global")
        res_admin = supabase.table("archives_absences").select("*").execute()
        if res_admin.data:
            df_all = pd.DataFrame(res_admin.data)
            st.metric("Total Enregistrements", len(df_all))
            st.dataframe(df_all, use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_all.to_excel(writer, index=False)
            st.download_button("📊 Télécharger (Excel)", output.getvalue(), "Archives_Full.xlsx")
    else:
        st.warning("Accès réservé à l'administration.")

