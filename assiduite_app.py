import streamlit as st
import pandas as pd
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# 📧 ADRESSES FIXES (ADMINISTRATION)
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"        # À modifier
EMAIL_CHEF_ADJOINT = "nass_ka@yahoo.fr "  # À modifier
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP
EMAIL_SENDER = "milouafarid@gmail.com"  
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- 3. FONCTIONS ---
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
    # Nettoyage standard
    for df in [df_e, df_s]:
        df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignants', 'Enseignements', 'Promotion', 'Email_Enseignant', 'Email_Responsable_Parcours']:
        if col in df_e.columns:
            df_e[col] = df_e[col].astype(str).str.strip()
    return df_e, df_s

# --- 4. CHARGEMENT ET AUTH ---
df_edt, df_etudiants = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("### 🔑 Validation Enseignant")
    # ... (Bloc de login identique au précédent)
    st.stop()

# --- 5. INTERFACE ---
user = st.session_state["user_data"]
st.markdown(f"**{TITRE_OFFICIEL}**")

# Sélection Enseignant
profs = sorted(df_edt['Enseignants'].unique())
enseignant_sel = st.selectbox("👤 1. Sélectionner l'Enseignant :", profs, index=profs.index(user['nom_officiel']) if user['nom_officiel'] in profs else 0)

tab_saisie, _ = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    # ... (Blocs Promotion, Matière, Infos Séance, Groupes identiques)
    
    # Récupération des emails spécifiques depuis l'EDT
    ligne_info = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel) & (df_edt['Enseignements'] == matiere_sel)]
    
    # On initialise les emails (si colonnes présentes dans l'Excel)
    email_prof_concerné = ligne_info['Email_Enseignant'].values[0] if 'Email_Enseignant' in ligne_info.columns else user['email']
    email_resp_parcours = ligne_info['Email_Responsable_Parcours'].values[0] if 'Email_Responsable_Parcours' in ligne_info.columns else EMAIL_ADMIN_TECH

    # ... (Bloc Statistiques et Liste d'appel)

    # --- VALIDATION ET ENVOI MULTIPLE ---
    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if not obs or not sign or hash_pw(code_v) != user['password_hash']:
            st.error("Données invalides ou Code Unique incorrect.")
        else:
            # Liste des destinataires
            destinataires = [
                EMAIL_CHEF_DEPT, 
                EMAIL_CHEF_ADJOINT, 
                email_prof_concerné, 
                email_resp_parcours,
                EMAIL_ADMIN_TECH
            ]
            # Nettoyage de la liste (enlever les doublons ou adresses vides)
            destinataires = list(set([d for d in destinataires if "@" in str(d)]))

            rapport = f"""
            RAPPORT DE SÉANCE - {TITRE_OFFICIEL}
            ------------------------------------------
            DE : {enseignant_sel}
            POUR : {matiere_sel} ({promo_sel})
            GROUPE : {groupe_sel} | SG : {sg_sel}
            DATE : {date_s}
            ------------------------------------------
            ABSENTS : {", ".join(absents) if absents else "Aucun"}
            ------------------------------------------
            OBSERVATIONS : {obs}
            SIGNATURE : {sign}
            """
            
            with st.spinner("Envoi aux responsables en cours..."):
                success, error_msg = send_report_multi(destinataires, f"Rapport Assiduité - {promo_sel} - {enseignant_sel}", rapport)
                
                if success:
                    st.success(f"✅ Rapport envoyé avec succès à : {', '.join(destinataires)}")
                    st.balloons()
                else:
                    st.error(f"❌ Erreur d'envoi : {error_msg}")
