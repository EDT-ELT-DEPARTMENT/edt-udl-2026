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
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_CHEF_ADJOINT = "nass_ka@yahoo.fr"
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

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
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    for df in [df_e, df_s]:
        df.columns = [str(c).strip() for c in df.columns]
    return df_e, df_s

# --- 4. CHARGEMENT ET AUTHENTIFICATION ---
df_edt, df_etudiants = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# Initialisation de l'état de maintenance
if "maintenance_mode" not in st.session_state:
    st.session_state["maintenance_mode"] = False

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
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<h3 style='text-align:center; color:#003366;'>{TITRE_PLATEFORME}</h3>", unsafe_allow_html=True)

# BARRE LATÉRALE ET MODE MAINTENANCE
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

with st.sidebar:
    st.markdown(f"**Utilisateur :**\n{user['nom_officiel']}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ Mode Administrateur")
        enseignant_sel = st.selectbox("👤 Sélectionner l'Enseignant :", sorted(df_edt['Enseignants'].unique()))
        
        # BOUTON MAINTENANCE AVEC CONFIRMATION
        st.divider()
        st.warning("⚙️ ZONE TECHNIQUE")
        if not st.session_state["maintenance_mode"]:
            if st.button("Activer la Maintenance"):
                st.session_state["maintenance_confirm"] = True
            
            if st.session_state.get("maintenance_confirm"):
                st.error("Confirmer l'arrêt des saisies ?")
                if st.button("OUI, ACTIVER MAINTENANT"):
                    st.session_state["maintenance_mode"] = True
                    st.session_state["maintenance_confirm"] = False
                    st.rerun()
        else:
            st.error("🔴 MAINTENANCE ACTIVE")
            if st.button("Désactiver la Maintenance"):
                st.session_state["maintenance_mode"] = False
                st.rerun()
    else:
        enseignant_sel = st.selectbox("👤 Enseignant :", [user['nom_officiel']], disabled=True)

# LOGIQUE D'AFFICHAGE SELON MAINTENANCE
if st.session_state["maintenance_mode"] and not is_admin:
    st.warning("⚠️ La plateforme est actuellement en maintenance pour mise à jour. Les saisies sont temporairement désactivées. Merci de votre patience.")
    st.stop()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive des Absences & Notes"])

