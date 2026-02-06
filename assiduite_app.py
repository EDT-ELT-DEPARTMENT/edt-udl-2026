import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import re
import random
import string
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
    st.error("⚠️ Configuration Supabase manquante dans les secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_email_rapport(destinataires, sujet, corps):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = sujet
        msg.attach(MIMEText(corps, 'plain'))
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
        
        # Nettoyage global et mise en MAJUSCULES pour éviter les erreurs de frappe
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().str.upper().replace(['NAN', 'NONE', ''], '')
        
        # --- GESTION DU STAFF (MILOUA FARID & FETHI) ---
        if 'NOM' in df_staff.columns and 'PRÉNOM' in df_staff.columns:
            # On crée le nom complet pour le staff (pour le login/sidebar)
            df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        
        # Note : On ne touche plus à df_e['Enseignants'] car il contient déjà 
        # les prénoms (MILOUA FARID, etc.) dans votre Excel.
        
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}"); st.stop()

# --- CHARGEMENT ---
df_edt, df_etudiants, df_staff = load_data()

# --- CRÉATION DU FULL_N ÉTUDIANTS ---
# Attention : vérifiez si votre Excel étudiant utilise 'NOM' ou 'Nom'
if 'NOM' in df_etudiants.columns and 'PRÉNOM' in df_etudiants.columns:
    df_etudiants['Full_N'] = (df_etudiants['NOM'] + " " + df_etudiants['PRÉNOM']).str.upper().str.strip()
elif 'Nom' in df_etudiants.columns and 'Prénom' in df_etudiants.columns:
    df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()

# --- FONCTION DE COLORATION ---
def color_edt(val):
    if not val or val == "": return ""
    v = str(val).upper()
    if "COURS" in v: return 'background-color: #d1e7dd; color: #084298; font-weight: bold; border: 1px solid #084298;'
    if "TD" in v: return 'background-color: #fff3cd; color: #856404; font-weight: bold; border: 1px solid #856404;'
    if "TP" in v: return 'background-color: #cfe2ff; color: #004085; font-weight: bold; border: 1px solid #004085;'
    return ''

