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
    st.subheader("🤖 IA de Génération d'Emplois du Temps")
    st.markdown("> Cet outil utilise des algorithmes de contraintes pour optimiser les salles.")
    
    with st.expander("⚙️ Paramètres de génération"):
        st.number_input("Nombre de groupes max par salle", 1, 5, 1)
        st.multiselect("Priorité des créneaux", ["Matin", "Après-midi"], ["Matin"])
    
    if st.button("🚀 Lancer la génération (Bêta)", type="primary"):
        with st.status("Calcul des collisions en cours..."):
            st.write("Vérification des disponibilités enseignants...")
            st.write("Optimisation des salles de TP...")
        st.error("Le moteur de calcul nécessite une base de données 'Vœux Enseignants' complète.")

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
