import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import urllib.parse

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

# --- SÉLECTION ENSEIGNANT ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 Sélectionner l'Enseignant :", ["-- Choisir --"] + liste_profs)

if enseignant_sel != "-- Choisir --":
    tab_saisie, tab_historique, tab_alertes = st.tabs(["📝 Saisie Séance", "📜 Historique", "⚠️ Alertes"])

    with tab_saisie:
        # Filtres dynamiques
        promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        col1, col2 = st.columns(2)
        with col1:
            promo_sel = st.selectbox("🎓 Promotion :", ["-- Choisir --"] + promos_liees)
        
        if promo_sel != "-- Choisir --":
            with col2:
                filtre = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
                matieres = sorted(df_edt[filtre]['Enseignements'].unique())
                matiere_sel = st.selectbox("📖 Matière :", matieres)

            # Infos EDT automatiques
            info_ligne = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel) & (df_edt['Enseignements'] == matiere_sel)].iloc[0]
            st.info(f"📍 {info_ligne['Jours']} | {info_ligne['Horaire']} | Lieu: {info_ligne['Lieu']}")

            # Avancement
            st.subheader("📈 Avancement Pédagogique")
            ca1, ca2 = st.columns(2)
            with ca1:
                type_av = st.selectbox("Type :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°"])
            with ca2:
                num_av = st.selectbox("Numéro :", list(range(1, 31)))
            
            # Appel
            st.subheader(f"👥 Appel ({promo_sel})")
            liste_noms = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())
            absents_sel = st.multiselect("❌ Sélectionner les ABSENTS :", options=liste_noms)

            # Enregistrement
            with st.form("form_val"):
                date_j = st.date_input("📅 Date réelle :")
                obs = st.text_area("🗒️ Observations :")
                code = st.text_input("🔑 Code (2026) :", type="password")
                btn_save = st.form_submit_button("💾 1. Enregistrer dans la Base", use_container_width=True)

            if btn_save:
                if code == "2026":
                    txt_abs = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                    avanc_txt = f"{type_av} {num_av}"
                    full_obs = f"Avancement: {avanc_txt} | Lieu: {info_ligne['Lieu']} | Obs: {obs}"
                    
                    # Supabase
                    supabase.table("suivi_assiduite_2026").insert({
                        "enseignant": enseignant_sel, "matiere": matiere_sel,
                        "promotion": promo_sel, "absents": txt_abs, "note_etudiant": full_obs
                    }).execute()
                    
                    st.success("✅ Enregistré en base de données. Vous pouvez maintenant exporter et envoyer l'email.")
                    
                    # Stockage temporaire pour l'email et l'export
                    st.session_state['last_data'] = {
                        "date": date_j, "prof": enseignant_sel, "mat": matiere_sel,
                        "prom": promo_sel, "av": avanc_txt, "abs": txt_abs, "obs": obs
                    }

            # --- ZONE DE CONFIRMATION D'ENVOI ET EXPORT ---
            if 'last_data' in st.session_state:
                st.divider()
                st.subheader("📤 Confirmation et Envoi")
                d = st.session_state['last_data']
                
                c_ex, c_em = st.columns(2)
                
                with c_ex:
                    df_exp = pd.DataFrame([d])
                    # Export Excel
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as w:
                        df_exp.to_excel(w, index=False)
                    st.download_button("📥 Télécharger Rapport Excel", buf.getvalue(), f"Rapport_{d['date']}.xlsx")

                with c_em:
                    # Préparation Email
                    destinataires = "chef-departement@univ-sba.dz, responsable-parcours@univ-sba.dz"
                    sujet = f"Rapport d'assiduité - {d['prom']} - {d['mat']}"
                    corps = (f"Bonjour,\n\nVoici le rapport de séance du {d['date']}:\n\n"
                             f"Enseignant: {d['prof']}\nPromotion: {d['prom']}\n"
                             f"Matière: {d['mat']}\nAvancement: {d['av']}\n"
                             f"Absents: {d['abs']}\nObservations: {d['obs']}\n\nCordialement.")
                    
                    mailto = f"mailto:{destinataires}?subject={urllib.parse.quote(sujet)}&body={urllib.parse.quote(corps)}"
                    
                    st.warning("⚠️ Cliquez ci-dessous pour confirmer l'envoi au Chef de Département et Responsable.")
                    st.markdown(f'<a href="{mailto}" target="_blank" style="display: block; width: 100%; padding: 10px; background-color: #FF4B4B; color: white; text-align: center; border-radius: 5px; text-decoration: none; font-weight: bold;">📧 CONFIRMER ET ENVOYER L\'EMAIL</a>', unsafe_allow_html=True)

    with tab_historique:
        st.subheader("📜 Mes dernières séances")
        res = supabase.table("suivi_assiduite_2026").select("*").eq("enseignant", enseignant_sel).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data)[["matiere", "promotion", "absents", "note_etudiant"]], use_container_width=True)

    with tab_alertes:
        st.subheader("⚠️ Alertes Absences (+3 séances)")
        # Logique de calcul identique à la précédente
        all_d = supabase.table("suivi_assiduite_2026").select("absents, promotion").execute()
        if all_d.data:
            counts = []
            for r in all_d.data:
                if r['absents'] and r['absents'] != "Aucun absent":
                    for n in r['absents'].split(","):
                        counts.append({"Etudiant": n.strip(), "Promotion": r['promotion']})
            if counts:
                df_c = pd.DataFrame(counts)
                recap = df_c.groupby(["Etudiant", "Promotion"]).size().reset_index(name="Absences")
                st.table(recap[recap["Absences"] >= 3])
