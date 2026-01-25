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
jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
nom_jour_fr = jours_semaine[now.weekday()]

# --- STYLE CSS HARMONISÉ ---
st.markdown(f"""
    <style>
    .main-title {{ color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px; }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
    .date-badge {{ background-color: #1E3A8A; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; float: right; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    .stat-container {{ display: flex; justify-content: space-around; margin: 20px 0; gap: 10px; }}
    .stat-box {{ flex: 1; padding: 15px; border-radius: 12px; color: white; font-weight: bold; text-align: center; font-size: 14px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .bg-cours {{ background: linear-gradient(135deg, #1E3A8A, #3B82F6); }}
    .bg-td {{ background: linear-gradient(135deg, #15803d, #22c55e); }}
    .bg-tp {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 100px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

def normalize(s):
    if not s or s == "Non défini": return "vide"
    s = str(s).strip().lower().replace(" ", "").replace("-", "").replace("–", "")
    return s.replace(":00", "").replace("h00", "h")

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    cols_attendues = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
    for col in cols_attendues:
        df[col] = df[col].fillna("Non défini").astype(str).str.strip()
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    t_conn, t_ins, t_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    
    with t_conn:
        e_in = st.text_input("Email", key="l_email")
        p_in = st.text_input("Pass", type="password", key="l_pass")
        if st.button("Se connecter", use_container_width=True):
            res = supabase.table("enseignants_auth").select("*").eq("email", e_in).eq("password_hash", hash_pw(p_in)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")

    with t_ins:
        st.subheader("📝 Inscription Enseignant")
        noms = sorted(df["Enseignants"].unique()) if df is not None else []
        col1, col2 = st.columns(2)
        u_nom = col1.selectbox("Nom dans l'EDT", noms)
        u_email = col1.text_input("Email")
        u_statut = col2.radio("Statut", ["Permanent", "Vacataire"])
        u_phone = col2.text_input("Téléphone") if u_statut == "Vacataire" else ""
        u_pass = st.text_input("Mot de passe", type="password")
        if st.button("Créer le compte", use_container_width=True):
            data = {"nom_officiel": u_nom, "email": u_email, "password_hash": hash_pw(u_pass), "role": "enseignant", "statut": u_statut, "telephone": u_phone}
            supabase.table("enseignants_auth").insert(data).execute()
            st.success("Compte créé !")

    with t_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Accès Maître"):
                st.session_state["user_data"] = {"nom_officiel": "ADMINISTRATEUR", "role": "admin", "email": "milouafarid@gmail.com"}
                st.rerun()

user = st.session_state.get("user_data")
if user is None: st.stop()

# --- LOGIQUE D'AFFICHAGE ---
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]
map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

with st.sidebar:
    st.header(f"👤 {user.get('nom_officiel')}")
    portail = st.selectbox("Espace", ["📖 Emploi du Temps", "✍️ Éditeur"])
    mode_view = st.radio("Vue", ["Personnel", "Promotion", "Salles"]) if is_admin else "Personnel"
    poste_sup = st.checkbox("Poste Supérieur (Décharge)")
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None
        st.rerun()

# --- HEADER ---
st.markdown(f"<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail}</div>", unsafe_allow_html=True)

if portail == "📖 Emploi du Temps" and df is not None:
    cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir:", sorted(df["Enseignants" if mode_view=="Personnel" else "Promotion" if mode_view=="Promotion" else "Lieu"].unique()))
    
    col_key = "Enseignants" if mode_view == "Personnel" else "Promotion" if mode_view == "Promotion" else "Lieu"
    df_f = df[df[col_key].str.contains(cible, case=False, na=False)].copy()

    # Bilan pour enseignants
    if mode_view == "Personnel":
        df_f['Type'] = df_f['Code'].apply(lambda x: "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP"))
        df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
        
        st.markdown(f"""<div class="stat-container">
            <div class="stat-box bg-cours">📘 {len(df_f[df_f['Type'] == 'COURS'])} Cours</div>
            <div class="stat-box bg-td">📗 {len(df_f[df_f['Type'] == 'TD'])} TD</div>
            <div class="stat-box bg-tp">📙 {len(df_f[df_f['Type'] == 'TP'])} TP</div>
        </div>""", unsafe_allow_html=True)

    def format_case(rows):
        items = []
        for _, r in rows.iterrows():
            color = "#1E3A8A" if "COURS" in str(r['Code']).upper() else "#15803d" if "TD" in str(r['Code']).upper() else "#b45309"
            items.append(f"<b style='color:{color};'>{r['Code']}</b><br>{r['Enseignements']}<br><small>{r['Promotion']} | {r['Lieu']}</small>")
        return "<div class='separator'></div>".join(items)

    grid = df_f.groupby(['h_norm', 'j_norm']).apply(format_case).unstack('j_norm')
    grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
    grid.index = horaires_list
    grid.columns = jours_list
    st.write(grid.to_html(escape=False), unsafe_allow_html=True)

elif portail == "✍️ Éditeur" and is_admin:
    st.session_state.df_admin = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Sauvegarder sur le serveur"):
        st.session_state.df_admin.to_excel(NOM_FICHIER_FIXE, index=False)
        st.success("Fichier mis à jour !")
