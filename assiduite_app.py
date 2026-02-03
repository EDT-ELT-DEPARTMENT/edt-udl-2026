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
    # Source EDT
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    # Source Étudiants
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
    
    # Onglets pour séparer Saisie et Historique
    tab_saisie, tab_historique, tab_alertes = st.tabs(["📝 Nouvelle Séance", "📜 Historique Personnel", "⚠️ Alertes Absences"])

    with tab_saisie:
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
                    
                    data_db = {
                        "enseignant": enseignant_sel,
                        "matiere": matiere_sel,
                        "promotion": promo_sel,
                        "absents": texte_absents,
                        "note_etudiant": full_obs
                    }
                    supabase.table("suivi_assiduite_2026").insert(data_db).execute()
                    st.success("✅ Séance enregistrée avec succès.")

                    # Préparation Export
                    report_data = pd.DataFrame([{
                        "Date": date_reelle, "Enseignant": enseignant_sel, "Matière": matiere_sel,
                        "Promotion": promo_sel, "Avancement": label_avancement, "Absents": texte_absents
                    }])

                    # Boutons Téléchargement
                    col_ex, col_ht = st.columns(2)
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        report_data.to_excel(writer, index=False)
                    col_ex.download_button("📥 Télécharger EXCEL", output.getvalue(), f"Rapport_{date_reelle}.xlsx")
                    col_ht.download_button("📄 Télécharger HTML", report_data.to_html(index=False), f"Rapport_{date_reelle}.html", "text/html")

                    # Email
                    subject = urllib.parse.quote(f"Rapport d'avancement - {promo_sel}")
                    body = urllib.parse.quote(f"Enseignant: {enseignant_sel}\nPromo: {promo_sel}\nAvancement: {label_avancement}\nAbsents: {texte_absents}")
                    mailto_link = f"mailto:chef-adjoint@univ-sba.dz?subject={subject}&body={body}"
                    st.markdown(f'<a href="{mailto_link}" style="display:inline-block;padding:12px;background:#D4442E;color:white;border-radius:8px;text-decoration:none;">📧 Envoyer Email Responsables</a>', unsafe_allow_html=True)
                else:
                    st.error("⚠️ Code incorrect.")

    with tab_historique:
        st.subheader(f"📜 Historique des séances de M. {enseignant_sel}")
        response = supabase.table("suivi_assiduite_2026").select("*").eq("enseignant", enseignant_sel).execute()
        if response.data:
            df_hist = pd.DataFrame(response.data)
            # On réorganise les colonnes pour la lecture
            cols = ["id", "matiere", "promotion", "absents", "note_etudiant"]
            st.dataframe(df_hist[cols], use_container_width=True)
        else:
            st.write("Aucun historique trouvé.")

    with tab_alertes:
        st.subheader("⚠️ Signalement des Absences Répétées")
        limit = st.number_input("Seuil d'alerte (nb d'absences)", min_value=1, value=3)
        
        # Récupérer TOUTES les absences pour cet enseignant ou toute la base
        all_res = supabase.table("suivi_assiduite_2026").select("absents, promotion").execute()
        if all_res.data:
            # On crée une liste plate de tous les noms cités dans la colonne 'absents'
            absences_count = []
            for entry in all_res.data:
                if entry['absents'] and entry['absents'] != "Aucun absent":
                    noms = [n.strip() for n in entry['absents'].split(",")]
                    for nom in noms:
                        absences_count.append({"Etudiant": nom, "Promotion": entry['promotion']})
            
            if absences_count:
                df_count = pd.DataFrame(absences_count)
                # Groupement par étudiant et comptage
                recap_absences = df_count.groupby(["Etudiant", "Promotion"]).size().reset_index(name="Total_Absences")
                # Filtrage par le seuil
                alertes = recap_absences[recap_absences["Total_Absences"] >= limit].sort_values(by="Total_Absences", ascending=False)
                
                if not alertes.empty:
                    st.warning(f"Liste des étudiants ayant atteint ou dépassé {limit} absences :")
                    st.table(alertes)
                else:
                    st.success(f"Aucun étudiant n'a atteint le seuil de {limit} absences pour le moment.")
            else:
                st.write("Aucune absence enregistrée.")
else:
    st.info("Veuillez sélectionner un enseignant pour afficher les outils de gestion.")
