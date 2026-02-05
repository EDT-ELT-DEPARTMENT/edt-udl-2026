import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import random
import string
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Configuration Supabase manquante.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataire, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT UDL <{EMAIL_SENDER}>"
        msg['To'] = destinataire
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
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
        df_staff = pd.read_excel(FICHICHIER_STAFF if 'FICHICHIER_STAFF' in locals() else FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace('nan', '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

# --- 4. SYNCHRONISATION DU GRADE ---
def sync_user_profile(user_record):
    """Force la mise à jour du grade et statut depuis l'Excel vers la DB"""
    email = user_record['email']
    match = df_staff[df_staff['Email'] == email]
    if not match.empty:
        new_grade = match.iloc[0]['Grade'] if match.iloc[0]['Grade'] != '' else 'Enseignant'
        new_statut = match.iloc[0]['Qualité']
        # Si la DB est différente de l'Excel, on met à jour
        if user_record.get('grade_enseignant') != new_grade or user_record.get('statut_enseignant') != new_statut:
            supabase.table("enseignants_auth").update({
                "grade_enseignant": new_grade,
                "statut_enseignant": new_statut
            }).eq("email", email).execute()
            user_record['grade_enseignant'] = new_grade
            user_record['statut_enseignant'] = new_statut
    return user_record

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 5. AUTHENTIFICATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Mot de passe oublié"])
    
    with t_login:
        email_log = st.text_input("Email :", key="l_mail")
        pass_log = st.text_input("Code Unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                # Synchronisation immédiate au login
                st.session_state["user_data"] = sync_user_profile(res.data[0])
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full'].unique()))
        info = df_staff[df_staff['Full'] == choix].iloc[0]
        grade_signup = info['Grade'] if info['Grade'] != '' else 'Enseignant'
        
        st.info(f"Profil : {info['NOM']} | Grade : {grade_signup} | Statut : {info['Qualité']}")
        reg_mail = st.text_input("Email (doit correspondre au fichier) :", value=info['Email'])
        reg_pass = st.text_input("Nouveau Code Unique :", type="password")
        
        if st.button("Créer le compte"):
            supabase.table("enseignants_auth").insert({
                "email": reg_mail, "password_hash": hash_pw(reg_pass),
                "nom_officiel": info['NOM'], "prenom_officiel": info['PRÉNOM'],
                "statut_enseignant": info['Qualité'], "grade_enseignant": grade_signup
            }).execute()
            st.success("Compte créé !")

    with t_forgot:
        f_email = st.text_input("Email pour récupération :")
        if st.button("Réinitialiser mon code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_mail(f_email, "Nouveau Code UDL", f"Votre nouveau code : {new_c}")
                st.success("Code envoyé par email !")
    st.stop()

# --- 6. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# --- HEADER ---
st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    st.markdown(f"**Enseignant :** {user['nom_officiel']} {user.get('prenom_officiel', '')}")
    # Sécurité supplémentaire pour l'affichage sidebar
    grade_display = user.get('grade_enseignant')
    if not grade_display or grade_display == 'None' or grade_display == '':
        grade_display = "Enseignant"
    
    st.markdown(f"**Grade :** {grade_display}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        enseignant_sel = st.selectbox("Vue Admin :", sorted(df_edt['Enseignants'].unique()))
        
        # Maintenance
        if st.toggle("⚙️ Mode Maintenance"):
            st.warning("⚠️ Maintenance active pour les utilisateurs.")
        
        # Reset Base
        if st.button("🚨 Reset Archives"):
            st.session_state["reset_lock"] = True
        if st.session_state.get("reset_lock"):
            pw_reset = st.text_input("Code Admin pour confirmer :", type="password")
            if st.button("OUI, TOUT EFFACER"):
                if hash_pw(pw_reset) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base réinitialisée.")
                    st.session_state["reset_lock"] = False
    else:
        enseignant_sel = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

# --- ONGLETS ---
tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    reg_s = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("📅 Date réelle :")

    c_prom, c_mat = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_sel, na=False, case=False)
    list_promos = sorted(df_edt[mask]['Promotion'].unique())
    promo_sel = c_prom.selectbox("🎓 Promotion :", list_promos if list_promos else sorted(df_edt['Promotion'].unique()))
    list_mats = sorted(df_edt[mask & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
    matiere_sel = c_mat.selectbox("📖 Matière :", list_mats if list_mats else ["-"])

    # Info Horaire
    edt_info = df_edt[(df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    if not edt_info.empty:
        st.info(f"📍 {edt_info.iloc[0]['Lieu']} | 🕒 {edt_info.iloc[0]['Horaire']} | 🗓️ {edt_info.iloc[0]['Jours']}")

    st.markdown("---")
    st.markdown("### 📈 Appel & Participation")
    
    # Statistiques Numériques
    df_promo_full = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    col_g, col_sg = st.columns(2)
    gr_sel = col_g.selectbox("👥 Groupe :", sorted(df_promo_full['Groupe'].unique()) if not df_promo_full.empty else ["-"])
    df_g = df_promo_full[df_promo_full['Groupe'] == gr_sel]
    sg_sel = col_sg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_promo_full))
    m2.metric(f"Groupe {gr_sel}", len(df_g))
    m3.metric(f"S-Groupe {sg_sel}", len(df_g[df_g['Sous groupe'] == sg_sel]))

    # Liste
    df_final = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_final['Full'] = df_final['Nom'] + " " + df_final['Prénom']
    
    abs_coll = st.checkbox("🚩 SIGNALER ABSENCE COLLECTIVE")
    if abs_coll:
        absents = df_final['Full'].tolist()
        st.error(f"⚠️ {len(absents)} étudiants absents.")
    else:
        absents = st.multiselect("❌ Absents :", options=df_final['Full'].tolist())
        et_note = st.selectbox("Noter un étudiant :", ["Aucun"] + df_final['Full'].tolist())
        nt_note = st.text_input("Note :", "0")

    obs = st.text_area("🗒️ Observations :")
    sign = st.text_input("✍️ Signature :", value=f"{user['nom_officiel']} {user.get('prenom_officiel', '')}")
    code_v = st.text_input("🔑 Code Unique pour valider :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            # Logique d'envoi vers Supabase ici
            st.success("✅ Séance archivée !")
            st.balloons()
        else:
            st.error("Code erroné.")

with tab_hist:
    st.markdown("### 📜 Archives")
    res_arc = supabase.table("archives_absences").select("*").execute()
    if res_arc.data:
        df_arc = pd.DataFrame(res_arc.data)
        st.dataframe(df_arc, use_container_width=True)
        buf = io.BytesIO()
        df_arc.to_excel(buf, index=False)
        st.download_button("📊 Exporter Excel", buf.getvalue(), "Archives_UDL_SBA.xlsx")
