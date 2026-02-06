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
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'none', 'NAN'], '')
        
        if 'NOM' in df_staff.columns and 'PRÉNOM' in df_staff.columns:
            df_staff['Full_S'] = (df_staff['NOM'] + " " + df_staff['PRÉNOM']).str.upper()
        
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()
df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()

def color_edt(val):
    if not val or val == "": return ""
    if "Cours" in val: return 'background-color: #d1e7dd; color: #084298; font-weight: bold; border: 1px solid #084298;'
    if "Td" in val or "TD" in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold; border: 1px solid #856404;'
    if "TP" in val: return 'background-color: #cfe2ff; color: #004085; font-weight: bold; border: 1px solid #004085;'
    return ''

# --- 4. AUTHENTIFICATION & ESPACE ÉTUDIANT ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :", key="log_e")
        p_log = st.text_input("Code Unique :", type="password", key="log_p")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Email ou code incorrect.")

    with t_signup:
        choix_signup = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()))
        inf = df_staff[df_staff['Full_S'] == choix_signup].iloc[0]
        
        st.info(f"Grade détecté : {inf['Grade']} | Statut : {inf['Qualité']}")
        
        reg_e = st.text_input("Email Professionnel :", value=inf['Email'])
        reg_p = st.text_input("Créer votre Code Unique :", type="password", help="Ce code servira à vous connecter et à valider vos rapports.")
        
        if st.button("Valider l'inscription", use_container_width=True):
            try:
                # Préparation des données pour une correspondance stricte
                data_to_insert = {
                    "email": reg_e.strip(),
                    "password_hash": hash_pw(reg_p),
                    "nom_officiel": str(inf['NOM']).strip().upper(),
                    "prenom_officiel": str(inf['PRÉNOM']).strip().upper(),
                    "statut_enseignant": str(inf['Qualité']).strip(),
                    "grade_enseignant": str(inf['Grade']).strip()
                }
                
                # Insertion dans Supabase
                supabase.table("enseignants_auth").insert(data_to_insert).execute()
                
                st.success(f"✅ Compte créé avec succès pour {inf['NOM']} {inf['PRÉNOM']} !")
                st.balloons()
                st.info("Vous pouvez maintenant passer à l'onglet 'Connexion'.")
            except Exception as e:
                st.error(f"Erreur lors de l'inscription : {e}")

    with t_student:
        nom_st = st.selectbox("Sélectionner votre nom (Étudiant) :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            
            # --- HEADER ÉTUDIANT ---
            st.markdown(f"### 👤 Dossier Étudiant : {nom_st}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Promotion", profil['Promotion'])
            c2.metric("Groupe", profil['Groupe'])
            c3.metric("Sous-groupe", profil['Sous groupe'])
            
            # --- EMPLOI DU TEMPS INDIVIDUEL ---
            st.markdown("#### 📅 Mon Emploi du Temps Hebdomadaire")
            
            def filter_st_edt(row):
                if str(row['Promotion']).upper() != str(profil['Promotion']).upper(): return False
                ens, code = str(row['Enseignements']).upper(), str(row['Code']).upper()
                if "COURS" in ens: return True
                num_g = re.findall(r'\d+', str(profil['Groupe']))[0] if re.findall(r'\d+', str(profil['Groupe'])) else ""
                if "TD" in ens:
                    if str(profil['Groupe']).upper() in code or (num_g == "1" and "-A" in code) or (num_g == "2" and "-B" in code): return True
                num_sg = re.findall(r'\d+', str(profil['Sous groupe']))[0] if re.findall(r'\d+', str(profil['Sous groupe'])) else ""
                if "TP" in ens:
                    suff = "A" if num_sg == "1" else "B" if num_sg == "2" else "C" if num_sg == "3" else ""
                    if suff and f"-{suff}" in code: return True
                return False

            edt_st = df_edt[df_edt.apply(filter_st_edt, axis=1)].copy()
            if not edt_st.empty:
                # Pivot pour calendrier
                grid = edt_st.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                grid = grid.reindex(columns=[j for j in jours_ordre if j in grid.columns])
                
                # Affichage stylisé
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True, height=400)
            else:
                st.warning("Aucun emploi du temps trouvé pour vos critères.")

            # --- SYNTHÈSE DES ABSENCES ---
            st.markdown("#### ❌ Suivi des Absences par Matière")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            
            if res_abs.data:
                df_abs_raw = pd.DataFrame(res_abs.data)
                # Filtrer uniquement les types absences
                df_abs_filtré = df_abs_raw[df_abs_raw['note_evaluation'].str.contains("Absence|Exclusion", case=False, na=False)]
                
                if not df_abs_filtré.empty:
                    # Regroupement pour compter par matière
                    synthèse = df_abs_filtré.groupby(['matiere', 'enseignant']).agg({
                        'date_seance': lambda x: ', '.join(sorted(list(set(x)))),
                        'note_evaluation': 'count'
                    }).reset_index()
                    
                    synthèse.columns = ['Matière', 'Chargé de Cours / TD / TP', 'Dates des Absences', 'Total Absences']
                    st.table(synthèse)
                else:
                    st.success("Félicitations ! Aucune absence enregistrée.")
            else:
                st.info("Aucune donnée d'absence enregistrée dans la base.")
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user.get('email') == EMAIL_ADMIN_TECH)

