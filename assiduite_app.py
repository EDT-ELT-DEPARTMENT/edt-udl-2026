import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import random
import string
import segno  # Pour le QR Code
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 EMAILS ADMINISTRATION
EMAIL_CHEF_DEPT = "chef.department.elt.fge@gmail.com"
EMAIL_CHEF_ADJOINT = ""
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur de configuration Supabase. Vérifiez vos secrets Streamlit.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body, is_html=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires) if isinstance(destinataires, list) else destinataires
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
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
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'NAN'], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

def get_live_grade(user_nom, user_email):
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    if not match.empty:
        g = match.iloc[0]['Grade']
        return g if g != "" else "Enseignant"
    return "Enseignant"

def extraire_heure_debut(creneau):
    try:
        h_part = creneau.split('-')[0].split('h')[0].strip()
        return float(h_part.replace(':', '.'))
    except: return 99.0

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        email_log = st.text_input("Email :", key="log_email")
        pass_log = st.text_input("Code Unique :", type="password", key="log_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Email ou code incorrect.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full'].unique()))
        info_s = df_staff[df_staff['Full'] == choix].iloc[0]
        st.info(f"Profil : {info_s['NOM']} | Grade actuel : {info_s['Grade']}")
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Créer votre Code Unique :", type="password")
        if st.button("Valider Inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'],
                    "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']
                }).execute()
                st.success("Compte créé avec succès !")
            except: st.error("Erreur : Email déjà utilisé.")

    with t_forgot:
        f_email = st.text_input("Saisissez votre Email :")
        if st.button("M'envoyer un nouveau code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_mail(f_email, "Nouveau Code UDL", f"Votre nouveau code est : {new_c}")
                st.success("Consultez votre boîte mail.")

    with t_student:
        st.subheader("🎓 Portail Étudiant")
        nom_in = st.text_input("Nom et Prénom (MAJUSCULES) :").upper().strip()
        if st.button("Consulter ma fiche", use_container_width=True):
            df_etudiants['Search_Full'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()
            profil = df_etudiants[df_etudiants['Search_Full'] == nom_in]
            if not profil.empty:
                p = profil.iloc[0]
                st.success(f"✅ Dossier trouvé : {nom_in}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Promotion", p['Promotion'])
                c2.metric("Groupe", p['Groupe'])
                c3.metric("Sous-Groupe", p['Sous groupe'])
                
                # EDT Filtré et Trié
                edt_raw = df_edt[df_edt['Promotion'] == p['Promotion']].copy()
                mask_cours = edt_raw['Enseignements'].str.contains("Cours", case=False, na=False)
                mask_gp = edt_raw['Enseignements'].str.contains(p['Groupe'], na=False)
                mask_sgp = edt_raw['Enseignements'].str.contains(p['Sous groupe'], na=False)
                edt_filtre = edt_raw[mask_cours | mask_gp | mask_sgp].copy()
                
                if not edt_filtre.empty:
                    edt_filtre['tri_h'] = edt_filtre['Horaire'].apply(extraire_heure_debut)
                    edt_filtre = edt_filtre.sort_values(by='tri_h')
                    pivot = edt_filtre.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(list(dict.fromkeys(x))), sort=False)
                    jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                    st.table(pivot[[j for j in jours_ordre if j in pivot.columns]])
                
                # Absences
                res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_in).eq("note_evaluation", "ABSENCE").execute()
                if res_abs.data:
                    st.markdown("#### 🚩 État des Absences")
                    st.table(pd.DataFrame(res_abs.data).groupby('matiere').size().reset_index(name='Total'))
                else: st.info("Aucune absence signalée.")
            else: st.error("Étudiant non reconnu.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE (ENSEIGNANTS) ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
current_grade = get_live_grade(user['nom_officiel'], user['email'])

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    st.markdown(f"**Enseignant :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {current_grade}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
        st.divider()
        st.warning("🚨 ZONE DANGEREUSE")
        if st.button("Vider les Archives"): st.session_state["confirm_reset"] = True
        if st.session_state.get("confirm_reset"):
            confirm_p = st.text_input("Confirmez avec votre code unique :", type="password")
            if st.button("OUI, TOUT SUPPRIMER"):
                if hash_pw(confirm_p) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base de données vidée.")
                    st.session_state["confirm_reset"] = False
                    st.rerun()
    else: enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    reg_s = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("📅 Date réelle :", value=datetime.now())

    cp, cm = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    list_promos = sorted(df_edt[mask]['Promotion'].unique())
    p_sel = cp.selectbox("🎓 Promotion :", list_promos if list_promos else sorted(df_edt['Promotion'].unique()))
    list_mats = sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique())
    m_sel = cm.selectbox("📖 Matière :", list_mats if list_mats else ["-"])

    st.markdown("---")
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p_full[df_p_full['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p_full.empty else ["SG1"])

    df_appel = df_p_full[(df_p_full['Groupe']==g_sel) & (df_p_full['Sous groupe']==sg_sel)].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    liste_noms = df_appel['Full'].tolist()

    col_abs, col_note = st.columns(2)
    with col_abs:
        abs_coll = st.checkbox("🚩 SIGNALER ABSENCE COLLECTIVE")
        absents_sel = liste_noms if abs_coll else st.multiselect("❌ Absents :", options=liste_noms)
    with col_note:
        et_a_noter = st.selectbox("📝 Noter un étudiant :", ["Aucun"] + liste_noms)
        val_note = st.text_input("Valeur (ex: +1) :", "0")

    obs_txt = st.text_area("🗒️ Observations :")
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            meta = {"promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_grade} {user['nom_officiel']}", "date_seance": str(date_s), "regime_heure": reg_s, "observations": obs_txt, "categorie_seance": cat_s}
            for ab in absents_sel:
                r = meta.copy(); r.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                supabase.table("archives_absences").insert(r).execute()
            if et_a_noter != "Aucun":
                rn = meta.copy(); rn.update({"etudiant_nom": et_a_noter, "note_evaluation": val_note})
                supabase.table("archives_absences").insert(rn).execute()
            send_mail([EMAIL_CHEF_DEPT, user['email']], f"Rapport {m_sel}", f"Validé par {user['nom_officiel']}")
            st.success("✅ Archivé !")
            st.balloons()
        else: st.error("Code incorrect.")

with tab_suivi:
    df_etudiants['Search_Full'] = df_etudiants['Nom'] + " " + df_etudiants['Prénom']
    etudiant_search = st.selectbox("🎯 Rechercher un étudiant :", ["-- Sélectionner --"] + sorted(df_etudiants['Search_Full'].unique()))
    if etudiant_search != "-- Sélectionner --":
        res_sql = supabase.table("archives_absences").select("*").eq("etudiant_nom", etudiant_search).execute()
        if res_sql.data:
            df_abs_et = pd.DataFrame(res_sql.data)
            st.table(df_abs_et[['date_seance', 'matiere', 'enseignant', 'note_evaluation']])
            buf = io.BytesIO(); df_abs_et.to_excel(buf, index=False)
            st.download_button("📥 Télécharger Excel", buf.getvalue(), f"Suivi_{etudiant_search}.xlsx")

with tab_hist:
    res_glob = supabase.table("archives_absences").select("*").execute()
    if res_glob.data:
        df_glob = pd.DataFrame(res_glob.data)
        st.dataframe(df_glob, use_container_width=True)
        buf_g = io.BytesIO(); df_glob.to_excel(buf_g, index=False)
        st.download_button("📊 Exporter tout", buf_g.getvalue(), "Archives_Globales.xlsx")
