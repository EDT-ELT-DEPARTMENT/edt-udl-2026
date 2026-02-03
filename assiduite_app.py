import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import urllib.parse

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Assiduité & Avancement - UDL SBA", layout="wide")

# Titre officiel requis
TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- CONNEXION SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erreur de configuration des secrets Supabase.")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_all_data():
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str).str.upper() + " " + df_etudiants['Prénom'].astype(str)
    return df_edt, df_etudiants

df_edt, df_etudiants = load_all_data()

st.markdown(f"#### {TITRE_OFFICIEL}")
st.header("📊 Suivi d'Assiduité et Avancement Pédagogique")

# --- FILTRES EN CASCADE ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 1. Sélectionner l'Enseignant :", ["-- Choisir --"] + liste_profs)

if enseignant_sel != "-- Choisir --":
    promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
    
    col_p, col_m = st.columns(2)
    with col_p:
        promo_sel = st.selectbox("🎓 2. Sélectionner la Promotion :", ["-- Choisir --"] + promos_liees)
    
    if promo_sel != "-- Choisir --":
        with col_m:
            filtre_seance = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
            matieres_dispo = sorted(df_edt[filtre_seance]['Enseignements'].unique())
            matiere_sel = st.selectbox("📖 3. Sélectionner la Matière :", matieres_dispo)

        # Récupération infos EDT
        infos = df_edt[(df_edt['Enseignants'] == enseignant_sel) & 
                       (df_edt['Promotion'] == promo_sel) & 
                       (df_edt['Enseignements'] == matiere_sel)].iloc[0]
        
        st.success(f"📍 **Planning :** {infos['Jours']} à {infos['Horaire']} | **Lieu :** {infos['Lieu']}")

        st.divider()

        # --- SECTION AVANCEMENT PÉDAGOGIQUE ---
        st.subheader("📈 État d'Avancement")
        col_type, col_num = st.columns(2)
        with col_type:
            type_avanc = st.selectbox("Type d'avancement :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°"])
        with col_num:
            num_avanc = st.selectbox("Numéro :", list(range(1, 31)))
        
        label_avancement = f"{type_avanc} {num_avanc}"

        # --- SECTION APPEL ---
        st.subheader(f"👥 Liste d'appel ({promo_sel})")
        etudiants_final = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())
        absents_sel = st.multiselect("❌ Cocher les étudiants ABSENTS :", options=etudiants_final)

        # --- VALIDATION ET EXPORT ---
        with st.form("form_global"):
            date_reelle = st.date_input("📅 Date du jour :")
            note_obs = st.text_area("🗒️ Observations complémentaires :")
            code_verif = st.text_input("🔑 Code Validation (2026) :", type="password")
            
            submit = st.form_submit_button("🚀 Enregistrer et Générer le Rapport", use_container_width=True)

        if submit:
            if code_verif == "2026":
                texte_absents = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                full_obs = f"Avancement: {label_avancement} | Lieu: {infos['Lieu']} | Obs: {note_obs}"
                
                # 1. Envoi Supabase
                data_db = {
                    "enseignant": enseignant_sel,
                    "matiere": matiere_sel,
                    "promotion": promo_sel,
                    "absents": texte_absents,
                    "note_etudiant": full_obs
                }
                supabase.table("suivi_assiduite_2026").insert(data_db).execute()
                
                st.success("✅ Données enregistrées dans Supabase.")

                # 2. Création du DataFrame pour export
                report_data = {
                    "Date": [date_reelle],
                    "Enseignant": [enseignant_sel],
                    "Matière": [matiere_sel],
                    "Promotion": [promo_sel],
                    "Avancement": [label_avancement],
                    "Lieu": [infos['Lieu']],
                    "Absents": [texte_absents],
                    "Observations": [note_obs]
                }
                df_report = pd.DataFrame(report_data)

                # --- BOUTONS DE TÉLÉCHARGEMENT ---
                st.divider()
                st.write("### 📥 Télécharger le rapport de séance")
                col_ex, col_ht = st.columns(2)
                
                # Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_report.to_excel(writer, index=False, sheet_name='Rapport')
                excel_data = output.getvalue()
                col_ex.download_button(label="📥 Télécharger EXCEL", data=excel_data, file_name=f"Rapport_{promo_sel}_{date_reelle}.xlsx")

                # HTML
                html_report = df_report.to_html(index=False).replace('<table', '<table style="width:100%; border:1px solid black;"')
                col_ht.download_button(label="📄 Télécharger HTML", data=html_report, file_name=f"Rapport_{promo_sel}_{date_reelle}.html", mime="text/html")

                # --- ENVOI EMAIL (MAILTO) ---
                st.divider()
                st.write("### 📧 Notification aux Responsables")
                
                subject = urllib.parse.quote(f"Rapport d'avancement et assiduité - {promo_sel}")
                body = urllib.parse.quote(
                    f"Bonjour,\n\nVoici le rapport du cours :\n"
                    f"- Enseignant: {enseignant_sel}\n"
                    f"- Matière: {matiere_sel}\n"
                    f"- Promotion: {promo_sel}\n"
                    f"- État d'avancement: {label_avancement}\n"
                    f"- Absents: {texte_absents}\n"
                    f"- Observations: {note_obs}\n\nCordialement."
                )
                
                # Adresses fictives à remplacer par les vraies
                mail_to = "chef-adjoint@univ-sba.dz,responsable-formation@univ-sba.dz"
                mailto_link = f"mailto:{mail_to}?subject={subject}&body={body}"
                
                st.markdown(f'<a href="{mailto_link}" style="display: inline-block; padding: 12px 20px; background-color: #D4442E; color: white; text-align: center; text-decoration: none; font-size: 16px; border-radius: 8px;">📧 Envoyer par Email au Chef de Dépt & Responsable</a>', unsafe_allow_html=True)
                
            else:
                st.error("⚠️ Code de validation incorrect.")
else:
    st.info("Sélectionnez un enseignant pour commencer.")
