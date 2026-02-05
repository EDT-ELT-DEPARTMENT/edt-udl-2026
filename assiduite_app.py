import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Gestion Électrotechnique UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion du département d'électrotechnique - États d'avancement des enseignements - Assiduité des étudiants"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# 📧 EMAILS ADMIN
EMAIL_CHEF_DEPT = "chef.department.elt.fge@gmail.com"
EMAIL_CHEF_ADJOINT = ""
EMAIL_ADMIN_TECH = ""

# 🔑 CONFIGURATION SMTP
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataires, subject, body, is_html=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
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
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    for df in [df_e, df_s]:
        df.columns = [str(c).strip() for c in df.columns]
    return df_e, df_s

# --- 4. AUTHENTIFICATION ---
df_edt, df_etudiants = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"### 🔑 Accès Enseignant")
    t_login, t_signup, t_perdu = st.tabs(["Connexion", "Inscription", "Code oublié ?"])
    
    with t_login:
        email_log = st.text_input("Email professionnel :", key="l_mail")
        pass_log = st.text_input("Code Unique :", type="password", key="l_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
    # (Inscription et Perdu restent identiques)
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<h3 style='text-align:center; color:#003366;'>{TITRE_PLATEFORME}</h3>", unsafe_allow_html=True)

is_admin = (user['email'] == EMAIL_ADMIN_TECH)
if is_admin:
    st.sidebar.success("Mode Administrateur")
    enseignant_sel = st.selectbox("👤 Sélectionner l'Enseignant (Admin) :", sorted(df_edt['Enseignants'].unique()))
else:
    enseignant_sel = st.selectbox("👤 Enseignant :", [user['nom_officiel']], disabled=True)

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive des Absences & Notes"])

# --- ONGLET 1 : SAISIE ---
with tab_saisie:
    # --- DÉTAILS DE LA SÉANCE ---
    c_cat, c_type, c_date = st.columns(3)
    cat_seance = c_cat.selectbox("🏷️ Rapport de séance :", ["Cours", "TD", "TP", "Examen", "Autre"])
    type_seance = c_type.selectbox("📂 État de la séance :", ["Séance Normale", "Séance de Rattrapage"])
    date_seance = c_date.date_input("📅 Date réelle :")

    c1, c2 = st.columns(2)
    promo_sel = c1.selectbox("🎓 Promotion :", sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique()))
    matiere_sel = c2.selectbox("📖 Matière :", sorted(df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique()))

    res_s = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    horaire_v = res_s.iloc[0]['Horaire'] if not res_s.empty else "N/A"
    
    st.markdown("---")
    st.markdown("### 📈 Gestion des Étudiants (Présence & Notes)")
    
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    df_g = df_p[df_p['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    # --- ABSENCE COLLECTIVE ---
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")

    df_f = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_f['Full'] = df_f['Nom'].astype(str) + " " + df_f['Prénom'].astype(str)
    
    if abs_collective:
        absents = df_f['Full'].tolist()
        st.warning(f"⚠️ {len(absents)} étudiants seront marqués absents.")
        note_val = "0" # Pas de note en cas d'absence collective
    else:
        absents = st.multiselect("❌ Sélectionner les ABSENTS :", options=df_f['Full'].tolist())
        st.markdown("#### ⭐ Participation / Note d'examen (Optionnel)")
        # Sélection de l'étudiant méritant ou examiné
        etudiant_note = st.selectbox("Sélectionner l'étudiant à noter :", ["Aucun"] + df_f['Full'].tolist())
        note_val = st.text_input("Saisir la note ou observation (Ex: 15/20 ou +2 participation) :", value="0")

    obs = st.text_area("🗒️ Observations (Motif, Avancement du programme...) :")
    sign = st.text_input("✍️ Signature :", value=user['nom_officiel'])
    code_f = st.text_input("🔑 Code Unique :", type="password")

    if st.button("🚀 VALIDER ET ARCHIVER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_f) == user['password_hash']:
            with st.spinner("Enregistrement en cours..."):
                # 1. ARCHIVAGE ABSENCES
                for etud in absents:
                    supabase.table("archives_absences").insert({
                        "etudiant_nom": etud, "promotion": promo_sel, "groupe": gr_sel,
                        "sous_groupe": sg_sel, "matiere": matiere_sel, "enseignant": enseignant_sel,
                        "date_seance": str(date_seance), "horaire": horaire_v,
                        "type_seance": type_seance, "categorie_seance": cat_seance,
                        "absence_collective": abs_collective, "note_evaluation": "ABS"
                    }).execute()
                
                # 2. ARCHIVAGE NOTE (Si un étudiant est noté et n'est pas absent)
                if not abs_collective and etudiant_note != "Aucun" and etudiant_note not in absents:
                    supabase.table("archives_absences").insert({
                        "etudiant_nom": etudiant_note, "promotion": promo_sel, "groupe": gr_sel,
                        "sous_groupe": sg_sel, "matiere": matiere_sel, "enseignant": enseignant_sel,
                        "date_seance": str(date_seance), "horaire": horaire_v,
                        "type_seance": type_seance, "categorie_seance": cat_seance,
                        "absence_collective": False, "note_evaluation": note_val
                    }).execute()

                # 3. EMAIL HIÉRARCHIQUE
                mail_html = f"""
                <h3>Rapport de Séance : {cat_seance} ({type_seance})</h3>
                <p><b>Enseignant :</b> {enseignant_sel} | <b>Matière :</b> {matiere_sel}</p>
                <p><b>Statut :</b> {'⚠️ ABSENCE COLLECTIVE' if abs_collective else 'Normal'}</p>
                <p><b>Nombre d'absents :</b> {len(absents)}</p>
                <p><b>Note attribuée :</b> {note_val} à {etudiant_note if not abs_collective else 'N/A'}</p>
                <p><b>Observations :</b> {obs}</p>
                <p><b>Signé :</b> {sign}</p>
                """
                send_mail([EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']], f"[{cat_seance}] {promo_sel} - {enseignant_sel}", mail_html, is_html=True)
                
                st.success("✅ Rapport envoyé et archivé !")
                st.balloons()
        else:
            st.error("Code Unique incorrect.")

# --- ONGLET 2 : ARCHIVES ---
with tab_hist:
    st.markdown("### 📋 Historique des Présences et Evaluations")
    try:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data:
            df_arc = pd.DataFrame(res.data)
            # Ordonner les colonnes pour la lecture
            cols = ['date_seance', 'etudiant_nom', 'promotion', 'categorie_seance', 'matiere', 'note_evaluation', 'absence_collective']
            st.dataframe(df_arc[cols], use_container_width=True)
            
            buf = io.BytesIO()
            df_arc.to_excel(buf, index=False)
            st.download_button("📊 Télécharger EXCEL Complet", buf.getvalue(), "Archives_UDL_2026.xlsx", use_container_width=True)
    except:
        st.info("Aucune archive disponible.")

if st.sidebar.button("🚪 Déconnexion"):
    st.session_state["user_data"] = None
    st.rerun()


