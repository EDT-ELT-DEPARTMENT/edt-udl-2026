import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion du département d'électrotechnique-2025-2026 - États d'avancement des enseignements - Assiduité des étudiants"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# 📧 EMAILS ADMIN
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_CHEF_ADJOINT = ""
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body, is_html=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
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
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    for df in [df_e, df_s]:
        df.columns = [str(c).strip() for c in df.columns]
    return df_e, df_s

# --- 4. CHARGEMENT ET AUTHENTIFICATION ---
df_edt, df_etudiants = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"### 🔑 Accès Enseignant")
    t_login, t_signup, t_perdu = st.tabs(["Connexion", "Inscription", "Code oublié ?"])
    
    with t_login:
        email_log = st.text_input("Email professionnel :", key="l_mail")
        pass_log = st.text_input("Code Unique :", type="password", key="l_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

    with t_signup:
        st.info("Créez votre accès à la plateforme")
        new_nom = st.selectbox("Sélectionnez votre nom dans l'EDT :", sorted(df_edt['Enseignants'].unique()))
        new_mail = st.text_input("Email professionnel (Sert d'identifiant) :")
        new_pass = st.text_input("Créez votre Code Unique :", type="password")
        if st.button("Valider l'inscription"):
            data_user = {"email": new_mail, "password_hash": hash_pw(new_pass), "nom_officiel": new_nom}
            try:
                supabase.table("enseignants_auth").insert(data_user).execute()
                st.success("Inscription réussie ! Connectez-vous.")
            except:
                st.error("Email déjà utilisé.")

    with t_perdu:
        st.warning("Une demande sera envoyée à l'administrateur.")
        mail_oublie = st.text_input("Entrez votre email de compte :")
        if st.button("Envoyer la demande"):
            send_mail(EMAIL_ADMIN_TECH, "RÉCUPÉRATION CODE", f"L'enseignant {mail_oublie} a oublié son code.")
            st.success("Demande envoyée.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<h3 style='text-align:center; color:#003366;'>{TITRE_PLATEFORME}</h3>", unsafe_allow_html=True)

is_admin = (user['email'] == EMAIL_ADMIN_TECH)
profs_list = sorted(df_edt['Enseignants'].unique())

if is_admin:
    st.sidebar.success("Mode Administrateur")
    enseignant_sel = st.selectbox("👤 Sélectionner l'Enseignant (Admin) :", profs_list)
else:
    enseignant_sel = st.selectbox("👤 Enseignant :", [user['nom_officiel']], disabled=True)

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive des Absences"])

with tab_saisie:
    # --- TYPE DE SEANCE ET CALENDRIER ---
    c_type, c_date = st.columns(2)
    type_seance = c_type.selectbox("📂 Type de séance :", ["Séance Normale", "Séance de Rattrapage"])
    date_seance = c_date.date_input("📅 Date de la séance :", datetime.now())

    c1, c2 = st.columns(2)
    promos = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
    promo_sel = c1.selectbox("🎓 Promotion :", promos)
    mats = sorted(df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
    matiere_sel = c2.selectbox("📖 Matière :", mats)

    res_s = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    horaire_v = res_s.iloc[0]['Horaire'] if not res_s.empty else "Rattrapage (H. non définie)"
    
    st.markdown("### 📈 Appel & Absences")
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    df_g = df_p[df_p['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    # --- OPTION ABSENCE COLLECTIVE ---
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE (Tous les étudiants du groupe)")

    df_f = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_f['Full'] = df_f['Nom'].astype(str) + " " + df_f['Prénom'].astype(str)
    
    if abs_collective:
        absents = df_f['Full'].tolist()
        st.warning(f"⚠️ {len(absents)} étudiants seront marqués absents collectivement.")
    else:
        absents = st.multiselect("❌ Sélectionner les étudiants ABSENTS :", options=df_f['Full'].tolist())

    obs = st.text_area("🗒️ Observations (Ex: Motif du rattrapage ou de l'absence collective) :")
    
    s_col, k_col = st.columns(2)
    signature = s_col.text_input("✍️ Signature :")
    code_final = k_col.text_input("🔑 Code Unique :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_final) == user['password_hash']:
            # 1. ARCHIVAGE SUPABASE
            mention_abs = "OUI" if not abs_collective else "COLLECTIVE"
            for etud in absents:
                supabase.table("archives_absences").insert({
                    "etudiant_nom": etud, 
                    "promotion": promo_sel, 
                    "groupe": gr_sel,
                    "sous_groupe": sg_sel, 
                    "matiere": matiere_sel, 
                    "enseignant": enseignant_sel,
                    "date_seance": str(date_seance), 
                    "horaire": horaire_v,
                    "type_seance": type_seance,
                    "absence_collective": abs_collective
                }).execute()

            # 2. EMAIL
            msg_coll = "⚠️ ABSENCE COLLECTIVE" if abs_collective else "Absences individuelles"
            mail_body = f"""
            <h2>Rapport de Séance - {type_seance}</h2>
            <p><b>Statut :</b> {msg_coll}</p>
            <p><b>Enseignant :</b> {enseignant_sel} | <b>Matière :</b> {matiere_sel}</p>
            <p><b>Nombre d'absents :</b> {len(absents)}</p>
            <p><b>Observations :</b> {obs}</p>
            <p><b>Signé :</b> {signature}</p>
            """
            destinataires = [EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']]
            if send_mail(destinataires, f"[{type_seance}] {promo_sel} - {enseignant_sel}", mail_body, is_html=True):
                st.success("✅ Séance archivée et rapport envoyé !")
                st.balloons()
        else:
            st.error("Code Unique incorrect.")

with tab_hist:
    st.markdown("### 📋 Historique Global")
    try:
        data_arc = supabase.table("archives_absences").select("*").execute()
        if data_arc.data:
            df_arc = pd.DataFrame(data_arc.data)
            # Affichage ordonné
            cols_to_show = ['etudiant_nom', 'promotion', 'groupe', 'matiere', 'enseignant', 'date_seance', 'type_seance']
            st.dataframe(df_arc[cols_to_show], use_container_width=True)
            
            # Export
            buf = io.BytesIO()
            df_arc.to_excel(buf, index=False)
            st.download_button("📊 Télécharger EXCEL", buf.getvalue(), "Archives_Complet.xlsx")
    except:
        st.info("Aucune archive.")

if st.sidebar.button("Se déconnecter"):
    st.session_state["user_data"] = None
    st.rerun()

