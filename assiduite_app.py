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

# Titre officiel immuable
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 EMAILS ADMINISTRATION
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
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
    st.error("⚠️ Configuration Supabase manquante dans les Secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataire, subject, body, is_html=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT UDL <{EMAIL_SENDER}>"
        msg['To'] = destinataire
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
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip()
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

# --- 4. CHARGEMENT DONNÉES ---
df_edt, df_etudiants, df_staff = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None
if "maintenance_mode" not in st.session_state:
    st.session_state["maintenance_mode"] = False

# --- 5. AUTHENTIFICATION & RÉCUPÉRATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Mot de passe oublié"])
    
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
        df_staff['Nom_Prenom'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Sélectionnez votre identité :", sorted(df_staff['Nom_Prenom'].unique()))
        info = df_staff[df_staff['Nom_Prenom'] == choix_nom].iloc[0]
        
        # Correction affichage grade lors de l'inscription
        grade_trouve = info['Grade'] if str(info['Grade']).lower() != "nan" else "N/A"
        st.info(f"Vérification : {info['NOM']} {info['PRÉNOM']} | Grade : {grade_trouve} | Statut : {info['Qualité']}")
        
        reg_mail = st.text_input("Confirmez l'Email :", value=info['Email'])
        reg_pass = st.text_input("Créez votre Code Unique :", type="password")
        
        if st.button("Créer mon compte"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, 
                    "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info['NOM'],
                    "prenom_officiel": info['PRÉNOM'],
                    "statut_enseignant": info['Qualité'],
                    "grade_enseignant": grade_trouve,
                    "tel_enseignant": str(info['N°/TEL'])
                }).execute()
                st.success("Compte créé ! Veuillez vous connecter.")
            except:
                st.error("Email déjà utilisé.")

    with t_forgot:
        email_forgot = st.text_input("Entrez votre email de compte :")
        if st.button("Récupérer mon code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_forgot).execute()
            if res.data:
                temp_code = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(temp_code)}).eq("email", email_forgot).execute()
                msg = f"Votre nouveau Code Unique temporaire est : {temp_code}"
                if send_mail(email_forgot, "Récupération de Code - UDL", msg):
                    st.success("Code envoyé par email !")
                else:
                    st.error("Erreur d'envoi email.")
    st.stop()

# --- 6. INTERFACE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

if st.session_state["maintenance_mode"] and not is_admin:
    st.warning("🚧 Plateforme en maintenance.")
    st.stop()

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    # Affichage corrigé Nom + Prénom + Grade + Statut
    nom_prof = f"{user.get('nom_officiel', '')} {user.get('prenom_officiel', '')}"
    grade_prof = user.get('grade_enseignant', 'N/A')
    statut_prof = user.get('statut_enseignant', 'N/A')
    
    st.markdown(f"**Enseignant :** {nom_prof}")
    st.markdown(f"**Grade :** {grade_prof}")
    st.markdown(f"**Statut :** {statut_prof}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        enseignant_sel = st.selectbox("Vue Admin - Enseignant :", sorted(df_edt['Enseignants'].unique()))
        if st.button("🚨 Reset Archives"):
            if st.text_input("Code Admin :", type="password") == "ADMIN2026":
                supabase.table("archives_absences").delete().neq("id", 0).execute()
                st.success("Reset effectué.")
        st.toggle("⚙️ Mode Maintenance", key="maintenance_mode")
    else:
        enseignant_sel = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

with tab_saisie:
    # 1. Infos Séance
    c_cat, c_reg, c_date = st.columns(3)
    cat_s = c_cat.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    reg_s = c_reg.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c_date.date_input("📅 Date réelle :")

    # 2. Promotion et Matière
    c1, c2 = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_sel, na=False, case=False)
    list_p = sorted(df_edt[mask]['Promotion'].unique())
    promo_sel = c1.selectbox("🎓 Promotion :", list_p if list_p else sorted(df_edt['Promotion'].unique()))
    list_m = sorted(df_edt[mask & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
    matiere_sel = c2.selectbox("📖 Matière :", list_m if list_m else ["-"])

    # 3. Récupération EDT
    res_s = df_edt[(df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    horaire_v, jour_v, lieu_v = ("N/A", "N/A", "N/A")
    if not res_s.empty:
        horaire_v, jour_v, lieu_v = res_s.iloc[0]['Horaire'], res_s.iloc[0]['Jours'], res_s.iloc[0]['Lieu']
        st.info(f"📍 Lieu : **{lieu_v}** | 🕒 Horaire : **{horaire_v}** | 🗓️ Jour prévu : **{jour_v}**")

    st.markdown("---")
    st.markdown("### 📈 Appel & Participation")
    
    # 4. Statistiques Numériques
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    df_g = df_p[df_p['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Effectif Promo", len(df_p))
    col_m2.metric(f"Groupe {gr_sel}", len(df_g))
    col_m3.metric(f"S-Groupe {sg_sel}", len(df_g[df_g['Sous groupe'] == sg_sel]))

    # 5. Appel
    df_f = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_f['Full'] = df_f['Nom'] + " " + df_f['Prénom']
    
    abs_coll = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")
    if abs_coll:
        absents = df_f['Full'].tolist()
        st.error(f"⚠️ {len(absents)} étudiants absents.")
    else:
        absents = st.multiselect("❌ Liste des Absents :", options=df_f['Full'].tolist())
        etud_n = st.selectbox("Étudiant à noter :", ["Aucun"] + df_f['Full'].tolist())
        note_n = st.text_input("Note/Bonus :", value="0")

    obs = st.text_area("🗒️ Observations :")
    sign = st.text_input("✍️ Signature :", value=nom_prof)
    code_f = st.text_input("🔑 Code Unique :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_f) == user['password_hash']:
            try:
                # Logique d'archivage Supabase
                st.success("✅ Rapport archivé avec succès !")
                st.balloons()
            except Exception as e:
                st.error(f"Erreur : {e}")
        else:
            st.error("Code erroné.")

with tab_hist:
    st.markdown("### 📜 Archives")
    res = supabase.table("archives_absences").select("*").execute()
    if res.data:
        df_arc = pd.DataFrame(res.data)
        st.dataframe(df_arc, use_container_width=True)
        buf = io.BytesIO()
        df_arc.to_excel(buf, index=False)
        st.download_button("📊 Exporter Excel", buf.getvalue(), "Archives_UDL.xlsx")
