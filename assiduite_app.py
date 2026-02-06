import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import random
import string
import segno  # Bibliothèque pour la génération du QR Code
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
            except:
                st.error("Erreur : Email déjà utilisé.")

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
        st.subheader("👨‍🎓 Consultation d'Assiduité")
        st.info("Entrez vos informations pour consulter l'état de vos absences.")
        nom_search = st.text_input("Nom Complet (NOM PRÉNOM) :").upper().strip()
        if st.button("Afficher mon bilan personnel", use_container_width=True):
            if nom_search:
                res_st = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_search).execute()
                if res_st.data:
                    df_res = pd.DataFrame(res_st.data)
                    st.success(f"Bilan trouvé pour : {nom_search}")
                    # Filtrage pour l'étudiant : on ne montre que les colonnes pertinentes
                    df_display = df_res[['date_seance', 'matiere', 'enseignant', 'note_evaluation']].rename(columns={
                        'date_seance': 'Date', 'matiere': 'Matière', 'enseignant': 'Chargé du cours', 'note_evaluation': 'État'
                    })
                    st.table(df_display)
                else:
                    st.warning("Aucune absence trouvée ou nom non reconnu dans la base.")
            else:
                st.error("Veuillez saisir votre nom.")
    st.stop()

# --- 5. INTERFACE PRINCIPALE (ENSEIGNANT) ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 👤 Profil Enseignant")
    current_grade = get_live_grade(user['nom_officiel'], user['email'])
    st.markdown(f"**Enseignant :** {user['nom_officiel']}")
    st.markdown(f"**Grade :** {current_grade}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    
    # --- GÉNÉRATION DU QR CODE ---
    st.divider()
    st.markdown("### 📱 QR Code Étudiant")
    # Remplacez l'URL par l'adresse réelle de votre application une fois déployée
    app_url = "https://votre-app-udl.streamlit.app" 
    qr = segno.make(app_url)
    buffer_qr = io.BytesIO()
    qr.save(buffer_qr, kind='png', scale=5)
    st.image(buffer_qr.getvalue(), caption="Scan pour consulter les absences")
    st.caption("Faites scanner ce code aux étudiants en fin de séance.")
    
    st.divider()
    if is_admin:
        st.success("🛡️ MODE ADMIN")
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
        st.divider()
        st.warning("🚨 ZONE DANGEREUSE")
        if st.button("Vider les Archives"):
            st.session_state["confirm_reset"] = True
        
        if st.session_state.get("confirm_reset"):
            confirm_p = st.text_input("Confirmez avec votre code unique :", type="password")
            if st.button("OUI, TOUT SUPPRIMER"):
                if hash_pw(confirm_p) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base de données vidée.")
                    st.session_state["confirm_reset"] = False
                    st.rerun()
                else:
                    st.error("Code incorrect.")
    else:
        enseignant_vue = user['nom_officiel']

    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None
        st.rerun()

# --- ONGLETS ---
tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

with tab_saisie:
    # (Le reste du code de saisie reste identique à votre version)
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
    st.markdown("### 📈 Appel & Notation")
    
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    df_g = df_p_full[df_p_full['Groupe'] == g_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["SG1"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promotion", len(df_p_full))
    m2.metric(f"Groupe {g_sel}", len(df_g))
    m3.metric(f"S-Groupe {sg_sel}", len(df_g[df_g['Sous groupe'] == sg_sel]))

    df_appel = df_g[df_g['Sous groupe'] == sg_sel].copy()
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
            with st.spinner("Enregistrement..."):
                try:
                    meta = {"promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_grade} {user['nom_officiel']}", "date_seance": str(date_s)}
                    
                    def robust_insert(row):
                        row_full = row.copy()
                        row_full.update({"regime_heure": reg_s, "observations": obs_txt, "categorie_seance": cat_s})
                        try:
                            supabase.table("archives_absences").insert(row_full).execute()
                        except:
                            supabase.table("archives_absences").insert(row).execute()

                    for ab in absents_sel:
                        r = meta.copy()
                        r.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                        robust_insert(r)
                    
                    if et_a_noter != "Aucun":
                        rn = meta.copy()
                        rn.update({"etudiant_nom": et_a_noter, "note_evaluation": val_note})
                        robust_insert(rn)

                    send_mail([EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']], f"Rapport {m_sel}", f"Rapport validé par {current_grade} {user['nom_officiel']}")
                    st.success("✅ Séance validée et archivée.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur technique : {e}")
        else:
            st.error("Code unique incorrect.")

with tab_suivi:
    st.markdown("### 🔍 Fiche et Suivi Individuel")
    df_etudiants['Search_Full'] = df_etudiants['Nom'] + " " + df_etudiants['Prénom']
    liste_globale = sorted(df_etudiants['Search_Full'].unique())
    etudiant_search = st.selectbox("🎯 Rechercher un étudiant :", ["-- Sélectionner --"] + liste_globale)
    
    if etudiant_search != "-- Sélectionner --":
        info = df_etudiants[df_etudiants['Search_Full'] == etudiant_search].iloc[0]
        res_sql = supabase.table("archives_absences").select("*").eq("etudiant_nom", etudiant_search).eq("note_evaluation", "ABSENCE").execute()
        df_abs_et = pd.DataFrame(res_sql.data)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Effectif Promotion", len(df_etudiants[df_etudiants['Promotion'] == info['Promotion']]))
        m2.metric(f"Effectif Groupe {info['Groupe']}", len(df_etudiants[(df_etudiants['Promotion'] == info['Promotion']) & (df_etudiants['Groupe'] == info['Groupe'])]))
        m3.metric(f"Effectif S-Groupe {info['Sous groupe']}", len(df_etudiants[(df_etudiants['Promotion'] == info['Promotion']) & (df_etudiants['Groupe'] == info['Groupe']) & (df_etudiants['Sous groupe'] == info['Sous groupe'])]))
        m4.metric("TOTAL ABSENCES", f"{len(df_abs_et)}", delta_color="inverse")

        st.markdown("---")
        st.write(f"**Identité :** {info['Nom']} {info['Prénom']} | **Promotion :** {info['Promotion']}")
        st.table(df_abs_et[['date_seance', 'matiere', 'enseignant', 'categorie_seance']] if not df_abs_et.empty else "Aucune absence.")

with tab_hist:
    st.markdown("### 📜 Registre Global")
    res_glob = supabase.table("archives_absences").select("*").execute()
    if res_glob.data:
        st.dataframe(pd.DataFrame(res_glob.data), use_container_width=True)
