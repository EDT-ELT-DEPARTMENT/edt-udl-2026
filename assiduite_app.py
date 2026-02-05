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

# Titre officiel rappelé systématiquement
TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

# 📧 EMAILS ADMINISTRATION
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
EMAIL_CHEF_ADJOINT = "nass_ka@yahoo.fr"
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"

# 🔑 CONFIGURATION SMTP (GMAIL)
EMAIL_SENDER = "milouafarid@gmail.com"
EMAIL_PASSWORD = "kmtk zmkd kwpd cqzz" 

# --- 2. CONNEXION SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("⚠️ Erreur de secrets Supabase. Vérifiez votre configuration dans .streamlit/secrets.toml.")
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
    for df in [df_e, df_s]:
        df.columns = [str(c).strip() for c in df.columns]
    return df_e, df_s

# --- 4. CHARGEMENT ET AUTHENTIFICATION ---
df_edt, df_etudiants = load_data()

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if "maintenance_mode" not in st.session_state:
    st.session_state["maintenance_mode"] = False

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>{TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_perdu = st.tabs(["🔐 Connexion", "📝 Inscription Enseignant", "🔑 Code oublié ?"])
    
    with t_login:
        email_log = st.text_input("Email professionnel :", key="l_mail")
        pass_log = st.text_input("Code Unique :", type="password", key="l_pass")
        if st.button("Accéder à la plateforme", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

    with t_signup:
        st.info("Formulaire d'inscription pour les nouveaux enseignants")
        new_nom = st.selectbox("Sélectionnez votre nom (selon EDT) :", sorted(df_edt['Enseignants'].unique()))
        new_statut = st.radio("Statut de l'enseignant :", ["Permanent", "Vacataire"], horizontal=True)
        new_mail = st.text_input("Email (Identifiant) :")
        new_pass = st.text_input("Créer votre Code Unique :", type="password")
        if st.button("Valider l'inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": new_mail, 
                    "password_hash": hash_pw(new_pass), 
                    "nom_officiel": new_nom,
                    "statut_enseignant": new_statut
                }).execute()
                st.success("Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
            except:
                st.error("Erreur : Cet email est déjà utilisé.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

# BARRE LATÉRALE
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

with st.sidebar:
    st.markdown(f"👤 **Enseignant :**\n{user['nom_officiel']}")
    st.markdown(f"🏷️ **Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        enseignant_sel = st.selectbox("Choisir un Enseignant (Vue Admin) :", sorted(df_edt['Enseignants'].unique()))
        
        st.divider()
        st.warning("⚙️ MAINTENANCE")
        if not st.session_state["maintenance_mode"]:
            if st.button("Lancer Maintenance"):
                st.session_state["maintenance_confirm"] = True
            if st.session_state.get("maintenance_confirm"):
                if st.button("CONFIRMER LE VERROUILLAGE"):
                    st.session_state["maintenance_mode"] = True
                    st.session_state["maintenance_confirm"] = False
                    st.rerun()
        else:
            if st.button("Arrêter Maintenance"):
                st.session_state["maintenance_mode"] = False
                st.rerun()

        st.divider()
        st.error("🗑️ RESET DONNÉES")
        if st.button("Vider les Archives"):
            st.session_state["reset_confirm"] = True
        
        if st.session_state.get("reset_confirm"):
            code_reset = st.text_input("Code Admin requis :", type="password")
            if st.button("OUI, TOUT SUPPRIMER"):
                if hash_pw(code_reset) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.session_state["reset_confirm"] = False
                    st.success("Archives vidées.")
                    st.rerun()
    else:
        enseignant_sel = user['nom_officiel']

# BLOCAGE MAINTENANCE
if st.session_state["maintenance_mode"] and not is_admin:
    st.warning("⚠️ La plateforme est en maintenance. Revenez plus tard.")
    st.stop()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Historique Absences & Notes"])

# --- ONGLET 1 : SAISIE ---
with tab_saisie:
    # --- DÉTAILS DE LA SÉANCE ---
    c_cat, c_reg, c_date = st.columns(3)
    cat_seance = c_cat.selectbox("🏷️ Nature de la séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    regime_heure = c_reg.selectbox("⏳ Régime Horaire :", ["Charge Horaire (Normale)", "Heures Supplémentaires"])
    date_seance = c_date.date_input("📅 Date de la séance :")

    c1, c2 = st.columns(2)
    promo_sel = c1.selectbox("🎓 Promotion :", sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique()))
    matiere_sel = c2.selectbox("📖 Matière :", sorted(df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)]['Enseignements'].unique()))

    # Extraction des données EDT
    res_s = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Enseignements'] == matiere_sel)]
    horaire_v = res_s.iloc[0]['Horaire'] if not res_s.empty else "N/A"
    jour_v = res_s.iloc[0]['Jours'] if not res_s.empty else "N/A"
    lieu_v = res_s.iloc[0]['Lieu'] if not res_s.empty else "N/A"
    
    st.info(f"📍 **Lieu :** {lieu_v} | 🕒 **Horaire :** {horaire_v} | 🗓️ **Jour prévu :** {jour_v}")

    st.markdown("---")
    st.markdown("### 📈 Appel et Participation")
    
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
        st.warning(f"⚠️ {len(absents)} étudiants déclarés absents.")
        note_val = "0"
    else:
        absents = st.multiselect("❌ Liste des Absents :", options=df_f['Full'].tolist())
        st.markdown("#### ⭐ Note de participation ou Quiz")
        etudiant_note = st.selectbox("Étudiant à noter :", ["Aucun"] + df_f['Full'].tolist())
        note_val = st.text_input("Note ou Bonus :", value="0")

    obs = st.text_area("🗒️ Observations / Avancement :")
    sign = st.text_input("✍️ Signature :", value=user['nom_officiel'])
    code_f = st.text_input("🔑 Code Unique de validation :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_f) == user['password_hash']:
            with st.spinner("Enregistrement en cours..."):
                try:
                    # Données de base pour l'archivage
                    data_base = {
                        "promotion": promo_sel, "groupe": gr_sel, "sous_groupe": sg_sel,
                        "matiere": matiere_sel, "enseignant": enseignant_sel,
                        "statut_enseignant": user.get('statut_enseignant', 'Permanent'),
                        "date_seance": str(date_seance), "horaire": horaire_v, "jour_nom": jour_v,
                        "lieu_seance": lieu_v, "categorie_seance": cat_seance, "regime_heure": regime_heure,
                        "absence_collective": abs_collective
                    }

                    # Enregistrement des Absents
                    for etud in absents:
                        d_abs = data_base.copy()
                        d_abs.update({"etudiant_nom": etud, "note_evaluation": "ABS"})
                        supabase.table("archives_absences").insert(d_abs).execute()
                    
                    # Enregistrement de la Note
                    if not abs_collective and etudiant_note != "Aucun" and etudiant_note not in absents:
                        d_note = data_base.copy()
                        d_note.update({"etudiant_nom": etudiant_note, "note_evaluation": note_val, "absence_collective": False})
                        supabase.table("archives_absences").insert(d_note).execute()

                    # Rapport HTML pour Email
                    mail_html = f"""
                    <div style="font-family: Arial; border: 2px solid #003366; padding: 20px; border-radius: 10px;">
                        <h2 style="color: #003366; text-align: center;">Rapport de Séance : {cat_seance}</h2>
                        <hr>
                        <p><b>Enseignant :</b> {enseignant_sel} ({user.get('statut_enseignant', 'Permanent')})</p>
                        <p><b>Matière :</b> {matiere_sel} | <b>Promotion :</b> {promo_sel}</p>
                        <p><b>Régime :</b> <span style="color:blue;">{regime_heure}</span></p>
                        <p><b>Date :</b> {date_seance} | <b>Lieu :</b> {lieu_v} | <b>Horaire :</b> {horaire_v}</p>
                        <p><b>Étudiants absents :</b> {len(absents)}</p>
                        <p><b>Note participation :</b> {note_val} à {etudiant_note}</p>
                        <p><b>Observations :</b> {obs}</p>
                        <p style="text-align: right; font-weight: bold;">Signature : {sign}</p>
                    </div>
                    """
                    destinataires = [EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']]
                    if send_mail(destinataires, f"[{cat_seance}] {promo_sel} - {enseignant_sel}", mail_html, is_html=True):
                        st.success("✅ Rapport validé et transmis à l'administration !")
                        st.balloons()
                except Exception as e:
                    st.error(f"Erreur d'archivage : {e}")
        else:
            st.error("Code Unique invalide.")

# --- ONGLET 2 : ARCHIVES ---
with tab_hist:
    st.markdown("### 📋 Consultation des Archives")
    try:
        res = supabase.table("archives_absences").select("*").execute()
        if res.data:
            df_arc = pd.DataFrame(res.data)
            # Affichage sélectif pour la clarté
            cols_show = ['date_seance', 'enseignant', 'statut_enseignant', 'matiere', 'regime_heure', 'etudiant_nom', 'note_evaluation']
            st.dataframe(df_arc[cols_show], use_container_width=True)
            
            buf = io.BytesIO()
            df_arc.to_excel(buf, index=False)
            st.download_button("📊 Exporter la base vers EXCEL", buf.getvalue(), "Archives_Electrotech_2026.xlsx", use_container_width=True)
        else:
            st.info("Aucune donnée archivée pour le moment.")
    except:
        st.info("Initialisation de l'historique...")

if st.sidebar.button("🚪 Déconnexion"):
    st.session_state["user_data"] = None
    st.rerun()
