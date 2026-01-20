import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
from supabase import create_client
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- FONCTION SÉCURITÉ ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .main-title {{ color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; }}
    .welcome-box {{ background-color: #e8f0fe; border-left: 5px solid #1E3A8A; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .stat-box {{ padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; margin-bottom: 5px; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; height: 95px; font-size: 11px; background-color: white; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    @media print {{ section[data-testid="stSidebar"], button {{ display: none !important; }} }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU FICHIER ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None
if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns: df[col] = df[col].fillna("Non défini").astype(str).str.strip()

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🔑 Connexion", "📝 Inscription Enseignant", "🛡️ Admin"])
    with t1:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
    with t2:
        new_em = st.text_input("Email professionnel")
        new_nom = st.selectbox("Sélectionnez votre nom officiel", sorted(df['Enseignants'].unique())) if df is not None else ""
        new_ps = st.text_input("Mot de passe", type="password")
        if st.button("Valider l'inscription"):
            try:
                supabase.table("enseignants_auth").insert({"email": new_em, "nom_officiel": new_nom, "password_hash": hash_pw(new_ps)}).execute()
                st.success("Compte créé avec succès !")
            except: st.error("Email déjà utilisé ou erreur.")
    with t3:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Accès Direction"): st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}; st.rerun()
    st.stop()

# --- ESPACE CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    poste_sup = st.checkbox("Poste Supérieur (Décharge 50%)") if not is_admin else False
    if is_admin: mode = st.radio("Navigation", ["Promotion", "Enseignant", "🚩 Vérificateur"])
    else: mode = "Personnel"
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

# --- CALCUL ET AFFICHAGE ---
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

if df is not None:
    cible = user['nom_officiel'] if mode == "Personnel" else (st.selectbox("Choisir Enseignant", sorted(df['Enseignants'].unique())) if mode == "Enseignant" else None)
    
    if cible:
        df_f = df[df['Enseignants'] == cible].copy()
        
        # Logique de calcul précise
        def get_val(ens):
            txt = str(ens).upper()
            if "COURS" in txt: return 1.5, "COURS"
            if "TD" in txt: return 1.0, "TD"
            if "TP" in txt: return 1.0, "TP"
            return 0.0, "AUTRE"

        df_f[['h_val', 'Type']] = df_f['Enseignements'].apply(lambda x: pd.Series(get_val(x)))
        df_unique = df_f.drop_duplicates(subset=['Jours', 'Horaire'])
        
        # --- CALCUL DEMANDÉ ---
        charge_reelle = df_unique['h_val'].sum()
        charge_reglementaire = 3.0 if poste_sup else 6.0
        heures_sup = charge_reelle - charge_reglementaire
        
        # --- AFFICHAGE DES MÉTRIQUES ---
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2 style='color:#1E3A8A;'>{charge_reelle}h</h2></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2 style='color:#1E3A8A;'>{charge_reglementaire}h</h2></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'>Heures Sup<br><h2 style='color:{'#28a745' if heures_sup >= 0 else '#d33'};'>{heures_sup}h</h2></div>", unsafe_allow_html=True)
        
        # Badges statistiques
        s1, s2, s3 = st.columns(3)
        s1.markdown(f"<div class='stat-box' style='background:#1E3A8A;'>📘 {len(df_unique[df_unique['Type']=='COURS'])} COURS</div>", unsafe_allow_html=True)
        s2.markdown(f"<div class='stat-box' style='background:#28a745;'>📗 {len(df_unique[df_unique['Type']=='TD'])} TD</div>", unsafe_allow_html=True)
        s3.markdown(f"<div class='stat-box' style='background:#e67e22;'>📙 {len(df_unique[df_unique['Type']=='TP'])} TP</div>", unsafe_allow_html=True)

        # Tableau d'emploi du temps
        jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
        heures = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
        def fmt(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
        grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt).unstack('Jours').reindex(index=heures, columns=jours).fillna("")
        st.write(grid.to_html(escape=False), unsafe_allow_html=True)
        components.html("<button onclick='window.parent.print()' style='width:100%; padding:10px; background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold; margin-top:10px; cursor:pointer;'>🖨️ IMPRIMER L'EMPLOI DU TEMPS</button>", height=70)

    elif mode == "Promotion":
        p = st.selectbox("Choisir la Promotion", sorted(df['Promotion'].unique()))
        df_p = df[df['Promotion'] == p]
        def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
        grid = df_p.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"], columns=["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]).fillna("")
        st.write(f"### Planning : {p}")
        st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    elif mode == "🚩 Vérificateur":
        st.subheader("🚩 Vérification des conflits d'enseignants")
        dup = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
        conflits = df[dup]
        if conflits.empty: st.success("✅ Aucun conflit détecté.")
        else: st.warning("Des chevauchements ont été trouvés :"); st.dataframe(conflits)
