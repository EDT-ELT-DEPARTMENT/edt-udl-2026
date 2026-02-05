import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import random
import string
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Gestion Électrotechnique UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 EMAILS ADMINISTRATION
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP (Gmail)
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Configuration Supabase manquante dans les Secrets.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_mail(destinataire, subject, body, is_html=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT UDL <{EMAIL_SENDER}>"
        msg['To'] = destinataire if isinstance(destinataire, str) else ", ".join(destinataire)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
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
                df[col] = df[col].astype(str).str.strip()
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur Excel : {e}")
        st.stop()

# --- 4. CHARGEMENT DONNÉES ---
df_edt, df_etudiants, df_staff = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None
if "maintenance_mode" not in st.session_state:
    st.session_state["maintenance_mode"] = False

# --- 5. AUTHENTIFICATION & RÉCUPÉRATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Mot de passe oublié"])
    
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

    with t_signup:
        df_staff['Nom_Prenom'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Sélectionnez votre identité :", sorted(df_staff['Nom_Prenom'].unique()))
        info = df_staff[df_staff['Nom_Prenom'] == choix_nom].iloc[0]
        
        st.info(f"Détails trouvés : Grade: {info['Grade']} | Statut: {info['Qualité']}")
        reg_mail = st.text_input("Confirmez l'Email :", value=info['Email'])
        reg_pass = st.text_input("Créez votre Code Unique :", type="password")
        
        if st.button("Créer mon compte"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, 
                    "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info['NOM'],
                    "prenom_officiel": info['PRÉNOM'],
                    "statut_enseignant": info['Qualité'],
                    "grade_enseignant": info['Grade'],
                    "tel_enseignant": str(info['N°/TEL'])
                }).execute()
                st.success("Compte créé avec succès !")
            except:
                st.error("Erreur : Ce compte existe déjà ou l'email est utilisé.")

    with t_forgot:
        st.subheader("Récupération de compte")
        email_forgot = st.text_input("Entrez votre email inscrit :")
        if st.button("Envoyer un nouveau code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_forgot).execute()
            if res.data:
                new_pass = ''.join(random.choices(string.digits, k=6))
                new_hash = hash_pw(new_pass)
                supabase.table("enseignants_auth").update({"password_hash": new_hash}).eq("email", email_forgot).execute()
                
                body = f"Votre nouveau Code Unique temporaire est : {new_pass}\nVeuillez le changer après connexion."
                if send_mail(email_forgot, "Récupération Code Unique - UDL", body):
                    st.success("Un nouveau code a été envoyé à votre adresse email.")
                else:
                    st.error("Erreur lors de l'envoi de l'email.")
            else:
                st.error("Email non trouvé dans la base.")
    st.stop()

# --- 6. GESTION MAINTENANCE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

if st.session_state["maintenance_mode"] and not is_admin:
    st.warning("🚧 Plateforme en maintenance. Merci de votre patience.")
    st.stop()

# --- 7. INTERFACE PRINCIPALE ---
st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    # Affichage NOM + PRÉNOM
    nom_complet = f"{user.get('nom_officiel', '')} {user.get('prenom_officiel', '')}"
    st.markdown(f"**Enseignant :** {nom_complet}")
    st.markdown(f"**Grade :** {user.get('grade_enseignant', 'N/A')}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'N/A')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        enseignant_sel = st.selectbox("Vue Admin - Enseignant :", sorted(df_edt['Enseignants'].unique()))
        
        if st.checkbox("⚙️ Mode Maintenance"):
            if st.button("CONFIRMER ÉTAT"):
                st.session_state["maintenance_mode"] = not st.session_state["maintenance_mode"]
                st.rerun()
        
        st.divider()
        if st.button("🚨 Reset Base de Données"):
            st.session_state["reset_db"] = True
        if st.session_state.get("reset_db"):
            pw_adm = st.text_input("Code Admin pour RESET :", type="password")
            if st.button("VALIDER SUPPRESSION"):
                if hash_pw(pw_adm) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Archives vidées.")
                    st.session_state["reset_db"] = False
    else:
        enseignant_sel = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

with tab_saisie:
    # Infos Séance
    c_cat, c_reg, c_date = st.columns(3)
    cat_seance = c_cat.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    regime_heure = c_reg.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_seance = c_date.date_input("📅 Date réelle :")

    c1, c2 = st.columns(2)
    # Filtrage précis selon le nom (supporte le nom partiel ou complet dans l'EDT)
    mask = df_edt['Enseignants'].str.contains(enseignant_sel, na=False, case=False)
    list_p = sorted(df_edt[mask]['Promotion'].unique())
    promo_sel = c1.selectbox("🎓 Promotion :", list_p if list_p else sorted(df_edt['Promotion'].unique()))
    
    list_m = sorted(df_edt[mask & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
    matiere_sel = c2.selectbox("📖 Matière :", list_m if list_m else ["-"])

    # Récupération EDT
    res_s = df_edt[(df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    horaire_v, jour_v, lieu_v = ("N/A", "N/A", "N/A")
    if not res_s.empty:
        horaire_v, jour_v, lieu_v = res_s.iloc[0]['Horaire'], res_s.iloc[0]['Jours'], res_s.iloc[0]['Lieu']
        st.info(f"📍 Lieu : **{lieu_v}** | 🕒 Horaire : **{horaire_v}** | 🗓️ Jour prévu : **{jour_v}**")

    st.markdown("---")
    st.markdown("### 📈 Appel & Participation")
    
    # Statistiques numériques
    df_promo = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_promo['Groupe'].unique()) if not df_promo.empty else ["G1"])
    df_g = df_promo[df_promo['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["SG11"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", f"{len(df_promo)} étu.")
    m2.metric(f"Effectif Groupe {gr_sel}", f"{len(df_g)} étu.")
    m3.metric(f"Effectif Sous-G {sg_sel}", f"{len(df_g[df_g['Sous groupe'] == sg_sel])} étu.")

    # Liste Appel
    df_appel = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    
    abs_coll = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")
    
    if abs_coll:
        absents = df_appel['Full'].tolist()
        st.error(f"⚠️ {len(absents)} étudiants signalés absents.")
    else:
        absents = st.multiselect("❌ Liste des Absents :", options=df_appel['Full'].tolist())
        etud_note = st.selectbox("Étudiant à noter :", ["Aucun"] + df_appel['Full'].tolist())
        val_note = st.text_input("Note/Bonus :", value="0")

    obs = st.text_area("🗒️ Observations :")
    sign = st.text_input("✍️ Signature :", value=f"{user['nom_officiel']} {user.get('prenom_officiel', '')}")
    code_f = st.text_input("🔑 Code Unique :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_f) == user['password_hash']:
            with st.spinner("Archivage..."):
                try:
                    meta = {
                        "promotion": promo_sel, "groupe": gr_sel, "sous_groupe": sg_sel,
                        "matiere": matiere_sel, "enseignant": nom_complet,
                        "statut_enseignant": user.get('statut_enseignant'),
                        "grade_enseignant": user.get('grade_enseignant'),
                        "date_seance": str(date_seance), "horaire": horaire_v,
                        "lieu_seance": lieu_v, "categorie_seance": cat_seance, "regime_heure": regime_heure
                    }
                    for etud in absents:
                        row = meta.copy()
                        row.update({"etudiant_nom": etud, "note_evaluation": "ABS"})
                        supabase.table("archives_absences").insert(row).execute()
                    
                    if not abs_coll and etud_note != "Aucun":
                        row_n = meta.copy()
                        row_n.update({"etudiant_nom": etud_note, "note_evaluation": val_note})
                        supabase.table("archives_absences").insert(row_n).execute()

                    st.success("✅ Données archivées !")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur technique : {e}")
        else:
            st.error("Code Unique incorrect.")

with tab_hist:
    st.markdown("### 📜 Consultation des Archives")
    res = supabase.table("archives_absences").select("*").execute()
    if res.data:
        df_arc = pd.DataFrame(res.data)
        st.dataframe(df_arc, use_container_width=True)
        
        buf = io.BytesIO()
        df_arc.to_excel(buf, index=False)
        st.download_button("📊 Exporter vers Excel", buf.getvalue(), "Archives_EDT_2026.xlsx")
