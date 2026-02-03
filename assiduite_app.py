import streamlit as st
import pandas as pd
from supabase import create_client, Client
import io
import urllib.parse
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Assiduité & Avancement - UDL SBA", layout="wide")

# Titre officiel obligatoire
TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"

# --- CONNEXION SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erreur de connexion aux secrets Supabase.")

# --- CHARGEMENT DES DONNÉES (EDT & ÉTUDIANTS) ---
@st.cache_data
def load_all_data():
    # Source 1 : Emploi du temps et structure des cours
    df_edt = pd.read_excel("DATA-ASSUIDUITE-2026.xlsx")
    # Source 2 : Liste nominative des étudiants
    df_etudiants = pd.read_excel("Liste des étudiants-2025-2026.xlsx")
    # Formatage du nom pour l'appel
    df_etudiants['Nom_Complet'] = df_etudiants['Nom'].astype(str).str.upper() + " " + df_etudiants['Prénom'].astype(str)
    return df_edt, df_etudiants

df_edt, df_etudiants = load_all_data()

# --- INTERFACE PRINCIPALE ---
st.markdown(f"#### {TITRE_OFFICIEL}")
st.header("📊 Gestion de l'Assiduité et de l'Avancement")

# --- BARRE LATÉRALE (MAINTENANCE) ---
with st.sidebar:
    st.title("🛠️ Administration")
    with st.expander("Options de Maintenance"):
        st.warning("Zone réservée : Réinitialisation des données")
        pwd_maint = st.text_input("Code Maintenance :", type="password")
        if st.button("🗑️ Reset Table Assiduité"):
            if pwd_maint == "ADMIN-RESET-2026":
                try:
                    # Supabase ne permet pas un 'TRUNCATE' direct via API, 
                    # mais on simule le reset ou on prévient l'admin
                    st.error("Action de suppression globale activée. Contactez le DBA.")
                except Exception as e:
                    st.error(f"Erreur : {e}")
            else:
                st.error("Code de maintenance invalide.")

# --- ÉTAPE 1 : SÉLECTION DE L'ENSEIGNANT ---
liste_profs = sorted(df_edt['Enseignants'].dropna().unique())
enseignant_sel = st.selectbox("👤 1. Sélectionner l'Enseignant :", ["-- Faire un choix --"] + liste_profs)

