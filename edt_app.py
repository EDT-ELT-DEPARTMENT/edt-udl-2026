import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- CONNEXION DB ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- GESTION DU TEMPS ---
now = datetime.now()
jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
nom_jour_fr = jours_semaine[now.weekday()]

# --- CHARGEMENT DES DONNÉES ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
COLONNES_CLES = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']

def normalize(s):
    if not s or s == "Non défini": return "vide"
    return str(s).strip().lower().replace(" ", "").replace("-", "").replace(":", "").replace("h00", "h")

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    for col in COLONNES_CLES:
        df[col] = df[col].fillna("Non défini").astype(str).str.strip()
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)
else:
    df = pd.DataFrame(columns=COLONNES_CLES)

# --- AUTHENTIFICATION (Simplifiée pour le rendu) ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# (Note: Insérez ici votre bloc de login/inscription habituel)
# Supposons l'utilisateur connecté pour la suite :
user = st.session_state.get("user_data")
if not user:
    # Simuler un accès admin pour le développement si nécessaire ou afficher le login
    st.warning("Veuillez vous connecter.")
    st.stop()

is_admin = user.get("role") == "admin"

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Sélectionner Espace", [
        "📖 Emploi du Temps", 
        "📅 Surveillances Examens", 
        "🤖 Générateur Automatique", 
        "👥 Portail Enseignants", 
        "🎓 Portail Étudiants"
    ])
    st.divider()
    if portail == "📖 Emploi du Temps" and is_admin:
        mode_view = st.radio("Vue Admin :", ["Enseignant", "Promotion", "🏢 Planning Salles", "🚩 Conflits", "✍️ Éditeur"])
    else:
        mode_view = "Personnel"
    
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None
        st.rerun()

