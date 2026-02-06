import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import segno
import re
import random
import string
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

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
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()
df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()

def color_edt(val):
    if not val or val == "": return ""
    if "Cours" in val: return 'background-color: #d1e7dd; color: #084298; font-weight: bold;'
    if "Td" in val or "TD" in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
    if "TP" in val: return 'background-color: #cfe2ff; color: #004085; font-weight: bold;'
    return ''

# --- 4. AUTHENTIFICATION & ESPACES PUBLICS ---
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
        df_staff['Full_S'] = (df_staff['NOM'] + " " + df_staff['PRÉNOM']).str.upper()
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()))
        inf = df_staff[df_staff['Full_S'] == choix].iloc[0]
        st.info(f"Grade : {inf['Grade']} | Statut : {inf['Qualité']}")
        reg_e = st.text_input("Email :", value=inf['Email'])
        reg_p = st.text_input("Créer Code Unique :", type="password")
        if st.button("Valider l'inscription"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf['NOM'], "prenom_officiel": inf['PRÉNOM'],
                "statut_enseignant": inf['Qualité'], "grade_enseignant": inf['Grade']
            }).execute()
            st.success("Compte créé avec succès !")

    with t_forgot:
        f_email = st.text_input("Saisissez votre Email professionnel :")
        if st.button("Réinitialiser mon code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_email_rapport([f_email], "Récupération Code Unique", f"Votre nouveau code est : {new_c}")
                st.success("Nouveau code envoyé par email.")
            else: st.error("Email non reconnu.")

    with t_student:
        nom_st = st.selectbox("Sélectionnez votre nom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.info(f"🎓 {profil['Promotion']} | Groupe {profil['Groupe']} | {profil['Sous groupe']}")
            
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
                grid = edt_st.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                grid = grid.reindex(columns=[j for j in jours_ordre if j in grid.columns])
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True)
            else:
                st.warning("Emploi du temps non trouvé.")
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# Correction du grade et statut
grade_fix = user.get('grade_enseignant', 'Enseignant')
if not grade_fix or grade_fix == "nan": grade_fix = "Enseignant"
statut_fix = user.get('statut_enseignant', 'Permanent')
if not statut_fix or statut_fix == "nan": statut_fix = "Permanent"

st.markdown(f"<h4 style='text-align:center;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}")
    st.success(f"**Grade :** {grade_fix}")
    st.warning(f"**Statut :** {statut_fix}")
    st.divider()
    ens_actif = st.selectbox("Vue Simulation (Admin) :", sorted(df_edt['Enseignants'].unique())) if is_admin else user['nom_officiel']
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET 1 : SAISIE ---
with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True)
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    date_s = c3.date_input("Date réelle :", value=datetime.now())
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    # 📊 AFFICHAGE NUMÉRIQUE DES EFFECTIFS
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"Sous-groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    st.markdown("---")

    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])
    
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")
    
    if abs_collective:
        absents_final = eff_liste['Full_N'].tolist()
        type_abs = "Absence Collective"
    else:
        absents_final = st.multiselect("Sélectionner les étudiants absents :", options=eff_liste['Full_N'].tolist())
        type_abs = st.selectbox("Nature de l'absence :", ["Absence non justifiée", "Absence justifiée", "Exclusion"])

    st.divider()
    st.markdown("### 📝 Notation / Participation")
    cn1, cn2, cn3 = st.columns(3)
    etudiant_note = cn1.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist())
    critere = cn2.selectbox("Critère :", ["Test", "Examen de TD", "Participation", "Interrogation"])
    valeur = cn3.text_input("Note/Observation :")
    obs_input = st.text_area("🗒️ Observations générales de la séance :")

    # 📧 DESTINATAIRE SUPPLÉMENTAIRE
    st.markdown("### ✉️ Diffusion du Rapport")
    staff_options = {row['Full_S']: row['Email'] for _, row in df_staff.iterrows()}
    dest_sup_nom = st.selectbox("Ajouter un destinataire (ex: Responsable de spécialité) :", ["Aucun"] + sorted(list(staff_options.keys())))
    
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password")
    
    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            # Archivage Absences
            for name in absents_final:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": name, "note_evaluation": type_abs,
                    "observations": obs_input, "categorie_seance": charge, "type_seance": type_seance
                }).execute()
            # Archivage Note
            if etudiant_note != "Aucun":
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": etudiant_note, "note_evaluation": f"{critere}: {valeur}",
                    "observations": obs_input, "categorie_seance": charge, "type_seance": type_seance
                }).execute()
            
            # Construction liste destinataires
            liste_mails = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
            if dest_sup_nom != "Aucun":
                liste_mails.append(staff_options[dest_sup_nom])
            
            corps = f"Rapport de {user['nom_officiel']}\nPromo: {p_sel}\nMatière: {m_sel}\nAbsents: {len(absents_final)}\nObs: {obs_input}"
            send_email_rapport(liste_mails, f"Rapport Séance - {m_sel}", corps)
            
            st.success("✅ Rapport archivé et emails envoyés !"); st.balloons()
        else:
            st.error("Code de validation incorrect.")

# --- ONGLET 2 : SUIVI ÉTUDIANT ---
with t_suivi:
    st.markdown("### 🔍 Fiche de Suivi Individuelle")
    mask_ens = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    mes_promos = sorted(df_edt[mask_ens]['Promotion'].unique()) if any(mask_ens) else sorted(df_edt['Promotion'].unique())
    p_suivi = st.selectbox("1️⃣ Promotion :", mes_promos, key="suivi_p")
    etudiants_promo = df_etudiants[df_etudiants['Promotion'] == p_suivi]
    nom_suivi = st.selectbox("2️⃣ Étudiant :", ["--"] + sorted(etudiants_promo['Full_N'].unique()), key="suivi_n")
    
    if nom_suivi != "--":
        st.divider()
        st.markdown(f"#### 📊 Dossier de : {nom_suivi}")
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_suivi).execute()
        
        if res.data:
            df_res = pd.DataFrame(res.data)
            df_res.columns = [c.lower() for c in df_res.columns]
            
            st.markdown("##### ❌ Historique des Absences")
            if 'note_evaluation' in df_res.columns:
                df_abs = df_res[df_res['note_evaluation'].str.contains("Absence|Exclusion", na=False)]
                if not df_abs.empty:
                    st.table(df_abs[['date_seance', 'matiere', 'note_evaluation']])
                else: st.info("Aucune absence.")

            st.markdown("##### 📝 Évaluations & Participation")
            if 'note_evaluation' in df_res.columns:
                df_notes = df_res[df_res['note_evaluation'].str.contains("Test|Examen|Participation|Interrogation", na=False)]
                if not df_notes.empty:
                    st.table(df_notes[['date_seance', 'matiere', 'note_evaluation']])
                else: st.info("Aucune note.")

            st.markdown("##### 🗒️ Observations Générales")
            if 'observations' in df_res.columns:
                df_obs = df_res[(df_res['observations'].notna()) & (df_res['observations'] != "")]
                if not df_obs.empty:
                    for _, row in df_obs.iterrows():
                        with st.expander(f"Séance du {row['date_seance']} - {row['matiere']}"):
                            st.write(f"**Obs :** {row['observations']}")
                else: st.info("Aucune observation.")
        else:
            st.warning("Aucune donnée pour cet étudiant.")

# --- ONGLET 3 : ADMIN ---
with t_admin:
    if is_admin:
        res_adm = supabase.table("archives_absences").select("*").execute()
        if res_adm.data:
            st.dataframe(pd.DataFrame(res_adm.data), use_container_width=True)
    else:
        st.error("Espace réservé à l'administration.")
