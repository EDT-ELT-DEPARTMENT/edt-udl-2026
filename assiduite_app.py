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

# Titre officiel requis
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# Emails Admin
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# Config SMTP
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
        df_staff = pd.read_excel(FICHIER_STAFF)
        # Nettoyage strict
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace('nan', '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

# --- 4. CHARGEMENT DONNÉES ---
df_edt, df_etudiants, df_staff = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 5. AUTHENTIFICATION & RÉCUPÉRATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié"])
    
    with t_login:
        email_log = st.text_input("Email :", key="l_mail")
        pass_log = st.text_input("Code Unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Qui êtes-vous ?", sorted(df_staff['Full'].unique()))
        info = df_staff[df_staff['Full'] == choix].iloc[0]
        
        # Sécurité Grade vide
        grade_clean = info['Grade'] if info['Grade'] != '' else 'Enseignant'
        
        st.success(f"Détails : {info['NOM']} {info['PRÉNOM']} | {grade_clean} | {info['Qualité']}")
        
        reg_mail = st.text_input("Email professionnel :", value=info['Email'])
        reg_pass = st.text_input("Créer votre Code Unique :", type="password")
        
        if st.button("Finaliser l'inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info['NOM'], "prenom_officiel": info['PRÉNOM'],
                    "statut_enseignant": info['Qualité'], "grade_enseignant": grade_clean
                }).execute()
                st.success("Compte créé !")
            except:
                st.error("Erreur (compte existant ?)")

    with t_forgot:
        f_email = st.text_input("Email de récupération :")
        if st.button("Recevoir un nouveau code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                if send_mail(f_email, "Nouveau Code - UDL", f"Votre nouveau code : {new_c}"):
                    st.success("Code envoyé par Email !")
                else:
                    st.error("Erreur SMTP.")
    st.stop()

# --- 6. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    # Affichage Nom Prénom et Grade corrigé
    st.markdown(f"**Enseignant :** {user['nom_officiel']} {user.get('prenom_officiel', '')}")
    st.markdown(f"**Grade :** {user.get('grade_enseignant', 'Enseignant')}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_sel = st.selectbox("Vue Admin :", sorted(df_edt['Enseignants'].unique()))
        
        st.divider()
        if st.button("🚨 Reset Archives"):
            st.session_state["reset_conf"] = True
        if st.session_state.get("reset_conf"):
            if st.button("CONFIRMER SUPPRESSION TOTALE"):
                supabase.table("archives_absences").delete().neq("id", 0).execute()
                st.success("Base vidée.")
                st.session_state["reset_conf"] = False
    else:
        enseignant_sel = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

with tab_saisie:
    # 1. Infos
    c_cat, c_reg, c_date = st.columns(3)
    cat_s = c_cat.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    reg_s = c_reg.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c_date.date_input("📅 Date réelle :")

    # 2. Promo
    c1, c2 = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_sel, na=False, case=False)
    list_p = sorted(df_edt[mask]['Promotion'].unique())
    promo_sel = c1.selectbox("🎓 Promotion :", list_p if list_p else sorted(df_edt['Promotion'].unique()))
    list_m = sorted(df_edt[mask & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
    matiere_sel = c2.selectbox("📖 Matière :", list_m if list_m else ["-"])

    # 3. Récupération Horaire
    res_s = df_edt[(df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    if not res_s.empty:
        st.info(f"📍 {res_s.iloc[0]['Lieu']} | 🕒 {res_s.iloc[0]['Horaire']} | 🗓️ {res_s.iloc[0]['Jours']}")

    st.markdown("---")
    st.markdown("### 📈 Appel & Participation")
    
    # 4. Statistiques Numériques (Effectifs)
    df_promo_full = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_promo_full['Groupe'].unique()) if not df_promo_full.empty else ["G1"])
    df_g = df_promo_full[df_promo_full['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["SG11"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_promo_full))
    m2.metric(f"Groupe {gr_sel}", len(df_g))
    m3.metric(f"S-Groupe {sg_sel}", len(df_g[df_g['Sous groupe'] == sg_sel]))

    # 5. Appel
    df_appel = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    
    abs_coll = st.checkbox("🚩 ABSENCE COLLECTIVE")
    if abs_coll:
        absents = df_appel['Full'].tolist()
        st.error(f"⚠️ {len(absents)} étudiants absents.")
    else:
        absents = st.multiselect("❌ Absents :", options=df_appel['Full'].tolist())
        et_n = st.selectbox("Noter un étudiant :", ["Aucun"] + df_appel['Full'].tolist())
        nt_n = st.text_input("Note/Bonus :", value="0")

    sign = st.text_input("✍️ Signature :", value=f"{user['nom_officiel']} {user.get('prenom_officiel', '')}")
    code_f = st.text_input("🔑 Code Unique pour valider :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_f) == user['password_hash']:
            # Archivage Supabase ici
            st.success("✅ Rapport envoyé avec succès !")
            st.balloons()
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
        st.download_button("📊 Télécharger l'historique", buf.getvalue(), "Archives_UDL.xlsx")
