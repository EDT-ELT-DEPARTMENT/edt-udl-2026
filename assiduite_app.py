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
st.set_page_config(page_title="Gestion EDT UDL", layout="wide")

# Titre officiel
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
    st.error("⚠️ Erreur de configuration Supabase. Vérifiez vos secrets.")
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
    df_e = pd.read_excel(FICHIER_EDT)
    df_s = pd.read_excel(FICHIER_ETUDIANTS)
    df_staff = pd.read_excel(FICHIER_STAFF)
    # Nettoyage des colonnes
    for df in [df_e, df_s, df_staff]:
        df.columns = [str(c).strip() for c in df.columns]
    return df_e, df_s, df_staff

# --- 4. AUTHENTIFICATION ---
df_edt, df_etudiants, df_staff = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if "maintenance_mode" not in st.session_state:
    st.session_state["maintenance_mode"] = False

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_perdu = st.tabs(["🔐 Connexion", "📝 Inscription", "🔑 Code oublié ?"])
    
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
        st.info("Récupération automatique des données depuis le fichier Staff")
        # On concatène Nom et Prénom pour la sélection
        df_staff['Full_Staff'] = df_staff['NOM'].astype(str) + " " + df_staff['PRÉNOM'].astype(str)
        choix_staff = st.selectbox("Sélectionnez votre nom complet :", sorted(df_staff['Full_Staff'].unique()))
        
        # Extraction des infos auto
        infos_perso = df_staff[df_staff['Full_Staff'] == choix_staff].iloc[0]
        
        st.write(f"**Qualité :** {infos_perso['Qualité']} | **Grade :** {infos_perso['Grade']}")
        
        new_mail = st.text_input("Email (Identifiant) :", value=str(infos_perso['Email']))
        new_pass = st.text_input("Créer votre Code Unique :", type="password")
        
        if st.button("Valider l'inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": new_mail,
                    "password_hash": hash_pw(new_pass),
                    "nom_officiel": str(infos_perso['NOM']),
                    "statut_enseignant": str(infos_perso['Qualité']),
                    "grade_enseignant": str(infos_perso['Grade']),
                    "tel_enseignant": str(infos_perso['N°/TEL'])
                }).execute()
                st.success("Compte créé ! Veuillez vous connecter.")
            except Exception as e:
                st.error(f"Erreur : Email déjà utilisé ou problème réseau ({e}).")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<h4 style='text-align:center; color:#003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

is_admin = (user['email'] == EMAIL_ADMIN_TECH)

# BARRE LATÉRALE
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/fr/b/be/Logo_UDL_SBA.png", width=100) # Optionnel
    st.markdown(f"👤 **Enseignant :**\n{user['nom_officiel']}")
    st.markdown(f"🎓 **Grade :** {user.get('grade_enseignant', 'N/A')}")
    st.markdown(f"🏷️ **Statut :** {user.get('statut_enseignant', 'N/A')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ ADMIN")
        enseignant_sel = st.selectbox("Vue Admin - Enseignant :", sorted(df_edt['Enseignants'].unique()))
        
        if st.button("🚨 Vider les Archives"):
            st.session_state["reset_confirm"] = True
        if st.session_state.get("reset_confirm"):
            pw_r = st.text_input("Code Admin pour RESET :", type="password")
            if st.button("CONFIRMER SUPPRESSION"):
                if hash_pw(pw_r) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base vidée.")
                    st.rerun()
    else:
        enseignant_sel = user['nom_officiel']

# MAINTENANCE
if st.session_state["maintenance_mode"] and not is_admin:
    st.warning("⚠️ Plateforme en maintenance.")
    st.stop()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

