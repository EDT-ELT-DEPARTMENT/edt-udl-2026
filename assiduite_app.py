import streamlit as st
import pandas as pd
import hashlib
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Gestion EDT - UDL SBA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CONSTANTES ET TITRE ---
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# Configuration SMTP (Pour les rapports et récupération de code)
EMAIL_SENDER = "votre_email@gmail.com"  
EMAIL_PASSWORD = "votre_code_application_google" # Code à 16 lettres
EMAIL_ADMIN = "milouafarid@gmail.com"

# --- 3. CONNEXION SUPABASE ---
# Assurez-vous que ces clés sont dans vos Secrets Streamlit
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- 4. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    """Crypte le mot de passe pour la comparaison"""
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_email(destinataire, sujet, corps):
    """Envoie un email via le serveur Gmail"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = destinataire
        msg['Subject'] = sujet
        msg.attach(MIMEText(corps, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False

@st.cache_data
def load_and_clean_all_data():
    """Charge les fichiers Excel et nettoie les données"""
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    
    # Nettoyage des noms de colonnes
    df_e.columns = [str(c).strip() for c in df_e.columns]
    df_s.columns = [str(c).strip() for c in df_s.columns]
    
    # Nettoyage des contenus pour éviter les erreurs de correspondance
    for col in ['Enseignants', 'Enseignements', 'Promotion']:
        if col in df_e.columns:
            df_e[col] = df_e[col].astype(str).str.strip()
            
    return df_e, df_s

# --- 5. CHARGEMENT DES DONNÉES ---
try:
    df_edt, df_etudiants = load_and_clean_all_data()
except Exception as e:
    st.error(f"Erreur lors du chargement des fichiers Excel : {e}")
    st.stop()

# --- 6. SYSTÈME D'AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"### 🔑 Validation Enseignant")
    tab_login, tab_recovery = st.tabs(["Connexion", "Code Unique oublié ?"])
    
    with tab_login:
        email_in = st.text_input("Entrez votre Email professionnel :")
        pass_in = st.text_input("Entrez votre mot de passe / Code Unique :", type="password")
        
        if st.button("Accéder à la plateforme", use_container_width=True):
            # Vérification dans Supabase
            res = supabase.table("enseignants_auth").select("*").eq("email", email_in).eq("password_hash", hash_pw(pass_in)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Email ou Code Unique incorrect.")

    with tab_recovery:
        st.write("Si vous avez oublié votre code, entrez votre email pour notifier l'administration.")
        email_recup = st.text_input("Votre Email professionnel :", key="recup_email")
        if st.button("Envoyer une demande de réinitialisation"):
            if email_recup:
                succes = send_email(EMAIL_ADMIN, "DEMANDE DE RÉINITIALISATION DE CODE", f"L'enseignant {email_recup} a oublié son code d'accès.")
                if succes:
                    st.success("Demande envoyée à M. Miloua.")
                else:
                    st.error("Erreur d'envoi. Veuillez contacter l'admin directement.")
    st.stop()

# --- 7. INTERFACE PRINCIPALE (Connecté) ---
user = st.session_state["user_data"]
st.markdown(f"<div style='background-color:#003366; color:white; padding:15px; border-radius:10px; text-align:center; font-weight:bold; font-size:1.2em;'>{TITRE_PLATEFORME}</div>", unsafe_allow_html=True)

# Sélection Enseignant
st.markdown("### 👤 1. Sélectionner l'Enseignant :")
liste_enseignants = sorted(df_edt['Enseignants'].unique())
# On tente de présélectionner l'utilisateur connecté
try:
    idx_default = liste_enseignants.index(user['nom_officiel'])
except:
    idx_default = 0
enseignant_sel = st.selectbox("", liste_enseignants, index=idx_default)

# --- ONGLETS ---
tab_saisie, tab_historique = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    col_prom, col_mat = st.columns(2)
    
    with col_prom:
        promos_dispo = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", promos_dispo)
        
    with col_mat:
        mats_dispo = sorted(df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", mats_dispo)

    # --- AFFICHAGE INFOS SÉANCE (Anti-crash) ---
    res_seance = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    
    if not res_seance.empty:
        info = res_seance.iloc[0]
        st.info(f"📍 {info['Jours']} | {info['Horaire']} | Lieu: {info['Lieu']}")
    else:
        st.warning("⚠️ Séance non trouvée dans l'emploi du temps pour cette sélection.")

    st.markdown("### 📈 État d'Avancement & Appel")
    
    # Filtrage des étudiants
    df_etud_promo = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    
    cg, csg = st.columns(2)
    with cg:
        groupes_list = sorted(df_etud_promo['Groupe'].unique()) if not df_etud_promo.empty else ["N/A"]
        groupe_sel = st.selectbox("👥 Sélectionner le Groupe :", groupes_list)
        
    with csg:
        df_etud_g = df_etud_promo[df_etud_promo['Groupe'] == groupe_sel]
        sgroupes_list = sorted(df_etud_g['Sous groupe'].unique()) if not df_etud_g.empty else ["N/A"]
        sg_sel = st.selectbox("🔢 Sélectionner le Sous-groupe :", sgroupes_list)

    # --- STATISTIQUES ---
    st.markdown("#### 📊 Statistiques de présence")
    st1, st2, st3 = st.columns(3)
    df_etud_final = df_etud_g[df_etud_g['Sous groupe'] == sg_sel]
    
    st1.metric("Effectif Promotion", len(df_etud_promo))
    st2.metric(f"Effectif {groupe_sel}", len(df_etud_g))
    st3.metric(f"Effectif {sg_sel}", len(df_etud_final))

    # --- DÉTAILS UNITÉ ---
    st.divider()
    cu1, cu2 = st.columns(2)
    with cu1:
        type_unite = st.selectbox("Type d'unité :", ["Chapitre", "TP Numéro", "TD Série", "Examen", "Autre"])
    with cu2:
        num_unite = st.text_input("Numéro :")

    # --- APPEL DES ÉTUDIANTS ---
    st.markdown(f"### ❌ Sélectionner les ABSENTS :")
    st.write(f"Liste des {len(df_etud_final)} étudiants du {sg_sel}")
    
    if not df_etud_final.empty:
        df_etud_final['NomComplet'] = df_etud_final['Nom'].astype(str) + " " + df_etud_final['Prénom'].astype(str)
        liste_absents = st.multiselect("Cochez les étudiants absents :", options=df_etud_final['NomComplet'].tolist())
    else:
        st.write("Aucun étudiant trouvé.")
        liste_absents = []

    # --- VALIDATION ---
    st.divider()
    cdat, cobs = st.columns(2)
    with cdat:
        date_reelle = st.date_input("📅 Date réelle de la séance :")
    with cobs:
        observations = st.text_area("🗒️ Observations (Obligatoire) :")
        
    csig, ccode = st.columns(2)
    with csig:
        nom_signature = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    with ccode:
        code_verif = st.text_input("🔑 Entrez votre Code Unique :", type="password")

    # --- BOUTON FINAL ---
    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if not observations or not nom_signature or not code_verif:
            st.error("Veuillez remplir tous les champs obligatoires.")
        elif hash_pw(code_verif) != user['password_hash']:
            st.error("Code Unique incorrect. Signature refusée.")
        else:
            # Construction du rapport
            corps_rapport = f"""
            RAPPORT DE SÉANCE - {TITRE_PLATEFORME}
            --------------------------------------------------
            ENSEIGNANT : {enseignant_sel}
            SÉANCE : {matiere_sel} ({type_unite} n°{num_unite})
            PROMOTION : {promo_sel} | GROUPE : {groupe_sel} | SG : {sg_sel}
            DATE : {date_reelle}
            --------------------------------------------------
            ABSENTS ({len(liste_absents)}) :
            {', '.join(liste_absents) if liste_absents else 'Aucun absent'}
            --------------------------------------------------
            OBSERVATIONS : {observations}
            SIGNATURE : {nom_signature}
            """
            
            with st.spinner("Envoi du rapport en cours..."):
                succes_mail = send_email(EMAIL_ADMIN, f"Présence {promo_sel} - {enseignant_sel}", corps_rapport)
                if succes_mail:
                    st.success("✅ Séance validée et rapport envoyé à l'administration !")
                    st.balloons()
                else:
                    st.warning("⚠️ Séance enregistrée, mais l'envoi de l'email a échoué.")

with tab_historique:
    st.info("L'historique des séances sera chargé depuis la base de données prochainement.")
