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

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
heure_str = now.strftime("%H:%M")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .main-title {{ color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px; }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    .stat-box {{ padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
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
    df['Lieu_Racine'] = df['Lieu'].apply(lambda x: x.split('/')[0].strip() if x != "Non défini" else "Non défini")

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    with t1:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
    with t3:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Accès Admin"): st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}; st.rerun()
    st.stop()

# --- PARAMÈTRES ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

with st.sidebar:
    portail = st.selectbox("🚀 MODULE", ["📖 Emploi du Temps", "📅 Surveillances Examens"])
    if is_admin:
        mode_view = st.radio("Vue Admin :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"])
    else:
        mode_view = "Personnel"
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

if df is not None:
    if portail == "📖 Emploi du Temps":
        # --- LOGIQUE ADMIN VUE PROMOTION ---
        if is_admin and mode_view == "Promotion":
            p_list = sorted(df["Promotion"].unique())
            p_sel = st.selectbox("Sélectionnez la Promotion :", p_list)
            df_p = df[df["Promotion"] == p_sel]
            
            def fmt(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_p.groupby(['Horaire', 'Jours']).apply(fmt).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(f"### 📅 Emploi du Temps : {p_sel}")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        # --- LOGIQUE VUE ENSEIGNANT (ADMIN OU PERSO) ---
        elif mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            df_f = df[df["Enseignants"] == cible].copy()
            
            # Calcul Charge
            df_f['h_val'] = df_f['Enseignements'].apply(lambda x: 1.5 if "COURS" in str(x).upper() else 1.0)
            df_u = df_f.drop_duplicates(subset=['Jours', 'Horaire'])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Charge Réelle", f"{df_u['h_val'].sum()} h")
            
            def fmt_e(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid_e = df_f.groupby(['Horaire', 'Jours']).apply(fmt_e).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(f"### 📅 Emploi du Temps : {cible}")
            st.write(grid_e.to_html(escape=False), unsafe_allow_html=True)

        # --- AUTRES VUES ADMIN (Salles / Vérificateur) ---
        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Salle :", sorted(df['Lieu_Racine'].unique()))
            df_s = df[df['Lieu_Racine'] == s_sel]
            def fmt_s(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Promotion']}" for _,r in rows.iterrows()])
            st.write(df_s.groupby(['Horaire', 'Jours']).apply(fmt_s).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("").to_html(escape=False), unsafe_allow_html=True)

    elif portail == "📅 Surveillances Examens":
        # Logique surveillance (identique au précédent)
        df_surv = df[df['Enseignements'].str.contains("EXAMEN|CONTRÔLE", case=False, na=False)]
        if not df_surv.empty:
            m = st.selectbox("Matière :", sorted(df_surv['Enseignements'].unique()))
            st.table(df_surv[df_surv['Enseignements'] == m][['Lieu', 'Enseignants', 'Promotion']])

    components.html("<button onclick='window.parent.print()' style='width:100%; padding:10px; background:#28a745; color:white; border:none; border-radius:5px; cursor:pointer;'>🖨️ IMPRIMER</button>", height=70)
