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
        st.info(f"Profil détecté : {info_s['NOM']} | Grade : {info_s['Grade']}")
        reg_mail = st.text_input("Email :", value=info_s['Email'])
        reg_pass = st.text_input("Créer Code Unique :", type="password")
        if st.button("Valider inscription"):
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
                send_mail(f_email, "Nouveau Code UDL", f"Votre nouveau code : {new_c}")
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
        enseignant_vue = st.selectbox("Vue Admin (EDT) :", sorted(df_edt['Enseignants'].unique()))
        
        st.divider()
        st.warning("🚨 ZONE DANGEREUSE")
        if st.button("Vider toutes les Archives"):
            st.session_state["confirm_reset"] = True
        
        if st.session_state.get("confirm_reset"):
            confirm_pw = st.text_input("Entrez votre code secret pour confirmer :", type="password")
            if st.button("CONFIRMER LE RESET TOTAL"):
                if hash_pw(confirm_pw) == user['password_hash']:
                    supabase.table("archives_absences").delete().neq("id", 0).execute()
                    st.success("Base de données réinitialisée.")
                    st.session_state["confirm_reset"] = False
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
    # 1. Infos séance
    c1, c2, c3 = st.columns(3)
    cat_s = c1.selectbox("🏷️ Séance :", ["Cours", "TD", "TP", "Examen", "Rattrapage"])
    reg_s = c2.selectbox("⏳ Régime :", ["Charge Horaire", "Heures Supplémentaires"])
    date_s = c3.date_input("📅 Date réelle :", value=datetime.now())

    cp, cm = st.columns(2)
    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    list_p = sorted(df_edt[mask]['Promotion'].unique())
    p_sel = cp.selectbox("🎓 Promotion :", list_p if list_p else sorted(df_edt['Promotion'].unique()))
    list_m = sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique())
    m_sel = cm.selectbox("📖 Matière :", list_m if list_m else ["-"])

    st.markdown("---")
    st.markdown("### 📈 Appel & Notation")
    
    df_p_full = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p_full['Groupe'].unique()) if not df_p_full.empty else ["G1"])
    df_g = df_p_full[df_p_full['Groupe'] == g_sel]
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_g['Sous groupe'].unique()) if not df_g.empty else ["SG1"])

    df_appel = df_g[df_g['Sous groupe'] == sg_sel].copy()
    df_appel['Full'] = df_appel['Nom'] + " " + df_appel['Prénom']
    noms = df_appel['Full'].tolist()

    col_a, col_n = st.columns(2)
    with col_a:
        abs_coll = st.checkbox("🚩 SIGNALER ABSENCE COLLECTIVE")
        absents = noms if abs_coll else st.multiselect("❌ Absents :", options=noms)
    with col_n:
        et_noter = st.selectbox("📝 Noter un étudiant :", ["Aucun"] + noms)
        val_note = st.text_input("Valeur (ex: +1) :", "0")

    obs_txt = st.text_area("🗒️ Observations :")
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password")

    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            with st.spinner("Archivage..."):
                try:
                    meta = {"promotion": p_sel, "matiere": m_sel, "enseignant": f"{current_grade} {user['nom_officiel']}", "date_seance": str(date_s)}
                    
                    def robust_insert(row):
                        try:
                            # Tentative avec colonnes additionnelles
                            row_full = row.copy()
                            row_full.update({"regime_heure": reg_s, "observations": obs_txt, "categorie_seance": cat_s})
                            supabase.table("archives_absences").insert(row_full).execute()
                        except:
                            # Repli sur colonnes de base
                            supabase.table("archives_absences").insert(row).execute()

                    for ab in absents:
                        r = meta.copy()
                        r.update({"etudiant_nom": ab, "note_evaluation": "ABSENCE"})
                        robust_insert(r)
                    
                    if et_noter != "Aucun":
                        rn = meta.copy()
                        rn.update({"etudiant_nom": et_noter, "note_evaluation": val_note})
                        robust_insert(rn)

                    send_mail([EMAIL_CHEF_DEPT, EMAIL_CHEF_ADJOINT, user['email']], f"Rapport {m_sel}", f"Séance validée par {user['nom_officiel']}")
                    st.success("✅ Rapport envoyé et archivé !")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.error("Code incorrect.")

# --- NOUVEL ONGLET : SUIVI ÉTUDIANT ---
with tab_suivi:
    st.markdown("### 🔍 Fiche Individuelle de l'Étudiant")
    
    # 1. Liste globale de tous les étudiants
    df_etudiants['Full_Search'] = df_etudiants['Nom'] + " " + df_etudiants['Prénom']
    liste_globale = sorted(df_etudiants['Full_Search'].unique())
    
    etudiant_choisi = st.selectbox("Sélectionnez un étudiant pour voir son assiduité :", ["-- Choisir --"] + liste_globale)
    
    if etudiant_choisi != "-- Choisir --":
        # Récupération des infos Excel
        info_et = df_etudiants[df_etudiants['Full_Search'] == etudiant_choisi].iloc[0]
        
        # Récupération des absences en base
        res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", etudiant_choisi).eq("note_evaluation", "ABSENCE").execute()
        df_abs_et = pd.DataFrame(res_abs.data)
        
        # Affichage
        c_i1, c_i2 = st.columns([1, 2])
        with c_i1:
            st.info("📌 Informations Générales")
            st.write(f"**Nom & Prénom :** {etudiant_choisi}")
            st.write(f"**Promotion :** {info_et['Promotion']}")
            st.write(f"**Groupe :** {info_et['Groupe']}")
            st.write(f"**Sous-Groupe :** {info_et['Sous groupe']}")
        
        with c_i2:
            st.error("🚩 Bilan des Absences")
            nb_abs = len(df_abs_et)
            st.metric("Nombre total d'absences", f"{nb_abs} séance(s)")
            
            if nb_abs > 0:
                st.write("**Détails des absences :**")
                # On renomme pour la clarté
                df_clean = df_abs_et[['date_seance', 'matiere', 'enseignant', 'promotion']]
                st.table(df_clean)
                
                # Option Export pour cet étudiant
                buf_et = io.BytesIO()
                df_clean.to_excel(buf_et, index=False)
                st.download_button(f"📄 Télécharger Fiche Absences - {info_et['Nom']}", buf_et.getvalue(), f"Absences_{info_et['Nom']}.xlsx")
            else:
                st.success("Cet étudiant n'a aucune absence enregistrée.")

with tab_hist:
    st.markdown("### 📜 Toutes les Archives")
    res_all = supabase.table("archives_absences").select("*").execute()
    if res_all.data:
        df_all = pd.DataFrame(res_all.data)
        st.dataframe(df_all, use_container_width=True)
        
        buf_all = io.BytesIO()
        df_all.to_excel(buf_all, index=False)
        st.download_button("📊 Exporter la base complète", buf_all.getvalue(), "Archives_EDT_S2_2026.xlsx")
