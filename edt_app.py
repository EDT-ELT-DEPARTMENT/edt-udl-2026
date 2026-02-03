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

jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]

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
    st.subheader("✍️ Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

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
    st.markdown("<h1 class='main-title' style='border-bottom: none; margin-top: 0;'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

with col_date:
    st.markdown(f"<div class='date-badge' style='float: right;'>📅 {nom_jour_fr}<br>{date_str}</div>", unsafe_allow_html=True)

# Ligne dorée décorative et badge du mode
st.markdown("<div style='border-bottom: 3px solid #D4AF37; margin-bottom: 10px;'></div>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE ACTIF : {portail.upper()}</div>", unsafe_allow_html=True)

# --- LOGIQUE PRINCIPALE ---

# --- DÉBUT DU BLOC ENSEIGNANT / PERSONNEL ---
if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
    if mode_view == "Personnel":
        # Récupère le nom de l'utilisateur connecté
        cible = user['nom_officiel']
    else:
        # Affiche la liste déroulante pour l'administrateur
        enseignants_liste = sorted(df["Enseignants"].unique())
        cible = st.selectbox("Sélectionner l'Enseignant :", enseignants_liste)
    
    # Préparation des données filtrées pour l'enseignant sélectionné
    # Utilisation de .copy() pour éviter les avertissements de modification sur vue
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
        
        charge_reelle = df_u['h_val'].sum()
        charge_reg = 3.0 if poste_sup else 6.0
        h_sup = charge_reelle - charge_reg
        color_sup = "#e74c3c" if h_sup > 0 else "#27ae60"

        # ============================================================
# --- ONGLETS ---
# ============================================================

tab_view, tab_t6 = st.tabs(["📅 Mon Emploi du Temps", "📝 Suivi de Séance (T6)"])

# ============================================================
# 📅 ONGLET : EMPLOI DU TEMPS ENSEIGNANT
# ============================================================

with tab_view:
    st.markdown(f"### 📊 Bilan Horaire : {cible}")

    c_m1, c_m2, c_m3 = st.columns(3)

    with c_m1:
        st.markdown(
            f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>",
            unsafe_allow_html=True
        )

    with c_m2:
        st.markdown(
            f"<div class='metric-card'>Réglementaire<br><h2>{charge_reg} h</h2></div>",
            unsafe_allow_html=True
        )

    with c_m3:
        st.markdown(
            f"<div class='metric-card' style='border-color:{color_sup};'>"
            f"Heures Sup.<br><h2 style='color:{color_sup};'>{h_sup} h</h2></div>",
            unsafe_allow_html=True
        )

    def format_case(rows):
        items = []
        for _, r in rows.iterrows():
            txt = (
                f"<b>{get_nature(r['Code'])} : {r['Enseignements']}</b><br>"
                f"({r['Promotion']})<br><i>{r['Lieu']}</i>"
            )
            items.append(txt)
        return "<div class='separator'></div>".join(items)

    if not df_f.empty:
        grid = (
            df_f
            .groupby(['h_norm', 'j_norm'])
            .apply(format_case, include_groups=False)
            .unstack('j_norm')
        )

        grid = (
            grid
            .reindex(
                index=[normalize(h) for h in horaires_list],
                columns=[normalize(j) for j in jours_list]
            )
            .fillna("")
        )

        grid.index = [map_h.get(i, i) for i in grid.index]
        grid.columns = [map_j.get(c, c) for c in grid.columns]

        st.write(grid.to_html(escape=False), unsafe_allow_html=True)


# ============================================================
# 📝 ONGLET : SUIVI DE SÉANCE (T6)
# ============================================================

with tab_t6:
    st.subheader("📝 Registre Numérique de Séance (T6)")
    st.info(f"Enseignant : **{cible}** | S2-2026")

    pwd_t6 = st.text_input("🔑 Code Session :", type="password", key="secu_t6")

    if pwd_t6 == "2026":
        if not df_f.empty:
            mat_t6 = st.selectbox(
                "📚 Séance de :",
                sorted(df_f["Enseignements"].unique())
            )

            promo_t6 = (
                df_f[df_f["Enseignements"] == mat_t6]["Promotion"]
                .iloc[0]
            )

            if st.button("🚀 Valider la séance (Supabase)", use_container_width=True):
                try:
                    payload = {
                        "expediteur": cible,
                        "promotion": promo_t6,
                        "matiere": mat_t6
                    }
                    supabase.table("rapports_assiduite").insert(payload).execute()
                    st.success("✅ Séance enregistrée !")
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.warning("Aucune donnée disponible pour cet enseignant.")
    else:
        st.warning("Veuillez saisir le code '2026'.")


# ============================================================
# 📋 VUE ADMIN : PROMOTION
# ============================================================

elif is_admin and mode_view == "Promotion":
    st.subheader("📋 Vue par Promotion")

    promos_dispo = sorted(df["Promotion"].unique())
    p_sel = st.selectbox("Choisir Promotion :", promos_dispo)

    df_p = df[df["Promotion"] == p_sel]

    def fmt_p(rows):
        items = []
        for _, r in rows.iterrows():
            nat = (
                '📘 COURS' if 'COURS' in str(r['Code']).upper()
                else '📗 TD' if 'TD' in str(r['Code']).upper()
                else '📙 TP'
            )
            items.append(
                f"<b>{nat} : {r['Enseignements']}</b><br>"
                f"{r['Enseignants']}<br><i>{r['Lieu']}</i>"
            )
        return "<div class='separator'></div>".join(items)

    if not df_p.empty:
        grid_p = (
            df_p
            .groupby(['h_norm', 'j_norm'])
            .apply(fmt_p, include_groups=False)
            .unstack('j_norm')
        )

        grid_p = (
            grid_p
            .reindex(
                index=[normalize(h) for h in horaires_list],
                columns=[normalize(j) for j in jours_list]
            )
            .fillna("")
        )

        grid_p.index = horaires_list
        grid_p.columns = jours_list

        st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)
