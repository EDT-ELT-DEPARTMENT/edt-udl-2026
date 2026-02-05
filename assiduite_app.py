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

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 EMAILS ADMINISTRATION
EMAIL_CHEF_DEPT = "milouafarid@gmail.com"
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
    st.error("⚠️ Configuration Supabase manquante dans les Secrets.")
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
        st.error(f"Erreur fichiers Excel : {e}")
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

if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- 4. AUTHENTIFICATION ---
if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié"])
    
    with t_login:
        email_log = st.text_input("Email :", key="login_e")
        pass_log = st.text_input("Code Unique :", type="password", key="login_p")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_log).eq("password_hash", hash_pw(pass_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

    with t_signup:
        df_staff['Full'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full'].unique()))
        info_s = df_staff[df_staff['Full'] == choix].iloc[0]
        st.info(f"Profil : {info_s['NOM']} | Grade : {info_s['Grade']}")
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Code Unique :", type="password")
        if st.button("Créer compte"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_mail, "password_hash": hash_pw(reg_pass),
                    "nom_officiel": info_s['NOM'], "prenom_officiel": info_s['PRÉNOM'],
                    "statut_enseignant": info_s['Qualité'], "grade_enseignant": info_s['Grade']
                }).execute()
                st.success("Compte créé !")
            except:
                st.error("Email déjà utilisé.")

    with t_forgot:
        f_email = st.text_input("Email oublié :")
        if st.button("Envoyer code"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_mail(f_email, "Code UDL", f"Votre nouveau code : {new_c}")
                st.success("Code envoyé par email.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    current_grade = get_live_grade(user['nom_officiel'], user['email'])
    st.markdown(f"**Enseignant :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {current_grade}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (Filtrer EDT) :", sorted(df_edt['Enseignants'].unique()))
    else:
        enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

tab_saisie, tab_hist = st.tabs(["📝 Saisie Séance", "📜 Archive & Export"])

with tab_saisie:
    # 1. Infos de base
    c1, c2, c3 = st.columns(3)
    cat_seance = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    regime_seance = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_seance = c3.date_input("📅 Date réelle :", value=datetime.now())

    # 2. Promotion & Matière
    cp, cm = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    list_promos = sorted(df_edt[mask]['Promotion'].unique())
    p_sel = cp.selectbox("🎓 Promotion :", list_promos if list_promos else sorted(df_edt['Promotion'].unique()))
    
    list_mats = sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique())
    m_sel = cm.selectbox("📖 Matière :", list_mats if list_mats else ["-"])

    st.markdown("---")
    st.markdown("### 📈 Appel & Notation")

    # 3. Effectifs
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    df_g = df_p_full[df_p_full['Groupe'] == g_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["SG1"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_p_full))
    m2.metric(f"Groupe {g_sel}", len(df_g))
    m3.metric(f"S-Groupe {sg_sel}", len(df_g[df_g['Sous groupe'] == sg_sel]))

    # 4. Listes pour l'Appel
    df_appel = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    liste_noms = df_appel['Full'].tolist()

    col_abs, col_note = st.columns(2)
    with col_abs:
        abs_coll = st.checkbox("🚩 SIGNALER ABSENCE COLLECTIVE")
        absents_choisis = liste_noms if abs_coll else st.multiselect("❌ Sélectionner les Absents :", options=liste_noms)
    with col_note:
        etudiant_a_noter = st.selectbox("📝 Noter un étudiant (Bonus/Note) :", ["Aucun"] + liste_noms)
        valeur_note = st.text_input("Valeur (ex: +1, 15/20) :", "0")

    obs_txt = st.text_area("🗒️ Observations / Chapitre traité :")
    signature = st.text_input("✍️ Signature :", value=f"{current_grade} {user['nom_officiel']}")
    code_valid = st.text_input("🔑 Code Unique pour archivage :", type="password")

    if st.button("🚀 VALIDER ET ENVOYER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_valid) == user['password_hash']:
            with st.spinner("Archivage en cours..."):
                try:
                    # 1. PRÉPARATION DES DONNÉES (Structure souple)
                    # On crée d'abord le dictionnaire avec toutes les colonnes souhaitées
                    data_full = {
                        "promotion": p_sel, 
                        "matiere": m_sel, 
                        "enseignant": f"{current_grade} {user['nom_officiel']}",
                        "date_seance": str(date_seance), 
                        "categorie_seance": cat_seance,
                        "regime_heure": regime_seance,
                        "observations": obs_txt
                    }

                    # Fonction pour insérer intelligemment (ignore les colonnes manquantes en DB)
                    def robust_insert(base_meta, nom_etudiant, note):
                        row = base_meta.copy()
                        row.update({"etudiant_nom": nom_etudiant, "note_evaluation": note})
                        
                        try:
                            # Essai d'insertion complète
                            supabase.table("archives_absences").insert(row).execute()
                        except:
                            # Si échec, on réduit aux colonnes "SÉCURISÉES" qui existent forcément
                            row_safe = {
                                "promotion": row["promotion"],
                                "matiere": row["matiere"],
                                "enseignant": row["enseignant"],
                                "date_seance": row["date_seance"],
                                "etudiant_nom": row["etudiant_nom"],
                                "note_evaluation": row["note_evaluation"]
                            }
                            supabase.table("archives_absences").insert(row_safe).execute()

                    # 2. ENREGISTREMENT
                    for ab in absents_choisis:
                        robust_insert(data_full, ab, "ABSENCE")
                    
                    if etudiant_a_noter != "Aucun":
                        robust_insert(data_full, etudiant_a_noter, valeur_note)

                    # 3. EMAIL (Lui, il contient TOUT car il ne dépend pas de Supabase)
                    corps_html = f"""
                    <div style="font-family: Arial; border: 1px solid #003366; padding: 15px;">
                        <h2 style="color: #003366;">Rapport de Séance - UDL SBA</h2>
                        <p><b>Enseignant :</b> {current_grade} {user['nom_officiel']}</p>
                        <p><b>Matière :</b> {m_sel} ({cat_seance})</p>
                        <p><b>Régime :</b> {regime_seance}</p>
                        <p><b>Date :</b> {date_seance}</p>
                        <hr>
                        <p><b>Absents :</b> {", ".join(absents_choisis) if absents_choisis else "Aucun"}</p>
                        <p><b>Note :</b> {valeur_note} pour {etudiant_a_noter}</p>
                        <p><b>Observations :</b> {obs_txt}</p>
                    </div>
                    """
                    send_mail([EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']], 
                              f"Rapport {m_sel} - {user['nom_officiel']}", corps_html, is_html=True)

                    st.success("✅ Rapport envoyé par email et archivé (champs additionnels ignorés si absents en DB).")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur technique : {e}")
        else:
            st.error("Code Unique incorrect.")

with tab_hist:
    st.markdown("### 📜 Archives")
    res_arc = supabase.table("archives_absences").select("*").execute()
    if res_arc.data:
        st.dataframe(pd.DataFrame(res_arc.data), use_container_width=True)
