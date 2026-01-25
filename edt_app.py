import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime, timedelta, date
from supabase import create_client

# --- TITRE OFFICIEL ET CONFIG ---
TITRE_OFFICIEL = "Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA"
st.set_page_config(page_title="EDT UDL 2026", layout="wide", initial_sidebar_state="expanded")

# --- CONNEXION BASE DE DONNÉES ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- CHARGEMENT DES DONNÉES ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"

@st.cache_data
def charger_donnees():
    if os.path.exists(NOM_FICHIER_FIXE):
        df_src = pd.read_excel(NOM_FICHIER_FIXE)
        df_src.columns = [str(c).strip() for c in df_src.columns]
        # On garde uniquement les cours pour les examens
        df_cours = df_src[df_src['Code'].str.contains("Cours", case=False, na=False)].copy()
        tous_profs = sorted(df_src['Enseignants'].dropna().unique().tolist())
        return df_src, df_cours, tous_profs
    return pd.DataFrame(), pd.DataFrame(), []

df_global, df_examens, liste_enseignants_globale = charger_donnees()

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .main-title {{ color: #1E3A8A; text-align: center; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; font-size: 20px; }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 10px; }}
    </style>
""", unsafe_allow_html=True)

# --- SYSTÈME D'AUTH ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown(f"<h1 class='main-title'>{TITRE_OFFICIEL}</h1>", unsafe_allow_html=True)
    t_conn, t_ins, t_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    
    with t_conn:
        email_in = st.text_input("Email", key="l_email")
        pass_in = st.text_input("Password", type="password", key="l_pass")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_in).eq("password_hash", hash_pw(pass_in)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
    
    with t_ins:
        st.subheader("📝 Nouveau Compte")
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            n_nom = st.selectbox("Nom dans l'EDT", liste_enseignants_globale)
            n_email = st.text_input("Email")
            n_statut = st.radio("Statut", ["Permanent", "Vacataire"], horizontal=True)
        with col_n2:
            n_pass = st.text_input("Mot de passe", type="password")
            n_conf = st.text_input("Confirmation", type="password")
            n_phone = st.text_input("Téléphone (Obligatoire pour vacataires)") if n_statut == "Vacataire" else None

        if st.button("Créer le compte"):
            if n_pass == n_conf and n_email:
                data = {"nom_officiel": n_nom, "email": n_email, "password_hash": hash_pw(n_pass), "role": "enseignant", "statut": n_statut, "telephone": n_phone}
                supabase.table("enseignants_auth").insert(data).execute()
                st.success("Compte créé !")

    with t_adm:
        code_admin = st.text_input("Code Admin", type="password")
        if st.button("Accès Admin"):
            if code_admin == "doctorat2026":
                st.session_state["user_data"] = {"nom_officiel": "ADMINISTRATEUR", "role": "admin"}
                st.rerun()
    st.stop()

# --- ESPACE CONNECTÉ ---
user = st.session_state["user_data"]
with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Sélectionner Espace", ["📖 Emploi du Temps", "🤖 Générateur Automatique"])
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None
        st.rerun()

# --- LOGIQUE GÉNÉRATEUR AUTOMATIQUE (EXAMENS) ---
if portail == "🤖 Générateur Automatique":
    st.markdown(f"<h2 class='main-title'>{TITRE_OFFICIEL}</h2>", unsafe_allow_html=True)
    st.markdown("<div class='portal-badge'>MODE : GÉNÉRATEUR AUTOMATIQUE D'EXAMENS</div>", unsafe_allow_html=True)

    # 1. PÉRIODE
    st.subheader("📅 1. Période des Examens")
    c1, c2 = st.columns(2)
    d_debut = c1.date_input("Début", date(2026, 5, 17))
    d_fin = c2.date_input("Fin", d_debut + timedelta(days=14))
    
    jours_v = [d_debut + timedelta(days=x) for x in range((d_fin-d_debut).days + 1) if (d_debut + timedelta(days=x)).weekday() not in [4, 5]]
    
    # 2. SURVEILLANCE
    st.subheader("👨‍🏫 2. Attribution & Quotas")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        q_amphi = st.number_input("Surveillants / Amphi", 1, 5, 3)
        q_salle = st.number_input("Surveillants / Salle", 1, 5, 2)
    with col_s2:
        # Récupération des vacataires/sup depuis la DB pour réduction de charge
        vacataires_db = supabase.table("enseignants_auth").select("nom_officiel").eq("statut", "Vacataire").execute()
        liste_vacs = [v['nom_officiel'] for v in vacataires_db.data]
        profs_reduits = st.multiselect("Postes Sup / Vacataires (Charge réduite)", liste_enseignants_globale, default=liste_vacs)
        coeff = st.slider("Coefficient de charge (%)", 10, 100, 50)

    # 3. LOGISTIQUE PAR PROMO
    st.subheader("📦 3. Salles & Amphis")
    L_SALLES = [f"Salle {i:02d}" for i in range(1, 19)]
    L_AMPHIS = [f"Amphi A{i:02d}" for i in range(1, 13)]
    
    config_promo = {}
    for promo in sorted(df_examens['Promotion'].unique()):
        with st.expander(f"🎓 {promo}"):
            c_h, c_e = st.columns(2)
            horaire = c_h.selectbox("Horaire", ["09h00 - 11h00", "14h00 - 16h00"], key=f"h_{promo}")
            eff = c_e.number_input("Effectif", 10, 500, 60, key=f"e_{promo}")
            sel_a = st.multiselect("Amphis", L_AMPHIS, key=f"a_{promo}")
            sel_s = st.multiselect("Salles", L_SALLES, key=f"s_{promo}")
            besoin = (len(sel_a) * q_amphi) + (len(sel_s) * q_salle)
            st.info(f"Besoin : {besoin} surveillants")
            
            config_promo[promo] = {
                "matieres": df_examens[df_examens['Promotion']==promo]['Enseignements'].tolist(),
                "responsables": df_examens[df_examens['Promotion']==promo]['Enseignants'].tolist(),
                "horaire": horaire, "locaux": sel_a + sel_s, "besoin": besoin
            }

    # 4. GÉNÉRATION
    if st.button("🚀 GÉNÉRER LE PLANNING FINAL", type="primary", use_container_width=True):
        charge = {p: 0 for p in liste_enseignants_globale}
        resultats = []
        
        for i, jour in enumerate(jours_v):
            for promo, cfg in config_logistique.items():
                if i < len(cfg['matieres']):
                    resp = cfg['responsables'][i]
                    # Tri par charge pondérée
                    pool = sorted(liste_enseignants_globale, key=lambda p: charge[p] / (coeff/100 if p in profs_reduits else 1))
                    
                    choisis = []
                    for cand in pool:
                        if cand != resp and len(choisis) < cfg['besoin']:
                            choisis.append(cand)
                            charge[cand] += 1
                    
                    resultats.append({
                        "Enseignements": cfg['matieres'][i],
                        "Code": f"Resp: {resp}",
                        "Enseignants": ", ".join(choisis),
                        "Horaire": cfg['horaire'],
                        "Jours": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][jour.weekday()],
                        "Lieu": " / ".join(cfg['locaux']),
                        "Promotion": promo,
                        "Date": jour.strftime('%d/%m/%Y')
                    })
        
        df_res = pd.DataFrame(resultats)
        # Disposition demandée : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
        cols_ordre = ["Enseignements", "Code", "Enseignants", "Horaire", "Jours", "Lieu", "Promotion"]
        st.success("✅ Planning Généré")
        st.dataframe(df_res[cols_ordre], use_container_width=True)
