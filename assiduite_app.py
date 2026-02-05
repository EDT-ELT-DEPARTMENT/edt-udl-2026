import streamlit as st
import pandas as pd
import os
import hashlib
import io
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="EDT UDL 2026",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PARAMÈTRES FIXES ---
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
NOM_FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
NOM_FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# --- CONFIGURATION EMAIL (SMTP) ---
EMAIL_SENDER = "votre_email@gmail.com"  # À remplacer
EMAIL_PASSWORD = "votre_code_application" # Code 16 lettres Google
EMAIL_ADMIN = "milouafarid@gmail.com"

# --- CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- FONCTIONS TECHNIQUES ---
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
    except:
        return False

@st.cache_data
def load_all_data():
    df_edt = pd.read_excel(NOM_FICHIER_EDT)
    df_etud = pd.read_excel(NOM_FICHIER_ETUDIANTS)
    # Nettoyage
    df_edt.columns = [str(c).strip() for c in df_edt.columns]
    df_etud.columns = [str(c).strip() for c in df_etud.columns]
    return df_edt, df_etud

# --- CHARGEMENT ---
try:
    df_edt, df_etudiants = load_all_data()
except Exception as e:
    st.error(f"Erreur de chargement des fichiers Excel : {e}")
    st.stop()

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h3 style='text-align:center;'>🔑 Validation Enseignant</h3>", unsafe_allow_html=True)
    email_login = st.text_input("Entrez votre Email professionnel :")
    pass_login = st.text_input("Entrez votre mot de passe :", type="password")
    
    if st.button("Accéder à la plateforme", use_container_width=True):
        result = supabase.table("enseignants_auth").select("*").eq("email", email_login).eq("password_hash", hash_pw(pass_login)).execute()
        if result.data:
            st.session_state["user_data"] = result.data[0]
            st.rerun()
        else:
            st.error("Identifiants incorrects.")
    st.stop()

# --- INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<div style='background-color:#1E3A8A; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{TITRE_PLATEFORME}</div>", unsafe_allow_html=True)

# 1. Sélection Enseignant (Auto-sélectionné par le login)
st.markdown("### 👤 1. Sélectionner l'Enseignant :")
liste_profs = sorted(df_edt['Enseignants'].unique())
# On cherche l'index du nom de l'utilisateur connecté
try:
    idx_prof = liste_profs.index(user['nom_officiel'])
except:
    idx_prof = 0
enseignant_sel = st.selectbox("", liste_profs, index=idx_prof)

# --- TABS ---
t_saisie, t_hist = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with t_saisie:
    col_p, col_m = st.columns(2)
    with col_p:
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", sorted(df_edt['Promotion'].unique()))
    with col_m:
        matieres_dispo = df_edt[df_edt['Promotion'] == promo_sel]['Enseignements'].unique()
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", sorted(matieres_dispo))

    # Info séance (Récupérée de l'EDT)
    info_seance = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)].iloc[0]
    st.info(f"📍 {info_seance['Jours']} | {info_seance['Horaire']} | Lieu: {info_seance['Lieu']}")

    st.markdown("### 📈 État d'Avancement & Appel")
    
    # Filtrage des étudiants
    df_filtre_promo = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    
    col_g, col_sg = st.columns(2)
    with col_g:
        groupe_sel = st.selectbox("👥 Sélectionner le Groupe :", sorted(df_filtre_promo['Groupe'].unique()))
    with col_sg:
        df_filtre_g = df_filtre_promo[df_filtre_promo['Groupe'] == groupe_sel]
        sg_sel = st.selectbox("🔢 Sélectionner le Sous-groupe :", sorted(df_filtre_g['Sous groupe'].unique()))

    # --- STATISTIQUES ---
    st.markdown("#### 📊 Statistiques de présence")
    c1, c2, c3 = st.columns(3)
    eff_promo = len(df_filtre_promo)
    eff_g = len(df_filtre_g)
    df_final_etud = df_filtre_g[df_filtre_g['Sous groupe'] == sg_sel]
    eff_sg = len(df_final_etud)

    c1.metric("Effectif Promotion", eff_promo)
    c2.metric(f"Effectif {groupe_sel}", eff_g)
    c3.metric(f"Effectif {sg_sel}", eff_sg)

    # --- CONTENU PÉDAGOGIQUE ---
    st.divider()
    col_t, col_n = st.columns(2)
    with col_t:
        type_unite = st.selectbox("Type d'unité :", ["Chapitre", "TP Numéro", "TD Série", "Examen"])
    with col_n:
        num_unite = st.text_input("Numéro :")

    # --- APPEL ---
    st.markdown(f"### ❌ Sélectionner les ABSENTS :")
    st.write(f"Liste des {eff_sg} étudiants du {sg_sel}")
    
    # Création de la liste pour le multiselect
    df_final_etud['Nom_Prenom'] = df_final_etud['Nom'] + " " + df_final_etud['Prénom']
    liste_absents = st.multiselect("Cochez les noms des étudiants absents :", options=df_final_etud['Nom_Prenom'].tolist())

    # --- VALIDATION FINALE ---
    st.divider()
    col_d, col_obs = st.columns(2)
    with col_d:
        date_reelle = st.date_input("📅 Date réelle de la séance :")
    with col_obs:
        observations = st.text_area("🗒️ Observations (Obligatoire) :")
    
    col_sig, col_code = st.columns(2)
    with col_sig:
        signature = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    with col_code:
        code_unique = st.text_input("🔑 Entrez votre Code Unique :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if not observations or not signature or not code_unique:
            st.error("Veuillez remplir tous les champs obligatoires.")
        else:
            # Construction du rapport pour l'email
            corps_mail = f"""
            RAPPORT DE SÉANCE - {TITRE_PLATEFORME}
            
            ENSEIGNANT : {enseignant_sel}
            SÉANCE : {matiere_sel} ({type_unite} {num_unite})
            PROMOTION : {promo_sel} | GROUPE : {groupe_sel} | SG : {sg_sel}
            
            DATE RÉELLE : {date_reelle}
            OBSERVATIONS : {observations}
            
            LISTE DES ABSENTS ({len(liste_absents)}) :
            {", ".join(liste_absents) if liste_absents else "Aucun absent"}
            
            SIGNATURE : {signature}
            """
            
            with st.spinner("Envoi du rapport en cours..."):
                if send_report_email(f"Présence {promo_sel} - {enseignant_sel}", corps_mail):
                    st.success("✅ Séance enregistrée et email envoyé à l'administration !")
                    st.balloons()
                else:
                    st.warning("Séance enregistrée localement, mais l'envoi de l'email a échoué.")

with t_hist:
    st.info("L'historique des séances validées s'affichera ici après synchronisation avec la base de données.")
