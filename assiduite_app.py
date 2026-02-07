import streamlit as st
import pandas as pd
import hashlib
import smtplib
import io
import segno
import re
import random
import string
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client

# --- 1. CONFIGURATION ET TITRE OFFICIEL ---
st.set_page_config(page_title="Plateforme EDT UDL", layout="wide")

TITRE_PLATEFORME = "Plateforme de gestion des enseignements et assuiduité des étudiants 2025-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

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
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("⚠️ Configuration Supabase manquante dans les secrets.")
        return None

supabase = init_connection()

# --- 3. FONCTIONS TECHNIQUES ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generate_qr(data):
    qr = segno.make(data)
    out = io.BytesIO()
    qr.save(out, kind='png', scale=10)
    return out.getvalue()

def send_email_rapport(destinataires, sujet, corps):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Gestion EDT-UDL <{EMAIL_SENDER}>"
        msg['To'] = ", ".join(destinataires)
        msg['Subject'] = sujet
        
        # CHANGEMENT ICI : On utilise 'html' au lieu de 'plain'
        msg.attach(MIMEText(corps, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        # Optionnel : st.error(f"Erreur SMTP : {e}") pour déboguer
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
                df[col] = df[col].astype(str).str.strip().replace(['nan', 'None', 'none', 'NAN'], '')
        return df_e, df_s, df_staff
    except Exception as e:
        st.error(f"Erreur de lecture Excel : {e}"); st.stop()

df_edt, df_etudiants, df_staff = load_data()
df_etudiants['Full_N'] = (df_etudiants['Nom'] + " " + df_etudiants['Prénom']).str.upper().str.strip()

def color_edt(val):
    if not val or val == "": return ""
    if "Cours" in val: return 'background-color: #d1e7dd; color: #084298; font-weight: bold;'
    if "Td" in val or "TD" in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
    if "TP" in val: return 'background-color: #cfe2ff; color: #004085; font-weight: bold;'
    return ''

# --- 4. AUTHENTIFICATION & ESPACES PUBLICS ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h2 style='text-align:center; color:#003366;'>🔑 {TITRE_PLATEFORME}</h2>", unsafe_allow_html=True)
    t_login, t_signup, t_forgot, t_student = st.tabs(["🔐 Connexion", "📝 Inscription", "❓ Code oublié", "🎓 Espace Étudiant"])
    
    with t_login:
        e_log = st.text_input("Email Professionnel :", key="main_log_e")
        p_log = st.text_input("Code Unique :", type="password", key="main_log_p")
        if st.button("Se connecter", use_container_width=True, key="btn_login"):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_log).execute()
            if res.data and res.data[0]['password_hash'] == hash_pw(p_log):
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Email ou code incorrect.")

    with t_signup:
        df_staff['Full_S'] = df_staff['NOM'] + " " + df_staff['PRÉNOM']
        choix = st.selectbox("Sélectionnez votre nom :", sorted(df_staff['Full_S'].unique()), key="signup_name")
        inf = df_staff[df_staff['Full_S'] == choix].iloc[0]
        st.info(f"Profil : {inf['Grade']} | {inf['Qualité']}")
        reg_e = st.text_input("Confirmer Email :", value=inf['Email'], key="signup_email")
        reg_p = st.text_input("Créer Code Unique :", type="password", key="signup_p")
        if st.button("Valider Inscription", key="btn_signup"):
            supabase.table("enseignants_auth").insert({
                "email": reg_e, "password_hash": hash_pw(reg_p),
                "nom_officiel": inf['NOM'], "prenom_officiel": inf['PRÉNOM'],
                "statut_enseignant": inf['Qualité'], "grade_enseignant": inf['Grade']
            }).execute()
            st.success("Compte créé !")

    with t_forgot:
        f_email = st.text_input("Email d'inscription :", key="forgot_email_input")
        if st.button("Récupérer mon code", key="btn_forgot"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_email_rapport([f_email], "Votre nouveau code UDL", f"Votre code est : {new_c}")
                st.success("Code envoyé par email.")
            else: st.error("Email inconnu.")

    with t_student:
        nom_st = st.selectbox("Nom de l'étudiant :", ["--"] + sorted(df_etudiants['Full_N'].unique()), key="student_view_name")
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.info(f"🎓 {profil['Promotion']} | Groupe {profil['Groupe']} | {profil['Sous groupe']}")
            
            def filter_st_edt(row):
                if str(row['Promotion']).upper() != str(profil['Promotion']).upper(): return False
                ens, code = str(row['Enseignements']).upper(), str(row['Code']).upper()
                if "COURS" in ens: return True
                num_g = re.findall(r'\d+', str(profil['Groupe']))[0] if re.findall(r'\d+', str(profil['Groupe'])) else ""
                if "TD" in ens:
                    if str(profil['Groupe']).upper() in code or (num_g == "1" and "-A" in code) or (num_g == "2" and "-B" in code): return True
                num_sg = re.findall(r'\d+', str(profil['Sous groupe']))[0] if re.findall(r'\d+', str(profil['Sous groupe'])) else ""
                if "TP" in ens:
                    suff = "A" if num_sg == "1" else "B" if num_sg == "2" else "C" if num_sg == "3" else ""
                    if suff and f"-{suff}" in code: return True
                return False

            edt_st = df_edt[df_edt.apply(filter_st_edt, axis=1)].copy()
            if not edt_st.empty:
                grid = edt_st.pivot_table(index='Horaire', columns='Jours', values='Enseignements', aggfunc=lambda x: ' / '.join(x)).fillna("")
                grid = grid.reindex(columns=["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"])
                st.dataframe(grid.style.applymap(color_edt), use_container_width=True)
            
            st.markdown("### ❌ Absences & Évaluations")
            res_st = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            if res_st.data:
                st.table(pd.DataFrame(res_st.data)[['date_seance', 'matiere', 'note_evaluation']])
    st.stop()

# --- 5. ESPACE ENSEIGNANT CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
grade_fix = user.get('grade_enseignant', 'Enseignant')

st.markdown(f"<h4 style='text-align:center; border-bottom: 2px solid #003366; padding-bottom: 10px;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"### 👤 {user['nom_officiel']}")
    st.markdown(f"**Grade :** {grade_fix}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        # 1. On initialise un compteur de reset dans le session_state s'il n'existe pas
        if "reset_counter" not in st.session_state:
            st.session_state.reset_counter = 0

        # 2. La clé du selectbox change si le compteur change, ce qui force le reset
        ens_actif = st.selectbox(
            "Vue Simulation (Admin) :", 
            sorted(df_edt['Enseignants'].unique()), 
            key=f"admin_sim_ens_{st.session_state.reset_counter}"
        )
        
        # 3. Système de Reset avec Confirmation
        if 'confirm_reset' not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:
            if st.button("♻️ Réinitialiser Simulation", use_container_width=True):
                st.session_state.confirm_reset = True
                st.rerun()
        else:
            st.warning("Confirmer le reset ?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Oui", use_container_width=True):
                    # AU LIEU DE MODIFIER LA VALEUR, ON CHANGE LA CLÉ DU WIDGET
                    st.session_state.reset_counter += 1
                    st.session_state.confirm_reset = False
                    st.rerun()
            with c2:
                if st.button("❌ Non", use_container_width=True):
                    st.session_state.confirm_reset = False
                    st.rerun()
    else:
        ens_actif = user['nom_officiel']

    st.markdown("---")

    if st.button("🚪 Déconnexion", use_container_width=True, key="btn_logout_sidebar"):
        st.session_state["user_data"] = None
        st.rerun()

t_saisie, t_suivi, t_admin = st.tabs(["📝 Saisie Rapport", "🔍 Suivi Étudiant", "🛡️ Panneau Admin"])

# --- ONGLET SAISIE ---
with t_saisie:
    st.markdown("### ⚙️ Paramètres de la Séance")
    charge = st.radio("Régime :", ["Charge Normale", "Heures Supplémentaires"], horizontal=True, key="saisie_regime")
    
    c1, c2, c3 = st.columns(3)
    type_seance = c1.selectbox("Type :", ["Cours", "TD", "TP", "Examen", "Rattrapage"], key="saisie_type")
    date_s = c3.date_input("Date réelle :", value=datetime.now(), key="saisie_date")
    
    mask = df_edt['Enseignants'].str.contains(ens_actif, na=False, case=False)
    p_sel = st.selectbox("🎓 Promotion :", sorted(df_edt[mask]['Promotion'].unique()) if any(mask) else sorted(df_edt['Promotion'].unique()), key="saisie_promo")
    
    df_p = df_etudiants[df_etudiants['Promotion'] == p_sel]
    cg, csg = st.columns(2)
    g_sel = cg.selectbox("👥 Groupe :", sorted(df_p['Groupe'].unique()) if not df_p.empty else ["G1"], key="saisie_grp")
    sg_sel = csg.selectbox("🔢 Sous-groupe :", sorted(df_p[df_p['Groupe']==g_sel]['Sous groupe'].unique()) if not df_p.empty else ["SG1"], key="saisie_sgrp")
    
    # AFFICHAGE NUMÉRIQUE
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Effectif Promo", len(df_p))
    m2.metric(f"Groupe {g_sel}", len(df_p[df_p['Groupe']==g_sel]))
    m3.metric(f"S-Groupe {sg_sel}", len(df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]))
    st.markdown("---")

    m_sel = st.selectbox("📖 Matière :", sorted(df_edt[mask & (df_edt['Promotion'] == p_sel)]['Enseignements'].unique()) if any(mask) else ["-"], key="saisie_matiere")
    
    # --- ❌ GESTION DES ABSENCES ---
    st.markdown("### ❌ Gestion des Absences")
    eff_liste = df_p[(df_p['Groupe']==g_sel) & (df_p['Sous groupe']==sg_sel)]
    
    abs_collective = st.checkbox("🚩 SIGNALER UNE ABSENCE COLLECTIVE", key="cb_abs_coll")
    
    if abs_collective:
        absents_final = eff_liste['Full_N'].tolist()
        st.warning(f"⚠️ {len(absents_final)} étudiants seront marqués absents.")
        type_abs = "Absence Collective"
    else:
        absents_final = st.multiselect("Sélectionner les étudiants absents :", options=eff_liste['Full_N'].tolist(), key="ms_absents")
        type_abs = st.selectbox("Nature de l'absence :", ["Absence non justifiée", "Absence justifiée", "Exclusion"], key="sb_nature_abs")

    st.divider()
    
    # --- 📝 NOTATION ---
    st.markdown("### 📝 Notation / Participation")
    cn1, cn2, cn3 = st.columns(3)
    etudiant_note = cn1.selectbox("Cibler un étudiant :", ["Aucun"] + eff_liste['Full_N'].tolist(), key="sb_note_target")
    critere = cn2.selectbox("Evaluation :", ["Test", "Examen de TD", "Examen de TP", "Participation", "Interrogation"], key="sb_note_critere")
    valeur = cn3.text_input("Note/Observation :", key="ti_note_val")

    obs = st.text_area("🗒️ Observations générales :", key="ta_obs_gen")
    code_v = st.text_input("🔑 Code Unique pour archivage :", type="password", key="ti_code_v")
    
    if st.button("🚀 VALIDER LE RAPPORT ET ENVOYER EMAILS", use_container_width=True, type="primary", key="btn_validate_all"):
        if hash_pw(code_v) == user['password_hash']:
            
            # --- SÉCURITÉ : ÉVITER ABSENT + ÉVALUÉ ---
            # On crée une copie de la liste pour ne pas modifier l'affichage du multiselect
            liste_absents_reelle = absents_final.copy()
            
            if etudiant_note != "Aucun" and etudiant_note in liste_absents_reelle:
                liste_absents_reelle.remove(etudiant_note)
                st.warning(f"🔄 **Note :** {etudiant_note} a été retiré de la liste des absences car il/elle a reçu une évaluation.")

            # 1. Archivage Absences (via la liste corrigée)
            for name in liste_absents_reelle:
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, 
                    "matiere": m_sel, 
                    "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), 
                    "etudiant_nom": name, 
                    "note_evaluation": type_abs,
                    "observations": f"{charge} | {type_seance}", 
                    "categorie_seance": charge,
                    "groupe": g_sel,         # Important pour l'affichage Suivi
                    "sous_groupe": sg_sel    # Important pour l'affichage Suivi
                }).execute()
            
            # 2. Archivage Note
            if etudiant_note != "Aucun":
                supabase.table("archives_absences").insert({
                    "promotion": p_sel, 
                    "matiere": m_sel, 
                    "enseignant": f"{grade_fix} {user['nom_officiel']}",
                    "date_seance": str(date_s), 
                    "etudiant_nom": etudiant_note, 
                    "note_evaluation": f"{critere}: {valeur}",
                    "observations": obs, 
                    "categorie_seance": charge,
                    "groupe": g_sel,
                    "sous_groupe": sg_sel
                }).execute()
            
            # --- 3. GÉNÉRATION DU RAPPORT HTML ET ENVOI ---
            # Préparation de la liste des noms des absents en format HTML
            noms_absents_html = "".join([f"<li style='color: #cc0000;'>{n}</li>" for n in liste_absents_reelle])
            if not noms_absents_html: 
                noms_absents_html = "<li>Aucun absent (Présence totale)</li>"

            html_corps = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 700px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #003366; color: white; padding: 20px; text-align: center;">
                        <h2 style="margin: 0;">Rapport de Séance d'Enseignement</h2>
                        <p style="margin: 5px 0 0 0;">Département d'Électrotechnique - UDL SBA</p>
                    </div>
                    
                    <div style="padding: 20px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background-color: #f9f9f9;">
                                <th style="text-align: left; padding: 10px; border-bottom: 1px solid #eee; width: 35%;">Enseignant</th>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">{grade_fix} {user['nom_officiel']}</td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 10px; border-bottom: 1px solid #eee;">Matière</th>
                                <td style="padding: 10px; border-bottom: 1px solid #eee; font-weight: bold; color: #003366;">{m_sel}</td>
                            </tr>
                            <tr style="background-color: #f9f9f9;">
                                <th style="text-align: left; padding: 10px; border-bottom: 1px solid #eee;">Date & Promotion</th>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">{date_s} | <b>{p_sel}</b></td>
                            </tr>
                            <tr>
                                <th style="text-align: left; padding: 10px; border-bottom: 1px solid #eee;">Groupe / S-Groupe</th>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;">{g_sel} / {sg_sel} ({charge})</td>
                            </tr>
                            <tr style="background-color: #fffde7;">
                                <th style="text-align: left; padding: 10px; border-bottom: 1px solid #eee;">Évaluation (Note)</th>
                                <td style="padding: 10px; border-bottom: 1px solid #eee; color: #d32f2f; font-weight: bold;">
                                    {etudiant_note if etudiant_note != "Aucun" else "Néant"} 
                                    {f'({critere}: {valeur})' if etudiant_note != "Aucun" else ""}
                                </td>
                            </tr>
                        </table>

                        <h4 style="color: #003366; border-bottom: 2px solid #003366; padding-bottom: 5px; margin-top: 25px;">🗒️ Observations</h4>
                        <p style="background: #f4f4f4; padding: 10px; border-left: 4px solid #003366;">{obs if obs else "RAS"}</p>

                        <h4 style="color: #cc0000; border-bottom: 2px solid #cc0000; padding-bottom: 5px; margin-top: 25px;">❌ Liste des Absents ({len(liste_absents_reelle)})</h4>
                        <ul style="column-count: 2; -webkit-column-count: 2; list-style-type: square; padding-left: 20px;">
                            {noms_absents_html}
                        </ul>
                    </div>
                    
                    <div style="background-color: #f1f1f1; padding: 10px; text-align: center; font-size: 11px; color: #777;">
                        Ceci est un rapport automatique généré par la Plateforme de gestion des EDTs-S2-2026.
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Utilisation de la fonction d'envoi (assurez-vous d'utiliser 'html' dans send_email_rapport)
            # Modifiez votre fonction send_email_rapport pour accepter MIMEMultipart avec subtype='html'
            success_mail = send_email_rapport_html([EMAIL_CHEF_DEPT, EMAIL_ADJOINT], f"Rapport UDL - {m_sel} - {p_sel}", html_corps)
            
            if success_mail:
                st.success("✅ Archivage réussi et rapport HTML envoyé aux responsables !"); st.balloons()
            else:
                st.warning("✅ Archivage réussi, mais l'envoi de l'email a échoué.")
        else: 
            st.error("Code de validation incorrect.")