# --- ONGLET 1 : SAISIE ---
with tab_saisie:
    if st.session_state["maintenance_mode"]:
        st.error("🛠️ MODE MAINTENANCE : Seul l'administrateur peut tester les saisies.")

    c_cat, c_type, c_date = st.columns(3)
    cat_seance = c_cat.selectbox("🏷️ Rapport de séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    type_seance = c_type.selectbox("📂 État de la séance :", ["Séance Normale", "Séance de Rattrapage"])
    date_seance = c_date.date_input("📅 Date réelle :")

    c1, c2 = st.columns(2)
    promo_sel = c1.selectbox("🎓 Promotion :", sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique()))
    matiere_sel = c2.selectbox("📖 Matière :", sorted(df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique()))

    res_s = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    horaire_v = res_s.iloc[0]['Horaire'] if not res_s.empty else "N/A"
    jour_v = res_s.iloc[0]['Jours'] if not res_s.empty else "N/A"
    lieu_v = res_s.iloc[0]['Lieu'] if not res_s.empty else "N/A"
    
    st.info(f"📅 **EDT :** {jour_v} | 🕒 **Horaire :** {horaire_v} | 📍 **Lieu :** {lieu_v}")

    st.markdown("---")
    st.markdown("### 📈 Gestion des Étudiants")
    
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    df_g = df_p[df_p['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")

    df_f = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_f['Full'] = df_f['Nom'].astype(str) + " " + df_f['Prénom'].astype(str)
    
    if abs_collective:
        absents = df_f['Full'].tolist()
        st.warning(f"⚠️ {len(absents)} étudiants marqués absents.")
        note_val = "0"
    else:
        absents = st.multiselect("❌ Sélectionner les ABSENTS :", options=df_f['Full'].tolist())
        st.markdown("#### ⭐ Participation / Note d'examen")
        etudiant_note = st.selectbox("Sélectionner l'étudiant à noter :", ["Aucun"] + df_f['Full'].tolist())
        note_val = st.text_input("Saisir la note (Ex: 15/20) :", value="0")

    obs = st.text_area("🗒️ Observations :")
    sign = st.text_input("✍️ Signature :", value=user['nom_officiel'])
    code_f = st.text_input("🔑 Code Unique :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_f) == user['password_hash']:
            with st.spinner("Archivage..."):
                try:
                    # 1. ARCHIVAGE ABSENCES
                    for etud in absents:
                        supabase.table("archives_absences").insert({
                            "etudiant_nom": etud, "promotion": promo_sel, "groupe": gr_sel,
                            "sous_groupe": sg_sel, "matiere": matiere_sel, "enseignant": enseignant_sel,
                            "date_seance": str(date_seance), "horaire": horaire_v, "jour_nom": jour_v,
                            "lieu_seance": lieu_v, "type_seance": type_seance, "categorie_seance": cat_seance,
                            "absence_collective": abs_collective, "note_evaluation": "ABS"
                        }).execute()
                    
                    # 2. ARCHIVAGE NOTE
                    if not abs_collective and etudiant_note != "Aucun" and etudiant_note not in absents:
                        supabase.table("archives_absences").insert({
                            "etudiant_nom": etudiant_note, "promotion": promo_sel, "groupe": gr_sel,
                            "sous_groupe": sg_sel, "matiere": matiere_sel, "enseignant": enseignant_sel,
                            "date_seance": str(date_seance), "horaire": horaire_v, "jour_nom": jour_v,
                            "lieu_seance": lieu_v, "type_seance": type_seance, "categorie_seance": cat_seance,
                            "absence_collective": False, "note_evaluation": note_val
                        }).execute()

                    # 3. HTML EMAIL
                    mail_html = f"""
                    <div style="font-family: Arial; border: 1px solid #003366; padding: 15px; border-radius: 8px;">
                        <h2 style="color: #003366;">Rapport de Séance : {cat_seance}</h2>
                        <p><b>Enseignant :</b> {enseignant_sel}</p>
                        <p><b>Matière :</b> {matiere_sel}</p>
                        <p><b>Date :</b> {date_seance} ({jour_v})</p>
                        <p><b>Lieu :</b> {lieu_v}</p>
                        <p><b>Absents :</b> {len(absents)}</p>
                        <p><b>Observations :</b> {obs}</p>
                        <hr>
                        <p>Signé : {sign}</p>
                    </div>
                    """
                    destinataires = [EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']]
                    if send_mail(destinataires, f"[{cat_seance}] {promo_sel} - {enseignant_sel}", mail_html, is_html=True):
                        st.success("✅ Rapport envoyé !")
                        st.balloons()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.error("Code Unique incorrect.")

# --- ONGLET 2 : ARCHIVES ---
with tab_hist:
    st.markdown("### 📋 Historique récapitulatif")
    res = supabase.table("archives_absences").select("*").execute()
    if res.data:
        df_arc = pd.DataFrame(res.data)
        cols_display = ['date_seance', 'jour_nom', 'horaire', 'etudiant_nom', 'promotion', 'categorie_seance', 'note_evaluation', 'lieu_seance']
        st.dataframe(df_arc[cols_display], use_container_width=True)
        
        buf = io.BytesIO()
        df_arc.to_excel(buf, index=False)
        st.download_button("📊 Télécharger EXCEL", buf.getvalue(), "Archives_Assiduite_UDL.xlsx")

if st.sidebar.button("🚪 Déconnexion"):
    st.session_state["user_data"] = None
    st.rerun()
