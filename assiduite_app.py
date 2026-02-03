import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import urllib.parse
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Assiduité & Avancement - UDL SBA", layout="wide")

# Titre officiel requis par vos instructions
TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- CONNEXION SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erreur de configuration des secrets Supabase. Vérifiez le panneau Settings.")

# --- CHARGEMENT DES SOURCES DE DONNÉES ---
@st.cache_data
def load_all_data():
    # Source 1 : Emploi du temps (EDT)
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    # Source 2 : Liste des étudiants
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    # Préparation du nom complet (NOM en majuscules + Prénom)
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str).str.upper() + " " + df_etudiants['Prénom'].astype(str)
    return df_edt, df_etudiants

df_edt, df_etudiants = load_all_data()

# --- INTERFACE PRINCIPALE ---
st.markdown(f"#### {TITRE_OFFICIEL}")
st.header("📝 Registre d'Assiduité et État d'Avancement")

# --- BARRE LATÉRALE : MAINTENANCE ---
with st.sidebar:
    st.header("🛠️ Maintenance")
    with st.expander("Réinitialisation du système"):
        pwd_maint = st.text_input("Code Maintenance :", type="password")
        if st.button("🗑️ Reset Table Assiduité"):
            if pwd_maint == "ADMIN-RESET-2026":
                st.warning("Action de réinitialisation demandée. Contactez l'administrateur de la base.")
            else:
                st.error("Code de maintenance incorrect.")

# --- ÉTAPE 1 : SÉLECTION DE L'ENSEIGNANT ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 1. Sélectionner votre nom (Enseignant) :", ["-- Choisir Enseignant --"] + liste_profs)

