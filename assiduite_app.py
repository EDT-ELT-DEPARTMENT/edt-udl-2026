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

# Titre officiel immuable
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 EMAILS ADMINISTRATION
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_CHEF_ADJOINT = "nass_ka@yahoo.fr"
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
    st.error("⚠️ Erreur : Configuration Supabase introuvable dans les Secrets.")
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
    # Correction de la coquille ici : FICHIER_ETUDIANTS au lieu de FICHICHIER
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    df_staff = pd.read_excel(FICHIER_STAFF)
    
    # Nettoyage des données pour éviter les erreurs de correspondance
    for df in [df_e, df_s, df_staff]:
        df.columns = [str(c).strip() for c in df.columns]
        for col in df.select_dtypes(include=['object']):
            df[col] = df[col].astype(str).str.strip()
    return df_e, df_s, df_staff

# --- 4. CHARGEMENT DES DONNÉES ---
df_edt, df_etudiants, df_staff = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if "maintenance_mode" not in st.session_state:
    st.session_state["maintenance_mode"] = False

# --- 5. AUTHENTIFICATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>{TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup = st.tabs(["🔐 Connexion", "📝 Inscription Enseignant"])
    
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
        st.info("Sélectionnez votre nom pour récupérer vos informations (Grade, Qualité, etc.)")
        df_staff['Full_Name'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Votre Nom et Prénom :", sorted(df_staff['Full_Name'].unique()))
        
        info = df_staff[df_staff['Full_Name'] == choix_nom].iloc[0]
        st.write(f"📊 **Statut détecté :** {info['Qualité']} | **Grade :** {info['Grade']}")
        
        reg_mail = st.text_input("Confirmez votre Email :", value=info['Email'])
        reg_pass = st.text_input("Créez votre Code Unique :", type="password")
        
        if st.button("Valider l'inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail,
                    "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info['NOM'],
                    "statut_enseignant": info['Qualité'],
                    "grade_enseignant": info['Grade'],
                    "tel_enseignant": info['N°/TEL']
                }).execute()
                st.success("Inscription validée ! Vous pouvez vous connecter.")
            except:
                st.error("Erreur : Cet email existe déjà dans la base.")
    st.stop()

# --- 6. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# BARRE LATÉRALE
with st.sidebar:
    st.markdown(f"👤 **Enseignant :** {user['nom_officiel']}")
    st.markdown(f"🎓 **Grade :** {user.get('grade_enseignant', 'N/A')}")
    st.markdown(f"🏷️ **Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        enseignant_sel = st.selectbox("Vue Admin - Enseignant :", sorted(df_edt['Enseignants'].unique()))
        
        # BOUTON RESET (DANS SIDEBAR POUR ADMIN)
        if st.button("🚨 Vider les Archives"):
            st.session_state["reset_confirm"] = True
        
        if st.session_state.get("reset_confirm"):
            st.warning("Action irréversible !")
            pw_check = st.text_input("Code Admin pour RESET :", type="password")
            if st.button("CONFIRMER LA SUPPRESSION"):
                if hash_pw(pw_check) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Archives vidées.")
                    st.session_state["reset_confirm"] = False
                    st.rerun()
    else:
        enseignant_sel = user['nom_officiel']

    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

# --- ONGLET 1 : SAISIE ---
with tab_saisie:
    c_cat, c_reg, c_date = st.columns(3)
    cat_seance = c_cat.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    regime_heure = c_reg.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_seance = c_date.date_input("📅 Date réelle :")

    c1, c2 = st.columns(2)
    # Filtrage des promotions où l'enseignant intervient
    list_promos = sorted(df_edt[df_edt['Enseignants'].str.contains(enseignant_sel, na=False)]['Promotion'].unique())
    promo_sel = c1.selectbox("🎓 Promotion :", list_promos if list_promos else sorted(df_edt['Promotion'].unique()))
    
    list_matieres = sorted(df_edt[(df_edt['Enseignants'].str.contains(enseignant_sel, na=False)) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique())
    matiere_sel = c2.selectbox("📖 Matière :", list_matieres if list_matieres else ["Aucune matière trouvée"])

    # Récupération données EDT
    res_s = df_edt[(df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    if not res_s.empty:
        horaire_v = res_s.iloc[0]['Horaire']
        jour_v = res_s.iloc[0]['Jours']
        lieu_v = res_s.iloc[0]['Lieu']
        st.info(f"📍 Lieu : **{lieu_v}** | 🕒 Horaire : **{horaire_v}** | 🗓️ Jour prévu : **{jour_v}**")
    else:
        horaire_v, jour_v, lieu_v = "N/A", "N/A", "N/A"

    st.markdown("---")
    st.markdown("### 📈 Appel & Participation")
    
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    df_g = df_p[df_p['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["SG11"])

    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE")
    df_f = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_f['Full'] = df_f['Nom'] + " " + df_f['Prénom']
    
    if abs_collective:
        absents = df_f['Full'].tolist()
        st.error(f"⚠️ {len(absents)} étudiants seront marqués absents.")
        note_val = "0"
    else:
        absents = st.multiselect("❌ Liste des Absents :", options=df_f['Full'].tolist())
        etudiant_note = st.selectbox("Étudiant à noter :", ["Aucun"] + df_f['Full'].tolist())
        note_val = st.text_input("Note/Bonus :", value="0")

    obs = st.text_area("🗒️ Observations :")
    sign = st.text_input("✍️ Signature :", value=user['nom_officiel'])
    code_f = st.text_input("🔑 Code Unique :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_f) == user['password_hash']:
            with st.spinner("Archivage..."):
                try:
                    meta_data = {
                        "promotion": promo_sel, "groupe": gr_sel, "sous_groupe": sg_sel,
                        "matiere": matiere_sel, "enseignant": enseignant_sel,
                        "statut_enseignant": user.get('statut_enseignant'),
                        "grade_enseignant": user.get('grade_enseignant'),
                        "date_seance": str(date_seance), "horaire": horaire_v, "jour_nom": jour_v,
                        "lieu_seance": lieu_v, "categorie_seance": cat_seance, "regime_heure": regime_heure,
                        "absence_collective": abs_collective
                    }

                    for etud in absents:
                        row = meta_data.copy()
                        row.update({"etudiant_nom": etud, "note_evaluation": "ABS"})
                        supabase.table("archives_absences").insert(row).execute()
                    
                    if not abs_collective and etudiant_note != "Aucun":
                        row_n = meta_data.copy()
                        row_n.update({"etudiant_nom": etudiant_note, "note_evaluation": note_val, "absence_collective": False})
                        supabase.table("archives_absences").insert(row_n).execute()

                    # Envoi Mail
                    mail_html = f"<h2>Rapport {cat_seance}</h2><p>Enseignant: {enseignant_sel}</p><p>Matière: {matiere_sel}</p>"
                    send_mail([EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']], f"[{cat_seance}] {promo_sel} - {enseignant_sel}", mail_html, is_html=True)
                    st.success("✅ Enregistré !")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur Supabase : {e}")
        else:
            st.error("Code incorrect.")

# --- ONGLET 2 : ARCHIVES ---
with tab_hist:
    st.markdown("### 📋 Historique")
    res = supabase.table("archives_absences").select("*").execute()
    if res.data:
        df_arc = pd.DataFrame(res.data)
        st.dataframe(df_arc, use_container_width=True)
        buf = io.BytesIO()
        df_arc.to_excel(buf, index=False)
        st.download_button("📊 Télécharger Excel", buf.getvalue(), "Archives_UDL_2026.xlsx")
