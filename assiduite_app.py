import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import segno
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

# Respect strict du titre mémorisé
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Fichiers sources
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 CONFIGURATION EMAILS (Paramètres mémorisés)
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_CHEF_DEPT = "chef.department.elt.fge@gmail.com"
EMAIL_ADJOINT = "milouafarid@gmail.com"
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur de configuration Supabase dans les Secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_qr_segno(data):
    qr = segno.make(data)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10)
    return out.getvalue()

def send_notification_admin(details):
    destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Système EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = f"Rapport de Séance : {details['matiere']} - {details['promotion']}"
        corps = f"""
        Bonjour,
        Un rapport de séance a été validé :
        - Enseignant : {details['enseignant']}
        - Matière : {details['matiere']}
        - Promotion : {details['promotion']}
        - Date : {details['date_seance']}
        - Nombre d'absents : {details['nb_absents']}
        """
        msg.attach(MIMEText(corps, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Erreur Email : {e}")

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        # Nettoyage des données
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'NAN'], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur lors du chargement des fichiers Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()
df_etudiants['Full_N'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()

def color_edt(val):
    if not val or val == "": return ""
    if "Cours" in val: return 'background-color: #d1e7dd; color: black; font-weight: bold;' # Vert
    if "TD" in val: return 'background-color: #fff3cd; color: black; font-weight: bold;'    # Jaune
    if "TP" in val: return 'background-color: #cfe2ff; color: black; font-weight: bold;'    # Bleu
    return ''

def safe_insert(table_name, data_dict):
    try:
        return supabase.table(table_name).insert(data_dict).execute()
    except Exception as e:
        st.error(f"Erreur d'insertion : {e}")

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_student = st.tabs(["🔐 Connexion Enseignant", "📝 Inscription", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :")
        p_log = st.text_input("Code Unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Email ou Code incorrect.")
        
        with st.expander("❓ Code unique oublié ?"):
            st.warning("Pour des raisons de sécurité, veuillez contacter l'administrateur technique ou le chef de département.")
            st.write(f"Contact technique : **{EMAIL_ADMIN_TECH}**")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Recherchez votre nom dans la liste du personnel :", sorted(df_staff['Full_S'].unique()))
        inf_s = df_staff[df_staff['Full_S'] == choix_nom].iloc[0]
        st.info(f"Grade : {inf_s['Grade']} | Qualité : {inf_s['Qualité']}")
        
        reg_e = st.text_input("Confirmez votre Email :", value=inf_s['Email'])
        reg_p = st.text_input("Définissez votre nouveau Code Unique :", type="password")
        reg_p_conf = st.text_input("Confirmez votre Code Unique :", type="password")
        
        if st.button("Créer mon compte"):
            if reg_p == reg_p_conf and len(reg_p) > 3:
                supabase.table("enseignants_auth").insert({
                    "email": reg_e, "password_hash": hash_pw(reg_p),
                    "nom_officiel": inf_s['NOM'], "prenom_officiel": inf_s['PRÉNOM'],
                    "statut_enseignant": inf_s['Qualité'], "grade_enseignant": inf_s['Grade']
                }).execute()
                st.success("Compte créé avec succès ! Vous pouvez vous connecter.")
            else:
                st.error("Les codes ne correspondent pas ou sont trop courts.")

    with t_student:
        st.markdown("### 🎓 Accès Étudiant")
        nom_st = st.selectbox("Rechercher mon Nom & Prénom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.success(f"Bienvenue {nom_st} \n\n **Promotion:** {profil['Promotion']} | **Groupe:** {profil['Groupe']} | **Sous-groupe:** {profil['Sous groupe']}")
            
            # --- FILTRAGE STRICT EDT ÉTUDIANT ---
            mask_cours = df_edt['Enseignements'].str.contains('Cours', case=False, na=False)
            mask_td = (df_edt['Enseignements'].str.contains('TD', case=False, na=False)) & (df_edt['Lieu'].str.contains(profil['Groupe'], case=False, na=False))
            mask_tp = (df_edt['Enseignements'].str.contains('TP', case=False, na=False)) & (df_edt['Lieu'].str.contains(profil['Sous groupe'], case=False, na=False))
            
            edt_individuel = df_edt[(df_edt['Promotion'] == profil['Promotion']) & (mask_cours | mask_td | mask_tp)].copy()
            
            st.markdown("#### 📅 Mon Emploi du Temps Hebdomadaire")
            if not edt_individuel.empty:
                # Tableau Croisé : Jours Horizontal / Heures Vertical
                jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                grid = edt_individuel.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                
                # Tri chronologique et ordonnancement des jours
                cols_presentes = [j for j in jours_ordre if j in grid.columns]
                grid = grid[cols_presentes].sort_index()
                
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True)
            
            # --- RÉCAPITULATIF DES ABSENCES ---
            st.markdown("#### ❌ Mon Bilan d'Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).eq("note_evaluation", "ABSENCE").execute()
            if res_abs.data:
                df_abs_st = pd.DataFrame(res_abs.data)
                recap_abs = df_abs_st.groupby(['matiere', 'enseignant']).size().reset_index(name='Nombre d\'absences')
                st.table(recap_abs)
            else:
                st.info("Aucune absence enregistrée. Félicitations !")
            
            st.write("📲 **Mon QR Code d'identification :**")
            st.image(generate_qr_segno(f"ST_ID:{nom_st}"), width=120)
    st.stop()

# --- 5. INTERFACE ENSEIGNANT CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# Rappel obligatoire du titre à chaque affichage
st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']} {user['prenom_officiel']}")
    st.write(f"Grade: {user.get('grade_enseignant', 'Enseignant')}")
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        enseignant_actif = st.selectbox("Simuler la vue de l'enseignant :", sorted(df_edt['Enseignants'].unique()))
    else:
        enseignant_actif = user['nom_officiel']
    
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie de Séance", "🔍 Suivi Étudiant", "📜 Archives Globales"])

# --- ONGLET 1 : SAISIE DE SÉANCE ---
with tab_saisie:
    c1, c2, c3 = st.columns(3)
    type_s = c1.selectbox("Type de séance :", ["Cours", "TD", "TP", "Examen"])
    regime_s = c2.selectbox("Régime :", ["Charge Horaire (H.C)", "Heures Supplémentaires (H.S)"])
    date_s = c3.date_input("Date de la séance :", value=datetime.now())

    # Filtrage de l'ED