# --- TITRE COMMUN ---
st.markdown(f"<h1 style='text-align:center; color:#1E3A8A; font-size:18px;'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div style='background:#D4AF37; color:#1E3A8A; text-align:center; font-weight:bold; padding:5px; border-radius:5px;'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)
st.write("---")

# --- LOGIQUE DES ESPACES (REMPLISSAGE) ---

if portail == "📖 Emploi du Temps":
    st.info("Utilisez les filtres de la barre latérale pour naviguer dans les plannings.")
    # (Votre logique d'affichage de tableau HTML ici)

elif portail == "📅 Surveillances Examens":
    st.subheader("📅 Planning des Surveillances - S2-2026")
    col1, col2 = st.columns(2)
    with col1:
        st.info("📢 Les convocations seront générées après la saisie des listes d'étudiants.")
    with col2:
        st.metric("Examens Prévus", "14", "Session Juin")
    
    st.write("### Vos Surveillances assignées")
    st.warning("Aucune surveillance n'est encore enregistrée pour votre compte.")

elif portail == "🤖 Générateur Automatique":
        if not is_admin:
            st.error("Accès réservé au Bureau des Examens.")
        else:
            st.header("⚙️ Moteur de Génération de Surveillances")
            st.write("Plateforme : **Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA**")

            # 1. RÉCUPÉRATION INITIALE DES COURS (Source vers Éditeur)
            # On extrait les cours du tableau principal mémorisé (st.session_state.df_main)
            if "df_source_exams" not in st.session_state:
                if 'df' in locals() and df is not None:
                    # On ne garde que les "Cours", on retire les doublons de matières
                    df_cours = df[df["Enseignements"].str.contains("Cours", case=False, na=False)].copy()
                    st.session_state.df_source_exams = df_cours[["Enseignements", "Promotion", "Jours"]].drop_duplicates()
                else:
                    st.session_state.df_source_exams = pd.DataFrame(columns=["Enseignements", "Promotion", "Jours"])

            with st.expander("📝 1. Valider la Liste des Examens (Source EDT)", expanded=True):
                st.info("Ce tableau contient les Cours détectés. Modifiez ou supprimez les lignes qui n'ont pas d'examen.")
                # L'éditeur de données permet de nettoyer la liste rapidement
                df_validated = st.data_editor(
                    st.session_state.df_source_exams, 
                    use_container_width=True, 
                    num_rows="dynamic", 
                    hide_index=True,
                    key="editor_exams"
                )

            # 2. CONFIGURATION DES LIEUX ET CRÉNEAUX
            if "exam_config" not in st.session_state:
                st.session_state.exam_config = {}
            
            if "creneaux_list" not in st.session_state:
                st.session_state.creneaux_list = ["08:30 - 10:30", "11:00 - 13:00", "13:30 - 15:30"]

            with st.expander("🏢 2. Configuration des Salles & Horaires", expanded=False):
                promos_presents = sorted(df_validated["Promotion"].unique())
                data_cfg = []
                for p in promos_presents:
                    v = st.session_state.exam_config.get(p, [1, 25, "S06", 0, 0, "", st.session_state.creneaux_list[0]])
                    data_cfg.append({
                        "Promotion": p, "Horaire": v[6], "Nb Salles": v[0], "Numéros Salles": v[2],
                        "Nb Amphis": v[3], "Noms Amphis": v[5], "Capacité/Lieu": v[1]
                    })
                
                df_cfg_edit = st.data_editor(
                    pd.DataFrame(data_cfg),
                    column_config={"Horaire": st.column_config.SelectboxColumn("Horaire", options=st.session_state.creneaux_list)},
                    use_container_width=True, hide_index=True
                )
                
                if st.button("💾 Enregistrer la Configuration"):
                    for _, r in df_cfg_edit.iterrows():
                        st.session_state.exam_config[r["Promotion"]] = [
                            int(r["Nb Salles"]), int(r["Capacité/Lieu"]), str(r["Numéros Salles"]),
                            int(r["Nb Amphis"]), int(r["Capacité/Lieu"]), str(r["Noms Amphis"]),
                            str(r["Horaire"])
                        ]
                    st.success("Configuration enregistrée.")

            # 3. GÉNÉRATION FINALE
            if st.button("🚀 GÉNÉRER LE PLANNING DE SURVEILLANCE", type="primary", use_container_width=True):
                # Récupération profs Supabase
                res_auth = supabase.table("enseignants_auth").select("nom_officiel, statut").execute()
                db_profs = {row['nom_officiel']: row['statut'] for row in res_auth.data}
                liste_profs = sorted(list(db_profs.keys()))
                
                stats_charge = {p: 0 for p in liste_profs}
                tracker, final_list = [], []

                for _, exam in df_validated.iterrows():
                    p_name = exam["Promotion"]
                    cfg = st.session_state.exam_config.get(p_name)
                    if not cfg: continue

                    nb_s, cap, list_s, nb_a, _, list_a, h_fixe = cfg
                    lieux = [a.strip() for a in list_a.split(",") if a.strip()] + [s.strip() for s in list_s.split(",") if s.strip()]
                    
                    for lieu in lieux:
                        besoin = max(2, round(cap / 25))
                        equipe = []
                        # Tri : Moins chargés d'abord, Vacataires prioritaires
                        tri_prio = sorted(liste_profs, key=lambda x: (stats_charge[x], 0 if db_profs[x] == "Vacataire" else 1))

                        for p in tri_prio:
                            if len(equipe) < besoin:
                                if not any(t for t in tracker if t['J']==exam["Jours"] and t['H']==h_fixe and t['N']==p):
                                    equipe.append(p)
                                    stats_charge[p] += 1
                                    tracker.append({'J': exam["Jours"], 'H': h_fixe, 'N': p})

                        final_list.append({
                            "Enseignements": exam["Enseignements"],
                            "Code": "S2-2026",
                            "Enseignants": " / ".join(equipe),
                            "Horaire": h_fixe,
                            "Jours": exam["Jours"],
                            "Lieu": lieu,
                            "Promotion": p_name
                        })

                st.session_state.df_surv_final = pd.DataFrame(final_list)
                st.rerun()

            # 4. AFFICHAGE RÉSULTAT
            if "df_surv_final" in st.session_state:
                st.subheader("📋 Planning de Surveillance S2-2026")
                st.dataframe(st.session_state.df_surv_final, use_container_width=True, hide_index=True)
elif portail == "👥 Portail Enseignants":
    st.subheader("👥 Espace Enseignants & Annuaire")
    
    # Récupération des enseignants depuis Supabase
    try:
        res = supabase.table("enseignants_auth").select("nom_officiel, email, statut, telephone").execute()
        annuaire_df = pd.DataFrame(res.data)
        
        tab1, tab2 = st.tabs(["📇 Annuaire", "📄 Documents Administratifs"])
        with tab1:
            st.dataframe(annuaire_df, use_container_width=True)
        with tab2:
            st.write("📂 **Modèles à télécharger :**")
            st.button("📥 Canevas de Note de Cours")
            st.button("📥 Formulaire d'Heures Supplémentaires")
    except:
        st.error("Impossible de charger l'annuaire.")

elif portail == "🎓 Portail Étudiants":
    st.subheader("🎓 Espace de Consultation Étudiants")
    promo_choice = st.selectbox("Sélectionnez votre Promotion / Section :", sorted(df["Promotion"].unique()))
    
    df_student = df[df["Promotion"] == promo_choice]
    
    if not df_student.empty:
        st.success(f"Affichage de l'EDT pour : {promo_choice}")
        # Affichage simplifié en liste pour mobile/étudiants
        for jour in jours_list:
            with st.expander(f"📅 {jour}"):
                day_data = df_student[df_student["Jours"] == jour].sort_values("Horaire")
                if day_data.empty:
                    st.write("Aucun cours.")
                else:
                    for _, r in day_data.iterrows():
                        st.write(f"🕒 **{r['Horaire']}** | {r['Enseignements']} ({r['Code']})")
                        st.caption(f"📍 Lieu : {r['Lieu']} | Enseignant : {r['Enseignants']}")
    else:
        st.info("Veuillez sélectionner une promotion pour voir l'emploi du temps.")


