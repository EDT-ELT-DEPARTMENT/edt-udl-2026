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

# --- CHARGEMENT DONNÉES ---
@st.cache_data
def load_all_data():
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str).str.upper() + " " + df_etudiants['Prénom'].astype(str)
    return df_edt, df_etudiants

df_edt, df_etudiants = load_all_data()

st.markdown(f"#### {TITRE_OFFICIEL}")

# --- LOGIQUE DE SÉLECTION ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 Sélectionner l'Enseignant :", ["-- Choisir --"] + liste_profs)

if enseignant_sel != "-- Choisir --":
    tab_saisie, tab_historique = st.tabs(["📝 Saisie Séance", "📜 Historique"])

    with tab_saisie:
        promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        c1, c2 = st.columns(2)
        with c1:
            promo_sel = st.selectbox("🎓 Promotion :", ["-- Choisir --"] + promos_liees)
        
        if promo_sel != "-- Choisir --":
            with c2:
                seance_filt = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
                matieres = sorted(df_edt[seance_filt]['Enseignements'].unique())
                matiere_sel = st.selectbox("📖 Matière :", matieres)

            # Infos EDT
            info = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel) & (df_edt['Enseignements'] == matiere_sel)].iloc[0]
            st.success(f"📍 {info['Jours']} | {info['Horaire']} | Lieu: {info['Lieu']}")

            # Avancement & Appel
            st.subheader("📈 Avancement & Appel")
            col_a, col_b = st.columns(2)
            with col_a:
                type_av = st.selectbox("Type :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°"])
                num_av = st.selectbox("Numéro :", list(range(1, 31)))
            with col_b:
                etudiants_promo = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())
                absents_sel = st.multiselect("❌ Sélectionner les ABSENTS :", options=etudiants_promo)

            with st.form("form_record"):
                date_j = st.date_input("📅 Date réelle :")
                obs = st.text_area("🗒️ Observations :")
                sign = st.text_input("✍️ Signature (Nom complet) :")
                code = st.text_input("🔑 Code (2026) :", type="password")
                btn_save = st.form_submit_button("💾 ENREGISTRER DANS LA BASE", use_container_width=True)

            if btn_save:
                if code == "2026" and sign:
                    txt_abs = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                    full_obs = f"Avancement: {type_av} {num_av} | Lieu: {info['Lieu']} | Signé: {sign} | Obs: {obs}"
                    
                    supabase.table("suivi_assiduite_2026").insert({
                        "enseignant": enseignant_sel, "matiere": matiere_sel,
                        "promotion": promo_sel, "absents": txt_abs, "note_etudiant": full_obs
                    }).execute()
                    
                    # Sauvegarde pour le mailto
                    st.session_state['data_mail'] = {
                        "date": date_j, "prof": enseignant_sel, "mat": matiere_sel,
                        "prom": promo_sel, "av": f"{type_av} {num_av}", "abs": txt_abs, "obs": obs, "sign": sign
                    }
                    st.success("✅ Enregistré ! Cliquez sur le bouton ci-dessous pour envoyer l'email.")

            # --- LOGIQUE MAILTO SÉCURISÉE ---
            if 'data_mail' in st.session_state:
                st.divider()
                m = st.session_state['data_mail']
                
                # Préparation des paramètres de l'URL
                dest = "chef-departement@univ-sba.dz,responsable-parcours@univ-sba.dz"
                sujet = f"RAPPORT - {m['prom']} - {m['mat']}"
                corps = (f"Rapport du {m['date']}\n"
                         f"Enseignant: {m['prof']}\n"
                         f"Avancement: {m['av']}\n"
                         f"Absents: {m['abs']}\n"
                         f"Obs: {m['obs']}\n\n"
                         f"Signé: {m['sign']}")

                # Encodage pour éviter les problèmes de caractères spéciaux
                mailto_url = f"mailto:{dest}?subject={urllib.parse.quote(sujet)}&body={urllib.parse.quote(corps)}"
                
                # Bouton HTML stylisé
                st.markdown(f"""
                    <a href="{mailto_url}" target="_self" style="text-decoration: none;">
                        <div style="background-color: #D4442E; color: white; padding: 18px; text-align: center; border-radius: 10px; font-weight: bold; font-size: 1.2rem; border: 2px solid #b33927;">
                            📧 CONFIRMER ET OUVRIR MON LOGICIEL EMAIL
                        </div>
                    </a>
                """, unsafe_allow_html=True)
                
                with st.expander("ℹ️ Si le bouton ne fonctionne pas"):
                    st.info("Vérifiez que vous avez une application mail (Outlook, Gmail) installée par défaut sur votre appareil.")
                    st.text_area("Copiez ce texte manuellement si besoin :", corps, height=150)

    with tab_historique:
        st.subheader("📜 Historique Personnel")
        res = supabase.table("suivi_assiduite_2026").select("*").eq("enseignant", enseignant_sel).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data)[["matiere", "promotion", "absents", "note_etudiant"]], use_container_width=True)
