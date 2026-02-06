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
    st.error("⚠️ Erreur de configuration Supabase.")
    st.stop()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_qr_segno(data):
    qr = segno.make(data)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10)
    return out.getvalue()

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

# Préparation de la liste complète des étudiants
df_etudiants['Full_N'] = (df_etudiants['Nom'].fillna('') + " " + df_etudiants['Prénom'].fillna('')).str.upper().str.strip()

def get_staff_info(user_nom, user_email):
    match = df_staff[df_staff['Email'].str.lower() == user_email.lower()]
    if not match.empty:
        return match.iloc[0].get('Grade', 'Enseignant'), match.iloc[0].get('Qualité', 'Permanent')
    return "Enseignant", "Permanent"

def safe_insert(table_name, data_dict):
    try:
        return supabase.table(table_name).insert(data_dict).execute()
    except:
        base_cols = ["promotion", "matiere", "enseignant", "date_seance", "etudiant_nom", "note_evaluation"]
        clean_dict = {k: v for k, v in data_dict.items() if k in base_cols}
        return supabase.table(table_name).insert(clean_dict).execute()

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
            st.write(f"Veuillez contacter l'administrateur technique à l'adresse : **{EMAIL_ADMIN_TECH}** ou le Chef de Département.")

    with t_student:
        nom_st = st.selectbox("Sélectionnez votre Nom & Prénom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.success(f"Promotion : {profil['Promotion']} | Groupe : {profil['Groupe']} | Sous-groupe : {profil['Sous groupe']}")
            
            # --- TABLEAU EDT DYNAMIQUE (Horiz: Jours, Vert: Heures) ---
            st.markdown("### 📅 Votre Emploi du Temps")
            edt_promo = df_edt[df_edt['Promotion'] == profil['Promotion']].copy()
            if not edt_promo.empty:
                try:
                    # Pivotage pour avoir Jours en colonnes et Heures en lignes
                    grid_edt = edt_promo.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x))
                    # Réorganisation des jours (Ordre de la semaine)
                    jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                    cols_presentes = [j for j in jours_ordre if j in grid_edt.columns]
                    st.dataframe(grid_edt[cols_presentes], use_container_width=True)
                except:
                    st.table(edt_promo[['Enseignements', 'Horaire', 'Jours', 'Lieu']])
            
            # --- ABSENCES ÉTUDIANT ---
            st.markdown("### ❌ Récapitulatif de vos Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).eq("note_evaluation", "ABSENCE").execute()
            if res_abs.data:
                df_abs_et = pd.DataFrame(res_abs.data)
                df_count = df_abs_et.groupby(['matiere', 'enseignant']).size().reset_index(name='Total Absences')
                st.table(df_count)
            else:
                st.info("Aucune absence signalée. Bravo !")

            st.write("📲 **QR Code d'accès rapide :**")
            st.image(generate_qr_segno(f"ID:{nom_st}"), width=120)
    st.stop()

# --- 5. INTERFACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
current_grade, current_statut = get_staff_info(user['nom_officiel'], user['email'])

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}\n**{current_grade}**")
    if is_admin: st.success("🛡️ MODE ADMIN")
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None; st.rerun()

tab_saisie, tab_suivi, tab_hist = st.tabs(["📝 Saisie Séance", "🔍 Suivi Étudiant", "📜 Archive Globale"])

# --- ONGLET SAISIE ---
with tab_saisie:
    # (Logique de saisie identique avec ajout du bandeau d'effectifs)
    c1, c2, c3 = st.columns(3)
    date_s = c3.date_input("Date :", value=datetime.now())
    enseignant_vue = st.selectbox("Vue Enseignant :", sorted(df_edt['Enseignants'].unique())) if is_admin else user['nom_officiel']
    
    mask = df_edt['Enseignants'].str.contains(enseignant_vue, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    g_sel = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()))
    sg_sel = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()))
    
    st.info(f"📊 Effectifs : Promo: {len(df_p)} | Groupe: {len(df_p[df_p['Groupe']==g_sel])} | SG: {len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)])}")
    
    # ... (Reste de la saisie identique)

# --- ONGLET SUIVI ÉTUDIANT (VERSION AMÉLIORÉE) ---
with tab_suivi:
    st.markdown("### 📋 Fiche Individuelle de l'Étudiant")
    et_target = st.selectbox("Rechercher un étudiant (Toutes Promotions) :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    
    if et_target != "--":
        info_adm = df_etudiants[df_etudiants['Full_N'] == et_target].iloc[0]
        
        c_a, c_b, c_c = st.columns(3)
        c_a.metric("Promotion", info_adm['Promotion'])
        c_b.metric("Groupe", info_adm['Groupe'])
        c_c.metric("Sous-groupe", info_adm['Sous groupe'])
        
        st.divider()
        st.subheader("📊 Détail des Absences par Matière")
        
        # Récupération des absences réelles en base
        res_suivi = supabase.table("archives_absences").select("*").eq("etudiant_nom", et_target).eq("note_evaluation", "ABSENCE").execute()
        
        if res_suivi.data:
            df_res = pd.DataFrame(res_suivi.data)
            
            # Jointure avec l'EDT pour récupérer Jour/Horaire
            recap = []
            abs_counts = df_res['matiere'].value_counts()
            
            for mat, count in abs_counts.items():
                # On cherche les infos de cette matière dans l'EDT de sa promotion
                info_edt = df_edt[(df_edt['Promotion'] == info_adm['Promotion']) & (df_edt['Enseignements'] == mat)]
                if not info_edt.empty:
                    ens = info_edt.iloc[0]['Enseignants']
                    jour = info_edt.iloc[0]['Jours']
                    heure = info_edt.iloc[0]['Horaire']
                else:
                    ens = "N/A"; jour = "N/A"; heure = "N/A"
                
                recap.append({
                    "Matière": mat,
                    "Enseignant": ens,
                    "Jour": jour,
                    "Horaire": heure,
                    "Nombre d'Absences": count
                })
            
            st.table(pd.DataFrame(recap))
        else:
            st.success("Cet étudiant n'a aucune absence enregistrée.")

with tab_hist:
    st.markdown("### 📊 Pilotage Global")
    res_glob = supabase.table("archives_absences").select("*").execute()
    if res_glob.data:
        st.dataframe(pd.DataFrame(res_glob.data), use_container_width=True)
