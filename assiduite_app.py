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
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur Supabase. Vérifiez vos secrets Streamlit.")
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
    except: return False

@st.cache_data
def load_data():
    try:
        df_e = pd.read_excel(FICHIER_EDT)
        df_s = pd.read_excel(FICHIER_ETUDIANTS)
        df_staff = pd.read_excel(FICHIER_STAFF)
        for df in [df_e, df_s, df_staff]:
            df.columns = [str(c).strip() for c in df.columns]
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'NAN', ''], 'Inconnu')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

df_edt, df_etudiants, df_staff = load_data()

def get_live_info(user_nom, user_email):
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if match.empty:
        match = df_staff[df_staff['NOM'].str.upper() == user_nom.upper()]
    if not match.empty:
        g = match.iloc[0].get('Grade', 'Enseignant')
        s = match.iloc[0].get('Qualité', 'Permanent')
        return g, s
    return "Enseignant", "Permanent"

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION & ESPACE ÉTUDIANT ---
if not st.session_state["user_data"]:
    st.markdown(f"<h3 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h3>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        email_log = st.text_input("Email :", key="l_email")
        pass_log = st.text_input("Code Unique :", type="password", key="l_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Nom :", sorted(df_staff['Full'].unique()))
        info_s = df_staff[df_staff['Full'] == choix].iloc[0]
        st.info(f"Profil : {info_s['NOM']} | {info_s['Grade']} ({info_s['Qualité']})")
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Créer Code Unique :", type="password")
        if st.button("Valider Inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'],
                    "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']
                }).execute()
                st.success("Inscription réussie !")
            except: st.error("Erreur (Email déjà utilisé).")

    with t_forgot:
        f_email = st.text_input("Email professionnel :")
        if st.button("Réinitialiser mon code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                if send_mail(f_email, "Nouveau Code Unique", f"Votre nouveau code est : {new_c}"):
                    st.success("Code envoyé par email.")
            else: st.error("Email non trouvé.")

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
                
                # --- FILTRAGE INTELLIGENT DE L'EDT ---
                edt_raw = df_edt[df_edt['Promotion'] == p['Promotion']].copy()
                
                # On garde : 1. Tous les Cours | 2. Les TD du groupe | 3. Les TP du sous-groupe
                mask_cours = edt_raw['Enseignements'].set_flags(case=False).str.contains("Cours", na=False)
                mask_td = (edt_raw['Enseignements'].str.contains("Td", case=False, na=False)) & (edt_raw['Enseignements'].str.contains(p['Groupe'], na=False))
                mask_tp = (edt_raw['Enseignements'].str.contains("TP", case=False, na=False)) & (edt_raw['Enseignements'].str.contains(p['Sous groupe'], na=False))
                
                # Cas particulier : certains TD/TP ne mentionnent pas le groupe dans le nom mais sont implicites
                # On combine les filtres
                edt_filtre = edt_raw[mask_cours | mask_td | mask_tp].copy()
                
                st.markdown("#### 📅 Votre Emploi du Temps Personnalisé")
                if not edt_filtre.empty:
                    # Création de la grille (Table Pivot)
                    # Index = Horaire, Colonnes = Jours
                    try:
                        pivot_edt = edt_filtre.pivot_table(
                            index='Horaire', 
                            columns='Jours', 
                            values='Enseignements', 
                            aggfunc=lambda x: ' / '.join(x)
                        )
                        # Réordonner les jours
                        jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                        colonnes_existantes = [j for j in jours_ordre if j in pivot_edt.columns]
                        pivot_edt = pivot_edt[colonnes_existantes]
                        st.table(pivot_edt)
                    except:
                        st.dataframe(edt_filtre[['Enseignements', 'Horaire', 'Jours', 'Lieu']], use_container_width=True)
                
                # --- ÉTAT DES ABSENCES PAR MATIÈRE ---
                st.markdown("#### 🚩 État des Absences")
                res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_in).execute()
                if res_abs.data:
                    df_abs = pd.DataFrame(res_abs.data)
                    # Comptage par matière
                    compte_abs = df_abs.groupby('matiere').size().reset_index(name='Nombre d\'absences')
                    st.table(compte_abs)
                    
                    with st.expander("Voir le détail des dates"):
                        st.dataframe(df_abs[['date_seance', 'matiere', 'enseignant', 'categorie_seance']], use_container_width=True)
                else:
                    st.info("Aucune absence signalée. Continuez ainsi !")
            else: st.error("❌ Étudiant non reconnu.")
    st.stop()

# --- 5. INTERFACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
grade_live, statut_live = get_live_info(user['nom_officiel'], user['email'])

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    st.markdown(f"**Enseignant :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {grade_live}")
    st.markdown(f"**Statut :** {statut_live}")
    st.divider()
    qr = segno.make("https://edt-udl-2026.streamlit.app")
    buf = io.BytesIO()
    qr.save(buf, kind='png', scale=5)
    st.image(buf.getvalue(), caption="Accès Étudiants")
    
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie", "🔍 Suivi", "📜 Archives"])

with tab_saisie:
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("Séance :", ["Cours", "TD", "TP", "Examen"])
    reg_s = c2.selectbox("Régime :", ["Charge Horaire", "H. Supplémentaires"])
    date_s = c3.date_input("Date :", value=datetime.now())

    # Filtrage EDT pour l'enseignant
    ens_nom = user['nom_officiel'] if not is_admin else st.selectbox("Admin - Voir :", sorted(df_edt['Enseignants'].unique()))
    mask_e = df_edt['Enseignants'].str.contains(ens_nom, na=False, case=False)
    
    cp, cm = st.columns(2)
    p_sel = cp.selectbox("Promotion :", sorted(df_edt[mask_e]['Promotion'].unique()) if any(mask_e) else sorted(df_edt['Promotion'].unique()))
    m_sel = cm.selectbox("Matière :", sorted(df_edt[mask_e & (df_edt['Promotion']==p_sel)]['Enseignements'].unique()) if any(mask_e) else ["-"])

    st.divider()
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = csg.selectbox("S-Groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])

    m_e1, m_e2, m_e3 = st.columns(3)
    m_e1.metric("Promo", len(df_p))
    m_e2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe'] == g_sel]))
    m_e3.metric(f"SG {sg_sel}", len(df_p[(df_p['Groupe'] == g_sel) & (df_p['Sous groupe'] == sg_sel)]))

    df_appel = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    absents = st.multiselect("❌ Absents :", options=df_appel['Full'].tolist())
    code_v = st.text_input("🔑 Code Validation :", type="password")

    if st.button("🚀 VALIDER", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            for ab in absents:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, "matiere": m_sel, "enseignant": f"{grade_live} {user['nom_officiel']}",
                    "date_seance": str(date_s), "etudiant_nom": ab, "note_evaluation": "ABSENCE",
                    "categorie_seance": cat_s, "regime_heure": reg_s
                }).execute()
            st.success("Archivé !")
        else: st.error("Code erroné.")

with tab_suivi:
    df_etudiants['F'] = df_etudiants['Nom'] + " " + df_etudiants['Prénom']
    et_sel = st.selectbox("Rechercher un étudiant :", ["--"] + sorted(df_etudiants['F'].unique()))
    if et_sel != "--":
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_sel).execute()
        if res.data: st.table(pd.DataFrame(res.data)[['date_seance', 'matiere', 'enseignant']])
        else: st.info("Rien à signaler.")

with tab_hist:
    all_res = supabase.table("archives_absences").select("*").execute()
    if all_res.data: st.dataframe(pd.DataFrame(all_res.data), use_container_width=True)
