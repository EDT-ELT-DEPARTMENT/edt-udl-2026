import streamlit as st
import pandas as pd
import hashlib
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# 📧 ADRESSES EMAILS SPÉCIFIQUES
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_CHEF_ADJOINT = "nass_ka@yahoo.fr"
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP (GMAIL)
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_report_multi(destinataires, subject, body):
    """Envoie l'email à une liste de destinataires"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Envoyé"
    except Exception as e:
        return False, str(e)

@st.cache_data
def load_data():
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    # Nettoyage
    for df in [df_e, df_s]:
        df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignants', 'Enseignements', 'Promotion']:
        if col in df_e.columns:
            df_e[col] = df_e[col].astype(str).str.strip()
    return df_e, df_s

# --- 4. CHARGEMENT ET AUTHENTIFICATION ---
try:
    df_edt, df_etudiants = load_data()
except Exception as e:
    st.error(f"Erreur de chargement des fichiers Excel : {e}")
    st.stop()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# BLOC DE CONNEXION (Indispensable pour voir l'interface)
if not st.session_state["user_data"]:
    st.markdown(f"### 🔑 Validation Enseignant")
    email_log = st.text_input("Entrez votre Email professionnel :")
    pass_log = st.text_input("Entrez votre Code Unique :", type="password")
    
    if st.button("Accéder à la plateforme", use_container_width=True):
        res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
        if res.data:
            st.session_state["user_data"] = res.data[0]
            st.rerun()
        else:
            st.error("Identifiants incorrects.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE (AFFICHEE APRES LOGIN) ---
user = st.session_state["user_data"]
st.markdown(f"<div style='background-color:#003366; color:white; padding:10px; border-radius:5px; text-align:center;'>{TITRE_PLATEFORME}</div>", unsafe_allow_html=True)

# 1. Sélection Enseignant
profs = sorted(df_edt['Enseignants'].unique())
idx_user = profs.index(user['nom_officiel']) if user['nom_officiel'] in profs else 0
enseignant_sel = st.selectbox("👤 1. Sélectionner l'Enseignant :", profs, index=idx_user)

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    col1, col2 = st.columns(2)
    with col1:
        promos = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", promos)
    with col2:
        mats = sorted(df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", mats)

    # Infos séance depuis l'EDT
    res_seance = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    if not res_seance.empty:
        info = res_seance.iloc[0]
        st.info(f"📍 {info['Jours']} | {info['Horaire']} | Lieu: {info['Lieu']}")
        # Récupération emails dynamiques si colonnes existent
        email_prof_concerne = info['Email_Enseignant'] if 'Email_Enseignant' in info else user['email']
        email_resp_parcours = info['Email_Responsable_Parcours'] if 'Email_Responsable_Parcours' in info else EMAIL_ADMIN_TECH
    else:
        st.warning("Séance non trouvée.")

    st.markdown("### 📈 État d'Avancement & Appel")
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    with cg:
        gr_sel = st.selectbox("👥 Sélectionner le Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    with csg:
        df_g = df_p[df_p['Groupe'] == gr_sel]
        sg_sel = st.selectbox("🔢 Sélectionner le Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    # Stats
    df_f = df_g[df_g['Sous groupe'] == sg_sel]
    s1, s2, s3 = st.columns(3)
    s1.metric("Effectif Promotion", len(df_p))
    s2.metric(f"Effectif {gr_sel}", len(df_g))
    s3.metric(f"Effectif {sg_sel}", len(df_f))

    # Appel
    st.markdown("### ❌ Sélectionner les ABSENTS :")
    df_f['Full'] = df_f['Nom'].astype(str) + " " + df_f['Prénom'].astype(str)
    absents = st.multiselect(f"Liste des {len(df_f)} étudiants", options=df_f['Full'].tolist())

    # Validation
    st.divider()
    v1, v2 = st.columns(2)
    date_s = v1.date_input("📅 Date réelle de la séance :")
    obs = v2.text_area("🗒️ Observations (Obligatoire) :")
    
    sig_col, code_col = st.columns(2)
    sign = sig_col.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    code_v = code_col.text_input("🔑 Entrez votre Code Unique :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if not obs or not sign or hash_pw(code_v) != user['password_hash']:
            st.error("Données invalides ou Code Unique incorrect.")
        else:
            destinataires = [EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, email_prof_concerne, email_resp_parcours, EMAIL_ADMIN_TECH]
            destinataires = list(set([d for d in destinataires if d and "@" in str(d)]))

            corps = f"""
            RAPPORT DE SÉANCE - {TITRE_PLATEFORME}
            ------------------------------------------
            ENSEIGNANT : {enseignant_sel}
            MATIÈRE : {matiere_sel} ({promo_sel})
            GROUPE : {gr_sel} | SG : {sg_sel}
            DATE : {date_s}
            ------------------------------------------
            ABSENTS : {", ".join(absents) if absents else "Aucun"}
            ------------------------------------------
            OBSERVATIONS : {obs}
            SIGNATURE : {sign}
            """
            
            with st.spinner("Envoi aux responsables..."):
                ok, error = send_report_multi(destinataires, f"Présence {promo_sel} - {enseignant_sel}", corps)
                if ok:
                    st.success(f"✅ Rapport envoyé à : {', '.join(destinataires)}")
                    st.balloons()
                else:
                    st.error(f"❌ Erreur : {error}")

with tab_hist:
    st.write("L'historique des séances apparaîtra ici.")