# --- ONGLET SUIVI ÉTUDIANT (VERSION PRATIQUE AVEC EXPORT GLOBAL) ---
with t_suivi:
    st.markdown("### 🔍 Dossier Pédagogique & Assiduité")
    
    # Chargement de la source Excel pour enrichir les données
    @st.cache_data
    def get_source_data():
        try:
            df_src = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
            return df_src[['Enseignements', 'Enseignants', 'Horaire']]
        except:
            return None

    df_info_suivi = get_source_data()

    # Récupération des noms existants dans la base
    res_noms = supabase.table("archives_absences").select("etudiant_nom").execute()
    liste_noms_existants = sorted(list(set([r['etudiant_nom'] for r in res_noms.data]))) if res_noms.data else []
    
    # AJOUT DE L'OPTION "TOUT SÉLECTIONNER"
    options_selection = ["--", "Afficher TOUT (Export global)"] + liste_noms_existants

    # --- SECTION A : ASSIDUITÉ ---
    st.subheader("❌ 1. État de l'Assiduité (Absences)")
    nom_abs = st.selectbox("Sélectionner l'étudiant ou global :", options_selection, key="search_abs")

    if nom_abs != "--":
        query_a = supabase.table("archives_absences").select("*")
        if nom_abs != "Afficher TOUT (Export global)":
            query_a = query_a.eq("etudiant_nom", nom_abs)
        
        res_a = query_a.execute()
        if res_a.data:
            df_all_a = pd.DataFrame(res_a.data)
            df_assiduite = df_all_a[df_all_a['note_evaluation'].str.contains("Absence", na=False)].copy()
            
            if not df_assiduite.empty:
                # Jointure avec le fichier source
                if df_info_suivi is not None:
                    df_assiduite = df_assiduite.merge(df_info_suivi, left_on='matiere', right_on='Enseignements', how='left')
                
                df_assiduite['G/SG'] = df_assiduite['groupe'].astype(str) + " / " + df_assiduite['sous_groupe'].astype(str)
                df_view_a = df_assiduite[['etudiant_nom', 'promotion', 'G/SG', 'matiere', 'Enseignants', 'Horaire', 'date_seance', 'note_evaluation']]
                df_view_a.columns = ['Nom & Prénom', 'Promotion', 'G/SG', 'Matière', 'Chargé', 'Horaire', 'Date', 'Type']
                
                st.dataframe(df_view_a.sort_values(by=["Date", "Nom & Prénom"], ascending=False), use_container_width=True)
                
                # BOUTON EXPORT EXCEL ASSIDUITÉ
                buf_a = io.BytesIO()
                df_view_a.to_excel(buf_a, index=False, engine='xlsxwriter')
                st.download_button(
                    label=f"📥 Télécharger l'Assiduité ({'Global' if nom_abs.startswith('Afficher') else nom_abs})",
                    data=buf_a.getvalue(),
                    file_name=f"Assiduite_{'Global' if nom_abs.startswith('Afficher') else nom_abs}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Aucune absence trouvée.")

    st.divider()

    # --- SECTION B : ÉVALUATIONS ---
    st.subheader("📝 2. Résultats des Évaluations (Evaluations)")
    nom_eval = st.selectbox("Sélectionner l'étudiant ou global :", options_selection, key="search_eval")

    if nom_eval != "--":
        query_e = supabase.table("archives_absences").select("*")
        if nom_eval != "Afficher TOUT (Export global)":
            query_e = query_e.eq("etudiant_nom", nom_eval)
            
        res_e = query_e.execute()
        if res_e.data:
            df_all_e = pd.DataFrame(res_e.data)
            df_evals = df_all_e[df_all_e['note_evaluation'].str.contains(":", na=False)].copy()
            
            if not df_evals.empty:
                if df_info_suivi is not None:
                    df_evals = df_evals.merge(df_info_suivi, left_on='matiere', right_on='Enseignements', how='left')
                
                df_evals['G/SG'] = df_evals['groupe'].astype(str) + " / " + df_evals['sous_groupe'].astype(str)
                df_view_e = df_evals[['etudiant_nom', 'promotion', 'G/SG', 'matiere', 'Enseignants', 'Horaire', 'date_seance', 'note_evaluation', 'observations']]
                df_view_e.columns = ['Nom & Prénom', 'Promotion', 'G/SG', 'Matière', 'Chargé de Matière', 'Horaire', 'Date', 'Evaluation (Note)', 'Observations']
                
                st.dataframe(df_view_e.sort_values(by=["Date", "Nom & Prénom"], ascending=False), use_container_width=True)
                
                # BOUTON EXPORT EXCEL ÉVALUATIONS
                buf_e = io.BytesIO()
                df_view_e.to_excel(buf_e, index=False, engine='xlsxwriter')
                st.download_button(
                    label=f"📥 Télécharger les Évaluations ({'Global' if nom_eval.startswith('Afficher') else nom_eval})",
                    data=buf_e.getvalue(),
                    file_name=f"Evaluations_{'Global' if nom_eval.startswith('Afficher') else nom_eval}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Aucune évaluation trouvée.")