# --- ONGLET 1 : SAISIE ---
with tab_saisie:
    c_cat, c_reg, c_date = st.columns(3)
    cat_seance = c_cat.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    regime_heure = c_reg.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_seance = c_date.date_input("📅 Date réelle :")

    c1, c2 = st.columns(2)
    promo_sel = c1.selectbox("🎓 Promotion :", sorted(df_edt[df_edt['Enseignants'].str.contains(str(user['nom_officiel']), na=False)]['Promotion'].unique()) if not is_admin else sorted(df_edt['Promotion'].unique()))
    matiere_sel = c2.selectbox("📖 Matière :", sorted(df_edt[(df_edt['Enseignants'].str.contains(str(user['nom_officiel']), na=False)) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique()) if not is_admin else sorted(df_edt['Enseignements'].unique()))

    # Infos EDT
    res_s = df_edt[(df_edt['Enseignements'] == matiere_sel) & (df_edt['Promotion'] == promo_sel)]
    horaire_v = res_s.iloc[0]['Horaire'] if not res_s.empty else "N/A"
    jour_v = res_s.iloc[0]['Jours'] if not res_s.empty else "N/A"
    lieu_v = res_s.iloc[0]['Lieu'] if not res_s.empty else "N/A"
    
    st.info(f"📍 Lieu: {lieu_v} | 🕒 Horaire: {horaire_v} | 🗓️ Jour prévu: {jour_v}")

    st.markdown("### 📈 Appel")
    df_p = df_etudiants[df_etudiants['Promotion'] == promo_sel]
    cg, csg = st.columns(2)
    gr_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["-"])
    df_g = df_p[df_p['Groupe'] == gr_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["-"])

    abs_collective = st.checkbox("🚩 ABSENCE COLLECTIVE")
    df_f = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_f['Full'] = df_f['Nom'].astype(str) + " " + df_f['Prénom'].astype(str)
    
    if abs_collective:
        absents = df_f['Full'].tolist()
        st.warning(f"⚠️ {len(absents)} étudiants absents.")
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
                        "matiere": matiere_sel, "enseignant": user['nom_officiel'],
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
                    
                    if not abs_collective and etudiant_note != "Aucun" and etudiant_note not in absents:
                        row_n = meta_data.copy()
                        row_n.update({"etudiant_nom": etudiant_note, "note_evaluation": note_val, "absence_collective": False})
                        supabase.table("archives_absences").insert(row_n).execute()

                    # Rapport HTML
                    mail_html = f"""
                    <div style="font-family: Arial; border: 2px solid #003366; padding: 15px; border-radius: 10px;">
                        <h2 style="color: #003366; text-align: center; border-bottom: 2px solid #003366;">RAPPORT DE SÉANCE</h2>
                        <p><b>Enseignant :</b> {user['nom_officiel']} ({user.get('grade_enseignant')})</p>
                        <p><b>Qualité :</b> {user.get('statut_enseignant')}</p>
                        <p><b>Régime :</b> {regime_heure} | <b>Séance :</b> {cat_seance}</p>
                        <p><b>Date :</b> {date_seance} | <b>Horaire :</b> {horaire_v} | <b>Lieu :</b> {lieu_v}</p>
                        <p><b>Nombre d'absents :</b> {len(absents)}</p>
                        <p><b>Note attribuée :</b> {note_val} à {etudiant_note}</p>
                        <p><b>Observations :</b> {obs}</p>
                        <p style="text-align: right;"><b>Signé numériquement :</b> {sign}</p>
                    </div>
                    """
                    send_mail([EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']], f"[{cat_seance}] {promo_sel} - {user['nom_officiel']}", mail_html, is_html=True)
                    st.success("✅ Rapport envoyé !")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.error("Code Unique incorrect.")

# --- ONGLET 2 : ARCHIVES ---
with tab_hist:
    st.markdown("### 📋 Historique")
    try:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data:
            df_arc = pd.DataFrame(res.data)
            st.dataframe(df_arc[['date_seance', 'enseignant', 'statut_enseignant', 'grade_enseignant', 'matiere', 'regime_heure', 'etudiant_nom', 'note_evaluation']], use_container_width=True)
            buf = io.BytesIO()
            df_arc.to_excel(buf, index=False)
            st.download_button("📊 Exporter Excel", buf.getvalue(), "Archives_Electrotech_S2_2026.xlsx")
    except:
        st.info("Aucune archive.")

if st.sidebar.button("🚪 Déconnexion"):
    st.session_state["user_data"] = None
    st.rerun()
