import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import segno
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# Fichiers sources
FICHIER_EDT = "dataEDT-ELT-S2-2026.xlsx"
FICHIER_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"
FICHIER_STAFF = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

# 📧 CONFIGURATION EMAILS
EMAIL_ADMIN_TECH = "milouafarid@gmail.com"
EMAIL_CHEF_DEPT = "chef.department.elt.fge@gmail.com"
EMAIL_ADJOINT = "milouafarid@gmail.com"
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

def generate_qr_segno(data):
    qr = segno.make(data)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10)
    return out.getvalue()

def send_notification_admin(details):
    destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Système EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = f"Rapport de Séance : {details['matiere']} - {details['promotion']}"
        corps = f"""
        Un nouveau rapport a été validé :
        - Enseignant : {details['enseignant']}
        - Matière : {details['matiere']}
        - Promotion : {details['promotion']}
        - Date : {details['date_seance']}
        - Absents : {details['nb_absents']}
        """
        msg.attach(MIMEText(corps, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except:
        pass

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
        st.error(f"Erreur Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()
df_etudiants['Full_N'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()

def color_edt(val):
    if not val or val == "": return ""
    if "Cours" in val: return 'background-color: #d1e7dd; color: #084298; font-weight: bold; border: 1px solid #badbcc;'
    if "TD" in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold; border: 1px solid #ffeeba;'
    if "TP" in val: return 'background-color: #cfe2ff; color: #004085; font-weight: bold; border: 1px solid #b8daff;'
    return 'background-color: #f8f9fa; color: #333;'

def safe_insert(table_name, data_dict):
    try:
        return supabase.table(table_name).insert(data_dict).execute()
    except Exception as e:
        st.error(f"Erreur DB : {e}")

# --- 4. AUTHENTIFICATION ET INTERFACE D'ACCÈS ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_student = st.tabs(["🔐 Enseignant", "📝 Inscription", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email :")
        p_log = st.text_input("Code Unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
        with st.expander("❓ Code unique oublié ?"):
            st.info(f"Veuillez contacter l'administrateur technique : **{EMAIL_ADMIN_TECH}**")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Recherchez votre nom dans le personnel :", sorted(df_staff['Full_S'].unique()))
        inf_s = df_staff[df_staff['Full_S'] == choix_nom].iloc[0]
        st.write(f"Vérification : {inf_s['Grade']} ({inf_s['Qualité']})")
        reg_e = st.text_input("Confirmez votre Email :", value=inf_s['Email'])
        reg_p = st.text_input("Définissez votre Code Unique :", type="password")
        if st.button("Valider l'inscription"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf_s['NOM'], "prenom_officiel": inf_s['PRÉNOM'],
                "statut_enseignant": inf_s['Qualité'], "grade_enseignant": inf_s['Grade']
            }).execute()
            st.success("Inscription réussie !")

    with t_student:
        nom_st = st.selectbox("Sélectionnez votre Nom & Prénom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.markdown(f"#### 📌 {profil['Promotion']} | Groupe : {profil['Groupe']} | Sous-groupe : {profil['Sous groupe']}")
            
            # --- LOGIQUE DE FILTRAGE STRICT TD/TP/COURS ---
            # 1. On prend tous les cours de la promotion
            m_cours = (df_edt['Promotion'] == profil['Promotion']) & (df_edt['Enseignements'].str.contains('Cours', case=False, na=False))
            
            # 2. On prend les TD qui mentionnent le GROUPE dans la colonne 'Lieu' ou 'Enseignements'
            m_td = (df_edt['Promotion'] == profil['Promotion']) & \
                   (df_edt['Enseignements'].str.contains('TD', case=False, na=False)) & \
                   (df_edt['Lieu'].str.contains(profil['Groupe'], case=False, na=False))
            
            # 3. On prend les TP qui mentionnent le SOUS-GROUPE dans la colonne 'Lieu' ou 'Enseignements'
            m_tp = (df_edt['Promotion'] == profil['Promotion']) & \
                   (df_edt['Enseignements'].str.contains('TP', case=False, na=False)) & \
                   (df_edt['Lieu'].str.contains(profil['Sous groupe'], case=False, na=False))
            
            edt_final = df_edt[m_cours | m_td | m_tp].copy()
            
            st.markdown("### 📅 Mon Emploi du Temps Personnalisé")
            if not edt_final.empty:
                jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                
                # Pivot pour tableau croisé
                grid = edt_final.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                
                # Tri chronologique des horaires (08h00, 09h30...)
                grid = grid.sort_index()
                
                # Réorganisation des colonnes jours
                cols_actives = [j for j in jours_ordre if j in grid.columns]
                st.dataframe(grid[cols_actives].style.applymap(color_edt), use_container_width=True)
            else:
                st.warning("Aucun enseignement trouvé pour vos critères (Promo/Groupe/SG).")

            st.markdown("### ❌ Bilan de mes Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).eq("note_evaluation", "ABSENCE").execute()
            if res_abs.data:
                df_abs = pd.DataFrame(res_abs.data)
                st.table(df_abs.groupby(['matiere', 'enseignant']).size().reset_index(name='Total Absences'))
            else:
                st.success("Aucune absence enregistrée.")
    st.stop()

# --- 5. ESPACE ENSEIGNANT CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
nom_aff = user.get('nom_officiel', 'Inconnu')

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {nom_aff} {user.get('prenom_officiel','')}")
    if is_admin:
        st.success("🛡️ MODE ADMINISTRATEUR")
        ens_actif = st.selectbox("Vue Enseignant :", sorted(df_edt['Enseignants'].unique()))
    else:
        ens_actif = nom_aff
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_hist = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "📜 Archives"])

with t_saisie:
    # Logic de saisie avec effectifs dynamiques
    c1, c2, c3 = st.columns(3)
    dt_s = c3.date_input("Date :", value=datetime.now())
    
    mask_e = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_choice = st.selectbox("Promotion :", sorted(df_edt[mask_e]['Promotion'].unique()) if any(mask_e) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_choice]
    g_choice = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()))
    sg_choice = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_choice]['Sous groupe'].unique()))
    
    eff_sg = df_p[(df_p['Groupe']==g_choice) & (df_p['Sous groupe']==sg_choice)]
    st.info(f"📊 Effectif présent pour l'appel : {len(eff_sg)} étudiants")
    
    m_choice = st.selectbox("Matière :", sorted(df_edt[mask_e & (df_edt['Promotion'] == p_choice)]['Enseignements'].unique()) if any(mask_e) else ["-"])
    
    abs_list = st.multiselect("❌ Liste des Absents :", options=eff_sg['Full_N'].tolist())
    code_v = st.text_input("🔑 Code Unique de validation :", type="password")
    
    if st.button("🚀 ENREGISTRER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            meta = {"promotion": p_choice, "matiere": m_choice, "enseignant": nom_aff, "date_seance": str(dt_s), "nb_absents": len(abs_list)}
            for student in abs_list:
                safe_insert("archives_absences", {**meta, "etudiant_nom": student, "note_evaluation": "ABSENCE"})
            send_notification_admin(meta)
            st.success("Rapport validé !"); st.balloons()
        else: st.error("Code invalide.")

with t_suivi:
    st.markdown("### 📋 Fiche de Suivi Étudiant")
    target = st.selectbox("Sélectionner un étudiant (Toutes Promotions) :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    if target != "--":
        adm_info = df_etudiants[df_etudiants['Full_N'] == target].iloc[0]
        st.write(f"**Promo:** {adm_info['Promotion']} | **Groupe:** {adm_info['Groupe']} | **SG:** {adm_info['Sous groupe']}")
        
        res_s = supabase.table("archives_absences").select("*").eq("etudiant_nom", target).eq("note_evaluation", "ABSENCE").execute()
        if res_s.data:
            df_res = pd.DataFrame(res_s.data)
            recap_final = []
            for mat, count in df_res['matiere'].value_counts().items():
                info_edt = df_edt[(df_edt['Promotion'] == adm_info['Promotion']) & (df_edt['Enseignements'] == mat)]
                recap_final.append({
                    "Matière": mat, "Absences": count,
                    "Enseignant": info_edt.iloc[0]['Enseignants'] if not info_edt.empty else "N/A",
                    "Jour": info_edt.iloc[0]['Jours'] if not info_edt.empty else "N/A",
                    "Horaire": info_edt.iloc[0]['Horaire'] if not info_edt.empty else "N/A"
                })
            st.table(pd.DataFrame(recap_final))
        else: st.success("Aucune absence pour cet étudiant.")

with t_hist:
    st.markdown("### 📊 Historique Global des Séances")
    res_g = supabase.table("archives_absences").select("*").execute()
    if res_g.data:
        df_all = pd.DataFrame(res_g.data)
        st.dataframe(df_all, use_container_width=True)
        buf = io.BytesIO()
        df_all.to_excel(buf, index=False)
        st.download_button("📥 Exporter Excel", buf.getvalue(), "Registre_S2_2026.xlsx")
