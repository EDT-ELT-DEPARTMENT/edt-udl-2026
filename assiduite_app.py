import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import qrcode
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

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def send_notification_admin(details):
    destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Système EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = f"Rapport de Séance : {details['matiere']} - {details['promotion']}"
        corps = f"""Rapport de séance validé :\n- Enseignant : {details['enseignant']}\n- Promotion : {details['promotion']}\n- Absents : {details['nb_absents']}"""
        msg.attach(MIMEText(corps, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except: pass

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
        st.error(f"Erreur Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()

def get_staff_info(user_nom, user_email):
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
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
    t_login, t_signup, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email :")
        p_log = st.text_input("Code :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")

    with t_student:
        st.info("Recherchez votre nom pour voir votre emploi du temps et générer votre QR Code d'accès.")
        df_etudiants['Full_N'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()
        nom_st = st.selectbox("Sélectionnez votre nom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.success(f"Promotion : {profil['Promotion']} | Groupe : {profil['Groupe']}")
            
            # Génération QR Code
            url_plateforme = f"https://votre-app.streamlit.app/?student={nom_st.replace(' ', '+')}"
            qr_img = generate_qr(url_plateforme)
            st.image(qr_img, caption="Votre QR Code d'accès rapide", width=150)
            
            # Affichage EDT
            edt_st = df_edt[df_edt['Promotion'] == profil['Promotion']]
            st.table(edt_st[['Enseignements', 'Horaire', 'Jours', 'Lieu']])
    st.stop()

# --- 5. INTERFACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
current_grade, current_statut = get_staff_info(user['nom_officiel'], user['email'])

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}\n**{current_grade}** ({current_statut})")
    st.divider()
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
        if st.button("🗑️ Vider Archives"): st.session_state["reset_trigger"] = True
    else: enseignant_vue = user['nom_officiel']
    
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<h4 style='text-align:center;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)
tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("Séance :", ["Cours", "TD", "TP", "Examen"])
    reg_s = c2.selectbox("Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("Date :", value=datetime.now())

    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    # CALCUL EFFECTIFS
    df_promo_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    eff_promo = len(df_promo_full)
    
    m_sel = st.selectbox("Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])

    col_g, col_sg = st.columns(2)
    with col_g:
        g_sel = st.selectbox("Groupe :", sorted(df_promo_full['Groupe'].unique()) if not df_promo_full.empty else ["G1"])
        eff_g = len(df_promo_full[df_promo_full['Groupe'] == g_sel])
    with col_sg:
        sg_sel = st.selectbox("Sous-groupe :", sorted(df_promo_full[df_promo_full['Groupe']==g_sel]['Sous groupe'].unique()) if not df_promo_full.empty else ["SG1"])
        eff_sg = len(df_promo_full[(df_promo_full['Groupe'] == g_sel) & (df_promo_full['Sous groupe'] == sg_sel)])

    # AFFICHAGE DES COMPTEURS
    st.markdown(f"""
    <div style="background-color:#f0f2f6; padding:10px; border-radius:10px; text-align:center;">
        <b>📊 Effectifs :</b> Promotion: <span style="color:blue;">{eff_promo}</span> | 
        Groupe ({g_sel}): <span style="color:green;">{eff_g}</span> | 
        Sous-groupe ({sg_sel}): <span style="color:orange;">{eff_sg}</span>
    </div>
    """, unsafe_allow_html=True)

    df_app = df_promo_full[(df_promo_full['Groupe']==g_sel) & (df_promo_full['Sous groupe']==sg_sel)].copy()
    df_app['Full_N'] = (df_app['Nom'].fillna('') + " " + df_app['Prénom'].fillna('')).str.upper().str.strip()
    liste_et = df_app['Full_N'].tolist()

    abs_sel = st.multiselect("❌ Absents :", options=liste_et)
    code_v = st.text_input("🔑 Code Unique :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            meta = {"promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_grade} {user['nom_officiel']}", "statut_enseignant": current_statut, "date_seance": str(date_s), "regime_heure": reg_s, "nb_absents": len(abs_sel)}
            for ab in abs_sel:
                row = meta.copy(); row.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                safe_insert("archives_absences", row)
            send_notification_admin(meta)
            st.success("✅ Rapport envoyé."); st.balloons()