if enseignant_sel != "-- Choisir Enseignant --":
    tab_saisie, tab_historique = st.tabs(["📝 Nouvelle Séance", "📜 Historique Personnel"])

    with tab_saisie:
        # --- FILTRES EN CASCADE ---
        promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        
        col1, col2 = st.columns(2)
        with col1:
            promo_sel = st.selectbox("🎓 2. Sélectionner la Promotion :", ["-- Choisir Promotion --"] + promos_liees)
        
        if promo_sel != "-- Choisir Promotion --":
            with col2:
                # Filtrer les matières par Enseignant ET Promotion
                filt_mat = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
                matieres_dispo = sorted(df_edt[filt_mat]['Enseignements'].unique())
                matiere_sel = st.selectbox("📖 3. Sélectionner la Matière :", matieres_dispo)

            # Récupération automatique des infos EDT (Lieu, Jour, Horaire)
            info_ligne = df_edt[(df_edt['Enseignants'] == enseignant_sel) & 
                                (df_edt['Promotion'] == promo_sel) & 
                                (df_edt['Enseignements'] == matiere_sel)].iloc[0]
            
            st.success(f"📍 **Détails planifiés :** {info_ligne['Jours']} | {info_ligne['Horaire']} | **Lieu :** {info_ligne['Lieu']}")

            st.divider()

            # --- AVANCEMENT PÉDAGOGIQUE ---
            st.subheader("📈 État d'Avancement")
            av1, av2 = st.columns(2)
            with av1:
                type_av = st.selectbox("Type d'unité :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°"])
            with av2:
                num_av = st.selectbox("Numéro de l'unité :", list(range(1, 31)))
            
            label_avancement = f"{type_av} {num_av}"

            # --- APPEL DES ÉTUDIANTS ---
            st.subheader(f"👥 Liste d'appel ({promo_sel})")
            etudiants_final = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())
            absents_sel = st.multiselect("❌ Sélectionner les étudiants ABSENTS :", options=etudiants_final)

            # --- FORMULAIRE DE VALIDATION ---
            with st.form("form_validation"):
                st.write("##### ✍️ Validation de la séance")
                date_r = st.date_input("📅 Date réelle de la séance :")
                obs = st.text_area("🗒️ Observations / Thème abordé :", placeholder="Indiquez ici le contenu du cours ou les incidents.")
                sign = st.text_input("✍️ Signature (Votre Nom et Prénom) :")
                code_v = st.text_input("🔑 Code de Validation (2026) :", type="password")
                
                submit_btn = st.form_submit_button("🚀 ENREGISTRER DANS LA BASE", use_container_width=True)

            if submit_btn:
                # Vérification stricte des champs obligatoires
                if not sign or not obs or not code_v or promo_sel == "-- Choisir Promotion --":
                    st.error("⚠️ ERREUR : Tous les champs (Promotion, Observations, Signature et Code) sont obligatoires.")
                elif code_v != "2026":
                    st.error("⚠️ Code de validation incorrect.")
                else:
                    # Préparation des données
                    txt_absents = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                    full_obs = f"Avancement: {label_avancement} | Lieu: {info_ligne['Lieu']} | Signé: {sign} | Obs: {obs}"
                    
                    # 1. Enregistrement Supabase
                    try:
                        supabase.table("suivi_assiduite_2026").insert({
                            "enseignant": enseignant_sel,
                            "matiere": matiere_sel,
                            "promotion": promo_sel,
                            "absents": txt_absents,
                            "note_etudiant": full_obs
                        }).execute()
                        
                        # Stockage en session pour les étapes suivantes
                        st.session_state['record_ok'] = {
                            "date": date_r, "prof": enseignant_sel, "mat": matiere_sel,
                            "prom": promo_sel, "av": label_avancement, "abs": txt_absents, 
                            "obs": obs, "sign": sign, "lieu": info_ligne['Lieu']
                        }
                        st.success("✅ Données enregistrées avec succès dans la base de données !")
                    except Exception as e:
                        st.error(f"Erreur Supabase : {e}")

            # --- SECTION TÉLÉCHARGEMENT & EMAIL (Après validation) ---
            if 'record_ok' in st.session_state:
                st.divider()
                d = st.session_state['record_ok']
                
                # Téléchargements
                st.subheader("📥 Téléchargement du Rapport de Séance")
                col_ex, col_ht = st.columns(2)
                
                df_rep = pd.DataFrame([d])
                
                # Excel
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as w:
                    df_rep.to_excel(w, index=False)
                col_ex.download_button("📥 Télécharger EXCEL", buf.getvalue(), f"Rapport_{d['date']}_{d['prom']}.xlsx")
                
                # HTML
                col_ht.download_button("📄 Télécharger HTML", df_rep.to_html(index=False), f"Rapport_{d['date']}.html", "text/html")

                st.divider()
                st.subheader("📧 Notification Email aux Responsables")
                
                # Liste déroulante prédéfinie pour l'envoi
                dest_option = st.selectbox("Sélectionner le destinataire pour l'envoi du rapport :", 
                                         ["Chef de Département & Adjoint", "Responsable de Parcours de Formation"] + liste_profs)
                
                # Définition des emails (à adapter avec les vrais emails)
                emails_defaut = {
                    "Chef de Département & Adjoint": "chef-dept@univ-sba.dz, adjoint-dept@univ-sba.dz",
                    "Responsable de Parcours de Formation": "responsable-parcours@univ-sba.dz"
                }
                # Si c'est un prof de la liste, on génère un email fictif basé sur son nom
                dest_final = emails_defaut.get(dest_option, f"{dest_option.lower().replace(' ', '.')}@univ-sba.dz")

                sujet_mail = f"RAPPORT ASSIDUITE ET AVANCEMENT - {d['prom']} - {d['mat']}"
                corps_mail = (f"Monsieur le Responsable,\n\n"
                              f"Je vous transmets le rapport de la séance effectuée :\n\n"
                              f"Date : {d['date']}\n"
                              f"Enseignant : {d['prof']}\n"
                              f"Promotion : {d['prom']}\n"
                              f"Matière : {d['mat']}\n"
                              f"Lieu : {d['lieu']}\n"
                              f"État d'avancement : {d['av']}\n"
                              f"Étudiants Absents : {d['abs']}\n"
                              f"Observations : {d['obs']}\n\n"
                              f"Rapport certifié par : {d['sign']}")

                # Encodage Mailto
                mailto_url = f"mailto:{dest_final}?subject={urllib.parse.quote(sujet_mail)}&body={urllib.parse.quote(corps_mail)}"
                
                st.warning(f"⚠️ Action requise : Cliquez ci-dessous pour confirmer l'envoi à : {dest_option}")
                st.markdown(f"""
                    <a href="{mailto_url}" target="_self" style="text-decoration: none;">
                        <div style="background-color: #D4442E; color: white; padding: 15px; text-align: center; border-radius: 10px; font-weight: bold; font-size: 1.1rem; border: 2px solid #b33927; cursor: pointer;">
                            📧 CONFIRMER ET ENVOYER LE RAPPORT PAR EMAIL
                        </div>
                    </a>
                """, unsafe_allow_html=True)

    with tab_historique:
        st.subheader(f"📜 Historique de vos séances")
        res = supabase.table("suivi_assiduite_2026").select("*").eq("enseignant", enseignant_sel).execute()
        if res.data:
            df_h = pd.DataFrame(res.data)
            st.dataframe(df_h[["id", "matiere", "promotion", "absents", "note_etudiant"]], use_container_width=True)
        else:
            st.info("Aucune séance enregistrée pour le moment.")
