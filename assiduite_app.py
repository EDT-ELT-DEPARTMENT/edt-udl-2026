import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import segno
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
    st.error("⚠️ Erreur de configuration Supabase.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_qr_segno(data):
    """Génère un QR Code avec Segno"""
    qr = segno.make(data)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10)
    return out.getvalue()

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
        
        Un rapport de séance a été validé par l'enseignant :
        - Enseignant : {details['enseignant']} ({details['statut_enseignant']})
        - Matière : {details['matiere']}
        - Promotion : {details['promotion']}
        - Date : {details['date_seance']}
        - Régime : {details['regime_heure']}
        - Absents relevés : {details['nb_absents']}
        
        Observations : {details.get('observations', 'Néant')}
        
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
        return match.iloc[0].get('Grade', 'Enseignant'), match.iloc[0].get('Qualité', 'Permanent')
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
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "🎓 Espace Étudiant"])
    
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
        choix_nom = st.selectbox("Nom :", sorted(df_staff['Full_S'].unique()))
        inf_s = df_staff[df_staff['Full_S'] == choix_nom].iloc[0]
        st.info(f"Profil détecté : {inf_s['Grade']} ({inf_s['Qualité']})")
        reg_e = st.text_input("Confirmez Email :", value=inf_s['Email'])
        reg_p = st.text_input("Code Unique :", type="password")
        if st.button("Créer mon compte"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf_s['NOM'], "prenom_officiel": inf_s['PRÉNOM'],
                "statut_enseignant": inf_s['Qualité'], "grade_enseignant": inf_s['Grade']
            }).execute()
            st.success("Compte créé.")

    with t_student:
        df_etudiants['Full_N'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()
        nom_st = st.selectbox("Rechercher votre nom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.success(f"Promotion : {profil['Promotion']} | Groupe : {profil['Groupe']}")
            
            # QR Code Étudiant
            st.write("📲 **Votre QR Code de suivi :**")
            qr_data = f"Etudiant: {nom_st} | Promo: {profil['Promotion']}"
            st.image(generate_qr_segno(qr_data), width=150)
            
            edt_st = df_edt[df_edt['Promotion'] == profil['Promotion']]
            st.table(edt_st[['Enseignements', 'Horaire', 'Jours', 'Lieu']])
    st.stop()

# --- 5. INTERFACE ET LOGIQUE PROFIL ---
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
            cp_conf = st.text_input("Code de confirmation :", type="password")
            if st.button("OUI, TOUT EFFACER"):
                if hash_pw(cp_conf) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base réinitialisée.")
                    st.session_state["reset_trigger"] = False
                    st.rerun()
    else: 
        enseignant_vue = user['nom_officiel']

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
    date_s = c3.date_input("Date réelle :", value=datetime.now())

    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    # --- LOGIQUE EFFECTIFS ---
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    eff_promo = len(df_p)
    
    m_sel = st.selectbox("Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])

    cg, csg = st.columns(2)
    with cg:
        g_sel = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
        eff_g = len(df_p[df_p['Groupe'] == g_sel])
    with csg:
        sg_sel = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
        eff_sg = len(df_p[(df_p['Groupe'] == g_sel) & (df_p['Sous groupe'] == sg_sel)])

    # BANDEAU EFFECTIFS DYNAMIQUE
    st.info(f"📊 **Effectifs :** Promotion: {eff_promo} | Groupe {g_sel}: {eff_g} | Sous-groupe {sg_sel}: {eff_sg}")

    df_app = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)].copy()
    df_app['Full_N'] = (df_app['Nom'].fillna('') + " " + df_app['Prénom'].fillna('')).str.upper().str.strip()
    liste_et = df_app['Full_N'].tolist()

    col_a, col_b = st.columns(2)
    with col_a:
        abs_c = st.checkbox("🚩 ABSENCE COLLECTIVE")
        abs_sel = liste_et if abs_c else st.multiselect("❌ Absents :", options=liste_et)
    with col_b:
        et_n = st.selectbox("📝 Noter un étudiant :", ["Aucun"] + liste_et)
        val_n = st.text_input("Note/Obs :", "0")

    obs_txt = st.text_area("Observations additionnelles :")
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            meta = {
                "promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_grade} {user['nom_officiel']}",
                "statut_enseignant": current_statut, "date_seance": str(date_s), "regime_heure": reg_s,
                "categorie_seance": cat_s, "observations": obs_txt, "nb_absents": len(abs_sel)
            }
            # Enregistrement des absents
            for ab in abs_sel:
                row = meta.copy(); row.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                safe_insert("archives_absences", row)
            # Enregistrement de la note si besoin
            if et_n != "Aucun":
                row_n = meta.copy(); row_n.update({"etudiant_nom": et_n, "note_evaluation": val_n})
                safe_insert("archives_absences", row_n)
            
            send_notification_admin(meta)
            st.success("✅ Rapport envoyé au département.")
            st.balloons()
        else: st.error("Code incorrect.")

# --- ONGLET 2 : SUIVI INDIVIDUEL ---
with tab_suivi:
    df_etudiants['Full_N'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()
    et_q = st.selectbox("🎯 Rechercher un étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    if et_q != "--":
        r = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_q).execute()
        if r.data:
            df_r = pd.DataFrame(r.data)
            cols_dispo = [c for c in ['date_seance', 'matiere', 'enseignant', 'note_evaluation', 'observations'] if c in df_r.columns]
            st.table(df_r[cols_dispo])
        else: st.info("Aucun historique pour cet étudiant.")

# --- ONGLET 3 : ARCHIVE GLOBALE ---
with tab_hist:
    st.markdown("### 📊 Pilotage Global")
    m_vue = st.radio("Filtrer par :", ["Vue complète", "Par Promotion", "Par Étudiant (Global)"], horizontal=True)
    res_all = supabase.table("archives_absences").select("*").execute()
    if res_all.data:
        df_glob = pd.DataFrame(res_all.data)
        if m_vue == "Par Promotion":
            p_choice = st.selectbox("Sélectionner Promotion :", sorted(df_glob['promotion'].unique()))
            df_disp = df_glob[df_glob['promotion'] == p_choice]
        elif m_vue == "Par Étudiant (Global)":
            e_choice = st.selectbox("Sélectionner Étudiant :", sorted(df_glob['etudiant_nom'].unique()))
            df_disp = df_glob[df_glob['etudiant_nom'] == e_choice]
        else:
            df_disp = df_glob
        st.dataframe(df_disp, use_container_width=True)
