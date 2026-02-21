import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="EDT UDL 2026",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONNEXION BASE DE DONNÉES ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- GESTION DU TEMPS ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
jours_semaine = [
    "Lundi", "Mardi", "Mercredi", 
    "Jeudi", "Vendredi", "Samedi", "Dimanche"
]
nom_jour_fr = jours_semaine[now.weekday()]

# --- STYLE CSS DÉTAILLÉ ---
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; 
        text-align: center; 
        font-family: 'serif'; 
        font-weight: bold; 
        border-bottom: 3px solid #D4AF37; 
        padding-bottom: 15px; 
        font-size: 18px; 
        margin-top: 5px;
    }}
    .portal-badge {{ 
        background-color: #D4AF37; 
        color: #1E3A8A; 
        padding: 5px 15px; 
        border-radius: 5px; 
        font-weight: bold; 
        text-align: center; 
        margin-bottom: 20px; 
    }}
    .date-badge {{ 
        background-color: #1E3A8A; 
        color: white; 
        padding: 5px 15px; 
        border-radius: 20px; 
        font-size: 12px; 
        float: right; 
    }}
    .metric-card {{ 
        background-color: #f8f9fa; 
        border: 1px solid #1E3A8A; 
        padding: 10px; 
        border-radius: 10px; 
        text-align: center; 
        height: 100%; 
    }}
    .stat-container {{ 
        display: flex; 
        justify-content: space-around; 
        margin: 20px 0; 
        gap: 10px; 
    }}
    .stat-box {{ 
        flex: 1; 
        padding: 15px; 
        border-radius: 12px; 
        color: white; 
        font-weight: bold; 
        text-align: center; 
        font-size: 16px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1); 
    }}
    .bg-cours {{ background: linear-gradient(135deg, #1E3A8A, #3B82F6); }}
    .bg-td {{ background: linear-gradient(135deg, #15803d, #22c55e); }}
    .bg-tp {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
    
    table {{ 
        width: 100%; 
        border-collapse: collapse; 
        table-layout: fixed; 
        margin-top: 10px; 
        background-color: white; 
    }}
    th {{ 
        background-color: #1E3A8A !important; 
        color: white !important; 
        border: 1px solid #000; 
        padding: 6px; 
        text-align: center; 
        font-size: 11px; 
    }}
    td {{ 
        border: 1px solid #000; 
        padding: 4px !important; 
        vertical-align: top; 
        text-align: center; 
        background-color: white; 
        height: 95px; 
        font-size: 11px; 
    }}
    .separator {{ 
        border-top: 1px dashed #bbb; 
        margin: 4px 0; 
    }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
# Titre : Plateforme de gestion des emplois du temps 2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA

NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
NOM_FICHIER_CONTACTS = "Permanents-Vacataires-ELT2-2025-2026.xlsx"

df = None
repertoire_source = {}

def normalize(s):
    if not s or s == "Non défini": 
        return "vide"
    s = str(s).strip().lower()
    s = s.replace(" ", "").replace("-", "").replace("–", "")
    s = s.replace(":00", "").replace("h00", "h")
    return s

# 1. Chargement du répertoire depuis le fichier Permanent/Vacataires
if os.path.exists(NOM_FICHIER_CONTACTS):
    try:
        df_contacts = pd.read_excel(NOM_FICHIER_CONTACTS)
        # On nettoie les noms de colonnes au cas où il y aurait des espaces
        df_contacts.columns = [str(c).strip() for c in df_contacts.columns]
        
        for _, row in df_contacts.iterrows():
            # On récupère le NOM (clé principale)
            nom_brut = str(row.get('NOM', '')).strip().upper()
            email_brut = str(row.get('Email', '')).strip()
            
            if nom_brut and email_brut and email_brut.lower() != 'nan':
                repertoire_source[nom_brut] = email_brut
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier contacts: {e}")

# 2. Chargement de l'Emploi du Temps
if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    
    colonnes_cles = [
        'Enseignements', 
        'Code', 
        'Enseignants', 
        'Horaire', 
        'Jours', 
        'Lieu', 
        'Promotion'
    ]
    
    for col in colonnes_cles:
        if col in df.columns: 
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
            
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)

# --- SYSTÈME D'AUTH ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    t_conn, t_ins, t_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    
    with t_conn:
        email_input = st.text_input("Adresse Email", key="login_email")
        pass_input = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter au portail", use_container_width=True):
            result = supabase.table("enseignants_auth").select("*").eq("email", email_input).eq("password_hash", hash_pw(pass_input)).execute()
            if result.data:
                st.session_state["user_data"] = result.data[0]
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect.")
                
    with t_ins:
        st.subheader("📝 Créer un nouveau compte Enseignant")
        # Récupération des noms depuis l'Excel
        noms_possibles = sorted(df["Enseignants"].unique()) if df is not None else []
        
        col1, col2 = st.columns(2)
        with col1:
            new_nom = st.selectbox("Sélectionnez votre nom (dans l'EDT)", noms_possibles)
            new_email = st.text_input("Votre adresse Email")
            
        with col2:
            # Nouveau : Choix du Statut
            statut_user = st.radio("Statut de l'enseignant", ["Permanent", "Vacataire"], horizontal=True)
            
            # Nouveau : Champ téléphone conditionnel
            new_phone = ""
            if statut_user == "Vacataire":
                new_phone = st.text_input("📱 Numéro de téléphone (Obligatoire)", placeholder="06XXXXXXXX")

        st.divider()
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            new_pass = st.text_input("Choisissez un mot de passe", type="password")
        with c_p2:
            confirm_pass = st.text_input("Confirmez le mot de passe", type="password")
        
        if st.button("Créer mon compte", use_container_width=True, type="primary"):
            if not new_email or not new_pass:
                st.warning("Veuillez remplir les champs obligatoires.")
            elif statut_user == "Vacataire" and not new_phone:
                st.error("Le numéro de téléphone est requis pour les vacataires.")
            elif new_pass != confirm_pass:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                # Vérifier si l'email existe déjà
                check = supabase.table("enseignants_auth").select("email").eq("email", new_email).execute()
                if check.data:
                    st.error("Cet email est déjà utilisé.")
                else:
                    data_ins = {
                        "nom_officiel": new_nom,
                        "email": new_email,
                        "password_hash": hash_pw(new_pass),
                        "role": "enseignant",
                        "statut": statut_user,
                        "telephone": new_phone if statut_user == "Vacataire" else None
                    }
                    try:
                        supabase.table("enseignants_auth").insert(data_ins).execute()
                        st.success("✅ Compte créé avec succès ! Connectez-vous maintenant.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erreur Supabase : {e}")

    with t_adm:
        code_admin = st.text_input("Code de sécurité Administration", type="password", key="admin_code")
        if st.button("Accès Administration", use_container_width=True):
            if code_admin == "doctorat2026":
                st.session_state["user_data"] = {
                    "nom_officiel": "ADMINISTRATEUR", 
                    "role": "admin",
                    "email": "milouafarid@gmail.com"
                }
                st.rerun()
            else:
                st.error("Code admin incorrect.")

# --- GARDIEN DE SESSION ---
user = st.session_state.get("user_data")
if user is None:
    st.stop() 

is_admin = user.get("role") == "admin"
# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="EDT UDL 2026",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONNEXION BASE DE DONNÉES ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- GESTION DU TEMPS ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
jours_semaine = [
    "Lundi", "Mardi", "Mercredi", 
    "Jeudi", "Vendredi", "Samedi", "Dimanche"
]
nom_jour_fr = jours_semaine[now.weekday()]

# --- STYLE CSS DÉTAILLÉ ---
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; 
        text-align: center; 
        font-family: 'serif'; 
        font-weight: bold; 
        border-bottom: 3px solid #D4AF37; 
        padding-bottom: 15px; 
        font-size: 18px; 
        margin-top: 5px;
    }}
    .portal-badge {{ 
        background-color: #D4AF37; 
        color: #1E3A8A; 
        padding: 5px 15px; 
        border-radius: 5px; 
        font-weight: bold; 
        text-align: center; 
        margin-bottom: 20px; 
    }}
    .date-badge {{ 
        background-color: #1E3A8A; 
        color: white; 
        padding: 5px 15px; 
        border-radius: 20px; 
        font-size: 12px; 
        float: right; 
    }}
    .metric-card {{ 
        background-color: #f8f9fa; 
        border: 1px solid #1E3A8A; 
        padding: 10px; 
        border-radius: 10px; 
        text-align: center; 
        height: 100%; 
    }}
    .stat-container {{ 
        display: flex; 
        justify-content: space-around; 
        margin: 20px 0; 
        gap: 10px; 
    }}
    .stat-box {{ 
        flex: 1; 
        padding: 15px; 
        border-radius: 12px; 
        color: white; 
        font-weight: bold; 
        text-align: center; 
        font-size: 16px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1); 
    }}
    .bg-cours {{ background: linear-gradient(135deg, #1E3A8A, #3B82F6); }}
    .bg-td {{ background: linear-gradient(135deg, #15803d, #22c55e); }}
    .bg-tp {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
    
    table {{ 
        width: 100%; 
        border-collapse: collapse; 
        table-layout: fixed; 
        margin-top: 10px; 
        background-color: white; 
    }}
    th {{ 
        background-color: #1E3A8A !important; 
        color: white !important; 
        border: 1px solid #000; 
        padding: 6px; 
        text-align: center; 
        font-size: 11px; 
    }}
    td {{ 
        border: 1px solid #000; 
        padding: 4px !important; 
        vertical-align: top; 
        text-align: center; 
        background-color: white; 
        height: 95px; 
        font-size: 11px; 
    }}
    .separator {{ 
        border-top: 1px dashed #bbb; 
        margin: 4px 0; 
    }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

def normalize(s):
    if not s or s == "Non défini": 
        return "vide"
    s = str(s).strip().lower()
    s = s.replace(" ", "").replace("-", "").replace("–", "")
    s = s.replace(":00", "").replace("h00", "h")
    return s

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    
    colonnes_cles = [
        'Enseignements', 
        'Code', 
        'Enseignants', 
        'Horaire', 
        'Jours', 
        'Lieu', 
        'Promotion'
    ]
    
    for col in colonnes_cles:
        if col in df.columns: 
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
            
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)

# --- SYSTÈME D'AUTH ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    t_conn, t_ins, t_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    
    with t_conn:
        email_input = st.text_input("Adresse Email", key="login_email")
        pass_input = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter au portail"):
            result = supabase.table("enseignants_auth").select("*").eq("email", email_input).eq("password_hash", hash_pw(pass_input)).execute()
            if result.data:
                st.session_state["user_data"] = result.data[0]
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect.")
                
    with t_ins:
        st.subheader("Créer un nouveau compte Enseignant")
        # On récupère la liste des noms depuis l'Excel pour éviter les erreurs de saisie
        noms_possibles = sorted(df["Enseignants"].unique()) if df is not None else []
        
        new_nom = st.selectbox("Sélectionnez votre nom (tel qu'il apparaît dans l'EDT)", noms_possibles)
        new_email = st.text_input("Votre adresse Email")
        new_pass = st.text_input("Choisissez un mot de passe", type="password")
        confirm_pass = st.text_input("Confirmez le mot de passe", type="password")
        
        if st.button("Créer mon compte"):
            if not new_email or not new_pass:
                st.warning("Veuillez remplir tous les champs.")
            elif new_pass != confirm_pass:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                # Vérifier si l'email existe déjà
                check = supabase.table("enseignants_auth").select("email").eq("email", new_email).execute()
                if check.data:
                    st.error("Cet email est déjà utilisé.")
                else:
                    data_ins = {
                        "nom_officiel": new_nom,
                        "email": new_email,
                        "password_hash": hash_pw(new_pass),
                        "role": "enseignant"
                    }
                    supabase.table("enseignants_auth").insert(data_ins).execute()
                    st.success("✅ Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
                    st.balloons()

    with t_adm:
        code_admin = st.text_input("Code de sécurité Administration", type="password", key="admin_code")
        if st.button("Accès Administration"):
            if code_admin == "doctorat2026":
                # On force l'email ici pour activer vos droits maître
                st.session_state["user_data"] = {
                    "nom_officiel": "ADMINISTRATEUR", 
                    "role": "admin",
                    "email": "milouafarid@gmail.com"  # <--- AJOUTER CETTE LIGNE
                }
                st.rerun()
            else:
                st.error("Code admin incorrect.")
# --- SOLUTIONS AUX ERREURS (Remplace le bloc supprimé) ---
user = st.session_state.get("user_data")

# Le st.stop() est le gardien : si pas de login, on n'affiche pas la suite
if user is None:
    st.stop() 

is_admin = user.get("role") == "admin"

# 1. Définition précise de votre nouvelle liste d'horaires (14 créneaux)
horaires_list = [
    "8h - 9h", "8h - 9h30", "8h - 10h", "9h - 10h", "9h30 - 11h", 
    "10h - 11h", "11h - 12h", "11h - 12h30", 
    "12h - 13h", "12h30 - 14h", "13h - 14h", "14h - 15h30", "14h - 16h", "15h30 - 17h"
]

# 2. Définition des jours de la semaine
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]

# 3. Mapping pour la normalisation (crucial pour faire le lien avec l'Excel)
# Cela permet de faire correspondre "8h-9h30" (Excel) avec "8h - 9h30" (Affichage)
map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

# --- BARRE LATÉRALE ---
with st.sidebar:
    # On utilise .get() pour éviter le crash si la donnée est corrompue
    st.header(f"👤 {user.get('nom_officiel', 'Utilisateur')}")
    portail = st.selectbox("🚀 Sélectionner Espace", [
        "📖 Emploi du Temps", "📅 Surveillances Examens", 
        "🤖 Générateur Automatique", "👥 Portail Enseignants", "🎓 Portail Étudiants"
    ])
    st.divider()
    
    mode_view = "Personnel"
    poste_sup = False
    
    if portail == "📖 Emploi du Temps":
        if is_admin:
            mode_view = st.radio("Vue Administration :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur de conflits","✍️ Éditeur de données"])
        else:
            mode_view = "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge 3h)")
        
    if st.button("🚪 Déconnexion du compte"):
        st.session_state["user_data"] = None
        st.rerun()
if st.button("🚪 Déconnexion du compte"):
        st.session_state["user_data"] = None
        st.rerun()

# --- ESPACE ÉDITEUR AVANCÉ (ADMIN UNIQUEMENT) ---
if is_admin and mode_view == "✍️ Éditeur de données":
    st.divider()
    st.subheader("✍️ Plateforme de gestion des emplois du temps 2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

    # 1. STRUCTURE ET NETTOYAGE
    cols_format = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion', 'Chevauchement']

    if 'df_admin' not in st.session_state:
        temp_df = df.copy()
        for col in cols_format:
            if col not in temp_df.columns:
                temp_df[col] = ""
            temp_df[col] = temp_df[col].astype(str).replace(['nan', 'None', '<NA>'], '')
        st.session_state.df_admin = temp_df

    # 2. PRÉPARATION DES OPTIONS
    horaires_ref = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h00", "14h00 - 15h30", "15h30 - 17h00"]
    h_existants = [h for h in st.session_state.df_admin["Horaire"].unique() if h and h.strip() != ""]
    liste_horaires = sorted(list(set(h_existants + horaires_ref)))
    jours_std = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    promos_existantes = [p for p in st.session_state.df_admin["Promotion"].unique() if p and p.strip() != ""]

    # --- NOUVEAUTÉ : FILTRE DE RECHERCHE ---
    st.markdown("### 🔍 Filtrer par Enseignant")
    search_prof = st.text_input("Tapez le nom de l'enseignant pour filtrer le tableau :", "")

    # Application du filtre
    if search_prof:
        # On filtre les données pour l'affichage
        df_to_edit = st.session_state.df_admin[
            st.session_state.df_admin["Enseignants"].str.contains(search_prof, case=False, na=False)
        ]
        st.info(f"💡 Affichage des cours de : **{search_prof}**. Les modifications ou ajouts ne concernernt que cette sélection.")
    else:
        df_to_edit = st.session_state.df_admin

    # 3. TABLEAU GLOBAL (ÉDITION, AJOUT & DÉTECTION DE CONFLITS)
    st.markdown("### 🌍 Tableau d'édition")
    
    # --- FORMULAIRE D'AJOUT AVEC VÉRIFICATION ---
    with st.expander("➕ Ajouter une nouvelle ligne (Vérification automatique)"):
        with st.form("form_nouvelle_ligne"):
            c1, c2, c3 = st.columns(3)
            with c1:
                n_ensg = st.text_input("📚 Enseignements")
                n_code = st.text_input("🔑 Code")
                n_promo = st.selectbox("🎓 Promotion", options=promos_existantes if promos_existantes else ["M2RE"])
            with c2:
                n_prof = st.text_input("👤 Enseignants")
                n_horaire = st.selectbox("🕒 Horaire", options=liste_horaires)
            with c3:
                n_jour = st.selectbox("📅 Jours", options=jours_std)
                n_lieu = st.text_input("🏢 Lieu (Salle)")
                n_chev = "Non"

            submit_add = st.form_submit_button("🔍 Vérifier et Insérer", use_container_width=True)

            if submit_add:
                # Vérification des conflits (Salle OU Enseignant occupés au même moment)
                conflit_salle = st.session_state.df_admin[
                    (st.session_state.df_admin['Jours'] == n_jour) & 
                    (st.session_state.df_admin['Horaire'] == n_horaire) & 
                    (st.session_state.df_admin['Lieu'] == n_lieu)
                ]
                
                conflit_prof = st.session_state.df_admin[
                    (st.session_state.df_admin['Jours'] == n_jour) & 
                    (st.session_state.df_admin['Horaire'] == n_horaire) & 
                    (st.session_state.df_admin['Enseignants'] == n_prof)
                ]

                if not conflit_salle.empty:
                    st.error(f"❌ CONFLIT SALLE : La salle {n_lieu} est déjà prise par {conflit_salle.iloc[0]['Enseignants']}.")
                elif not conflit_prof.empty:
                    st.error(f"❌ CONFLIT ENSEIGNANT : M. {n_prof} a déjà un cours à cette heure en salle {conflit_prof.iloc[0]['Lieu']}.")
                else:
                    new_row = pd.DataFrame([{
                        'Enseignements': n_ensg, 'Code': n_code, 'Enseignants': n_prof,
                        'Horaire': n_horaire, 'Jours': n_jour, 'Lieu': n_lieu,
                        'Promotion': n_promo, 'Chevauchement': n_chev
                    }])
                    st.session_state.df_admin = pd.concat([st.session_state.df_admin, new_row], ignore_index=True)
                    st.success("✅ Ligne ajoutée sans conflit !")
                    st.rerun()

    # --- ÉDITEUR DE TABLEAU ---
    edited_df = st.data_editor(
        df_to_edit[cols_format],
        use_container_width=True,
        num_rows="dynamic",
        key="editor_with_filter_2026",
        column_config={
            "Enseignements": st.column_config.TextColumn("📚 Matière"),
            "Horaire": st.column_config.SelectboxColumn("🕒 Horaire", options=liste_horaires),
            "Jours": st.column_config.SelectboxColumn("📅 Jours", options=jours_std),
            "Promotion": st.column_config.SelectboxColumn("🎓 Promotion", options=promos_existantes if promos_existantes else ["M2RE"]),
            "Chevauchement": st.column_config.TextColumn("⚠️ Chevauchement"),
        }
    )

    # Synchronisation
    if edited_df is not None and not edited_df.equals(df_to_edit[cols_format]):
        if search_prof:
            indices_modifies = df_to_edit.index
            df_others = st.session_state.df_admin.drop(indices_modifies)
            st.session_state.df_admin = pd.concat([df_others, edited_df], ignore_index=True)
        else:
            st.session_state.df_admin = edited_df

    # 4. SAUVEGARDE ET EXPORT
    st.write("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        if st.button("💾 Enregistrer sur Serveur", type="primary", use_container_width=True):
            try:
                st.session_state.df_admin[cols_format].to_excel(NOM_FICHIER_FIXE, index=False)
                st.success("✅ Modifications enregistrées !")
                st.balloons()
            except Exception as e:
                st.error(f"Erreur : {e}")

    with c2:
        if st.button("🔄 Réinitialiser l'éditeur", use_container_width=True):
            if 'df_admin' in st.session_state:
                del st.session_state.df_admin
            st.rerun()

    with c3:
        import io
        buffer = io.BytesIO()
        st.session_state.df_admin[cols_format].to_excel(buffer, index=False, engine='xlsxwriter')
        st.download_button("📥 Télécharger Excel", buffer.getvalue(), f"EDT_S2_2026.xlsx", use_container_width=True)

    st.stop() 


# --- EN-TÊTE HARMONISÉ (LOGO + TITRE + DATE) ---
col_logo, col_titre, col_date = st.columns([1, 5, 1.2])

with col_logo:
    try:
        st.image("logo.PNG", width=90)
    except:
        st.markdown("🏛️") # Secours si le fichier est manquant

with col_titre:
    st.markdown("<h1 class='main-title' style='border-bottom: none; margin-top: 0;'>Plateforme de gestion des emplois du temps 2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

with col_date:
    st.markdown(f"<div class='date-badge' style='float: right;'>📅 {nom_jour_fr}<br>{date_str}</div>", unsafe_allow_html=True)

# Ligne dorée décorative et badge du mode
st.markdown("<div style='border-bottom: 3px solid #D4AF37; margin-bottom: 10px;'></div>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE ACTIF : {portail.upper()}</div>", unsafe_allow_html=True)

# --- LOGIQUE PRINCIPALE ---
if df is not None:
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            if mode_view == "Personnel":
                cible = user['nom_officiel']
            else:
                cible = st.selectbox("Sélectionner l'Enseignant :", sorted(df["Enseignants"].unique()))
            
            df_f = df[df["Enseignants"].str.contains(cible, case=False, na=False)].copy()
            
            def get_nature(code):
                val = str(code).upper()
                if "COURS" in val: return "📘 COURS"
                if "TD" in val: return "📗 TD"
                if "TP" in val: return "📙 TP"
                return "📑"

            df_f['Type'] = df_f['Code'].apply(lambda x: "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP"))
            df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            df_u = df_f.drop_duplicates(subset=['j_norm', 'h_norm'])
            
            st.markdown(f"### 📊 Bilan Horaire : {cible}")
            st.markdown(f"""<div class="stat-container">
                <div class="stat-box bg-cours">📘 {len(df_u[df_u['Type'] == 'COURS'])} Séances Cours</div>
                <div class="stat-box bg-td">📗 {len(df_u[df_u['Type'] == 'TD'])} Séances TD</div>
                <div class="stat-box bg-tp">📙 {len(df_u[df_u['Type'] == 'TP'])} Séances TP</div>
            </div>""", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            charge_reelle = df_u['h_val'].sum()
            charge_reg = 3.0 if poste_sup else 6.0
            
            with c1:
                st.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
            
            h_sup = charge_reelle - charge_reg
            color_sup = "#e74c3c" if h_sup > 0 else "#27ae60"
            with c3:
                st.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup.<br><h2 style='color:{color_sup};'>{h_sup} h</h2></div>", unsafe_allow_html=True)

            def format_case(rows):
                items = []
                for _, r in rows.iterrows():
                    txt = f"<b>{get_nature(r['Code'])} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>"
                    items.append(txt)
                return "<div class='separator'></div>".join(items)
            
            if not df_f.empty:
                grid = df_f.groupby(['h_norm', 'j_norm']).apply(format_case, include_groups=False).unstack('j_norm')
                grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
                grid.index = [map_h.get(i, i) for i in grid.index]
                grid.columns = [map_j.get(c, c) for c in grid.columns]
                st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            
            def fmt_p(rows):
                items = []
                for _, r in rows.iterrows():
                    nat = '📘 COURS' if 'COURS' in str(r['Code']).upper() else '📗 TD' if 'TD' in str(r['Code']).upper() else '📙 TP'
                    items.append(f"<b>{nat} : {r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>")
                return "<div class='separator'></div>".join(items)
                
            grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
            grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_p.index = horaires_list
            grid_p.columns = jours_list
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Choisir Salle :", sorted(df["Lieu"].unique()))
            df_s = df[df["Lieu"] == s_sel]
            
            def fmt_s(rows):
                items = [f"<b>{r['Promotion']}</b><br>{r['Enseignements']}<br><i>{r['Enseignants']}</i>" for _, r in rows.iterrows()]
                return "<div class='separator'></div>".join(items)
                
            grid_s = df_s.groupby(['h_norm', 'j_norm']).apply(fmt_s, include_groups=False).unstack('j_norm')
            grid_s = grid_s.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_s.index = horaires_list
            grid_s.columns = jours_list
            st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)

      elif is_admin and mode_view == "🚩 Vérificateur de conflits":
          st.subheader("🚩 Analyse des Conflits & Assistant de Résolution")
    # Rappel du titre officiel mémorisé
    st.info("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
    st.markdown("---")
    
    # Nettoyage et filtrage pour exclure les enseignants non désignés (ND)
    # On considère comme ND : "ND", "nd", "Non défini", ou vide
    df_clean = df.copy()
    mask_nd = df_clean["Enseignants"].str.upper().isin(["ND", "NON DÉFINI", "NON DEFINI", ""]) | df_clean["Enseignants"].isna()
    df_real = df_clean[~mask_nd]

    errs_text = []      
    errs_for_df = []    

    # --- 1. DÉTECTION DES CONFLITS (Sur les enseignants réels uniquement) ---
    
    # A. Conflit Enseignant
    p_groups = df_real.groupby(['Jours', 'Horaire', 'Enseignants'])
    for (jour, horaire, prof), group in p_groups:
        lieux_uniques = group['Lieu'].unique()
        matieres_uniques = group['Enseignements'].unique()
        if len(lieux_uniques) > 1 or len(matieres_uniques) > 1:
            type_err = "❌ CONFLIT ENSEIGNANT"
            detail = f"L'enseignant est affecté à plusieurs lieux ({', '.join(lieux_uniques)}) ou matières."
            msg = f"**{type_err}** : {prof} | {jour} {horaire}"
            errs_text.append(("error", msg))
            errs_for_df.append({
                "Type": type_err, "Enseignant": prof, "Jour": jour, "Horaire": horaire, 
                "Détail": detail, "Lieu": ", ".join(lieux_uniques), 
                "Matières": ", ".join(matieres_uniques), "Promotion": ", ".join(group['Promotion'].unique())
            })

    # B. Conflit Salle (On garde le conflit même si un des profs est ND, car la salle est physiquement occupée)
    s_groups = df[(df["Lieu"] != "Non défini") & (df["Lieu"] != "A distance")].groupby(['Jours', 'Horaire', 'Lieu'])
    for (jour, horaire, lieu), group in s_groups:
        profs_en_salle = group['Enseignants'].unique()
        if len(profs_en_salle) > 1:
            # On ne signale le conflit de salle que si au moins un prof n'est pas "ND"
            profs_reels = [p for p in profs_en_salle if str(p).upper() not in ["ND", "NON DÉFINI"]]
            if len(profs_reels) > 0:
                type_err = "❌ CONFLIT SALLE OCCUPÉE"
                detail = f"La salle '{lieu}' est partagée par : {', '.join(profs_en_salle)}"
                msg = f"**{type_err}** : {lieu} | {jour} {horaire} ({', '.join(profs_en_salle)})"
                errs_text.append(("error", msg))
                for p in profs_reels:
                    errs_for_df.append({
                        "Type": type_err, "Enseignant": p, "Jour": jour, "Horaire": horaire, 
                        "Détail": detail, "Lieu": lieu, 
                        "Matières": ", ".join(group['Enseignements'].unique()), 
                        "Promotion": ", ".join(group['Promotion'].unique())
                    })

    # C. Conflit Promotion
    pr_groups = df.groupby(['Jours', 'Horaire', 'Promotion'])
    for (jour, horaire, promo), group in pr_groups:
        if len(group['Enseignements'].unique()) > 1:
            type_err = "⚠️ CONFLIT PROMOTION"
            matieres = group['Enseignements'].unique()
            detail = f"La promotion {promo} a plusieurs cours simultanés : {', '.join(matieres)}"
            msg = f"**{type_err}** : {promo} | {jour} {horaire}"
            errs_text.append(("warning", msg))
            errs_for_df.append({
                "Type": type_err, "Enseignant": "Multi-enseignants", "Jour": jour, "Horaire": horaire, 
                "Détail": detail, "Lieu": ", ".join(group['Lieu'].unique()), 
                "Matières": ", ".join(matieres), "Promotion": promo
            })

    # --- 2. AFFICHAGE ET RÉSOLUTION ---
    if errs_for_df:
        st.markdown(f"### 📊 Anomalies prioritaires (Hors ND) : {len(errs_text)}")
        for style, m in errs_text[:30]: # Limite à 30 pour la fluidité
            if style == "error": st.error(m)
            else: st.warning(m)

        st.divider()
        st.subheader("💡 Assistant de Résolution")
        
        tous_jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
        tous_horaires = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]
        tous_les_lieux = sorted([str(l) for l in df['Lieu'].unique() if str(l) not in ["nan", "Non défini"]])
        
        solutions_finales = []

        for i, cp in enumerate(errs_for_df):
            with st.expander(f"📍 Solution : {cp['Enseignant']} - {cp['Jour']}", expanded=(i==0)):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Problème :** {cp['Détail']}")
                    st.caption(f"Matières : {cp['Matières']} | Promo : {cp['Promotion']}")
                
                with c2:
                    l_init = str(cp['Lieu']).upper()
                    est_tp = any(k in l_init for k in ["LABO", "TP", "MICRO"])
                    est_amphi = "AMPHI" in l_init
                    
                    lieux_compatibles = [l for l in tous_les_lieux if (
                        (est_tp and any(k in l.upper() for k in ["LABO", "TP", "MICRO"])) or
                        (est_amphi and "AMPHI" in l.upper()) or
                        (not est_tp and not est_amphi and ("S" in l.upper() or "A" in l.upper()))
                    )]

                    suggestions = []
                    for j_sol in tous_jours:
                        for h_sol in tous_horaires:
                            # Prof libre ? (Seulement si prof réel)
                            p_check = True
                            if cp['Enseignant'] != "Multi-enseignants":
                                p_check = df[(df['Jours']==j_sol) & (df['Horaire']==h_sol) & (df['Enseignants']==cp['Enseignant'])].empty
                            
                            pr_free = df[(df['Jours']==j_sol) & (df['Horaire']==h_sol) & (df['Promotion']==cp['Promotion'])].empty
                            
                            if p_check and pr_free:
                                l_occ = df[(df['Jours']==j_sol) & (df['Horaire']==h_sol)]['Lieu'].unique()
                                s_libres = [sl for sl in lieux_compatibles if sl not in l_occ]
                                for s in s_libres[:1]:
                                    suggestions.append(f"{j_sol} | {h_sol} en {s}")

                    choix = st.selectbox("🚀 Créneau suggéré :", ["-- Garder actuel --"] + suggestions[:10], key=f"ai_sol_{i}")
                    
                    solutions_finales.append({
                        "Enseignements": cp['Matières'],
                        "Code": "S2-2026",
                        "Enseignants": cp['Enseignant'],
                        "Horaire": cp['Horaire'],
                        "Jours": cp['Jour'],
                        "Lieu": cp['Lieu'],
                        "Promotion": cp['Promotion'],
                        "PROPOSITION_CORRECTION": choix
                    })

        # --- 3. EXPORT ---
        st.divider()
        df_final = pd.DataFrame(solutions_finales)
        # Disposition demandée : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
        order = ["Enseignements", "Code", "Enseignants", "Horaire", "Jours", "Lieu", "Promotion", "PROPOSITION_CORRECTION"]
        df_final = df_final[order]
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Plan_Correction')
        
        st.download_button(
            label="📥 Télécharger le Plan de Correction (Excel)",
            data=output.getvalue(),
            file_name="Plan_Correction_EDT_S2_2026.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True,
            type="primary"
        )
    elif portail == "📅 Surveillances Examens":
        FILE_S = "surveillances_2026.xlsx"
        if os.path.exists(FILE_S):
            df_surv = pd.read_excel(FILE_S)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
            
            for c in df_surv.columns: 
                df_surv[c] = df_surv[c].fillna("").astype(str).str.strip()
                
            c_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_surv.columns else 'Enseignants'
            u_nom = user['nom_officiel']
            u_email = user.get('email', '').lower().strip()

            is_master_admin = (u_email == "milouafarid@gmail.com")

            if is_master_admin:
                tous_les_profs = []
                for entry in df_surv[c_prof].unique():
                    for p in entry.split('&'):
                        clean_p = p.strip()
                        if clean_p and clean_p not in ["nan", "Non défini", ""]:
                            tous_les_profs.append(clean_p)
                liste_profs = sorted(list(set(tous_les_profs)))
                st.success("🔓 Accès Maître : milouafarid@gmail.com")
                prof_sel = st.selectbox("🔍 Choisir un enseignant :", liste_profs)
            else:
                prof_sel = u_nom
                st.info(f"👤 Espace Personnel : **{u_nom}**")

            df_u_surv = df_surv[df_surv[c_prof].str.contains(prof_sel, case=False, na=False)].sort_values(by='Date_Tri')
            st.markdown(f"### 📋 Planning de : {prof_sel}")
            
            c1, c2, c3 = st.columns(3)
            nb_mat = len(df_u_surv[df_u_surv['Heure'].str.contains("08h|09h|10h", case=False)])
            c1.metric("Séances Total", len(df_u_surv))
            c2.metric("Matin", nb_mat)
            c3.metric("Après-midi", len(df_u_surv) - nb_mat)
            
            st.divider()

            if not df_u_surv.empty:
                for _, r in df_u_surv.iterrows():
                    st.markdown(f"""
                    <div style="background:#f9f9f9;padding:12px;border-radius:8px;border-left:5px solid #1E3A8A;margin-bottom:8px;">
                        <span style="font-weight:bold;color:#1E3A8A;">📅 {r['Jour']} {r['Date']}</span> | 🕒 {r['Heure']}<br>
                        <b>📖 {r['Matière']}</b><br>
                        <small>📍 {r['Salle']} | 🎓 {r['Promotion']} | 👥 {r[c_prof]}</small>
                    </div>""", unsafe_allow_html=True)
                
                buf = io.BytesIO()
                df_u_surv.drop(columns=['Date_Tri']).to_excel(buf, index=False)
                st.download_button(f"📥 Télécharger l'EDT de {prof_sel}", buf.getvalue(), f"Surv_{prof_sel}.xlsx")
            else:
                st.warning(f"⚠️ Aucune surveillance trouvée pour : {prof_sel}")
        else:
            st.error("Le fichier 'surveillances_2026.xlsx' est absent.")

    elif portail == "🤖 Générateur Automatique":
        if not is_admin:
            st.error("Accès réservé au Bureau des Examens.")
        else:
            st.header("⚙️ Moteur de Génération de Surveillances")
            if "effectifs_db" not in st.session_state:
                st.session_state.effectifs_db = {"ING1": [50, 4], "MCIL1": [40, 3], "L1MCIL": [288, 4], "L2ELT": [90, 2], "M1RE": [15, 1], "ING2": [16, 1]}

            with st.expander("📦 Gestion des Effectifs", expanded=False):
                data_eff = [{"Promotion": k, "Effectif Total": v[0], "Nb de Salles": v[1]} for k, v in st.session_state.effectifs_db.items()]
                edited_eff = st.data_editor(pd.DataFrame(data_eff), use_container_width=True, num_rows="dynamic", hide_index=True)
                if st.button("💾 Sauvegarder la configuration"):
                    st.session_state.effectifs_db = {row["Promotion"]: [int(row["Effectif Total"]), int(row["Nb de Salles"])] for _, row in edited_eff.iterrows()}
                    st.success("Mis à jour !")

            SRC = "surveillances_2026.xlsx"
            if os.path.exists(SRC):
                df_src = pd.read_excel(SRC)
                df_src.columns = [str(c).strip() for c in df_src.columns]
                for c in df_src.columns: df_src[c] = df_src[c].fillna("").astype(str).str.strip()
                
                C_MAT, C_RESP, C_SURV, C_DATE, C_HEURE, C_SALLE, C_PROMO = "Matière", "Chargé de matière", "Surveillant(s)", "Date", "Heure", "Salle", "Promotion"
                df_src = df_src[~df_src[C_MAT].str.contains(r'\bTP\b|\bTD\b', case=False, na=False)]
                liste_profs = sorted([p for p in df_src[C_SURV].unique() if p not in ["", "nan", "Non défini"]])

                with st.expander("⚖️ Plafonnement", expanded=True):
                    col1, col2 = st.columns(2)
                    m_base = col1.number_input("Max séances", min_value=1, value=10)
                    ratio = col2.number_input("Ratio Étud/Surv", min_value=1, value=25)
                
                p_cible = st.multiselect("🎓 Promotions :", sorted(df_src[C_PROMO].unique()))
                if st.button("🚀 GÉNÉRER LE PLANNING") and p_cible:
                    stats = {p: 0 for p in liste_profs}
                    tracker, res_list = [], []
                    for p_name in p_cible:
                        df_p = df_src[df_src[C_PROMO] == p_name].drop_duplicates(subset=[C_MAT, C_DATE, C_HEURE])
                        conf = st.session_state.effectifs_db.get(p_name, [30, 1])
                        eff_total, nb_salles = conf[0], int(conf[1])
                        for _, row in df_p.iterrows():
                            for s_idx in range(1, nb_salles + 1):
                                eff_salle = eff_total // nb_salles
                                nb_req = max(2, (eff_salle // ratio) + (1 if eff_salle % ratio > 0 else 0))
                                equipe = []
                                tri_prio = sorted(liste_profs, key=lambda x: stats[x])
                                for p in tri_prio:
                                    if len(equipe) < nb_req and stats[p] < m_base:
                                        if not any(t for t in tracker if t['D']==row[C_DATE] and t['H']==row[C_HEURE] and t['N']==p):
                                            equipe.append(p); stats[p] += 1
                                            tracker.append({'D': row[C_DATE], 'H': row[C_HEURE], 'N': p})
                                res_list.append({"Enseignements": row[C_MAT], "Code": "S2-2026", "Enseignants": " & ".join(equipe) if len(equipe) >= 2 else "⚠️ BESOIN RENFORT", "Horaire": row[C_HEURE], "Jours": row[C_DATE], "Lieu": f"Salle {s_idx}" if nb_salles > 1 else row[C_SALLE], "Promotion": f"{p_name} (S{s_idx})" if nb_salles > 1 else p_name})
                    st.session_state.df_genere = pd.DataFrame(res_list)
                    st.session_state.stats_charge = stats
                    st.rerun()

                if st.session_state.get("df_genere") is not None:
                    st.dataframe(st.session_state.df_genere, use_container_width=True, hide_index=True)
                    xlsx_buf = io.BytesIO()
                    with pd.ExcelWriter(xlsx_buf, engine='xlsxwriter') as writer: st.session_state.df_genere.to_excel(writer, index=False)
                    st.download_button("📥 TÉLÉCHARGER LE PLANNING", xlsx_buf.getvalue(), "EDT_Surveillances_2026.xlsx")

    elif portail == "👥 Portail Enseignants":
        if not is_admin:
            st.error("🚫 ACCÈS RESTREINT.")
            st.stop()
        
        # --- EN-TÊTE ---
        col_l, col_t = st.columns([1, 5])
        with col_l:
            st.image("logo.PNG", width=80)
        with col_t:
            st.header("🏢 Répertoire et Envoi Automatisé")
            st.write("Plateforme de gestion des emplois du temps 2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

        # 1. RÉCUPÉRATION DES DONNÉES (Supabase + Répertoire Source Excel)
        res_auth = supabase.table("enseignants_auth").select("nom_officiel, email, last_sent").execute()
        dict_auth = {str(row['nom_officiel']).strip().upper(): {
            "email": row['email'], 
            "statut": "✅ Envoyé" if row['last_sent'] else "⏳ En attente"
        } for row in res_auth.data} if res_auth.data else {}

        noms_excel = sorted([e for e in df['Enseignants'].unique() if str(e) not in ["Non défini", "nan", ""]])
        
        donnees_finales = []
        for nom in noms_excel:
            nom_key = str(nom).strip().upper()
            
            # Logique de récupération de l'email
            if nom_key in dict_auth:
                email = dict_auth[nom_key]["email"]
                etat = dict_auth[nom_key]["statut"]
            elif nom_key in repertoire_source:
                email = repertoire_source[nom_key]
                etat = "🟡 Dispo (Source Excel)"
            else:
                email = "⚠️ Mail introuvable"
                etat = "❌ Absent"
                
            donnees_finales.append({
                "Enseignant": nom,
                "Email": email,
                "État d'envoi": etat
            })

        # 2. BOUTONS D'ACTION
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Réinitialiser les statuts (Comptes)", use_container_width=True):
                supabase.table("enseignants_auth").update({"last_sent": None}).neq("email", "").execute()
                st.success("✅ Statuts réinitialisés !")
                st.rerun()
        
        with c2:
            if st.button("🚀 Lancer l'envoi groupé", type="primary", use_container_width=True):
                import smtplib
                import io
                import os
                import pandas as pd
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                from email.mime.base import MIMEBase
                from email import encoders
                from datetime import datetime

                try:
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
                    
                    for row in donnees_finales:
                        # On envoie si le mail est présent et l'état est "En attente" ou "Dispo Source"
                        if (row["État d'envoi"] in ["⏳ En attente", "🟡 Dispo (Source Excel)"]) and "@" in str(row["Email"]):
                            
                            # 1. FILTRAGE ET CALCULS
                            nom_cible = str(row['Enseignant']).strip().upper()
                            # Filtrage qui inclut les noms composés (comme FETHIMILOUA)
                            df_perso = df[df["Enseignants"].astype(str).str.upper().str.contains(nom_cible, na=False)]
                            df_mail = df_perso[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']]
                            
                            nb_cours = df_mail['Enseignements'].str.contains('Cours', case=False).sum()
                            nb_td = df_mail['Enseignements'].str.contains('TD', case=False).sum()
                            nb_tp = df_mail['Enseignements'].str.contains('TP', case=False).sum()

                            msg = MIMEMultipart()
                            msg['Subject'] = f"Votre Emploi du Temps S2-2026 - {row['Enseignant']}"
                            msg['From'] = st.secrets["EMAIL_USER"]
                            msg['To'] = row["Email"]
                            
                            # 2. CORPS DU MESSAGE (Structure identique à l'individuel)
                            corps_html = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                                <h2 style="color: #1E3A8A;">Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h2>
                                <p>Sallem M./Mme <b>{row['Enseignant']}</b>,</p>
                                
                                <div style="background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; border-radius: 5px; margin-bottom: 15px;">
                                    <b>📊 Récapitulatif de votre charge (S2-2026) :</b><br>
                                    <ul>
                                        <li>Nombre de Cours : <b>{nb_cours}</b></li>
                                        <li>Nombre de TD : <b>{nb_td}</b></li>
                                        <li>Nombre de TP : <b>{nb_tp}</b></li>
                                    </ul>
                                </div>

                                <div style="background-color: #fff4e5; border-left: 5px solid #ffa500; padding: 15px; margin: 20px 0; font-style: italic;">
                                    <p>J'ai été chargé en tant que représentant des responsables des équipes de formation, en concertation avec le chef de département et le vice doyen chargé de la graduation, de coordonner l'élaboration de ces emplois du temps.</p>
                                    <p>Je vous prie de bien vouloir nous signaler une éventuelle anomalie. Merci de nous renseigner le fichier Excel corrigé, au cas où tout est bon merci de nous envoyer <b>RAS</b>.</p>
                                </div>

                                {df_mail.to_html(index=False, border=1, justify='center')}

                                <p><br>Cordialement.<br>---<br><b>Service d'enseignement du département d'électrotechnique.</b></p>
                            </body>
                            </html>
                            """
                            msg.attach(MIMEText(corps_html, 'html'))

                            # 3. GÉNÉRATION DE L'EXCEL COLORÉ ET FILTRÉ (En mémoire)
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                df_mail.to_excel(writer, index=False, sheet_name='Mon EDT')
                                workbook = writer.book
                                worksheet = writer.sheets['Mon EDT']

                                # Formats
                                fmt_cours = workbook.add_format({'bg_color': '#D9EAD3', 'border': 1})
                                fmt_td = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1})
                                fmt_tp = workbook.add_format({'bg_color': '#F4CCCC', 'border': 1})
                                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})

                                for col_num, value in enumerate(df_mail.columns.values):
                                    worksheet.write(0, col_num, value, fmt_header)

                                for i, enseignement in enumerate(df_mail['Enseignements']):
                                    current_fmt = None
                                    if 'Cours' in str(enseignement): current_fmt = fmt_cours
                                    elif 'TD' in str(enseignement): current_fmt = fmt_td
                                    elif 'TP' in str(enseignement): current_fmt = fmt_tp
                                    if current_fmt: worksheet.set_row(i + 1, None, current_fmt)
                                
                                worksheet.set_column('A:G', 20)
                            
                            buffer.seek(0)
                            part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                            part.set_payload(buffer.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename="EDT_S2_2026_{row["Enseignant"]}.xlsx"')
                            msg.attach(part)
                            
                            # 4. ENVOI ET MISE À JOUR
                            server.send_message(msg)
                            
                            # Si c'est un inscrit Supabase, on met à jour la date
                            if row["État d'envoi"] == "⏳ En attente":
                                supabase.table("enseignants_auth").update({
                                    "last_sent": datetime.now().isoformat()
                                }).eq("email", row["Email"]).execute()
                    
                    server.quit()
                    st.success("✅ Envoi groupé terminé ! Chaque enseignant a reçu son Excel personnalisé.")
                    st.rerun()

                except Exception as e:
                    st.error(f"Erreur lors de l'envoi groupé : {e}")
        # 3. AFFICHAGE DU TABLEAU RECAPITULATIF
        st.divider()
        st.dataframe(pd.DataFrame(donnees_finales), use_container_width=True, hide_index=True)
        # --- 3. GESTION DES ENVOIS PERSONNALISÉS (INDIVIDUEL OU SÉLECTION) ---
        st.divider()
        st.subheader("📬 Gestion des envois personnalisés")

        # Option de mode d'envoi
        mode_envoi = st.radio("Choisir le mode d'envoi :", 
                              ["Un par un (Individuel)", "Sélection groupée (Multi-choix)"], 
                              horizontal=True)

        # --- ZONE DE FILTRES ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            liste_noms = ["TOUS"] + sorted([row["Enseignant"] for row in donnees_finales])
            choix_enseignant = st.selectbox("🔍 Chercher un nom :", liste_noms)
        with col_f2:
            choix_statut = st.selectbox("📊 Filtrer par statut :", ["TOUS", "⏳ En attente", "✅ Envoyé", "❌ Absent"])

        # Pré-filtrage de la liste pour les deux modes
        enseignants_filtres = []
        for row in donnees_finales:
            if choix_enseignant != "TOUS" and row["Enseignant"] != choix_enseignant:
                continue
            if choix_statut != "TOUS" and row["État d'envoi"] != choix_statut:
                continue
            enseignants_filtres.append(row)

        if mode_envoi == "Sélection groupée (Multi-choix)":
            # --- MODE MULTI-SÉLECTION ---
            st.info("Cochez les enseignants dans la liste déroulante ci-dessous pour lancer un envoi groupé spécifique.")
            
            noms_disponibles = [e["Enseignant"] for e in enseignants_filtres if "@" in str(e["Email"])]
            selection = st.multiselect("Sélectionner les enseignants :", noms_disponibles)
            
            if st.button(f"🚀 Envoyer à la sélection ({len(selection)})", type="primary"):
                if not selection:
                    st.warning("Veuillez sélectionner au moins un enseignant.")
                else:
                    import smtplib, io, pandas as pd
                    from email.mime.text import MIMEText
                    from email.mime.multipart import MIMEMultipart
                    from email.mime.base import MIMEBase
                    from email import encoders
                    from datetime import datetime

                    try:
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
                        
                        progress_bar = st.progress(0)
                        for i, nom in enumerate(selection):
                            # Trouver les infos de l'enseignant sélectionné
                            info_ens = next(e for e in enseignants_filtres if e["Enseignant"] == nom)
                            
                            # 1. FILTRAGE ET RECAP
                            nom_cible = str(nom).strip().upper()
                            df_perso = df[df["Enseignants"].astype(str).str.upper().str.contains(nom_cible, na=False)]
                            df_mail = df_perso[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']]
                            
                            nb_cours = df_mail['Enseignements'].str.contains('Cours', case=False).sum()
                            nb_td = df_mail['Enseignements'].str.contains('TD', case=False).sum()
                            nb_tp = df_mail['Enseignements'].str.contains('TP', case=False).sum()

                            msg = MIMEMultipart()
                            msg['Subject'] = f"Votre Emploi du Temps S2-2026 - {nom}"
                            msg['From'] = st.secrets["EMAIL_USER"]
                            msg['To'] = info_ens["Email"]

                            # 2. CORPS DU MESSAGE
                            corps_html = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                                <h2 style="color: #1E3A8A;">Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h2>
                                <p>Sallem M./Mme <b>{nom}</b>,</p>
                                <div style="background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; border-radius: 5px;">
                                    <b>📊 Récapitulatif de votre charge (S2-2026) :</b><br>
                                    <ul>
                                        <li>Nombre de Cours : <b>{nb_cours}</b></li>
                                        <li>Nombre de TD : <b>{nb_td}</b></li>
                                        <li>Nombre de TP : <b>{nb_tp}</b></li>
                                    </ul>
                                </div>
                                <div style="background-color: #fff4e5; border-left: 5px solid #ffa500; padding: 15px; margin: 20px 0; font-style: italic;">
                                    <p>J'ai été chargé en tant que représentant des responsables des équipes de formation, en concertation avec le chef de département et le vice doyen chargé de la graduation, de coordonner l'élaboration de ces emplois du temps.</p>
                                    <p>Je vous prie de bien vouloir nous signaler une éventuelle anomalie. Merci de nous renseigner le fichier Excel corrigé, au cas où tout est bon merci de nous envoyer <b>RAS</b>.</p>
                                </div>
                                {df_mail.to_html(index=False, border=1, justify='center')}
                                <p><br>Cordialement.<br>---<br><b>Service d'enseignement du département d'électrotechnique.</b></p>
                            </body>
                            </html>
                            """
                            msg.attach(MIMEText(corps_html, 'html'))

                            # 3. EXCEL COLORÉ
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                df_mail.to_excel(writer, index=False, sheet_name='Mon EDT')
                                workbook = writer.book
                                worksheet = writer.sheets['Mon EDT']
                                fmt_cours = workbook.add_format({'bg_color': '#D9EAD3', 'border': 1})
                                fmt_td = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1})
                                fmt_tp = workbook.add_format({'bg_color': '#F4CCCC', 'border': 1})
                                fmt_header = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
                                for col_num, val in enumerate(df_mail.columns.values): worksheet.write(0, col_num, val, fmt_header)
                                for idx_row, ens in enumerate(df_mail['Enseignements']):
                                    f = None
                                    if 'Cours' in str(ens): f = fmt_cours
                                    elif 'TD' in str(ens): f = fmt_td
                                    elif 'TP' in str(ens): f = fmt_tp
                                    if f: worksheet.set_row(idx_row + 1, None, f)
                                worksheet.set_column('A:G', 18)
                            
                            buffer.seek(0)
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(buffer.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename="EDT_2026_{nom}.xlsx"')
                            msg.attach(part)
                            
                            server.send_message(msg)
                            progress_bar.progress((i + 1) / len(selection))
                        
                        server.quit()
                        st.success(f"✅ Envoi terminé pour les {len(selection)} enseignant(s) sélectionné(s).")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

        else:
            # --- MODE INDIVIDUEL (Bouton par ligne) ---
            for idx, row in enumerate(enseignants_filtres):
                col_ens, col_mail, col_stat, col_act = st.columns([2, 2, 1, 1])
                col_ens.write(f"**{row['Enseignant']}**")
                col_mail.write(row['Email'])
                col_stat.write(row["État d'envoi"])
                
                if "@" in str(row["Email"]):
                    if col_act.button("📧 Envoyer", key=f"btn_unit_{row['Enseignant']}_{idx}"):
                        import smtplib, io, pandas as pd
                        from email.mime.text import MIMEText
                        from email.mime.multipart import MIMEMultipart
                        from email.mime.base import MIMEBase
                        from email import encoders
                        from datetime import datetime

                        try:
                            server = smtplib.SMTP('smtp.gmail.com', 587)
                            server.starttls()
                            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
                            
                            nom_cible = str(row['Enseignant']).strip().upper()
                            df_perso = df[df["Enseignants"].astype(str).str.upper().str.contains(nom_cible, na=False)]
                            df_mail = df_perso[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']]
                            
                            nb_cours = df_mail['Enseignements'].str.contains('Cours', case=False).sum()
                            nb_td = df_mail['Enseignements'].str.contains('TD', case=False).sum()
                            nb_tp = df_mail['Enseignements'].str.contains('TP', case=False).sum()

                            msg = MIMEMultipart()
                            msg['Subject'] = f"Votre Emploi du Temps S2-2026 - {row['Enseignant']}"
                            msg['From'] = st.secrets["EMAIL_USER"]
                            msg['To'] = row["Email"]
                            
                            corps_html = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                                <h2 style="color: #1E3A8A;">Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h2>
                                <p>Sallem M./Mme <b>{row['Enseignant']}</b>,</p>
                                <div style="background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; border-radius: 5px; margin-bottom:10px;">
                                    <b>📊 Récapitulatif de votre charge (S2-2026) :</b><br>
                                    <ul>
                                        <li>Nombre de Cours : <b>{nb_cours}</b></li>
                                        <li>Nombre de TD : <b>{nb_td}</b></li>
                                        <li>Nombre de TP : <b>{nb_tp}</b></li>
                                    </ul>
                                </div>
                                <div style="background-color: #fff4e5; border-left: 5px solid #ffa500; padding: 15px; margin: 20px 0; font-style: italic;">
                                    <p>J'ai été chargé en tant que représentant des responsables des équipes de formation, en concertation avec le chef de département et le vice doyen chargé de la graduation, de coordonner l'élaboration de ces emplois du temps.</p>
                                    <p>Je vous prie de bien vouloir nous signaler une éventuelle anomalie. Merci de nous renseigner le fichier Excel corrigé, au cas où tout est bon merci de nous envoyer <b>RAS</b>.</p>
                                </div>
                                {df_mail.to_html(index=False, border=1, justify='center')}
                                <p><br>Cordialement.<br>---<br><b>Service d'enseignement du département d'électrotechnique.</b></p>
                            </body>
                            </html>
                            """
                            msg.attach(MIMEText(corps_html, 'html'))

                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                df_mail.to_excel(writer, index=False, sheet_name='Mon EDT')
                                workbook = writer.book
                                worksheet = writer.sheets['Mon EDT']
                                f_cours = workbook.add_format({'bg_color': '#D9EAD3', 'border': 1})
                                f_td = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1})
                                f_tp = workbook.add_format({'bg_color': '#F4CCCC', 'border': 1})
                                f_head = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
                                for c, v in enumerate(df_mail.columns.values): worksheet.write(0, c, v, f_head)
                                for i, ens in enumerate(df_mail['Enseignements']):
                                    fmt = None
                                    if 'Cours' in str(ens): fmt = f_cours
                                    elif 'TD' in str(ens): fmt = f_td
                                    elif 'TP' in str(ens): fmt = f_tp
                                    if fmt: worksheet.set_row(i + 1, None, fmt)
                                worksheet.set_column('A:G', 18)
                            
                            buffer.seek(0)
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(buffer.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename="EDT_2026_{row["Enseignant"]}.xlsx"')
                            msg.attach(part)
                            
                            server.send_message(msg)
                            server.quit()
                            st.success(f"✅ Envoyé à {row['Enseignant']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
        # --- FIN DE LA BOUCLE ---
    elif portail == "🎓 Portail Étudiants":
        st.header("📚 Espace Étudiants")
        p_etu = st.selectbox("Choisir votre Promotion :", sorted(df["Promotion"].unique()))
        # DISPOSITION : Enseignements, Code, Enseignants, Horaire, Jours, Lieu
        disp_etu = df[df["Promotion"] == p_etu][['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu']]
        st.table(disp_etu.sort_values(by=["Jours", "Horaire"]))

        if is_admin:
            st.divider(); st.subheader("✍️ Espace Éditeur de Données (Admin)")
            search_query = st.text_input("🔍 Rechercher une ligne :")
            cols_format = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion', 'Chevauchement']
            for col in cols_format: 
                if col not in df.columns: df[col] = ""
            df_to_edit = df[df[cols_format].apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)].copy() if search_query else df[cols_format].copy()
            edited_df = st.data_editor(df_to_edit, use_container_width=True, num_rows="dynamic", key="admin_master_editor")

            if st.button("💾 Sauvegarder les modifications"):
                try:
                    if search_query: df.update(edited_df)
                    else: df = edited_df
                    df[cols_format].to_excel(NOM_FICHIER_FIXE, index=False)
                    st.success("✅ Modifications enregistrées !"); st.rerun()
                except Exception as e: st.error(f"Erreur : {e}")









































































