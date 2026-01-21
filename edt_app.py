import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client
import streamlit.components.v1 as components

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
    .stat-box {{ padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU FICHIER EDT ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

# Fonction de normalisation pour la correspondance parfaite (CORRECTION : support des variations de 00)
def normalize(s):
    if not s: return ""
    return str(s).strip().replace(" ", "").lower().replace("-", "").replace("–", "").replace(":00", "").replace("h00", "h")

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    # Disposition demandée : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
    for col in ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']:
        if col in df.columns: 
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
    
    # Création des clés de correspondance
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)
    df['Lieu_Racine'] = df['Lieu'].apply(lambda x: x.split('/')[0].strip() if x != "Non défini" else "Non défini")

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
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
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
# CORRECTION : Alignement des chaînes de caractères avec le format Excel standard (14h au lieu de 14h00)
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]

# Dictionnaires de mapping (CORRECTION : utilisation de .get pour éviter les plantages)
map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "📅 Surveillances Examens", "🤖 Générateur Automatique"])
    st.divider()
   
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            # 1. Liste unique des noms (on nettoie les noms multiples pour la liste de sélection)
            all_names = set()
            for x in df["Enseignants"].unique():
                for name in str(x).split('/'):
                    all_names.add(name.strip())
            
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(list(all_names)))
            
            # 2. CORRECTION CRUCIALE : On cherche si le nom est CONTENU dans la colonne Enseignants
            # Cela permet de trouver l'enseignant même s'il est associé à un autre (ex: TP en binôme)
            df_f = df[df["Enseignants"].str.contains(cible, na=False, case=False)].copy()
            
            # --- Le reste reste strictement identique à votre logique ---
            def get_t(x): 
                val = str(x).upper()
                if "COURS" in val: return "COURS"
                if "TD" in val: return "TD"
                return "TP"
            
            df_f['Type'] = df_f['Code'].apply(get_t)
            df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            
            df_u = df_f.drop_duplicates(subset=['j_norm', 'h_norm'])
            
            # --- CALCULS ---
            charge_reelle = df_u['h_val'].sum()
            charge_reglementaire = 3.0 if poste_sup else 6.0
            heures_sup = charge_reelle - charge_reglementaire
            
            st.markdown(f"### 📊 Bilan : {cible}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reglementaire} h</h2></div>", unsafe_allow_html=True)
            
            color_sup = "#e74c3c" if heures_sup > 0 else "#27ae60"
            c3.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup<br><h2 style='color:{color_sup};'>{heures_sup} h</h2></div>", unsafe_allow_html=True)
            
            st.write("") 
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {len(df_u[df_u['Type'] == 'COURS'])} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {len(df_u[df_u['Type'] == 'TD'])} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {len(df_u[df_u['Type'] == 'TP'])} TP</div>", unsafe_allow_html=True)

            def fmt_e(rows): 
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            
            grid = df_f.groupby(['h_norm', 'j_norm']).apply(fmt_e, include_groups=False).unstack('j_norm')
            grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            
            grid.index = [map_h.get(i, i) for i in grid.index]
            grid.columns = [map_j.get(c, c) for c in grid.columns]
            
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
            grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_p.index = [map_h.get(i, i) for i in grid_p.index]
            grid_p.columns = [map_j.get(c, c) for c in grid_p.columns]
            st.write(f"### 📅 Emploi du Temps : {p_sel}")
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Choisir Salle (Racine) :", sorted([r for r in df['Lieu_Racine'].unique() if r != "Non défini"]))
            df_s = df[df['Lieu_Racine'] == s_sel]
            def fmt_s(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><small>{r['Lieu']}</small>" for _,r in rows.iterrows()])
            grid_s = df_s.groupby(['h_norm', 'j_norm']).apply(fmt_s, include_groups=False).unstack('j_norm')
            grid_s = grid_s.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_s.index = [map_h.get(i, i) for i in grid_s.index]
            grid_s.columns = [map_j.get(c, c) for c in grid_s.columns]
            st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🚩 Vérificateur":
            dup = df[df['Enseignants'] != "Non défini"].duplicated(subset=['j_norm', 'h_norm', 'Enseignants'], keep=False)
            err = df[df['Enseignants'] != "Non défini"][dup]
            if err.empty: st.success("✅ Aucun conflit détecté.")
            else: st.warning("Conflits d'enseignants détectés :"); st.dataframe(err[['Enseignements', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']])

