import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
    .date-badge {{ background-color: #1E3A8A; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; float: right; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    .stat-container {{ display: flex; justify-content: space-around; margin: 20px 0; gap: 10px; }}
    .stat-box {{ flex: 1; padding: 15px; border-radius: 12px; color: white; font-weight: bold; text-align: center; font-size: 16px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }}
    .bg-cours {{ background: linear-gradient(135deg, #1E3A8A, #3B82F6); }}
    .bg-td {{ background: linear-gradient(135deg, #15803d, #22c55e); }}
    .bg-tp {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU FICHIER EDT ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

def normalize(s):
    if not s or str(s).lower() in ["non défini", "nan", "vide"]: return "vide"
    return str(s).strip().replace(" ", "").lower().replace("-", "").replace("–", "").replace(":00", "").replace("h00", "h")

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    cols_attendues = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
    for col in cols_attendues:
        if col in df.columns: 
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    tab_conn, tab_ins, tab_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    
    with tab_conn:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: 
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")
            
    with tab_ins:
        new_nom = st.text_input("Nom Complet (ex: ZIDI)")
        new_em = st.text_input("Email Professionnel")
        new_ps = st.text_input("Créer Mot de passe", type="password")
        if st.button("S'inscrire"):
            try:
                supabase.table("enseignants_auth").insert({
                    "nom_officiel": new_nom.upper(),
                    "email": new_em,
                    "password_hash": hash_pw(new_ps),
                    "role": "prof"
                }).execute()
                st.success("Compte créé ! Connectez-vous.")
            except: st.error("Erreur (Email déjà utilisé ?)")

    with tab_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Entrer en tant qu'Admin"):
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}
                st.rerun()
    st.stop()

# --- INITIALISATION PARAMÈTRES ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]
map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Espace", [
        "📖 Emploi du Temps", 
        "👨‍🏫 Données Enseignants", 
        "🎓 Données Étudiants", 
        "📅 Surveillances Examens", 
        "🤖 Générateur Automatique"
    ])
    st.divider()
    mode_view = "Personnel"
    poste_sup = False
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge)")
    if st.button("🚪 Déconnexion"): 
        st.session_state["user_data"] = None
        st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    # --- PORTAIL 1 : EMPLOI DU TEMPS ---
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            df_f = df[df["Enseignants"].str.contains(cible, case=False, na=False)].copy()
            
            def get_nature(code):
                val = str(code).upper()
                if "COURS" in val: return "📘 COURS"
                if "TD" in val: return "📗 TD"
                if "TP" in val: return "📙 TP"
                return "📑"

            if not df_f.empty:
                df_f['Type'] = df_f['Code'].apply(lambda x: "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP"))
                df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
                df_u = df_f.drop_duplicates(subset=['j_norm', 'h_norm'])
                
                st.markdown(f"### 📊 Bilan : {cible}")
                st.markdown(f"""<div class="stat-container">
                    <div class="stat-box bg-cours">📘 {len(df_u[df_u['Type'] == 'COURS'])} COURS</div>
                    <div class="stat-box bg-td">📗 {len(df_u[df_u['Type'] == 'TD'])} TD</div>
                    <div class="stat-box bg-tp">📙 {len(df_u[df_u['Type'] == 'TP'])} TP</div>
                </div>""", unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                charge_reelle = df_u['h_val'].sum()
                charge_reg = 3.0 if poste_sup else 6.0
                c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
                h_sup = charge_reelle - charge_reg
                color_sup = "#e74c3c" if h_sup > 0 else "#27ae60"
                c3.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup<br><h2 style='color:{color_sup};'>{h_sup} h</h2></div>", unsafe_allow_html=True)

                def fmt_e(rows):
                    items = [f"<b>{get_nature(r['Code'])} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _, r in rows.iterrows()]
                    return "<div class='separator'></div>".join(items)
                
                grid = df_f.groupby(['h_norm', 'j_norm']).apply(fmt_e, include_groups=False).unstack('j_norm')
                grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
                grid.index = [map_h.get(i, i) for i in grid.index]
                grid.columns = [map_j.get(c, c) for c in grid.columns]
                st.write(grid.to_html(escape=False), unsafe_allow_html=True)
            else:
                st.info("Aucun cours trouvé pour cet enseignant.")

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows):
                items = [f"<b>{('COURS' if 'COURS' in str(r['Code']).upper() else 'TD' if 'TD' in str(r['Code']).upper() else 'TP')} : {r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _, r in rows.iterrows()]
                return "<div class='separator'></div>".join(items)
            grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
            grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_p.index = horaires_list; grid_p.columns = jours_list
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

    # --- PORTAIL 4 : DONNÉES ENSEIGNANTS (ADMIN) ---
    elif portail == "👨‍🏫 Données Enseignants":
        if not is_admin:
            st.error("Accès réservé à l'administration.")
        else:
            st.header("🗂️ État du Corps Enseignant (Source : Fichier EDT)")
            raw_profs = []
            for entry in df["Enseignants"].dropna().unique():
                for p in str(entry).split('&'):
                    name = p.strip()
                    if name and name.lower() not in ["non défini", "nan", "vide"]:
                        raw_profs.append(name)
            liste_officielle = sorted(list(set(raw_profs)))
            
            try:
                res_auth = supabase.table("enseignants_auth").select("nom_officiel, email").execute()
                dict_auth = {str(row['nom_officiel']).strip().upper(): row['email'] for row in res_auth.data} if res_auth.data else {}
            except: dict_auth = {}

            tableau_profs = []
            for prof in liste_officielle:
                nom_maj = prof.upper()
                email = dict_auth.get(nom_maj, "⚠️ Non collecté")
                statut = "✅ Inscrit" if nom_maj in dict_auth else "❌ En attente"
                tableau_profs.append({"Nom": prof, "Email": email, "Statut": statut})

            st.dataframe(pd.DataFrame(tableau_profs), use_container_width=True, hide_index=True)

    # --- PORTAIL 5 : DONNÉES ÉTUDIANTS (ADMIN) ---
    elif portail == "🎓 Données Étudiants":
        if not is_admin:
            st.error("Accès réservé à l'administration.")
        else:
            st.header("📊 Base de Données des Étudiants")
            up_file = st.file_uploader("📂 Charger Excel Étudiants", type=["xlsx"])
            if up_file:
                df_s = pd.read_excel(up_file)
                df_s.columns = [str(c).strip() for c in df_s.columns]
                if 'Promotion' in df_s.columns:
                    p_list = sorted(df_s['Promotion'].unique())
                    sel_p = st.selectbox("Promotion :", p_list)
                    st.dataframe(df_s[df_s['Promotion'] == sel_p], use_container_width=True, hide_index=True)
                else: st.error("Colonne 'Promotion' manquante.")

    # --- PORTAIL SURVEILLANCES ---
    elif portail == "📅 Surveillances Examens":
        NOM_SURV = "surveillances_2026.xlsx"
        if os.path.exists(NOM_SURV):
            df_surv = pd.read_excel(NOM_SURV)
            st.dataframe(df_surv, use_container_width=True)
        else: st.error("Fichier surveillances_2026.xlsx introuvable.")

    # --- GÉNÉRATEUR ---
    elif portail == "🤖 Générateur Automatique":
        if is_admin:
            st.info("Le générateur utilise les données de surveillances_2026.xlsx pour équilibrer les charges.")
            # (Logique de génération simplifiée ici pour le code complet)
        else: st.error("Accès réservé.")

else:
    st.error("Fichier source 'dataEDT-ELT-S2-2026.xlsx' introuvable à la racine.")

