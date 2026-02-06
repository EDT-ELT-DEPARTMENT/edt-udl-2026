import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import segno
import re
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
    st.error("⚠️ Erreur de connexion Supabase. Vérifiez vos Secrets.")
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
        corps = f"Rapport validé :\n- Enseignant: {details['enseignant']}\n- Matière: {details['matiere']}\n- Absents: {details['nb_absents']}"
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
    if "Cours" in val: return 'background-color: #d1e7dd; color: #084298; font-weight: bold;'
    if "Td" in val or "TD" in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
    if "TP" in val: return 'background-color: #cfe2ff; color: #004085; font-weight: bold;'
    return ''

def safe_insert(table_name, data_dict):
    try:
        return supabase.table(table_name).insert(data_dict).execute()
    except Exception as e:
        st.error(f"Erreur DB : {e}")

# --- 4. AUTHENTIFICATION ---
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
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
        with st.expander("❓ Code oublié ?"):
            st.info(f"Contactez l'administrateur : {EMAIL_ADMIN_TECH}")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()))
        inf_s = df_staff[df_staff['Full_S'] == choix_nom].iloc[0]
        reg_e = st.text_input("Email :", value=inf_s['Email'])
        reg_p = st.text_input("Définir Code Unique :", type="password")
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
            st.markdown(f"#### 📌 {profil['Promotion']} | Groupe : {profil['Groupe']} | Sous-groupe : {profil['Sous groupe']}")
            
            # --- LOGIQUE DE FILTRAGE EDT ROBUSTE ---
            def filtrer_edt_etudiant(row):
                # 1. Vérifier la promotion
                if str(row['Promotion']).strip().upper() != str(profil['Promotion']).strip().upper():
                    return False
                
                enseignement = str(row['Enseignements']).upper()
                code_seance = str(row['Code']).upper()
                lieu = str(row['Lieu']).upper()
                
                # Cas 1 : Cours (Afficher pour tout le monde dans la promotion)
                if "COURS" in enseignement:
                    return True
                
                # Cas 2 : TD (Extraire le numéro de groupe, ex: "G1" -> "1")
                num_groupe = re.findall(r'\d+', str(profil['Groupe']))[0] if re.findall(r'\d+', str(profil['Groupe'])) else ""
                if "TD" in enseignement:
                    # On accepte si le groupe est cité dans Lieu, Enseignement ou Code
                    if str(profil['Groupe']).upper() in (enseignement + lieu + code_seance):
                        return True
                    # Ou si c'est marqué par une lettre correspondant au groupe (A=G1, B=G2)
                    if num_groupe == "1" and "-A" in code_seance: return True
                    if num_groupe == "2" and "-B" in code_seance: return True
                
                # Cas 3 : TP (Extraire le numéro de sous-groupe, ex: "SG1" -> "1")
                num_sg = re.findall(r'\d+', str(profil['Sous groupe']))[0] if re.findall(r'\d+', str(profil['Sous groupe'])) else ""
                if "TP" in enseignement:
                    # On accepte si le SG est cité
                    if str(profil['Sous groupe']).upper() in (enseignement + lieu + code_seance):
                        return True
                    # Cas spécial fichier M1CE : TP-IA-a (SG1) / TP-IA-b (SG2)
                    suffixe_sg = "A" if num_sg == "1" else "B" if num_sg == "2" else "C" if num_sg == "3" else ""
                    if f"-{suffixe_sg}" in code_seance:
                        return True
                
                return False

            edt_etudiant = df_edt[df_edt.apply(filtrer_edt_etudiant, axis=1)].copy()
            
            st.markdown("### 📅 Mon Emploi du Temps")
            if not edt_etudiant.empty:
                jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                
                # Pivot
                grid = edt_etudiant.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                
                # Ordonner les colonnes (Jours)
                cols = [j for j in jours_ordre if j in grid.columns]
                grid = grid[cols]
                
                # Ordonner les lignes (Heures) chronologiquement
                def get_hour(h_str):
                    match = re.search(r'(\d+)', str(h_str))
                    return int(match.group(1)) if match else 0
                
                grid['h_val'] = grid.index.map(get_hour)
                grid = grid.sort_values('h_val').drop(columns='h_val')
                
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True)
            else:
                st.warning("Aucun cours/TD/TP trouvé. Vérifiez les données du fichier.")

            st.markdown("### ❌ Bilan Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).eq("note_evaluation", "ABSENCE").execute()
            if res_abs.data:
                st.table(pd.DataFrame(res_abs.data).groupby(['matiere', 'enseignant']).size().reset_index(name='Absences'))
            else: st.info("Aucune absence.")
            st.image(generate_qr_segno(f"STUDENT:{nom_st}"), width=100)
    st.stop()

# --- 5. ESPACE ENSEIGNANT ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user.get('nom_officiel','')} {user.get('prenom_officiel','')}")
    ens_v = st.selectbox("Vue Enseignant :", sorted(df_edt['Enseignants'].unique())) if is_admin else user.get('nom_officiel','')
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_hist = st.tabs(["📝 Saisie", "🔍 Suivi", "📜 Archives"])

with t_saisie:
    c1, c2, c3 = st.columns(3)
    dt = c3.date_input("Date :", value=datetime.now())
    mask = df_edt['Enseignants'].str.contains(ens_v, na=False, case=False)
    promo = st.selectbox("Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == promo]
    g_s = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()))
    sg_s = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_s]['Sous groupe'].unique()))
    
    eff = df_p[(df_p['Groupe']==g_s) & (df_p['Sous groupe']==sg_s)]
    st.info(f"📊 Effectif : {len(eff)} étudiants")
    
    mat = st.selectbox("Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == promo)]['Enseignements'].unique()) if any(mask) else ["-"])
    abs_s = st.multiselect("❌ Absents :", options=eff['Full_N'].tolist())
    code = st.text_input("🔑 Code :", type="password")
    
    if st.button("🚀 VALIDER"):
        if hash_pw(code) == user['password_hash']:
            meta = {"promotion": promo, "matiere": mat, "enseignant": user.get('nom_officiel',''), "date_seance": str(dt), "nb_absents": len(abs_s)}
            for st_name in abs_s:
                safe_insert("archives_absences", {**meta, "etudiant_nom": st_name, "note_evaluation": "ABSENCE"})
            send_notification_admin(meta)
            st.success("Enregistré !"); st.balloons()
        else: st.error("Code erroné.")

with t_suivi:
    target = st.selectbox("Étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    if target != "--":
        adm = df_etudiants[df_etudiants['Full_N'] == target].iloc[0]
        res = supabase.table("archives_absences").select("*").eq("etudiant_nom", target).eq("note_evaluation", "ABSENCE").execute()
        if res.data:
            df_r = pd.DataFrame(res.data)
            recap = []
            for m, c in df_r['matiere'].value_counts().items():
                info = df_edt[(df_edt['Promotion'] == adm['Promotion']) & (df_edt['Enseignements'] == m)]
                recap.append({"Matière": m, "Absences": c, "Enseignant": info.iloc[0]['Enseignants'] if not info.empty else "N/A", "Jour": info.iloc[0]['Jours'] if not info.empty else "N/A"})
            st.table(pd.DataFrame(recap))
        else: st.success("Aucune absence.")

with t_hist:
    res_g = supabase.table("archives_absences").select("*").execute()
    if res_g.data: st.dataframe(pd.DataFrame(res_g.data), use_container_width=True)
