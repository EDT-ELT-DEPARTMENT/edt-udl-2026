import streamlit as st
import pandas as pd
import hashlib
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# 📧 ADRESSES EMAILS HIÉRARCHIQUES
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"  # Chef de Département (1er)
EMAIL_CHEF_ADJOINT = "nass_ka@yahoo.fr"    # Chef de Département Adjoint (2e)
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP (GMAIL)
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_html_report(destinataires, subject, html_body):
    """Envoie l'email au format HTML pour inclure le tableau"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, "Envoyé"
    except Exception as e:
        return False, str(e)

@st.cache_data
def load_data():
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    for df in [df_e, df_s]:
        df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignants', 'Enseignements', 'Promotion']:
        if col in df_e.columns:
            df_e[col] = df_e[col].astype(str).str.strip()
    return df_e, df_s

# --- 4. CHARGEMENT ET AUTHENTIFICATION ---
try:
    df_edt, df_etudiants = load_data()
except Exception as e:
    st.error(f"Erreur de chargement : {e}")
    st.stop()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"### 🔑 Validation Enseignant")
    email_log = st.text_input("Entrez votre Email professionnel :")
    pass_log = st.text_input("Entrez votre Code Unique :", type="password")
    
    if st.button("Accéder à la plateforme", use_container_width=True):
        res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
        if res.data:
            st.session_state["user_data"] = res.data[0]
            st.rerun()
        else:
            st.error("Identifiants incorrects.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<div style='background-color:#003366; color:white; padding:10px; border-radius:5px; text-align:center;'>{TITRE_PLATEFORME}</div>", unsafe_allow_html=True)

profs = sorted(df_edt['Enseignants'].unique())
idx_user = profs.index(user['nom_officiel']) if user['nom_officiel'] in profs else 0
enseignant_sel = st.selectbox("👤 1. Sélectionner l'Enseignant :", profs, index=idx_user)

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Historique"])

with tab_saisie:
    c1, c2 = st.columns(2)
    with c1:
        promos = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", promos)
    with c2:
        mats = sorted(df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
        matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", mats)

    res_seance = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    if not res_seance.empty:
        info = res_seance.iloc[0]
        st.info(f"📍 {info['Jours']} | {info['Horaire']} | Lieu: {info['Lieu']}")
        email_resp = info['Email_Responsable_Parcours'] if 'Email_Responsable_Parcours' in info else EMAIL_ADMIN_TECH
    else:
        st.warning("Séance non trouvée.")

    st.markdown("### 📈 État d'Avancement & Appel")
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Sélectionner le Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    df_g = df_p[df_p['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sélectionner le Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    st.markdown("#### 📊 Statistiques de présence")
    df_f = df_g[df_g['Sous groupe'] == sg_sel].copy()
    s1, s2, s3 = st.columns(3)
    s1.metric("Effectif Promotion", len(df_p))
    s2.metric(f"Effectif {gr_sel}", len(df_g))
    s3.metric(f"Effectif {sg_sel}", len(df_f))

    st.markdown("### ❌ Sélectionner les ABSENTS :")
    df_f['Full'] = df_f['Nom'].astype(str) + " " + df_f['Prénom'].astype(str)
    absents_choisis = st.multiselect(f"Liste des {len(df_f)} étudiants", options=df_f['Full'].tolist())

    st.divider()
    v1, v2 = st.columns(2)
    date_s = v1.date_input("📅 Date réelle de la séance :")
    obs = v2.text_area("🗒️ Observations (Obligatoire) :")
    
    sig_col, code_col = st.columns(2)
    sign = sig_col.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
    code_v = code_col.text_input("🔑 Entrez votre Code Unique :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if not obs or not sign or hash_pw(code_v) != user['password_hash']:
            st.error("Champs obligatoires manquants ou Code Unique incorrect.")
        else:
            # 1. Préparation du tableau récapitulatif HTML
            if absents_choisis:
                tableau_html = """
                <table border='1' style='border-collapse: collapse; width: 100%;'>
                    <tr style='background-color: #f2f2f2;'>
                        <th>Nom & Prénom</th>
                        <th>Promotion</th>
                        <th>Groupe</th>
                        <th>Sous-groupe</th>
                        <th>Chargé de Matière</th>
                    </tr>
                """
                for etud in absents_choisis:
                    tableau_html += f"""
                    <tr>
                        <td style='padding: 8px;'>{etud}</td>
                        <td style='padding: 8px;'>{promo_sel}</td>
                        <td style='padding: 8px;'>{gr_sel}</td>
                        <td style='padding: 8px;'>{sg_sel}</td>
                        <td style='padding: 8px;'>{enseignant_sel}</td>
                    </tr>
                    """
                tableau_html += "</table>"
            else:
                tableau_html = "<p><i>Aucun étudiant absent pour cette séance.</i></p>"

            # 2. Construction du corps de l'email HTML
            corps_html = f"""
            <html>
            <body>
                <h2>RAPPORT DE SÉANCE D'ASSIDUITÉ</h2>
                <p><b>Plateforme :</b> {TITRE_PLATEFORME}</p>
                <hr>
                <p><b>Enseignant :</b> {enseignant_sel}<br>
                <b>Matière :</b> {matiere_sel}<br>
                <b>Date :</b> {date_s}</p>
                
                <h3>Tableau récapitulatif des absences :</h3>
                {tableau_html}
                
                <p><b>Observations :</b> {obs}</p>
                <p><b>Signé par :</b> {sign}</p>
                <br>
                <small>Rapport généré automatiquement le {datetime.now().strftime('%d/%m/%Y %H:%M')}</small>
            </body>
            </html>
            """

            # 3. Liste des destinataires ordonnée
            destinataires = [EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email'], EMAIL_ADMIN_TECH]
            if 'email_resp' in locals(): destinataires.append(email_resp)
            destinataires = list(dict.fromkeys([d for d in destinataires if "@" in str(d)])) # Uniques

            with st.spinner("Envoi hiérarchique en cours..."):
                ok, error = send_html_report(destinataires, f"ABSENCES : {promo_sel} - {enseignant_sel}", corps_html)
                if ok:
                    st.success(f"✅ Rapport envoyé au Chef de Dept, Adjoint et Enseignant.")
                    st.balloons()
                else:
                    st.error(f"❌ Erreur : {error}")

with tab_hist:
    st.write("Historique bientôt disponible.")
