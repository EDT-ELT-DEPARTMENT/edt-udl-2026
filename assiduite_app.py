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

def generate_qr(data):
    qr = segno.make(data)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10)
    return out.getvalue()

def send_email(destinataire, sujet, corps):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"EDT UDL System <{EMAIL_SENDER}>"
        msg['To'] = destinataire
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

# --- 4. GESTION DES SESSIONS & AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :")
        p_log = st.text_input("Code Unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Email ou code incorrect.")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()))
        inf = df_staff[df_staff['Full_S'] == choix].iloc[0]
        st.info(f"Grade : {inf['Grade']} | Statut : {inf['Qualité']}")
        reg_e = st.text_input("Email :", value=inf['Email'])
        reg_p = st.text_input("Définir un Code Unique :", type="password")
        if st.button("Créer mon compte"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf['NOM'], "prenom_officiel": inf['PRÉNOM'],
                "statut_enseignant": inf['Qualité'], "grade_enseignant": inf['Grade']
            }).execute()
            st.success("Compte créé avec succès !")

    with t_forgot:
        st.subheader("Récupération de code")
        f_email = st.text_input("Email d'inscription :")
        if st.button("Réinitialiser mon code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_email(f_email, "Récupération Code UDL", f"Votre nouveau code : {new_c}")
                st.success("Code envoyé par mail.")
            else: st.error("Email inconnu.")

    with t_student:
        nom_st = st.selectbox("Sélectionner l'étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.markdown(f"#### 🎓 {profil['Promotion']} | G: {profil['Groupe']} | SG: {profil['Sous groupe']}")
            
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
            
            st.markdown("### ❌ Historique des Absences/Notes")
            abs_st = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            if abs_st.data:
                st.dataframe(pd.DataFrame(abs_st.data)[['date_seance', 'matiere', 'note_evaluation', 'observations']], use_container_width=True)
    st.stop()

# --- 5. ESPACE ENSEIGNANT (POST-LOGIN) ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
grade_fix = user.get('grade_enseignant', 'Enseignant')
if grade_fix in ["None", "", "nan"]: grade_fix = "Enseignant"

st.markdown(f"<h4 style='text-align:center; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}")
    st.info(f"**Grade :** {grade_fix}\n\n**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    ens_actif = st.selectbox("Vue Admin (Enseignant) :", sorted(df_edt['Enseignants'].unique())) if is_admin else user['nom_officiel']
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET SAISIE (V2 PROFESSIONNELLE) ---
with t_saisie:
    st.markdown("### 📋 Configuration de la Séance")
    
    # --- AJOUT TYPE DE CHARGE ---
    charge = st.radio("Type de charge :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True)
    
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    date_s = c3.date_input("Date :", value=datetime.now())
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    # Métriques d'effectifs
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promo", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"S-Groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    
    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"])
    
    st.divider()
    
    # --- GESTION DES ABSENCES AVEC CAS DÉROULANT ---
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    abs_sel = st.multiselect("Sélectionner les étudiants absents :", options=eff_liste['Full_N'].tolist())
    # Ajout du type d'absence
    type_abs = st.selectbox("Nature de l'absence :", ["Absence non justifiée", "Absence justifiée", "Absence Collective", "Exclusion de séance"])
    
    st.divider()
    
    # --- GESTION DE LA NOTATION ---
    st.markdown("### 📝 Évaluation & Participation")
    st.info("Sélectionnez un étudiant pour lui attribuer une note ou une observation spécifique.")
    c_note1, c_note2, c_note3 = st.columns(3)
    etudiant_note = c_note1.selectbox("Étudiant à évaluer :", ["Aucun"] + eff_liste['Full_N'].tolist())
    type_eval = c_note2.selectbox("Critère :", ["Test", "Examen de TD", "Participation", "Interrogation orale", "Travail rendu"])
    val_note = c_note3.text_input("Note / Appréciation :", placeholder="ex: 15/20 ou Excellent")
    
    obs = st.text_area("🗒️ Observations générales sur la séance :")
    code_v = st.text_input("🔑 Code Unique (Validation) :", type="password")
    
    if st.button("🚀 VALIDER ET ARCHIVER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            # 1. Enregistrement des absences
            for st_name in abs_sel:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": st_name, "note_evaluation": type_abs,
                    "observations": f"{charge} - {type_seance}", "categorie_seance": charge
                }).execute()
            
            # 2. Enregistrement de la note spécifique
            if etudiant_note != "Aucun":
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": etudiant_note, "note_evaluation": f"{type_eval}: {val_note}",
                    "observations": obs, "categorie_seance": charge
                }).execute()
            
            send_email(EMAIL_CHEF_DEPT, f"Rapport {m_sel} - {p_sel}", f"Validé par {user['nom_officiel']}\nType: {charge}\nAbsents: {len(abs_sel)}")
            st.success("Rapport enregistré avec succès !"); st.balloons()
        else:
            st.error("Code de validation incorrect.")

# --- ONGLET SUIVI ---
with t_suivi:
    st.subheader("🔍 Fiche de suivi individuelle")
    search = st.selectbox("Rechercher un étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    if search != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", search).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data)[['date_seance', 'matiere', 'note_evaluation', 'enseignant']], use_container_width=True)
        else: st.info("Aucun historique pour cet étudiant.")

# --- ONGLET ADMIN ---
with t_admin:
    if is_admin:
        st.subheader("🛡️ Administration Globale")
        res = supabase.table("archives_absences").select("*").execute()
        if res.data:
            df_all = pd.DataFrame(res.data)
            st.metric("Total Enregistrements", len(df_all))
            st.dataframe(df_all, use_container_width=True)
            buf = io.BytesIO(); df_all.to_excel(buf, index=False)
            st.download_button("📊 Exporter la base (Excel)", buf.getvalue(), "Archives_Globales.xlsx")
    else:
        st.warning("Accès restreint aux administrateurs.")
