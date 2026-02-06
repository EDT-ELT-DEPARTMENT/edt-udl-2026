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
    st.error("⚠️ Erreur Supabase : Vérifiez vos Secrets Streamlit.")
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
    """Envoi d'email au Chef de Département et à l'Adjoint"""
    destinataires = [EMAIL_CHEF_DEPT, EMAIL_ADJOINT]
    try:
        msg = MIMEMultipart()
        msg['From'] = f"EDT-UDL-SYSTEM <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = f"ALERTE : Rapport de Séance - {details['promotion']}"
        
        corps = f"""
        Bonjour,
        Un nouveau rapport de séance a été validé :
        - Enseignant : {details['enseignant']} ({details['statut']})
        - Matière : {details['matiere']}
        - Promotion : {details['promotion']}
        - Date : {details['date_seance']}
        - Nombre d'absents : {details['nb_absents']}
        - Observations : {details['obs']}
        """
        msg.attach(MIMEText(corps, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        st.warning(f"Notification email non envoyée : {e}")

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
    t_login, t_signup, t_student = st.tabs(["🔐 Connexion Enseignant", "📝 Inscription", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :")
        p_log = st.text_input("Code Unique :", type="password")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).eq("password_hash", hash_pw(p_log)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
        with st.expander("❓ Problème de connexion ?"):
            st.info(f"Contactez l'administrateur : {EMAIL_ADMIN_TECH}")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix_nom = st.selectbox("Sélectionnez votre nom dans la liste :", sorted(df_staff['Full_S'].unique()))
        inf_s = df_staff[df_staff['Full_S'] == choix_nom].iloc[0]
        st.warning(f"Profil détecté : {inf_s['Grade']} - {inf_s['Qualité']}")
        
        reg_e = st.text_input("Confirmez votre Email :", value=inf_s['Email'])
        reg_p = st.text_input("Créez votre Code Unique :", type="password")
        if st.button("Finaliser l'inscription"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf_s['NOM'], "prenom_officiel": inf_s['PRÉNOM'],
                "statut_enseignant": inf_s['Qualité'], "grade_enseignant": inf_s['Grade']
            }).execute()
            st.success("Compte créé avec succès !")

    with t_student:
        nom_st = st.selectbox("Recherchez votre Nom & Prénom :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.markdown(f"#### 📌 {profil['Promotion']} | Groupe : {profil['Groupe']} | Sous-groupe : {profil['Sous groupe']}")
            
            def filtrer_edt_etudiant(row):
                if str(row['Promotion']).strip().upper() != str(profil['Promotion']).strip().upper(): return False
                ens, code, lieu = str(row['Enseignements']).upper(), str(row['Code']).upper(), str(row['Lieu']).upper()
                if "COURS" in ens: return True
                num_g = re.findall(r'\d+', str(profil['Groupe']))[0] if re.findall(r'\d+', str(profil['Groupe'])) else ""
                if "TD" in ens:
                    if str(profil['Groupe']).upper() in (ens + lieu + code): return True
                    if num_g == "1" and "-A" in code: return True
                    if num_g == "2" and "-B" in code: return True
                num_sg = re.findall(r'\d+', str(profil['Sous groupe']))[0] if re.findall(r'\d+', str(profil['Sous groupe'])) else ""
                if "TP" in ens:
                    if str(profil['Sous groupe']).upper() in (ens + lieu + code): return True
                    suffixe = "A" if num_sg == "1" else "B" if num_sg == "2" else "C" if num_sg == "3" else ""
                    if f"-{suffixe}" in code: return True
                return False

            edt_final = df_edt[df_edt.apply(filtrer_edt_etudiant, axis=1)].copy()
            if not edt_final.empty:
                grid = edt_final.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                cols = [j for j in jours if j in grid.columns]
                grid = grid[cols]
                grid['h'] = grid.index.map(lambda x: int(re.search(r'\d+', str(x)).group(1)) if re.search(r'\d+', str(x)) else 0)
                grid = grid.sort_values('h').drop(columns='h')
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True)
            else: st.warning("Emploi du temps non disponible.")

            st.markdown("### ❌ Bilan des Absences")
            res_abs = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).eq("note_evaluation", "ABSENCE").execute()
            if res_abs.data:
                st.table(pd.DataFrame(res_abs.data).groupby(['matiere', 'enseignant']).size().reset_index(name='Total Absences'))
            else: st.info("Aucune absence signalée.")
            st.image(generate_qr_segno(f"ST:{nom_st}"), width=100)
    st.stop()

# --- 5. INTERFACE ENSEIGNANT & ADMINISTRATEUR ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)

st.markdown(f"<h4 style='text-align:center; color:#003366; border-bottom: 2px solid #003366;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user.get('nom_officiel','')} {user.get('prenom_officiel','')}")
    st.info(f"Grade : {user.get('grade_enseignant','')} \nStatut : {user.get('statut_enseignant','')}")
    
    if is_admin:
        st.success("🛡️ VUE ADMINISTRATEUR ACTIVE")
        ens_actif = st.selectbox("Simuler un enseignant :", sorted(df_edt['Enseignants'].unique()))
    else:
        ens_actif = user.get('nom_officiel','')

    if st.button("🔄 Reset / Actualiser"): st.rerun()
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state["user_data"] = None; st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET 1 : SAISIE ---
with t_saisie:
    c1, c2, c3 = st.columns(3)
    date_s = c3.date_input("Date du jour :", value=datetime.now())
    mask_e = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("Promotion :", sorted(df_edt[mask_e]['Promotion'].unique()) if any(mask_e) else sorted(df_edt['Promotion'].unique()))
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    g_sel = st.selectbox("Groupe :", sorted(df_p['Groupe'].unique()))
    sg_sel = st.selectbox("Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()))
    
    eff_list = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    st.markdown(f"📊 **Affichage Numérique : {len(eff_list)}** étudiants attendus.")
    
    m_sel = st.selectbox("Matière :", sorted(df_edt[mask_e & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask_e) else ["-"])
    abs_sel = st.multiselect("❌ Sélectionner les Absents :", options=eff_list['Full_N'].tolist())
    obs = st.text_area("Observations éventuelles :")
    code_v = st.text_input("🔑 Votre Code Unique :", type="password")
    
    if st.button("🚀 VALIDER LE RAPPORT", use_container_width=True, type="primary"):
        if hash_pw(code_v) == user['password_hash']:
            details = {
                "promotion": p_sel, "matiere": m_sel, "enseignant": user['nom_officiel'], 
                "statut": user['statut_enseignant'], "date_seance": str(date_s), 
                "nb_absents": len(abs_sel), "obs": obs
            }
            for student in abs_sel:
                safe_insert("archives_absences", {**details, "etudiant_nom": student, "note_evaluation": "ABSENCE"})
            
            # Alerte Chef de Dept et Adjoint
            send_notification_admin(details)
            st.success("Séance enregistrée et notifications envoyées !"); st.balloons()
        else: st.error("Code incorrect.")

# --- ONGLET 2 : SUIVI ---
with t_suivi:
    target = st.selectbox("Choisir un étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()))
    if target != "--":
        adm_i = df_etudiants[df_etudiants['Full_N'] == target].iloc[0]
        st.write(f"**Profil :** {adm_i['Promotion']} | {adm_i['Groupe']} | {adm_i['Sous groupe']}")
        res_s = supabase.table("archives_absences").select("*").eq("etudiant_nom", target).eq("note_evaluation", "ABSENCE").execute()
        if res_s.data:
            df_r = pd.DataFrame(res_s.data)
            recap = []
            for mat, count in df_r['matiere'].value_counts().items():
                info = df_edt[(df_edt['Promotion'] == adm_i['Promotion']) & (df_edt['Enseignements'] == mat)]
                recap.append({
                    "Matière": mat, "Total Absences": count,
                    "Enseignant": info.iloc[0]['Enseignants'] if not info.empty else "N/A",
                    "Jour": info.iloc[0]['Jours'] if not info.empty else "N/A"
                })
            st.table(pd.DataFrame(recap))
        else: st.success("Aucune absence.")

# --- ONGLET 3 : PANNEAU ADMIN (VUE CHEF DE DÉPARTEMENT) ---
with t_admin:
    if is_admin:
        st.markdown("### 🛡️ Gestion des Archives et Statistiques")
        res_g = supabase.table("archives_absences").select("*").execute()
        if res_g.data:
            df_global = pd.DataFrame(res_g.data)
            
            # Affichage Numérique des Statistiques
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Rapports", len(df_global['date_seance'].unique()))
            k2.metric("Total Absences", len(df_global))
            k3.metric("Étudiants Touchés", len(df_global['etudiant_nom'].unique()))
            
            st.divider()
            st.markdown("#### 📂 Registre complet")
            st.dataframe(df_global, use_container_width=True)
            
            # Exportation
            buf = io.BytesIO()
            df_global.to_excel(buf, index=False)
            st.download_button("📥 Télécharger Excel Global", buf.getvalue(), "Registre_Departement_2026.xlsx")
            
            if st.button("🗑️ Vider les archives (Action irréversible)", type="secondary"):
                st.error("Cette fonction est désactivée par mesure de sécurité.")
        else:
            st.info("Aucune donnée archivée pour le moment.")
    else:
        st.error("Accès réservé à l'administration technique et au Chef de Département.")
