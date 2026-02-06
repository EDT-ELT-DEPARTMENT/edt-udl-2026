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
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'none', 'NAN', ''], 'Non spécifié')
        
        # Création du nom complet pour le staff
        if 'NOM' in df_staff.columns and 'PRÉNOM' in df_staff.columns:
            df_staff['Full_S'] = (df_staff['NOM'] + " " + df_staff['PRÉNOM']).str.upper()
        
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()
df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()

def color_edt(val):
    if not val or val == "Non spécifié": return ""
    if "Cours" in val: return 'background-color: #d1e7dd; color: #084298; font-weight: bold;'
    if "Td" in val or "TD" in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
    if "TP" in val: return 'background-color: #cfe2ff; color: #004085; font-weight: bold;'
    return ''

# --- 4. AUTHENTIFICATION & ESPACES PUBLICS ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :", key="log_e")
        p_log = st.text_input("Code Unique :", type="password", key="log_p")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Email ou code incorrect.")

    with t_signup:
        choix_signup = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()))
        inf = df_staff[df_staff['Full_S'] == choix_signup].iloc[0]
        st.info(f"Grade détecté : {inf['Grade']} | Statut : {inf['Qualité']}")
        reg_e = st.text_input("Email :", value=inf['Email'])
        reg_p = st.text_input("Créer Code Unique :", type="password")
        if st.button("Valider l'inscription"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf['NOM'], "prenom_officiel": inf['PRÉNOM'],
                "statut_enseignant": inf['Qualité'], "grade_enseignant": inf['Grade']
            }).execute()
            st.success("Compte créé avec succès !")

    with t_student:
        nom_st = st.selectbox("Rechercher votre nom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            nb_abs = len(pd.DataFrame(res_abs.data)) if res_abs.data else 0
            
            st.markdown(f"### 👤 {nom_st}")
            c1, c2 = st.columns(2)
            c1.metric("Promotion", profil['Promotion'])
            c2.metric("Absences cumulées", nb_abs)
            
            st.info(f"Groupe : {profil['Groupe']} | Sous-groupe : {profil['Sous groupe']}")
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# Récupération précise du grade
grade_final = user.get('grade_enseignant', 'Enseignant')
statut_final = user.get('statut_enseignant', 'Permanent')

st.markdown(f"<h4 style='text-align:center;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}")
    st.success(f"**Grade :** {grade_final}")
    st.warning(f"**Statut :** {statut_final}")
    st.divider()
    ens_actif = st.selectbox("Simulation (Admin) :", sorted(df_edt['Enseignants'].unique())) if is_admin else user['nom_officiel']
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET 1 : SAISIE ---
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
    m1.metric("Effectif Promotion", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"Sous-groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    st.markdown("---")

    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])
    
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")
    
    if abs_collective:
        absents_final = eff_liste['Full_N'].tolist()
        type_abs = "Absence Collective"
    else:
        absents_final = st.multiselect("Sélectionner les étudiants absents :", options=eff_liste['Full_N'].tolist())
        type_abs = st.selectbox("Nature :", ["Absence non justifiée", "Absence justifiée", "Exclusion"])

    st.divider()
    st.markdown("### 📝 Notation / Participation")
    cn1, cn2, cn3 = st.columns(3)
    etudiant_note = cn1.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist())
    critere = cn2.selectbox("Critère :", ["Test", "Examen de TD", "Participation", "Interrogation"])
    valeur = cn3.text_input("Note/Observation :")
    obs_input = st.text_area("🗒️ Observations générales :")

    # --- PARTIE ENVOI DU RAPPORT ---
    st.markdown("### ✉️ Diffusion du Rapport")
    staff_options = {row['Full_S']: row['Email'] for _, row in df_staff.iterrows() if 'Full_S' in df_staff.columns}
    
    # Champ réservé pour le Responsable de spécialité
    resp_spe_nom = st.selectbox("Responsable de l'équipe de spécialité :", ["Aucun"] + sorted(list(staff_options.keys())))
    
    code_v = st.text_input("🔑 Code Unique pour validation :", type="password")
    
    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            # Archivage Supabase
            for name in absents_final:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_final} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": name, "note_evaluation": type_abs,
                    "observations": obs_input, "categorie_seance": charge, "type_seance": type_seance
                }).execute()
            
            # Préparation des destinataires (Chef de Dept + Adjoint systématiques)
            destinataires_mails = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
            
            # Ajout du responsable de spécialité si sélectionné
            if resp_spe_nom != "Aucun":
                destinataires_mails.append(staff_options[resp_spe_nom])
            
            corps_mail = f"""
            RAPPORT DE SÉANCE - {TITRE_PLATEFORME}
            --------------------------------------------------
            Enseignant : {grade_final} {user['nom_officiel']} {user['prenom_officiel']}
            Date : {date_s}
            Promotion : {p_sel}
            Matière : {m_sel}
            Type : {type_seance} ({charge})
            
            STATISTIQUES :
            - Nombre d'absents : {len(absents_final)}
            - Nature : {type_abs}
            
            NOTES / PARTICIPATION :
            - Étudiant ciblé : {etudiant_note}
            - Critère : {critere}
            - Valeur : {valeur}
            
            OBSERVATIONS :
            {obs_input}
            --------------------------------------------------
            Rapport généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}.
            """
            
            envoi_ok = send_email_rapport(destinataires_mails, f"Rapport {type_seance} - {m_sel} - {user['nom_officiel']}", corps_mail)
            
            if envoi_ok:
                st.success("✅ Rapport archivé et diffusé avec succès !"); st.balloons()
            else:
                st.warning("✅ Archivé, mais erreur lors de l'envoi des emails.")
        else:
            st.error("Code unique incorrect.")

# --- ONGLET 2 : SUIVI ÉTUDIANT ---
with t_suivi:
    st.markdown("### 🔍 Fiche de Suivi Individuelle")
    p_suivi = st.selectbox("1️⃣ Promotion :", sorted(df_etudiants['Promotion'].unique()), key="suivi_p")
    etudiants_promo = df_etudiants[df_etudiants['Promotion'] == p_suivi]
    nom_suivi = st.selectbox("2️⃣ Étudiant :", ["--"] + sorted(etudiants_promo['Full_N'].unique()), key="suivi_n")
    
    if nom_suivi != "--":
        res_suivi = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_suivi).execute()
        if res_suivi.data:
            st.table(pd.DataFrame(res_suivi.data)[['date_seance', 'matiere', 'note_evaluation', 'enseignant']])
        else:
            st.info("Aucun historique pour cet étudiant.")

# --- ONGLET 3 : ADMIN ---
with t_admin:
    if is_admin:
        res_all = supabase.table("archives_absences").select("*").execute()
        if res_all.data:
            st.dataframe(pd.DataFrame(res_all.data), use_container_width=True)
    else:
        st.error("Accès réservé à l'administration.")