if enseignant_sel != "-- Faire un choix --":
    tab_saisie, tab_historique, tab_alertes = st.tabs(["📝 Saisie de Séance", "📜 Historique", "⚠️ Alertes Absences"])

    with tab_saisie:
        # --- FILTRES EN CASCADE ---
        promos_liees = sorted(df_edt[df_edt['Enseignants'] == enseignant_sel]['Promotion'].unique())
        c1, c2 = st.columns(2)
        with c1:
            promo_sel = st.selectbox("🎓 Promotion :", ["-- Choisir --"] + promos_liees)
        
        if promo_sel != "-- Choisir --":
            with c2:
                filt = (df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel)
                matieres_dispo = sorted(df_edt[filt]['Enseignements'].unique())
                matiere_sel = st.selectbox("📖 Matière :", matieres_dispo)

            # Infos EDT Auto
            info = df_edt[(df_edt['Enseignants'] == enseignant_sel) & (df_edt['Promotion'] == promo_sel) & (df_edt['Enseignements'] == matiere_sel)].iloc[0]
            st.success(f"📍 Planning : {info['Jours']} | {info['Horaire']} | Lieu: {info['Lieu']}")

            # --- AVANCEMENT PÉDAGOGIQUE ---
            st.subheader("📈 État d'Avancement")
            av1, av2 = st.columns(2)
            with av1:
                type_av = st.selectbox("Type d'unité :", ["Chapitre", "Fiche de TD N°", "Fiche de TP N°"])
            with av2:
                num_av = st.selectbox("Numéro de l'unité :", list(range(1, 31)))
            
            # --- APPEL DES ÉTUDIANTS ---
            st.subheader(f"👥 Appel des Étudiants ({promo_sel})")
            etudiants_promo = sorted(df_etudiants[df_etudiants['Promotion'] == promo_sel]['Nom_Complet'].tolist())
            absents_sel = st.multiselect("❌ Cocher les ABSENTS :", options=etudiants_promo)

            # --- FORMULAIRE D'ENREGISTREMENT ---
            with st.form("form_final"):
                st.write("### Validation Finale")
                date_r = st.date_input("📅 Date réelle du cours :")
                obs = st.text_area("🗒️ Observations libres :")
                sign = st.text_input("✍️ Signature (Nom et Prénom) :")
                code_v = st.text_input("🔑 Code Validation (2026) :", type="password")
                btn_save = st.form_submit_button("🚀 ENREGISTRER & GÉNÉRER LES RAPPORTS", use_container_width=True)

            if btn_save:
                if code_v == "2026" and sign:
                    txt_abs = ", ".join(absents_sel) if absents_sel else "Aucun absent"
                    av_final = f"{type_av} {num_av}"
                    full_obs = f"Avanc: {av_final} | Lieu: {info['Lieu']} | Signé: {sign} | Obs: {obs}"
                    
                    # 1. Insertion Supabase
                    supabase.table("suivi_assiduite_2026").insert({
                        "enseignant": enseignant_sel, "matiere": matiere_sel,
                        "promotion": promo_sel, "absents": txt_abs, "note_etudiant": full_obs
                    }).execute()
                    
                    # 2. Mémorisation pour les outils d'export
                    st.session_state['report'] = {
                        "date": date_r, "prof": enseignant_sel, "mat": matiere_sel,
                        "prom": promo_sel, "avanc": av_final, "abs": txt_abs, "obs": obs, "sign": sign
                    }
                    st.success("✅ Données enregistrées. Utilisez les boutons ci-dessous pour exporter ou notifier.")
                else:
                    st.error("Vérifiez le code et votre signature.")

            # --- ZONE D'EXPORT ET ENVOI ---
            if 'report' in st.session_state:
                st.divider()
                st.subheader("📥 Téléchargements et Notification Email")
                rep = st.session_state['report']
                df_rep = pd.DataFrame([rep])

                col_ex, col_ht = st.columns(2)
                # Export Excel
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as w:
                    df_rep.to_excel(w, index=False)
                col_ex.download_button("📥 Télécharger Rapport EXCEL", buf.getvalue(), f"Rapport_{rep['date']}.xlsx")
                # Export HTML
                col_ht.download_button("📄 Télécharger Rapport HTML", df_rep.to_html(index=False), f"Rapport_{rep['date']}.html", "text/html")

                st.divider()
                st.subheader("📧 Envoi du Rapport par Email")
                
                # LISTE DÉROULANTE DES ENSEIGNANTS POUR L'ENVOI
                dest_option = st.selectbox("Choisir le destinataire du rapport :", 
                                         ["Chef de Département & Adjoint", "Responsable de Parcours"] + liste_profs)
                
                # Mapping des adresses fictives (à adapter)
                emails = {
                    "Chef de Département & Adjoint": "chef-dept@univ-sba.dz, adjoint-dept@univ-sba.dz",
                    "Responsable de Parcours": "responsable-formation@univ-sba.dz"
                }
                email_dest = emails.get(dest_option, f"{dest_option.lower().replace(' ', '.')}@univ-sba.dz")

                sujet = f"RAPPORT ASSIDUITE - {rep['prom']} - {rep['mat']}"
                corps = (f"Bonjour,\n\nVoici le rapport de séance :\n"
                         f"Date: {rep['date']}\nEnseignant: {rep['prof']}\n"
                         f"Promotion: {rep['prom']}\nMatière: {rep['mat']}\n"
                         f"Avancement: {rep['avanc']}\nAbsents: {rep['abs']}\n"
                         f"Observations: {rep['obs']}\nSigné par: {rep['sign']}")
                
                mailto_link = f"mailto:{email_dest}?subject={urllib.parse.quote(sujet)}&body={urllib.parse.quote(corps)}"
                
                st.markdown(f'<a href="{mailto_link}" target="_self" style="text-decoration:none;"><div style="background-color:#D4442E;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">📧 CONFIRMER ET ENVOYER À : {dest_option}</div></a>', unsafe_allow_html=True)

    with tab_historique:
        st.subheader(f"📜 Historique de M. {enseignant_sel}")
        hist = supabase.table("suivi_assiduite_2026").select("*").eq("enseignant", enseignant_sel).execute()
        if hist.data:
            st.dataframe(pd.DataFrame(hist.data)[["matiere", "promotion", "absents", "note_etudiant"]], use_container_width=True)

    with tab_alertes:
        st.subheader("⚠️ Étudiants à +3 absences")
        all_d = supabase.table("suivi_assiduite_2026").select("absents, promotion").execute()
        if all_d.data:
            counts = []
            for row in all_d.data:
                if row['absents'] and row['absents'] != "Aucun absent":
                    for name in row['absents'].split(","):
                        counts.append({"Etudiant": name.strip(), "Promotion": row['promotion']})
            if counts:
                df_c = pd.DataFrame(counts)
                res_alert = df_c.groupby(["Etudiant", "Promotion"]).size().reset_index(name="Absences")
                st.table(res_alert[res_alert["Absences"] >= 3])
