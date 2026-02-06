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
        Bonjour,
        Un rapport a été validé :
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
    """Applique des couleurs selon le type d'enseignement"""
    if not val or val == "": return ""
    color = "#f0f2f6" # Défaut
    if "Cours" in val: color = "#d1e7dd" # Vert clair
    elif "TD" in val: color = "#fff3cd"  # Jaune clair
    elif "TP" in val: color = "#cfe2ff"  # Bleu clair
    return f'background-color: {color}; color: black; font-weight: bold;'

# --- 4. AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_student = st.tabs(["🔐 Enseignant", "📝 Inscription", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email :")
        p_log = st.text_input("Code :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
        with st.expander("❓ Code oublié ?"):
            st.info(f"Veuillez contacter l'administrateur technique : {EMAIL_ADMIN_TECH}")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()))
        inf_s = df_staff[df_staff['Full_S'] == choix_nom].iloc[0]
        reg_e = st.text_input("Email de confirmation :", value=inf_s['Email'])
        reg_p = st.text_input("Nouveau Code Unique :", type="password")
        if st.button("Créer le compte"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf_s['NOM'], "prenom_officiel": inf_s['PRÉNOM'],
                "statut_enseignant": inf_s['Qualité'], "grade_enseignant": inf_s['Grade']
            }).execute()
            st.success("Compte créé !")

    with t_student:
        nom_st = st.selectbox("Sélectionnez votre Nom & Prénom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.success(f"📍 {profil['Promotion']} | Groupe : {profil['Groupe']} | Sous-groupe : {profil['Sous groupe']}")
            
            # FILTRAGE : Cours (Tous) + TD (Groupe) + TP (Sous-Groupe)
            m_cours = df_edt['Enseignements'].str.contains('Cours', case=False)
            m_td = (df_edt['Enseignements'].str.contains('TD', case=False)) & (df_edt['Lieu'].str.contains(profil['Groupe'], case=False))
            m_tp = (df_edt['Enseignements'].str.contains('TP', case=False)) & (df_edt['Lieu'].str.contains(profil['Sous groupe'], case=False))
            
            edt_indiv = df_edt[(df_edt['Promotion'] == profil['Promotion']) & (m_cours | m_td | m_tp)].copy()
            
            st.markdown("### 📅 Emploi du Temps Hebdomadaire")
            if not edt_indiv.empty:
                # Création du tableau croisé
                jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                # On s'assure que l'horaire est triable (ex: 08h00 avant 13h00)
                grid = edt_indiv.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                
                # Réorganiser les colonnes selon les jours de la semaine
                cols_existantes = [j for j in jours_ordre if j in grid.columns]
                grid = grid[cols_existantes]
                
                # Tri chronologique des lignes (index Horaire)
                grid = grid.sort_index()
                
                # Affichage avec style (couleurs)
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True)
            
            st.markdown("### ❌ Récapitulatif de vos Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).eq("note_evaluation", "ABSENCE").execute()
            if res_abs.data:
                df_a = pd.DataFrame(res_abs.data)
                df_sum = df_a.groupby(['matiere', 'enseignant']).size().reset_index(name='Total Absences')
                st.table(df_sum)
            else:
                st.info("Aucune absence signalée.")
            
            st.write("📲 **QR Code d'accès :**")
            st.image(generate_qr_segno(f"Etudiant:{nom_st}"), width=120)
    st.stop()

# --- 5. INTERFACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}")
    enseignant_vue = st.selectbox("Vue Enseignant :", sorted(df_edt['Enseignants'].unique())) if is_admin else user['nom_officiel']
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_hist = st.tabs(["📝 Saisie", "🔍 Suivi Étudiant", "📜 Archives"])

with t_saisie:
    # --- LOGIQUE DE SAISIE IDENTIQUE ---
    c1, c2, c3 = st.columns(3)
    date_s = c3.date_input("Date :", value=datetime.now())
    mask_e = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask_e]['Promotion'].unique()) if any(mask_e) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    g_sel = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"])
    sg_sel = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"])
    
    st.info(f"📊 Effectifs attendus : {len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)])} étudiants")
    
    df_app = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)].copy()
    liste_et = df_app['Full_N'].tolist()
    
    m_sel = st.selectbox("Matière :", sorted(df_edt[mask_e & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask_e) else ["-"])
    
    col_a, col_b = st.columns(2)
    with col_a:
        abs_c = st.checkbox("🚩 ABSENCE COLLECTIVE")
        abs_sel = liste_et if abs_c else st.multiselect("❌ Sélectionner Absents :", options=liste_et)
    with col_b:
        et_n = st.selectbox("📝 Noter un étudiant :", ["Aucun"] + liste_et)
        val_n = st.text_input("Note/Obs :", "0")

    code_v = st.text_input("🔑 Code de validation :", type="password")
    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            # Insertion Supabase et Notification
            meta = {"promotion": p_sel, "matiere": m_sel, "enseignant": user['nom_officiel'], "date_seance": str(date_s), "nb_absents": len(abs_sel)}
            for ab in abs_sel:
                safe_insert("archives_absences", {**meta, "etudiant_nom": ab, "note_evaluation": "ABSENCE"})
            if et_n != "Aucun":
                safe_insert("archives_absences", {**meta, "etudiant_nom": et_n, "note_evaluation": val_n})
            send_notification_admin(meta)
            st.success("Données enregistrées !"); st.balloons()

with t_suivi:
    st.markdown("### 📋 Fiche Académique")
    et_target = st.selectbox("Choisir un étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    
    if et_target != "--":
        info_adm = df_etudiants[df_etudiants['Full_N'] == et_target].iloc[0]
        
        c_a, c_b, c_c = st.columns(3)
        c_a.metric("Promo", info_adm['Promotion'])
        c_b.metric("Groupe", info_adm['Groupe'])
        c_c.metric("Sous-groupe", info_adm['Sous groupe'])
        
        st.divider()
        st.subheader("📊 Historique des Absences & Enseignants")
        
        r_suivi = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_target).eq("note_evaluation", "ABSENCE").execute()
        
        if r_suivi.data:
            df_res = pd.DataFrame(r_suivi.data)
            counts = df_res['matiere'].value_counts()
            recap_final = []
            
            for mat, n_abs in counts.items():
                info_edt = df_edt[(df_edt['Promotion'] == info_adm['Promotion']) & (df_edt['Enseignements'] == mat)]
                ens = info_edt.iloc[0]['Enseignants'] if not info_edt.empty else "N/A"
                jour = info_edt.iloc[0]['Jours'] if not info_edt.empty else "N/A"
                heure = info_edt.iloc[0]['Horaire'] if not info_edt.empty else "N/A"
                
                recap_final.append({
                    "Matière": mat, "Enseignant": ens, "Jour": jour, "Horaire": heure, "Absences": n_abs
                })
            st.table(pd.DataFrame(recap_final))
        else:
            st.success("Aucune absence enregistrée.")

with t_hist:
    st.markdown("### 📜 Archives Globales")
    res_all = supabase.table("archives_absences").select("*").execute()
    if res_all.data:
        st.dataframe(pd.DataFrame(res_all.data), use_container_width=True)
