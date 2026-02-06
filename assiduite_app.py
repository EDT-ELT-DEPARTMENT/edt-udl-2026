import streamlit as st
import pandas as pd
import hashlib
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des enseignements et assiduité des étudiants du département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Fichiers sources
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 CONFIGURATION EMAILS
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Configuration Supabase manquante dans les secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', ''], '')
        
        if 'NOM' in df_staff.columns and 'PRÉNOM' in df_staff.columns:
            df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}"); st.stop()

# --- CHARGEMENT ---
df_edt, df_etudiants, df_staff = load_data()

# --- SÉCURITÉ : CRÉATION DU FULL_N ÉTUDIANTS (CORRIGÉ) ---
# On normalise les noms de colonnes pour éviter les erreurs de casse (Maj/Min)
df_etudiants.columns = [c.upper() for c in df_etudiants.columns]

if 'NOM' in df_etudiants.columns and 'PRÉNOM' in df_etudiants.columns:
    df_etudiants['FULL_N'] = (df_etudiants['NOM'].astype(str) + " " + df_etudiants['PRÉNOM'].astype(str)).str.upper().str.strip()
elif 'NOM' in df_etudiants.columns and 'PRENOM' in df_etudiants.columns: # Cas sans accent
    df_etudiants['FULL_N'] = (df_etudiants['NOM'].astype(str) + " " + df_etudiants['PRENOM'].astype(str)).str.upper().str.strip()
else:
    # Si les colonnes sont introuvables, on crée une colonne de secours
    st.error("⚠️ Colonnes 'NOM'/'PRÉNOM' non trouvées dans le fichier Étudiants.")
    df_etudiants['FULL_N'] = "NOM INCONNU"

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        st.subheader("Accès Enseignant")
        email_log = st.text_input("Email professionnel :", key="log_email").strip().lower()
        pass_log = st.text_input("Code unique :", type="password", key="log_pass")
        if st.button("Se connecter", use_container_width=True):
            email_clean = email_log.replace(',', '.')
            try:
                res = supabase.table("enseignants_auth").select("*").eq("email", email_clean).execute()
                if res.data and res.data[0]['password_hash'] == hash_pw(pass_log):
                    st.session_state["user_data"] = res.data[0]
                    st.rerun()
                else:
                    st.error("Email ou code incorrect.")
            except Exception as e:
                st.error(f"Erreur de connexion : {e}")

    with t_signup:
        st.subheader("Créer un compte")
        # Vérification si le staff est chargé
        if not df_staff.empty:
            staff_nom = sorted(df_staff['NOM'].unique())
            nom_reg = st.selectbox("Votre NOM :", staff_nom)
            prenom_reg = st.selectbox("Votre PRÉNOM :", sorted(df_staff[df_staff['NOM'] == nom_reg]['PRÉNOM'].unique()))
            email_reg = st.text_input("Email (Identifiant) :").strip().lower()
            pass_reg = st.text_input("Créer votre code secret :", type="password")
            
            if st.button("Valider l'inscription", use_container_width=True):
                email_clean = email_reg.replace(',', '.')
                match = df_staff[(df_staff['NOM'] == nom_reg) & (df_staff['PRÉNOM'] == prenom_reg)]
                if not match.empty:
                    grade_reg = str(match.iloc[0].get('Grade', 'N/A'))
                    statut_reg = str(match.iloc[0].get('Qualité', 'Permanent'))
                    try:
                        supabase.table("enseignants_auth").insert({
                            "email": email_clean, "password_hash": hash_pw(pass_reg),
                            "nom_officiel": nom_reg, "prenom_officiel": prenom_reg,
                            "grade_enseignant": grade_reg, "statut_enseignant": statut_reg
                        }).execute()
                        st.success("✅ Compte créé ! Vous pouvez vous connecter.")
                    except:
                        st.error("❌ Cet email est déjà utilisé.")
        else:
            st.error("Fichier Staff non chargé.")

    with t_forgot:
        st.warning("Contact : milouafarid@gmail.com")

    with t_student:
        # Utilisation de la colonne FULL_N créée plus haut
        liste_noms = ["--"] + sorted(df_etudiants['FULL_N'].unique().tolist())
        nom_st = st.selectbox("Sélectionner votre nom (Étudiant) :", liste_noms)
        
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['FULL_N'] == nom_st].iloc[0]
            st.info(f"🎓 Étudiant : {nom_st} | Promo : {profil.get('PROMOTION', 'N/A')} | Groupe : {profil.get('GROUPE', 'N/A')}")
            
            # Fonction de filtrage EDT
            def filter_st_edt(row):
                if str(row.get('Promotion', '')).upper() != str(profil.get('PROMOTION', '')).upper(): 
                    return False
                return True 
            
            edt_st = df_edt[df_edt.apply(filter_st_edt, axis=1)].copy()
            # Disposition demandée : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
            cols_dispo = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
            st.dataframe(edt_st[[c for c in cols_dispo if c in edt_st.columns]], use_container_width=True)

    st.stop()

    with t_signup:
        st.subheader("Créer un compte")
        nom_reg = st.selectbox("Votre NOM :", sorted(df_staff['NOM'].unique()))
        prenom_reg = st.selectbox("Votre PRÉNOM :", sorted(df_staff[df_staff['NOM'] == nom_reg]['PRÉNOM'].unique()))
        email_reg = st.text_input("Email (Sert d'identifiant) :").strip().lower()
        pass_reg = st.text_input("Créer votre code secret :", type="password")
        
        if st.button("Valider l'inscription", use_container_width=True):
            email_clean = email_reg.replace(',', '.')
            match = df_staff[(df_staff['NOM'] == nom_reg) & (df_staff['PRÉNOM'] == prenom_reg)]
            if not match.empty:
                grade_reg = str(match.iloc[0].get('Grade', 'N/A'))
                statut_reg = str(match.iloc[0].get('Qualité', 'Permanent'))
                try:
                    supabase.table("enseignants_auth").insert({
                        "email": email_clean, "password_hash": hash_pw(pass_reg),
                        "nom_officiel": nom_reg, "prenom_officiel": prenom_reg,
                        "grade_enseignant": grade_reg, "statut_enseignant": statut_reg
                    }).execute()
                    st.success("✅ Compte créé avec succès ! Connectez-vous maintenant.")
                except:
                    st.error("❌ Erreur : Cet email est peut-être déjà utilisé.")

    with t_forgot:
        st.warning("En cas d'oubli, contactez l'administrateur à : milouafarid@gmail.com")

    with t_student:
        nom_st = st.selectbox("Sélectionner votre nom (Étudiant) :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.info(f"🎓 Étudiant : {nom_st} | Promo : {profil['Promotion']} | Groupe : {profil['Groupe']}")
            
            # Filtrage de l'EDT selon vos règles
            def filter_st_edt(row):
                if str(row['Promotion']).upper() != str(profil['Promotion']).upper(): return False
                ens = str(row['Enseignements']).upper()
                if "COURS" in ens: return True
                return False # Simplifié pour test
            
            edt_st = df_edt[df_edt.apply(filter_st_edt, axis=1)].copy()
            st.dataframe(edt_st[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']], use_container_width=True)

    st.stop()

# --- 5. ESPACE ENSEIGNANT (Une fois connecté) ---
user = st.session_state["user_data"]
st.sidebar.title(f"👤 {user['nom_officiel']} {user['prenom_officiel']}")
if st.sidebar.button("🚪 Déconnexion"):
    st.session_state["user_data"] = None
    st.rerun()

st.success(f"Bienvenue sur votre espace de gestion, {user['grade_enseignant']}.")


