import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
    .date-badge {{ background-color: #1E3A8A; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; float: right; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    .stat-container {{ display: flex; justify-content: space-around; margin: 20px 0; gap: 10px; }}
    .stat-box {{ flex: 1; padding: 15px; border-radius: 12px; color: white; font-weight: bold; text-align: center; font-size: 16px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .bg-cours {{ background: linear-gradient(135deg, #1E3A8A, #3B82F6); }}
    .bg-td {{ background: linear-gradient(135deg, #15803d, #22c55e); }}
    .bg-tp {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU FICHIER EDT ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

def normalize(s):
    if not s or s == "Non défini": return "vide"
    return str(s).strip().replace(" ", "").lower().replace("-", "").replace("–", "").replace(":00", "").replace("h00", "h")

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    cols_attendues = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
    for col in cols_attendues:
        if col in df.columns: 
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    tab_conn, tab_ins, tab_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    with tab_conn:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
    
    with tab_ins:
        st.subheader("Nouvelle Inscription")
        n_nom = st.text_input("Nom Complet (ex: ZIDI)")
        n_em = st.text_input("Email Professionnel")
        n_ps = st.text_input("Mot de passe", type="password")
        n_statut = st.radio("Statut :", ["Permanent", "Vacataire"], horizontal=True)
        n_grade = st.selectbox("Grade :", ["Professeur émérite", "Professeur", "MCA", "MCB", "MAA", "MAB", "Doctorant", "Mastérant"])
        
        if st.button("S'inscrire"):
            try:
                supabase.table("enseignants_auth").insert({
                    "nom_officiel": n_nom.upper(), "email": n_em, "password_hash": hash_pw(n_ps), 
                    "role": "prof", "statut_prof": n_statut, "grade_prof": n_grade
                }).execute()
                st.success("Inscription réussie ! Connectez-vous.")
            except: st.error("Erreur. Assurez-vous que les colonnes statut_prof et grade_prof existent sur Supabase.")

    with tab_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Entrer en tant qu'Admin"):
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin", "statut_prof": "Direction", "grade_prof": "Chef Dépt"}
                st.rerun()
    st.stop()

# --- INITIALISATION PARAMÈTRES ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]
map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

with st.sidebar:
    st.header(f"👤 {user.get('nom_officiel', 'Utilisateur')}")
    # Utilisation de .get() pour éviter le KeyError
    grade = user.get('grade_prof', '---')
    statut = user.get('statut_prof', '---')
    st.write(f"**{grade}** ({statut})")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "👨‍🏫 Données Enseignants", "🎓 Données Étudiants", "📅 Surveillances Examens", "🤖 Générateur Automatique"])
    st.divider()
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

if df is not None:
    if portail == "📖 Emploi du Temps":
        st.info("Espace Emploi du Temps")
        # [Logique de l'EDT...]
        
    elif portail == "👨‍🏫 Données Enseignants":
        if is_admin:
            st.header("🗂️ État du Corps Enseignant")
            raw_profs = []
            for entry in df["Enseignants"].dropna().unique():
                for p in str(entry).split('&'):
                    name = p.strip()
                    if name and name.lower() not in ["non défini", "nan", "vide"]: raw_profs.append(name)
            liste_officielle = sorted(list(set(raw_profs)))
            
            try:
                res_auth = supabase.table("enseignants_auth").select("*").execute()
                dict_auth = {str(row['nom_officiel']).strip().upper(): row for row in res_auth.data} if res_auth.data else {}
            except: dict_auth = {}
            
            tableau_profs = []
            for prof in liste_officielle:
                nom_maj = prof.upper()
                info = dict_auth.get(nom_maj, {})
                # Correction ICI : utilisation de .get() pour éviter le crash
                tableau_profs.append({
                    "Nom": prof, 
                    "Grade": info.get('grade_prof', '---'),
                    "Statut": info.get('statut_prof', '---'),
                    "Email": info.get('email', 'Non inscrit')
                })
            st.dataframe(pd.DataFrame(tableau_profs), use_container_width=True, hide_index=True)
        else: st.error("Accès réservé à l'Admin.")