# --- 4. AUTHENTIFICATION & ESPACE ÉTUDIANT ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        # Code de connexion ici...
        pass

    with t_signup:
        # Code d'inscription ici...
        pass

    with t_forgot:
        # Code code oublié ici...
        pass

    with t_student:
        nom_st = st.selectbox("Sélectionner votre nom (Étudiant) :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        
        if nom_st != "--":
            # --- CRUCIAL : Définition du profil pour éviter le NameError ---
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            
            st.info(f"🎓 **Étudiant :** {nom_st} | **Promo :** {profil['Promotion']} | **Groupe :** {profil['Groupe']}")

            # --- EMPLOI DU TEMPS INDIVIDUEL ---
            st.markdown("#### 📅 Mon Emploi du Temps Hebdomadaire")
            
            def filter_st_edt(row):
                if str(row['Promotion']).upper() != str(profil['Promotion']).upper(): 
                    return False
                
                ens, code = str(row['Enseignements']).upper(), str(row['Code']).upper()
                if "COURS" in ens: return True
                
                num_g = re.findall(r'\d+', str(profil['Groupe']))[0] if re.findall(r'\d+', str(profil['Groupe'])) else ""
                if "TD" in ens:
                    if str(profil['Groupe']).upper() in code or (num_g == "1" and "-A" in code) or (num_g == "2" and "-B" in code): 
                        return True
                
                num_sg = re.findall(r'\d+', str(profil['Sous groupe']))[0] if re.findall(r'\d+', str(profil['Sous groupe'])) else ""
                if "TP" in ens:
                    suff = "A" if num_sg == "1" else "B" if num_sg == "2" else "C" if num_sg == "3" else ""
                    if suff and f"-{suff}" in code: 
                        return True
                return False

            edt_st = df_edt[df_edt.apply(filter_st_edt, axis=1)].copy()
            
            if not edt_st.empty:
                # Affichage simple selon votre disposition demandée
                st.dataframe(edt_st[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']], use_container_width=True)
            else:
                st.warning("Aucun emploi du temps trouvé.")

            # --- SYNTHÈSE DES ABSENCES ---
            st.markdown("#### ❌ Suivi des Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            if res_abs.data:
                df_abs = pd.DataFrame(res_abs.data)
                st.table(df_abs[['matiere', 'date_seance', 'note_evaluation']])
            else:
                st.success("Aucune absence signalée.")

    st.stop() # Bloque l'exécution ici pour ne pas charger le reste de l'app

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user.get('email') == EMAIL_ADMIN_TECH)

# 1. Extraction et formatage de l'identité (Récupération directe de Supabase)
nom_session = str(user.get('nom_officiel', '')).strip().upper()
prenom_session = str(user.get('prenom_officiel', '')).strip().upper()

# Correction pour éviter le "NONE" si le prénom est mal lu
if prenom_session == "NONE" or not prenom_session:
    nom_complet_session = nom_session
else:
    nom_complet_session = f"{nom_session} {prenom_session}"

# 2. Récupération Grade et Statut (Directement depuis les colonnes Supabase)
# On utilise .get() pour lire les colonnes que vous avez ajoutées
grade_fix = str(user.get('grade_enseignant', '')).strip()
statut_fix = str(user.get('statut_enseignant', 'Permanent')).strip()

# Sécurité : si Supabase est vide, on tente un dernier secours sur le fichier staff
if not grade_fix or grade_fix == "NONE":
    match_staff = df_staff[
        (df_staff['NOM'].str.upper() == nom_session) & 
        (df_staff['PRÉNOM'].str.upper() == prenom_session)
    ]
    if not match_staff.empty:
        grade_fix = str(match_staff.iloc[0]['Grade']).strip()
        statut_fix = str(match_staff.iloc[0]['Qualité']).strip()

# --- SIDEBAR ---
st.sidebar.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom:2px solid #003366;'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h4>", unsafe_allow_html=True)

with st.sidebar:
    # Affichage de l'identité complète (Ex: MILOUA FARID)
    st.markdown(f"### 👤 {nom_complet_session}")
    
    if grade_fix: 
        st.success(f"**Grade :** {grade_fix}")
    
    st.warning(f"**Statut :** {statut_fix}")
    st.divider()
    
    # Logique de sélection de l'enseignant actif
    if is_admin:
        # L'admin peut choisir dans la liste complète issue de l'EDT
        liste_profs = sorted([str(x) for x in df_edt['Enseignants'].unique() if x])
        ens_actif = st.selectbox(
            "Simulation (Admin) :", 
            liste_profs, 
            key="unique_admin_sim_key"
        )
    else:
        # L'enseignant est verrouillé sur son nom complet de session
        # On s'assure que ens_actif correspond exactement au format de l'EDT
        ens_actif = nom_complet_session

    # Bouton de déconnexion
    if st.button("🚪 Déconnexion", use_container_width=True, key="unique_logout_key"):
        st.session_state["user_data"] = None
        st.rerun()

# --- APPLICATION DU FILTRE SUR L'EDT ---
# Ce masque est crucial pour séparer les homonymes comme les MILOUA
mask_edt = df_edt['Enseignants'].astype(str).str.upper().str.strip() == ens_actif.upper().strip()
df_perso = df_edt[mask_edt]

# --- INTERFACE PRINCIPALE ---
t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True)
    
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    date_s = c3.date_input("Date réelle :", value=datetime.now())
    
    # Filtrage précis de l'EDT
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    list_promos = sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique())
    p_sel = st.selectbox("🎓 Promotion :", list_promos)
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"Sous-groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    st.markdown("---")

    # Matière
    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])
    
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")
    
    if abs_collective:
        absents_final = eff_liste['Full_N'].tolist()
        type_abs = "Absence Collective"
    else:
        absents_final = st.multiselect("Sélectionner les étudiants absents :", options=eff_liste['Full_N'].tolist())
        type_abs = st.selectbox("Nature :", ["Absence non justifiée", "Absence justifiée", "Exclusion"])

    st.divider()
    st.markdown("### 📝 Notation / Participation")
    cn1, cn2, cn3 = st.columns(3)
    etudiant_note = cn1.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist())
    critere = cn2.selectbox("Critère :", ["Test", "Examen de TD", "Participation", "Interrogation"])
    valeur = cn3.text_input("Note/Observation :")
    obs_input = st.text_area("🗒️ Observations générales :")

    st.markdown("### ✉️ Diffusion du Rapport")
    staff_options = {row['Full_S']: row['Email'] for _, row in df_staff.iterrows() if 'Full_S' in df_staff.columns}
    resp_nom = st.selectbox("Responsable de l'équipe de spécialité :", ["Aucun"] + sorted(list(staff_options.keys())))
    code_v = st.text_input("🔑 Code Unique pour validation :", type="password")
    
    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            # Archivage avec Nom Complet
            for name in absents_final:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {nom_complet_session}",
                    "date_seance": str(date_s), "etudiant_nom": name, "note_evaluation": type_abs,
                    "observations": obs_input, "categorie_seance": charge, "type_seance": type_seance
                }).execute()
            
            destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
            if resp_nom != "Aucun": destinataires.append(staff_options[resp_nom])
            
            corps_mail = f"""
            RAPPORT DE SÉANCE - {TITRE_PLATEFORME}
            --------------------------------------------------
            Enseignant : {grade_fix} {nom_complet_session}
            Date : {date_s}
            Matière : {m_sel} ({type_seance})
            Régime : {charge}
            Absents : {len(absents_final)} ({type_abs})
            Note/Observation : {valeur if etudiant_note != "Aucun" else "N/A"}
            Commentaire : {obs_input}
            """
            send_email_rapport(destinataires, f"Rapport Séance - {m_sel} - {p_sel}", corps_mail)
            st.success("✅ Rapport archivé et diffusé !"); st.balloons()
        else:
            st.error("Code unique de validation incorrect.")

with t_suivi:
    st.markdown("### 🔍 Fiche de Suivi Individuelle")
    p_suivi = st.selectbox("1️⃣ Promotion :", sorted(df_etudiants['Promotion'].unique()), key="s_p")
    nom_suivi = st.selectbox("2️⃣ Étudiant :", ["--"] + sorted(df_etudiants[df_etudiants['Promotion'] == p_suivi]['Full_N'].unique()), key="s_n")
    if nom_suivi != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_suivi).execute()
        if res.data: st.table(pd.DataFrame(res.data)[['date_seance', 'matiere', 'note_evaluation', 'enseignant']])

with t_admin:
    if is_admin:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)
    else: st.error("Accès restreint.")


