# --- ONGLET ADMIN ---
with t_admin:
    if is_admin:
        # 1. Récupération des données pour l'affichage
        res = supabase.table("archives_absences").select("*").execute()
        
        if res.data:
            df_all = pd.DataFrame(res.data)
            
            # --- ENTÊTE ET EXPORT ---
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Total Enregistrements", len(df_all))
            with col2:
                buf = io.BytesIO()
                df_all.to_excel(buf, index=False, engine='xlsxwriter')
                st.download_button(
                    label="📊 Exporter Registre Complet (Excel)",
                    data=buf.getvalue(),
                    file_name="Archives_Globales_2026.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_download_admin"
                )

            # --- AFFICHAGE DU TABLEAU ---
            st.dataframe(df_all, use_container_width=True)

            # --- ZONE DE DANGER : RESET DU TABLEAU ---
            st.divider()
            st.subheader("⚠️ Zone de Danger")
            
            # Initialisation de l'état de confirmation
            if 'confirm_db_reset' not in st.session_state:
                st.session_state.confirm_db_reset = False

            if not st.session_state.confirm_db_reset:
                if st.button("🗑️ Vider complètement le tableau", use_container_width=True, help="Supprime définitivement toutes les archives"):
                    st.session_state.confirm_db_reset = True
                    st.rerun()
            else:
                st.error("❗ ÊTES-VOUS SÛR ? Cette action supprimera les données de Supabase définitivement.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔥 OUI, Tout supprimer", use_container_width=True):
                        # Suppression effective dans Supabase
                        supabase.table("archives_absences").delete().neq("etudiant_nom", "NULL_PROTECT").execute()
                        st.session_state.confirm_db_reset = False
                        st.success("Base de données réinitialisée !")
                        st.rerun()
                with c2:
                    if st.button("❌ Annuler", use_container_width=True):
                        st.session_state.confirm_db_reset = False
                        st.rerun()
        else:
            st.info("La base de données est actuellement vide.")
            
    else:
        st.warning("Espace réservé à l'administration.")
















