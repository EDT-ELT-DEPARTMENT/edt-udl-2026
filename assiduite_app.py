import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

# Définition du titre mémorisé
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Fichiers sources
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 CONFIGURATION EMAILS (Correction du NameError)
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_CHEF_DEPT = "chef.department.elt.fge@gmail.com"
EMAIL_ADJOINT = "milouafarid@gmail.com"  # Adresse de l'adjoint
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur de configuration Supabase. Vérifiez vos secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_notification_admin(details):
    """Envoi automatique au Chef de Dept et à l'Adjoint"""
    destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Système EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = f"Rapport de Séance : {details['matiere']} - {details['promotion']}"
        
        corps = f"""
        Bonjour,
        
        Un rapport de séance a été validé :
        - Enseignant : {details['enseignant']} ({details['statut_enseignant']})
        - Matière : {details['matiere']}
        - Promotion : {details['promotion']}
        - Date : {details['date_seance']}
        - Absents : {details['nb_absents']}
        
        Cordialement.
        """
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
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'NAN'], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

def get_staff_info(user_nom, user_email):
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    if not match.empty:
        return match.iloc[0].get('Grade', 'Pr'), match.iloc[0].get('Qualité', 'Permanent')
    return "Enseignant", "Permanent"

def safe_insert(table_name, data_dict):
    try:
        return supabase.table(table_name).insert(data_dict).execute()
    except:
        base_cols = ["promotion", "matiere", "enseignant", "date_seance", "etudiant_nom", "note_evaluation"]
        clean_dict = {k: v for k, v in data_dict.items() if k in base_cols}
        return supabase.table(table_name).insert(clean_dict).execute()

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup = st.tabs(["🔐 Connexion", "📝 Inscription"])
    with t_login:
        e_log = st.text_input("Email :")
        p_log = st.text_input("Code :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")
    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Nom :", sorted(df_staff['Full_S'].unique()))
        inf = df_staff[df_staff['Full_S'] == choix].iloc[0]
        reg_e = st.text_input("Email :", value=inf['Email'])
        reg_p = st.text_input("Nouveau Code :", type="password")
        if st.button("Valider"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf['NOM'], "prenom_officiel": inf['PRÉNOM'],
                "statut_enseignant": inf['Qualité'], "grade_enseignant": inf['Grade']
            }).execute()
            st.success("Compte créé.")
    st.stop()

# --- 5. LOGIQUE PROFIL ET INTERFACE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
current_grade, current_statut = get_staff_info(user['nom_officiel'], user['email'])

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}\n**{current_grade}** ({current_statut})")
    st.divider()
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
        st.divider()
        st.warning("🚨 ZONE DANGEREUSE")
        if st.button("Vider les Archives"):
            st.session_state["reset_trigger"] = True
        if st.session_state.get("reset_trigger"):
            cp = st.text_input("Code pour confirmer :", type="password")
            if st.button("OUI, RÉINITIALISER"):
                if hash_pw(cp) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base réinitialisée.")
                    st.session_state["reset_trigger"] = False
                    st.rerun()
    else: enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

# --- ONGLET 1 : SAISIE ---
with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("Séance :", ["Cours", "TD", "TP", "Examen"])
    reg_s = c2.selectbox("Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("Date :", value=datetime.now())

    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    m_sel = st.selectbox("Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])

    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    g_sel = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])

    df_app = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)].copy()
    df_app['Full'] = (df_app['Nom'].fillna('') + " " + df_app['Prénom'].fillna('')).str.upper().str.strip()
    liste_et = df_app['Full'].tolist()

    col_abs, col_not = st.columns(2)
    with col_abs:
        abs_c = st.checkbox("🚩 ABSENCE COLLECTIVE")
        abs_sel = liste_et if abs_c else st.multiselect("❌ Absents :", options=liste_et)
    with col_not:
        et_n = st.selectbox("📝 Noter un étudiant :", ["Aucun"] + liste_et)
        val_n = st.text_input("Note/Observation :", "0")

    obs = st.text_area("Observations :")
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            meta = {
                "promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_grade} {user['nom_officiel']}",
                "statut_enseignant": current_statut, "date_seance": str(date_s), "regime_heure": reg_s,
                "categorie_seance": cat_s, "observations": obs
            }
            for ab in abs_sel:
                row = meta.copy(); row.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                safe_insert("archives_absences", row)
            if et_n != "Aucun":
                row_n = meta.copy(); row_n.update({"etudiant_nom": et_n, "note_evaluation": val_n})
                safe_insert("archives_absences", row_n)
            
            meta['nb_absents'] = len(abs_sel)
            send_notification_admin(meta)
            st.success("✅ Rapport envoyé au Chef de Dept et Adjoint.")
            st.balloons()
        else: st.error("Code incorrect.")

# --- ONGLET 2 : SUIVI INDIVIDUEL ---
with tab_suivi:
    df_etudiants['Full'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()
    et_q = st.selectbox("🎯 Rechercher un étudiant :", ["--"] + sorted(df_etudiants['Full'].unique()))
    if et_q != "--":
        r = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_q).execute()
        if r.data:
            df_r = pd.DataFrame(r.data)
            st.table(df_r[['date_seance', 'matiere', 'enseignant', 'note_evaluation', 'observations']])
        else: st.info("Aucune donnée.")

# --- ONGLET 3 : ARCHIVE GLOBALE (SUIVI PROMO/NOM) ---
with tab_hist:
    st.markdown("### 📊 Pilotage Global")
    mode_vue = st.radio("Type de suivi :", ["Vue complète", "Par Promotion", "Par Étudiant (Global)"], horizontal=True)
    
    res_all = supabase.table("archives_absences").select("*").execute()
    if res_all.data:
        df_glob = pd.DataFrame(res_all.data)
        
        if mode_vue == "Par Promotion":
            prom_choice = st.selectbox("Sélectionner Promotion :", sorted(df_glob['promotion'].unique()))
            df_disp = df_glob[df_glob['promotion'] == prom_choice]
        elif mode_vue == "Par Étudiant (Global)":
            et_choice = st.selectbox("Sélectionner Étudiant :", sorted(df_glob['etudiant_nom'].unique()))
            df_disp = df_glob[df_glob['etudiant_nom'] == et_choice]
        else:
            df_disp = df_glob
            
        st.dataframe(df_disp, use_container_width=True)
        
        c_tot, c_abs = st.columns(2)
        c_tot.metric("Total Séances Archivées", len(df_disp['date_seance'].unique()))
        c_abs.metric("Nombre d'Absences relevées", len(df_disp[df_disp['note_evaluation'] == "ABSENCE"]))
        
        buf = io.BytesIO(); df_disp.to_excel(buf, index=False)
        st.download_button("📥 Télécharger Excel (Vue filtrée)", buf.getvalue(), "Archives_UDL.xlsx")
