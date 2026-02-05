import streamlit as st
import pandas as pd
import os
import hashlib
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Fichiers sources
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# Configuration Email Admin
EMAIL_SENDER = "votre_email@gmail.com"  # À configurer
EMAIL_PASSWORD = "votre_code_application" # Code 16 lettres Google
EMAIL_ADMIN = "milouafarid@gmail.com"

# --- 2. CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_report_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_ADMIN
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return False

@st.cache_data
def load_and_clean_data():
    # Lecture
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    
    # Nettoyage des colonnes (suppression espaces et forcçage texte)
    df_e.columns = [str(c).strip() for c in df_e.columns]
    df_s.columns = [str(c).strip() for c in df_s.columns]
    
    # Nettoyage des contenus pour éviter les erreurs de correspondance
    for col in ['Enseignants', 'Enseignements', 'Promotion']:
        if col in df_e.columns:
            df_e[col] = df_e[col].astype(str).str.strip()
            
    return df_e, df_s

# --- 4. CHARGEMENT DES DONNÉES ---
try:
    df_edt, df_etudiants = load_and_clean_data()
except Exception as e:
    st.error(f"Erreur de fichiers : {e}")
    st.stop()

# --- 5. SYSTÈME D'AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"### 🔑 Validation Enseignant")
    email_in = st.text_input("Entrez votre Email professionnel :")
    pass_in = st.text_input("Entrez votre mot de passe :", type="password")
    
    if st.button("Accéder à la plateforme", use_container_width=True):
        res = supabase.table("enseignants_auth").select("*").eq("email", email_in).eq("password_hash", hash_pw(pass_in)).execute()
        if res.data:
            st.session_state["user_data"] = res.data[0]
            st.rerun()
        else:
            st.error("Email ou mot de passe incorrect.")
    st.stop()

# --- 6. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"**{TITRE_OFFICIEL}**")

# Sélection Enseignant (Pré-rempli selon le login)
st.markdown("### 👤 1. Sélectionner l'Enseignant :")
profs_list = sorted(df_edt['Enseignants'].unique())
default_idx = profs_list.index(user['nom_officiel']) if user['nom_officiel'] in profs_list else 0
enseignant_sel = st.selectbox("", profs_list, index=default_idx)

# Onglets
tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    # Ligne 1 : Promotion et Matière
    c1, c2 = st.columns(2)
    with c1:
        # On filtre les promos pour cet enseignant uniquement
        promos_prof = df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique()
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", sorted(promos_prof))
    
    with c2:
        # On filtre les matières pour cet enseignant et cette promo
        mats_prof = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique()
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", sorted(mats_prof))

    # --- SÉCURITÉ CONTRE LE CRASH (IndexError) ---
    search_res = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    
    if not search_res.empty:
        info = search_res.iloc[0]
        st.info(f"📍 {info['Jours']} | {info['Horaire']} | Lieu: {info['Lieu']}")
    else:
        st.warning("⚠️ Séance non répertoriée dans l'emploi du temps pour ce choix.")

    st.markdown("### 📈 État d'Avancement & Appel")
    
    # Filtrage Etudiants
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    
    col_g, col_sg = st.columns(2)
    with col_g:
        groupe_sel = st.selectbox("👥 Sélectionner le Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    with col_sg:
        df_g = df_p[df_p['Groupe'] == groupe_sel]
        sg_sel = st.selectbox("🔢 Sélectionner le Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    # --- STATISTIQUES ---
    st.markdown("#### 📊 Statistiques de présence")
    stat1, stat2, stat3 = st.columns(3)
    
    df_sg_final = df_g[df_g['Sous groupe'] == sg_sel]
    
    stat1.metric("Effectif Promotion", len(df_p))
    stat2.metric(f"Effectif {groupe_sel}", len(df_g))
    stat3.metric(f"Effectif {sg_sel}", len(df_sg_final))

    # --- UNITÉ ---
    st.divider()
    cu1, cu2 = st.columns(2)
    with cu1:
        u_type = st.selectbox("Type d'unité :", ["Chapitre", "TP Numéro", "TD Série", "Autre"])
    with cu2:
        u_num = st.text_input("Numéro :")

    # --- LISTE D'APPEL ---
    st.markdown(f"### ❌ Sélectionner les ABSENTS :")
    st.write(f"Liste des {len(df_sg_final)} étudiants du {sg_sel}")
    
    # Création de l'affichage Nom Prénom
    if not df_sg_final.empty:
        df_sg_final['Full_Name'] = df_sg_final['Nom'].astype(str) + " " + df_sg_final['Prénom'].astype(str)
        absents_choisis = st.multiselect("Cochez les absents :", options=df_sg_final['Full_Name'].tolist())
    else:
        st.write("Aucun étudiant trouvé pour ce sous-groupe.")
        absents_choisis = []

    # --- VALIDATION ET EMAIL ---
    st.divider()
    d1, d2 = st.columns(2)
    with d1:
        date_seance = st.date_input("📅 Date réelle de la séance :")
    with d2:
        obs = st.text_area("🗒️ Observations (Obligatoire) :")
        
    s1, s2 = st.columns(2)
    with s1:
        sign = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    with s2:
        code_v = st.text_input("🔑 Entrez votre Code Unique :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if not obs or not sign or not code_v:
            st.error("Veuillez remplir tous les champs obligatoires.")
        else:
            # Préparation du rapport
            rapport = f"""
            RAPPORT D'ASSIDUITÉ - {TITRE_OFFICIEL}
            -----------------------------------------
            Enseignant : {enseignant_sel}
            Matière : {matiere_sel}
            Promotion : {promo_sel} | Groupe : {groupe_sel} | SG : {sg_sel}
            Contenu : {u_type} n°{u_num}
            Date : {date_seance}
            
            ABSENTS ({len(absents_choisis)}) :
            {', '.join(absents_choisis) if absents_choisis else "Aucun"}
            
            Observations : {obs}
            Signé par : {sign}
            """
            
            with st.spinner("Transmission à l'administration..."):
                ok = send_report_email(f"Présence - {promo_sel} - {enseignant_sel}", rapport)
                if ok:
                    st.success("✅ Rapport envoyé avec succès à milouafarid@gmail.com")
                    st.balloons()
                else:
                    st.warning("⚠️ Rapport validé, mais l'envoi de l'email a échoué (vérifiez vos paramètres SMTP).")

with tab_hist:
    st.write("L'historique des séances sera disponible prochainement.")
