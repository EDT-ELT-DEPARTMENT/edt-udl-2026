import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import urllib.parse
import hashlib

# --- CONFIGURATION ---
st.set_page_config(page_title="Assiduité & Avancement - UDL SBA", layout="wide")
TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- CONNEXION SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_all_data():
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str).str.upper() + " " + df_etudiants['Prénom'].astype(str)
    return df_edt, df_etudiants

df_edt, df_etudiants = load_all_data()

st.markdown(f"#### {TITRE_OFFICIEL}")

# --- SYSTÈME DE GÉNÉRATION DE CODE UNIQUE ---
def generate_teacher_code(email):
    # Crée un code unique de 6 caractères basé sur l'email
    hash_object = hashlib.sha256(email.lower().encode())
    return hash_object.hexdigest()[:6].upper()

# --- INTERFACE DE CONNEXION ---
st.sidebar.header("🔑 Validation Enseignant")
email_input = st.sidebar.text_input("Entrez votre Email professionnel :", placeholder="enseignant@univ-sba.dz")

if email_input:
    user_code = generate_teacher_code(email_input)
    st.sidebar.info(f"Votre code de validation unique est : **{user_code}**")
    st.sidebar.caption("💡 Note : Ce code est strictement personnel et lié à votre email.")

# --- SÉLECTION ENSEIGNANT ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 1. Sélectionner l'Enseignant :", ["-- Choisir --"] + liste_profs)

if enseignant_sel != "-- Choisir --":
    tab_saisie, tab_historique = st.tabs(["📝 Saisie Séance", "📜 Historique"])

    with tab_saisie:
        # Filtres dynamiques
        promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        c1, c2 = st.columns(2)
        with c1:
            promo_sel = st.selectbox("🎓 Promotion (Obligatoire) :", ["-- Choisir --"] + promos_liees)
        
        if promo_sel != "-- Choisir --":
            with c2:
                filt = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
                matieres = sorted(df_edt[filt]['Enseignements'].unique())
                matiere_sel = st.selectbox("📖 Matière (Obligatoire) :", matieres)

            # Infos EDT
            info = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel) & (df_edt['Enseignements'] == matiere_sel)].iloc[0]
            st.success(f"📍 {info['Jours']} | {info['Horaire']} | Lieu: {info['Lieu']}")

            # Avancement
            st.subheader("📈 État d'Avancement & Appel")
            col_a, col_b = st.columns(2)
            with col_a:
                type_av = st.selectbox("Type d'unité :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°"])
                num_av = st.selectbox("Numéro :", list(range(1, 31)))
            with col_b:
                liste_eleves = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())
                absents_sel = st.multiselect("❌ Sélectionner les ABSENTS :", options=liste_eleves)

            # --- FORMULAIRE DE VALIDATION STRICTE ---
            with st.form("form_global"):
                date_r = st.date_input("📅 Date réelle de la séance :")
                obs = st.text_area("🗒️ Observations (Obligatoire) :")
                sign = st.text_input("✍️ Signature Nom Prénom (Obligatoire) :")
                code_entre = st.text_input("🔑 Entrez votre Code Unique généré à gauche :", type="password")
                
                btn_save = st.form_submit_button("🚀 ENREGISTRER & GÉNÉRER LE RAPPORT", use_container_width=True)

            if btn_save:
                # Vérification de tous les champs
                if not email_input:
                    st.error("⚠️ Vous devez entrer votre email dans la barre latérale pour générer votre code.")
                elif not sign or not obs or not code_entre:
                    st.error("⚠️ Tous les champs (Signature, Observations, Code) sont obligatoires.")
                elif code_entre != generate_teacher_code(email_input):
                    st.error("⚠️ Code de validation incorrect pour cet email.")
                else:
                    # Traitement des données
                    txt_abs = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                    av_final = f"{type_av} {num_av}"
                    full_info = f"Avanc: {av_final} | Lieu: {info['Lieu']} | Signé: {sign} | Email: {email_input}"
                    
                    # 1. Enregistrement Supabase
                    supabase.table("suivi_assiduite_2026").insert({
                        "enseignant": enseignant_sel, "matiere": matiere_sel,
                        "promotion": promo_sel, "absents": txt_abs, "note_etudiant": full_info
                    }).execute()
                    
                    # Session state pour affichage après rechargement
                    st.session_state['ready'] = {
                        "date": date_r, "prof": enseignant_sel, "mat": matiere_sel, "prom": promo_sel,
                        "av": av_final, "abs": txt_abs, "obs": obs, "sign": sign, "lieu": info['Lieu']
                    }
                    st.success("✅ Séance enregistrée avec succès !")

            # --- ZONE EXPORTS ET EMAIL ---
            if 'ready' in st.session_state:
                d = st.session_state['ready']
                df_exp = pd.DataFrame([d])

                st.divider()
                st.subheader("📥 Téléchargement des rapports")
                ce, ch = st.columns(2)
                
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as w:
                    df_exp.to_excel(w, index=False)
                ce.download_button("📥 Télécharger EXCEL", buf.getvalue(), f"Rapport_{d['date']}.xlsx")
                ch.download_button("📄 Télécharger HTML", df_exp.to_html(index=False), f"Rapport_{d['date']}.html", "text/html")

                st.divider()
                st.subheader("📧 Notification aux Responsables")
                
                dest_option = st.selectbox("Choisir le destinataire :", ["Chef de Département & Adjoint", "Responsable de Parcours"])
                dest_mail = "chef-dept@univ-sba.dz" if "Chef" in dest_option else "responsable@univ-sba.dz"
                
                sujet = f"RAPPORT - {d['prom']} - {d['mat']}"
                corps = f"Date: {d['date']}\nEnseignant: {d['prof']}\nAvancement: {d['av']}\nAbsents: {d['abs']}\nSigné: {d['sign']}"

                mailto_url = f"mailto:{dest_mail}?subject={urllib.parse.quote(sujet)}&body={urllib.parse.quote(corps)}"
                
                st.markdown(f'<a href="{mailto_url}" target="_self" style="text-decoration:none;"><div style="background-color:#D4442E;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">📧 CONFIRMER L\'ENVOI À : {dest_option}</div></a>', unsafe_allow_html=True)

    with tab_historique:
        st.subheader("📜 Mon Historique")
        res = supabase.table("suivi_assiduite_2026").select("*").eq("enseignant", enseignant_sel).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data)[["matiere", "promotion", "absents", "note_etudiant"]], use_container_width=True)
