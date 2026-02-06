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
    """Sécurisation des codes d'accès."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body, is_html=False):
    """Envoi de notifications par email."""
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
    """Chargement et nettoyage rigoureux des fichiers Excel."""
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'NAN', ''], 'Inconnu')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

def get_live_info(user_nom, user_email):
    """Récupère le Grade et le Statut de l'enseignant en temps réel."""
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    if not match.empty:
        g = match.iloc[0].get('Grade', 'Enseignant')
        s = match.iloc[0].get('Qualité', 'Permanent')
        return g, s
    return "Enseignant", "Permanent"

def extraire_heure(creneau):
    """Extrait l'heure de début pour le tri chronologique (ex: '8h-9h30' -> 8.0)"""
    try:
        h_str = creneau.split('h')[0].strip()
        return float(h_str.replace(':', '.'))
    except:
        return 99.0

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION & ESPACE ÉTUDIANT ---
if not st.session_state["user_data"]:
    st.markdown(f"<h3 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h3>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        email_log = st.text_input("Email :", key="login_email_main")
        pass_log = st.text_input("Code Unique :", type="password", key="login_pass_main")
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
        st.info(f"Profil : {info_s['NOM']} | {info_s['Grade']} ({info_s['Qualité']})")
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Créer votre Code Unique :", type="password")
        if st.button("Valider Inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'],
                    "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']
                }).execute()
                st.success("Inscription réussie !")
            except: st.error("Email déjà utilisé.")

    with t_forgot:
        f_email = st.text_input("Saisissez votre Email professionnel :", key="forgot_email")
        if st.button("M'envoyer un nouveau code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                if send_mail(f_email, "Récupération Code - UDL", f"Votre nouveau code est : {new_c}"):
                    st.success("Nouveau code envoyé par email.")
            else: st.error("Email non trouvé.")

    with t_student:
        st.subheader("🎓 Portail Étudiant")
        nom_in = st.text_input("Nom et Prénom (MAJUSCULES) :").upper().strip()
        if st.button("Consulter ma fiche", use_container_width=True):
            df_etudiants['Search_Full'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()
            profil = df_etudiants[df_etudiants['Search_Full'] == nom_in]
            
            if not profil.empty:
                p = profil.iloc[0]
                st.success(f"✅ Dossier trouvé : {nom_in}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Promotion", p['Promotion'])
                c2.metric("Groupe", p['Groupe'])
                c3.metric("Sous-Groupe", p['Sous groupe'])
                
                # --- LOGIQUE FILTRAGE EDT ---
                edt_raw = df_edt[df_edt['Promotion'] == p['Promotion']].copy()
                
                # Filtres : Cours (Tous) OU Séance contenant le Groupe OU Séance contenant le S-Groupe
                mask_cours = edt_raw['Enseignements'].str.contains("Cours", case=False, na=False)
                mask_gp = edt_raw['Enseignements'].str.contains(p['Groupe'], na=False)
                mask_sgp = edt_raw['Enseignements'].str.contains(p['Sous groupe'], na=False)
                
                edt_filtre = edt_raw[mask_cours | mask_gp | mask_sgp].copy()
                
                st.markdown("#### 📅 Emploi du Temps (Ordre Chronologique)")
                if not edt_filtre.empty:
                    # Ajout d'une colonne de tri pour l'horaire
                    edt_filtre['tri_h'] = edt_filtre['Horaire'].apply(extraire_heure)
                    edt_filtre = edt_filtre.sort_values(by='tri_h')

                    # Création de la table pivot (Grille)
                    pivot = edt_filtre.pivot_table(
                        index='Horaire', 
                        columns='Jours', 
                        values='Enseignements', 
                        aggfunc=lambda x: ' / '.join(list(dict.fromkeys(x))), # Éviter les doublons texte
                        sort=False # On garde l'ordre chronologique déjà établi
                    )
                    
                    # Réorganiser les jours
                    jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                    cols = [j for j in jours_ordre if j in pivot.columns]
                    st.table(pivot[cols])
                else:
                    st.warning("Aucune donnée trouvée.")
                
                # --- ÉTAT DES ABSENCES ---
                st.markdown("#### 🚩 État des Absences")
                res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_in).execute()
                if res_abs.data:
                    df_abs = pd.DataFrame(res_abs.data)
                    stats = df_abs.groupby('matiere').size().reset_index(name='Nombre d\'absences')
                    st.table(stats)
                else:
                    st.info("Aucune absence signalée.")
            else:
                st.error("Étudiant non reconnu.")
    st.stop()

# --- 5. INTERFACE ENSEIGNANT CONNECTÉ ---
user = st.session_state["user_data"]
grade_live, statut_live = get_live_info(user['nom_officiel'], user['email'])

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    st.markdown(f"**Enseignant :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {grade_live}")
    st.markdown(f"**Statut :** {statut_live}")
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen"])
    reg_s = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("📅 Date réelle :", value=datetime.now())

    cp, cm = st.columns(2)
    ens_vue = user['nom_officiel']
    mask = df_edt['Enseignants'].str.contains(ens_vue, na=False, case=False)
    list_promos = sorted(df_edt[mask]['Promotion'].unique())
    p_sel = cp.selectbox("🎓 Promotion :", list_promos if list_promos else sorted(df_edt['Promotion'].unique()))
    list_mats = sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique())
    m_sel = cm.selectbox("📖 Matière :", list_mats if list_mats else ["-"])

    st.divider()
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p_full[df_p_full['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p_full.empty else ["SG1"])

    m_eff1, m_eff2, m_eff3 = st.columns(3)
    m_eff1.metric("Effectif Promotion", len(df_p_full))
    m_eff2.metric(f"Effectif Groupe {g_sel}", len(df_p_full[df_p_full['Groupe'] == g_sel]))
    m_eff3.metric(f"Effectif S-Groupe {sg_sel}", len(df_p_full[(df_p_full['Groupe'] == g_sel) & (df_p_full['Sous groupe'] == sg_sel)]))

    df_appel = df_p_full[(df_p_full['Groupe']==g_sel) & (df_p_full['Sous groupe']==sg_sel)].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    absents = st.multiselect("❌ Sélectionner les Absents :", options=df_appel['Full'].tolist())
    code_v = st.text_input("🔑 Votre Code Unique (Validation) :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            for ab in absents:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_live} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": ab, "note_evaluation": "ABSENCE",
                    "categorie_seance": cat_s, "regime_heure": reg_s
                }).execute()
            st.success("Données archivées avec succès.")
        else: st.error("Code incorrect.")

with tab
