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

TITRE_PLATEFORME = "Plateforme de gestion des enseignements et assuiduité des étudiants 2025-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

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
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("⚠️ Configuration Supabase manquante dans les secrets.")
        return None

supabase = init_connection()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_qr(data):
    qr = segno.make(data)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10)
    return out.getvalue()

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
    except Exception:
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
        e_log = st.text_input("Email Professionnel :", key="main_log_e")
        p_log = st.text_input("Code Unique :", type="password", key="main_log_p")
        if st.button("Se connecter", use_container_width=True, key="btn_login"):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).execute()
            if res.data and res.data[0]['password_hash'] == hash_pw(p_log):
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Email ou code incorrect.")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()), key="signup_name")
        inf = df_staff[df_staff['Full_S'] == choix].iloc[0]
        st.info(f"Profil : {inf['Grade']} | {inf['Qualité']}")
        reg_e = st.text_input("Confirmer Email :", value=inf['Email'], key="signup_email")
        reg_p = st.text_input("Créer Code Unique :", type="password", key="signup_p")
        if st.button("Valider Inscription", key="btn_signup"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf['NOM'], "prenom_officiel": inf['PRÉNOM'],
                "statut_enseignant": inf['Qualité'], "grade_enseignant": inf['Grade']
            }).execute()
            st.success("Compte créé !")

    with t_forgot:
        f_email = st.text_input("Email d'inscription :", key="forgot_email_input")
        if st.button("Récupérer mon code", key="btn_forgot"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_email_rapport([f_email], "Votre nouveau code UDL", f"Votre code est : {new_c}")
                st.success("Code envoyé par email.")
            else: st.error("Email inconnu.")

    with t_student:
        nom_st = st.selectbox("Nom de l'étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()), key="student_view_name")
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
                grid = grid.reindex(columns=["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"])
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True)
            
            st.markdown("### ❌ Absences & Évaluations")
            res_st = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            if res_st.data:
                st.table(pd.DataFrame(res_st.data)[['date_seance', 'matiere', 'note_evaluation']])
    st.stop()

# --- 5. ESPACE ENSEIGNANT CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
grade_fix = user.get('grade_enseignant', 'Enseignant')

st.markdown(f"<h4 style='text-align:center; border-bottom: 2px solid #003366; padding-bottom: 10px;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}")
    st.markdown(f"**Grade :** {grade_fix}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        ens_actif = st.selectbox("Vue Simulation (Admin) :", sorted(df_edt['Enseignants'].unique()), key="admin_sim_ens")
    else:
        ens_actif = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True, key="btn_logout_sidebar"):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET SAISIE ---
with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True, key="saisie_regime")
    
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"], key="saisie_type")
    date_s = c3.date_input("Date réelle :", value=datetime.now(), key="saisie_date")
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()), key="saisie_promo")
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"], key="saisie_grp")
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"], key="saisie_sgrp")
    
    # AFFICHAGE NUMÉRIQUE
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promo", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"S-Groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    st.markdown("---")

    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"], key="saisie_matiere")
    
    # --- ❌ GESTION DES ABSENCES ---
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE", key="cb_abs_coll")
    
    if abs_collective:
        absents_final = eff_liste['Full_N'].tolist()
        st.warning(f"⚠️ {len(absents_final)} étudiants seront marqués absents.")
        type_abs = "Absence Collective"
    else:
        absents_final = st.multiselect("Sélectionner les étudiants absents :", options=eff_liste['Full_N'].tolist(), key="ms_absents")
        type_abs = st.selectbox("Nature de l'absence :", ["Absence non justifiée", "Absence justifiée", "Exclusion"], key="sb_nature_abs")

    st.divider()
    
    # --- 📝 NOTATION ---
    st.markdown("### 📝 Notation / Participation")
    cn1, cn2, cn3 = st.columns(3)
    etudiant_note = cn1.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist(), key="sb_note_target")
    critere = cn2.selectbox("Critère :", ["Test", "Examen de TD", "Participation", "Interrogation"], key="sb_note_critere")
    valeur = cn3.text_input("Note/Observation :", key="ti_note_val")

    obs = st.text_area("🗒️ Observations générales :", key="ta_obs_gen")
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password", key="ti_code_v")
    
    if st.button("🚀 VALIDER LE RAPPORT ET ENVOYER EMAILS", use_container_width=True, type="primary", key="btn_validate_all"):
        if hash_pw(code_v) == user['password_hash']:
            # 1. Archivage Absences
            for name in absents_final:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": name, "note_evaluation": type_abs,
                    "observations": f"{charge} | {type_seance}", "categorie_seance": charge
                }).execute()
            
            # 2. Archivage Note
            if etudiant_note != "Aucun":
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": etudiant_note, "note_evaluation": f"{critere}: {valeur}",
                    "observations": obs, "categorie_seance": charge
                }).execute()
            
            # 3. Envoi Emails
            corps_mail = f"Nouveau Rapport : {user['nom_officiel']} | {p_sel} | {m_sel}\nDate: {date_s}\nAbsents: {len(absents_final)}\nNote: {etudiant_note} ({valeur})\nObs: {obs}"
            send_email_rapport([EMAIL_CHEF_DEPT, EMAIL_ADJOINT], f"Rapport UDL - {m_sel}", corps_mail)
            
            st.success("✅ Archivage réussi et emails envoyés !"); st.balloons()
        else: st.error("Code de validation incorrect.")