# 1. Extraction des identifiants session
nom_session = str(user.get('nom_officiel', '')).strip().upper()
prenom_session = str(user.get('prenom_officiel', '')).strip().upper()

# 2. PARCOURS DE LA LISTE POUR LE GRADE (Logique demandée)
# On cherche l'enseignant dans votre liste df_staff
match_staff = df_staff[
    (df_staff['NOM'].str.upper() == nom_session) & 
    (df_staff['PRÉNOM'].str.upper() == prenom_session)
]

if not match_staff.empty:
    grade_val = match_staff.iloc[0]['Grade']
    qualite_val = match_staff.iloc[0]['Qualité']
    
    # Si grade trouvé, on le garde, sinon rien
    grade_fix = str(grade_val).strip() if pd.notna(grade_val) and str(grade_val).strip() != "" else ""
    statut_fix = str(qualite_val).strip() if pd.notna(qualite_val) else "Permanent"
else:
    grade_fix = ""
    statut_fix = "Permanent"

# --- AFFICHAGE SIDEBAR (Un seul bloc pour éviter les doublons) ---
st.sidebar.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom:2px solid #003366;'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {nom_session} {prenom_session}")
    
    # Affichage du Grade uniquement s'il n'est pas vide
    if grade_fix:
        st.success(f"**Grade :** {grade_fix}")
    
    st.warning(f"**Statut :** {statut_fix}")
    st.divider()
    
    # 3. GESTION DE LA SIMULATION (Unique et Sécurisée)
    if is_admin:
        # On ajoute une 'key' pour éviter l'erreur StreamlitDuplicateElementId
        ens_actif = st.selectbox(
            "Simulation (Admin) :", 
            sorted(df_edt['Enseignants'].unique()),
            key="sb_admin_sim"
        )
    else:
        ens_actif = nom_session

    if st.button("🚪 Déconnexion", use_container_width=True, key="logout_btn"):
        st.session_state["user_data"] = None
        st.rerun()
    
    # 3. CORRECTION DE L'ERREUR StreamlitDuplicateElementId
    if is_admin:
        # L'ajout de key="sim_admin_unique" empêche l'erreur de duplication
        ens_actif = st.selectbox(
            "Simulation (Admin) :", 
            sorted(df_edt['Enseignants'].unique()),
            key="sim_admin_unique" 
        )
    else:
        ens_actif = nom_user

    if st.button("🚪 Déconnexion", use_container_width=True, key="logout_btn"):
        st.session_state["user_data"] = None
        st.rerun()
    
    # Détermination de l'enseignant pour le filtrage de l'EDT
    if is_admin:
        ens_actif = st.selectbox("Simulation (Admin) :", sorted(df_edt['Enseignants'].unique()))
    else:
        # On utilise le nom officiel pour filtrer les matières dans l'EDT Excel
        ens_actif = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET 1 : SAISIE ---
with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True)
    
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    date_s = c3.date_input("Date réelle :", value=datetime.now())
    
    # Filtrage des promotions où l'enseignant intervient
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
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

    # Sélection de la matière basée sur l'enseignant et la promo
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
            # Archivage Absences
            for name in absents_final:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": name, "note_evaluation": type_abs,
                    "observations": obs_input, "categorie_seance": charge, "type_seance": type_seance
                }).execute()
            
            # Envoi des emails aux responsables
            destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
            if resp_nom != "Aucun":
                destinataires.append(staff_options[resp_nom])
            
            corps_mail = f"""
            RAPPORT DE SÉANCE - {TITRE_PLATEFORME}
            --------------------------------------------------
            Enseignant : {grade_fix} {user['nom_officiel']}
            Date : {date_s}
            Matière : {m_sel} ({type_seance})
            Régime : {charge}
            Absents : {len(absents_final)} ({type_abs})
            Note/Observation : {valeur if etudiant_note != "Aucun" else "N/A"}
            Commentaire : {obs_input}
            """
            
            send_email_rapport(destinataires, f"Rapport Séance - {m_sel} - {p_sel}", corps_mail)
            st.success("✅ Rapport archivé et diffusé aux responsables !"); st.balloons()
        else:
            st.error("Code unique de validation incorrect.")

# --- ONGLET 2 : SUIVI ENSEIGNANT ---
with t_suivi:
    st.markdown("### 🔍 Fiche de Suivi Individuelle")
    p_suivi = st.selectbox("1️⃣ Promotion :", sorted(df_etudiants['Promotion'].unique()), key="s_p")
    etudiants_promo = df_etudiants[df_etudiants['Promotion'] == p_suivi]
    nom_suivi = st.selectbox("2️⃣ Étudiant :", ["--"] + sorted(etudiants_promo['Full_N'].unique()), key="s_n")
    if nom_suivi != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_suivi).execute()
        if res.data: st.table(pd.DataFrame(res.data)[['date_seance', 'matiere', 'note_evaluation', 'enseignant']])

# --- ONGLET 3 : ADMIN ---
with t_admin:
    if is_admin:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)
    else: st.error("Accès restreint.")






