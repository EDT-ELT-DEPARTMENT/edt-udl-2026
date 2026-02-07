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
        
        # On force l'interprétation du code comme du HTML
        msg.attach(MIMEText(corps, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
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

   # --- ONGLET : INSCRIPTION (VÉRIFICATION PAR EMAIL) ---
    with t_signup:
        st.subheader("📝 Inscription Enseignant")
        st.info("Entrez votre email professionnel pour recevoir votre code d'accès.")
        
        reg_e = st.text_input("Email Professionnel :", key="signup_email_field").strip().lower()
        
        if st.button("Vérifier et Envoyer mon Code", key="btn_signup_secure", use_container_width=True):
            # Vérification dans le fichier Excel du personnel
            staff_match = df_staff[df_staff['Email'].str.lower() == reg_e]
            
            if not staff_match.empty:
                inf = staff_match.iloc[0]
                # Génération d'un code secret de 6 chiffres
                code_secret = ''.join(random.choices(string.digits, k=6))
                
                # Envoi du mail avec le titre officiel
                sujet = "Activation Compte - Plateforme de gestion des EDTs-S2-2026"
                corps_html = f"""
                <div style="font-family: Arial; border: 1px solid #003366; padding: 20px; border-radius: 10px;">
                    <h2 style="color: #003366;">Bienvenue, {inf['Grade']} {inf['NOM']}</h2>
                    <p>Votre compte pour le Département d'Électrotechnique (UDL-SBA) a été pré-créé.</p>
                    <p style="font-size: 20px; background: #f4f4f4; padding: 10px; text-align: center; border: 1px dashed #003366;">
                        Votre code secret d'accès est : <b>{code_secret}</b>
                    </p>
                    <p style="color: red; font-size: 12px;">Note : Vous pourrez changer ce code dans votre profil après connexion.</p>
                </div>
                """
                
                if send_email_rapport([reg_e], sujet, corps_html):
                    # Inscription ou Mise à jour dans Supabase
                    check_exist = supabase.table("enseignants_auth").select("*").eq("email", reg_e).execute()
                    
                    data_user = {
                        "email": reg_e, 
                        "password_hash": hash_pw(code_secret),
                        "nom_officiel": inf['NOM'], 
                        "prenom_officiel": inf['PRÉNOM'],
                        "statut_enseignant": inf['Qualité'], 
                        "grade_enseignant": inf['Grade']
                    }
                    
                    if check_exist.data:
                        supabase.table("enseignants_auth").update(data_user).eq("email", reg_e).execute()
                    else:
                        supabase.table("enseignants_auth").insert(data_user).execute()
                        
                    st.success(f"✅ Code envoyé avec succès à {reg_e} !")
                    st.balloons()
                else:
                    st.error("❌ Erreur d'envoi d'email. Contactez l'administrateur.")
            else:
                st.error("❌ Cet email n'est pas reconnu dans la base du Département d'Électrotechnique.")

    # --- ONGLET : CODE OUBLIÉ ---
    with t_forgot:
        st.subheader("🔑 Récupération de compte")
        f_email = st.text_input("Saisissez votre email :", key="forgot_email_input")
        if st.button("Renvoyer un nouveau code", key="btn_forgot"):
            res = supabase.table("enseignants_auth").select("*").eq("email", f_email).execute()
            if res.data:
                new_c = ''.join(random.choices(string.digits, k=6))
                supabase.table("enseignants_auth").update({"password_hash": hash_pw(new_c)}).eq("email", f_email).execute()
                send_email_rapport([f_email], "Réinitialisation Code - UDL SBA", f"Votre nouveau code est : {new_c}")
                st.success("Un nouveau code a été envoyé dans votre boîte mail.")
            else: 
                st.error("Email non trouvé dans la base des inscrits.")

    # --- ONGLET : ESPACE ÉTUDIANT (EMPLOI DU TEMPS & ABSENCES) ---
    with t_student:
        st.subheader("🎓 Consultation Étudiant")
        nom_st = st.selectbox("Sélectionnez votre Nom & Prénom :", ["--"] + sorted(df_etudiants['Full_N'].unique()), key="student_view_name")
        
        if nom_st != "--":
            profil = df_etudiants[df_etudiants['Full_N'] == nom_st].iloc[0]
            st.warning(f"📋 **{profil['Promotion']}** | Groupe: **{profil['Groupe']}** | Sous-Groupe: **{profil['Sous groupe']}**")
            
            # Algorithme de filtrage de l'EDT dynamique
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
                st.markdown("#### 📅 Votre Emploi du Temps Hebdomadaire")
                
                # 1. Liste mise à jour selon VOTRE format (tiret collé)
                ordre_horaires = [
                    "8h-9h30", 
                    "9h30-11h", 
                    "11h-12h30", 
                    "12h30-14h", 
                    "14h-15h30", 
                    "15h30-17h"
                ]
                
                # 2. Ordre des jours
                jours_ordre = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
                
                # 3. Création du pivot table
                grid = edt_st.pivot_table(
                    index='Horaire', 
                    columns='Jours', 
                    values='Enseignements', 
                    aggfunc=lambda x: ' / '.join(x)
                ).fillna("")

                # 4. Extraction des index présents pour éviter les erreurs
                index_existants = [h for h in ordre_horaires if h in grid.index]
                # Sécurité : si un horaire n'est pas dans la liste ordre_horaires, on l'ajoute à la fin
                autres_horaires = [h for h in grid.index if h not in ordre_horaires]
                index_complet = index_existants + autres_horaires
                
                colonnes_existantes = [j for j in jours_ordre if j in grid.columns]

                # 5. Réindexation et affichage
                grid_final = grid.reindex(index=index_complet, columns=colonnes_existantes)
                st.dataframe(grid_final.style.applymap(color_edt), use_container_width=True)
            
            else:
                st.info(f"ℹ️ Aucun cours trouvé pour {nom_st}. Vérifiez la correspondance des groupes dans le fichier EDT.")

            st.markdown("---")
            st.markdown("#### ❌ Vos Absences & Notes de Participation")
            res_st = supabase.table("archives_absences").select("*").eq("etudiant_nom", nom_st).execute()
            
            if res_st.data:
                df_res_st = pd.DataFrame(res_st.data)[['date_seance', 'matiere', 'note_evaluation']]
                df_res_st.columns = ["Date", "Matière", "Statut / Note"]
                st.table(df_res_st)
            else:
                st.success("Excellent ! Aucune absence enregistrée pour vous.")
                
    st.stop()

# --- 5. ESPACE ENSEIGNANT CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = (user['email'] == EMAIL_ADMIN_TECH)
grade_fix = user.get('grade_enseignant', 'Enseignant')

st.markdown(f"<h4 style='text-align:center; border-bottom: 2px solid #003366; padding-bottom: 10px;'>{TITRE_PLATEFORME}</h4>", unsafe_allow_html=True)

with st.sidebar:
    # Récupération du prénom et du nom depuis les données utilisateur
    prenom = user.get('prenom_officiel', '')
    nom = user.get('nom_officiel', '')
    
    # Affichage complet : Prénom (1ère lettre Maj) et NOM (Tout en Maj)
    st.markdown(f"### 👤 {prenom.capitalize()} {nom.upper()}")
    
    st.markdown(f"**Grade :** {grade_fix}")
    st.markdown(f"**Statut :** {user.get('statut_enseignant', 'Permanent')}")
    st.divider()
    
    if is_admin:
        if "reset_counter" not in st.session_state:
            st.session_state.reset_counter = 0

        ens_actif = st.selectbox(
            "Vue Simulation (Admin) :", 
            sorted(df_edt['Enseignants'].unique()), 
            key=f"admin_sim_ens_{st.session_state.reset_counter}"
        )
        
        if 'confirm_reset' not in st.session_state:
            st.session_state.confirm_reset = False

        if not st.session_state.confirm_reset:
            if st.button("♻️ Réinitialiser Simulation", use_container_width=True, key="btn_reset_sim"):
                st.session_state.confirm_reset = True
                st.rerun()
        else:
            st.warning("Confirmer le reset ?")
            c1, c2 = st.columns(2)
            if c1.button("✅ Oui", use_container_width=True, key="admin_confirm_yes"):
                st.session_state.reset_counter += 1
                st.session_state.confirm_reset = False
                st.rerun()
            if c2.button("❌ Non", use_container_width=True, key="admin_confirm_no"):
                st.session_state.confirm_reset = False
                st.rerun()
    else:
        ens_actif = user['nom_officiel']

    # --- MODULE DE CHANGEMENT DE CODE ---
    st.divider()
    with st.expander("🔐 Modifier mon code secret"):
        st.write("Le nouveau code remplacera celui reçu par email.")
        old_p = st.text_input("Code actuel :", type="password", key="chng_old_p")
        new_p = st.text_input("Nouveau code :", type="password", key="chng_new_p")
        conf_p = st.text_input("Confirmer :", type="password", key="chng_conf_p")
        
        if st.button("Mettre à jour mon accès", use_container_width=True, key="btn_update_pass"):
            if hash_pw(old_p) == user['password_hash']:
                if new_p == conf_p and len(new_p) >= 4:
                    try:
                        supabase.table("enseignants_auth").update({
                            "password_hash": hash_pw(new_p)
                        }).eq("email", user['email']).execute()
                        st.session_state["user_data"]['password_hash'] = hash_pw(new_p)
                        st.success("✅ Code mis à jour !")
                    except Exception as e:
                        st.error(f"Erreur Supabase : {e}")
                else:
                    st.error("❌ Erreur : codes différents ou trop courts.")
            else:
                st.error("❌ L'ancien code est incorrect.")

    st.divider()
    # UN SEUL BOUTON DE DÉCONNEXION ICI AVEC UNE CLÉ UNIQUE
    if st.button("🚪 Déconnexion", use_container_width=True, key="sidebar_logout_final"):
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
            
            # --- CORRECTION DU NOM DE LA FONCTION ICI ---
            success_mail = send_email_rapport([EMAIL_CHEF_DEPT, EMAIL_ADJOINT], f"Rapport de séance - {m_sel} - {p_sel}", html_corps)
            
            if success_mail:
                st.success("✅ Archivage réussi et rapport HTML envoyé aux responsables !"); st.balloons()
            else:
                st.warning("✅ Archivage réussi, mais l'envoi de l'email a échoué (vérifiez vos identifiants SMTP).")
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
# --- ONGLET ADMIN (REGISTRE PROFESSIONNEL & ASSIDUITÉ) ---
with t_admin:
    if is_admin:
        # 1. Récupération des données
        res = supabase.table("archives_absences").select("*").execute()
        
        if res.data:
            df_all = pd.DataFrame(res.data)
            
            # --- PRÉPARATION DES DONNÉES ---
            # Colonnes pour le Registre
            col_ordre = ['etudiant_nom', 'promotion', 'groupe', 'matiere', 'note_evaluation', 'date_seance', 'enseignant']
            df_registre = df_all[[c for c in col_ordre if c in df_all.columns]].copy()
            df_registre.columns = ["Étudiant", "Promo", "Gr", "Matière", "Nature/Note", "Date", "Enseignant"]

            # Calcul de l'assiduité (on ne compte que les lignes de type 'Absence')
            df_abs_only = df_all[df_all['note_evaluation'].str.contains("Absence", na=False)].copy()
            
            # --- INTERFACE À DEUX VOLETS ---
            t_reg, t_assid = st.tabs(["📋 Registre Global", "📊 Cumul des Absences"])

            with t_reg:
                st.markdown("### 📄 Journal des Enseignements")
                st.metric("Total des fiches saisies", len(df_all))
                st.dataframe(df_registre.sort_values(by="Date", ascending=False), use_container_width=True)
                
                # Export Registre
                buf_r = io.BytesIO()
                df_registre.to_excel(buf_r, index=False, engine='xlsxwriter')
                st.download_button("📥 Télécharger Registre (.xlsx)", buf_r.getvalue(), "Registre_Global_UDL_2026.xlsx")

            with t_assid:
                st.markdown("### ❌ État de l'Assiduité par Module")
                if not df_abs_only.empty:
                    # Groupement pour compter les absences
                    recap = df_abs_only.groupby(['etudiant_nom', 'promotion', 'matiere']).size().reset_index(name='Total Absences')
                    recap = recap.sort_values(by='Total Absences', ascending=False)
                    recap.columns = ["Nom & Prénom", "Promotion", "Matière", "Nombre d'Absences"]

                    # Fonction pour colorer les étudiants en zone d'exclusion (3 absences ou plus)
                    def highlight_exclusion(val):
                        color = '#ffcccc' if isinstance(val, int) and val >= 3 else ''
                        return f'background-color: {color}'

                    st.write("⚠️ *Les cellules en rouge indiquent un seuil d'exclusion (>= 3 absences).*")
                    st.dataframe(
                        recap.style.applymap(highlight_exclusion, subset=["Nombre d'Absences"]),
                        use_container_width=True
                    )
                    
                    # Export Assiduité
                    buf_a = io.BytesIO()
                    recap.to_excel(buf_a, index=False, engine='xlsxwriter')
                    st.download_button("📥 Télécharger État des Absences", buf_a.getvalue(), "Recap_Assiduite_ELT.xlsx")
                else:
                    st.info("Aucune absence enregistrée pour le moment.")

            # --- ZONE DE DANGER (RESET) ---
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.expander("🚨 Zone de Maintenance"):
                st.warning("La suppression est irréversible.")
                if st.button("🗑️ VIDER TOUTES LES ARCHIVES", use_container_width=True):
                    # On utilise une variable de session pour la double confirmation
                    st.session_state.confirm_db_reset = True
                
                if st.session_state.get('confirm_db_reset', False):
                    st.error("ÊTES-VOUS ABSOLUMENT SÛR ?")
                    c1, c2 = st.columns(2)
                    if c1.button("🔥 OUI, SUPPRIMER TOUT"):
                        supabase.table("archives_absences").delete().neq("etudiant_nom", "NULL").execute()
                        st.session_state.confirm_db_reset = False
                        st.success("Base de données réinitialisée.")
                        st.rerun()
                    if c2.button("❌ ANNULER"):
                        st.session_state.confirm_db_reset = False
                        st.rerun()
        else:
            st.info("La base de données est vide.")
    else:
        st.warning("⚠️ Accès restreint à l'administrateur de la plateforme.")

