# --- ONGLET SUIVI ÉTUDIANT (DEUX SECTIONS DISTINCTES) ---
with t_suivi:
    st.markdown("### 🔍 Dossier Pédagogique & Assiduité")
    
    # Chargement de la source Excel pour enrichir les données
    @st.cache_data
    def get_source_data():
        try:
            df_src = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
            return df_src[['Enseignements', 'Enseignants', 'Horaire']]
        except:
            return None

    df_info_suivi = get_source_data()

    # --- RÉCUPÉRATION DES NOMS AYANT DÉJÀ DES ENREGISTREMENTS ---
    # On récupère tous les noms présents dans la table archives_absences
    res_noms = supabase.table("archives_absences").select("etudiant_nom").execute()
    liste_noms_existants = sorted(list(set([r['etudiant_nom'] for r in res_noms.data]))) if res_noms.data else []

    # --- SECTION A : ASSIDUITÉ ---
    st.subheader("❌ 1. État de l'Assiduité (Absences)")
    nom_abs = st.selectbox(
        "Sélectionner l'étudiant pour l'assiduité :",
        ["--"] + liste_noms_existants,
        key="search_abs"
    )

    if nom_abs != "--":
        res_a = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_abs).execute()
        if res_a.data:
            df_a = pd.DataFrame(res_a.data)
            df_assiduite = df_a[df_a['note_evaluation'].str.contains("Absence", na=False)].copy()
            
            if not df_assiduite.empty:
                # Merge avec Excel
                if df_info_suivi is not None:
                    df_assiduite = df_assiduite.merge(df_info_suivi, left_on='matiere', right_on='Enseignements', how='left')
                
                df_assiduite['G/SG'] = df_assiduite['groupe'].astype(str) + " / " + df_assiduite['sous_groupe'].astype(str)
                df_view_a = df_assiduite[['etudiant_nom', 'promotion', 'G/SG', 'matiere', 'Enseignants', 'Horaire', 'date_seance', 'note_evaluation']]
                df_view_a.columns = ['Nom & Prénom', 'Promotion', 'G/SG', 'Matière', 'Chargé', 'Horaire', 'Date', 'Type']
                
                st.dataframe(df_view_a.sort_values(by="Date", ascending=False), use_container_width=True)
            else:
                st.success(f"✅ Aucune absence enregistrée pour {nom_abs}.")

    st.divider()

    # --- SECTION B : ÉVALUATIONS ---
    st.subheader("📝 2. Résultats des Évaluations (Critères)")
    nom_eval = st.selectbox(
        "Sélectionner l'étudiant pour les évaluations :",
        ["--"] + liste_noms_existants,
        key="search_eval"
    )

    if nom_eval != "--":
        res_e = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_eval).execute()
        if res_e.data:
            df_e = pd.DataFrame(res_e.data)
            df_evals = df_e[df_e['note_evaluation'].str.contains(":", na=False)].copy()
            
            if not df_evals.empty:
                # Merge avec Excel
                if df_info_suivi is not None:
                    df_evals = df_evals.merge(df_info_suivi, left_on='matiere', right_on='Enseignements', how='left')
                
                df_evals['G/SG'] = df_evals['groupe'].astype(str) + " / " + df_evals['sous_groupe'].astype(str)
                df_view_e = df_evals[['etudiant_nom', 'promotion', 'G/SG', 'matiere', 'Enseignants', 'Horaire', 'date_seance', 'note_evaluation', 'observations']]
                df_view_e.columns = ['Nom & Prénom', 'Promotion', 'G/SG', 'Matière', 'Chargé de Matière', 'Horaire', 'Date', 'Critère (Note)', 'Observations']
                
                st.dataframe(
                    df_view_e.sort_values(by="Date", ascending=False).style.applymap(
                        lambda x: "background-color: #d1e7dd; color: #0f5132; font-weight: bold;", 
                        subset=["Critère (Note)"]
                    ),
                    use_container_width=True
                )
            else:
                st.info(f"ℹ️ Aucune évaluation enregistrée pour {nom_eval}.")

# --- ONGLET ADMIN ---
with t_admin:
    if is_admin:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data:
            df_all = pd.DataFrame(res.data)
            st.metric("Total Enregistrements", len(df_all))
            st.dataframe(df_all, use_container_width=True)
            buf = io.BytesIO(); df_all.to_excel(buf, index=False)
            st.download_button("📊 Exporter Registre (Excel)", buf.getvalue(), "Archives_Globales.xlsx", key="btn_download_admin")
    else: st.warning("Espace réservé à l'administration.")







