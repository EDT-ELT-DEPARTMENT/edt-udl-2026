import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
from supabase import create_client
import streamlit.components.v1 as components

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- GESTION DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
heure_str = now.strftime("%H:%M")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS (Inclus le style pour les tableaux et badges) ---
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
    .welcome-box {{ background-color: #e8f0fe; border-left: 5px solid #1E3A8A; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
    .date-badge {{ background-color: #1E3A8A; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; float: right; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    .stat-box {{ padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    @media print {{ section[data-testid="stSidebar"], .stActionButton, footer, header, button {{ display: none !important; }} }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_data(file_name):
    if os.path.exists(file_name):
        try:
            data = pd.read_excel(file_name)
            data.columns = [str(c).strip() for c in data.columns]
            return data
        except Exception as e:
            st.error(f"Erreur de lecture {file_name}: {e}")
    return None

df_edt = load_data("dataEDT-ELT-S2-2026.xlsx")
df_surv_global = load_data("surveillances.xlsx")

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
        new_em = st.text_input("Email professionnel")
        noms_list = sorted(df_edt['Enseignants'].unique()) if df_edt is not None else []
        new_nom = st.selectbox("Sélectionnez votre nom (pour liaison EDT)", noms_list)
        new_ps = st.text_input("Nouveau mot de passe", type="password")
        if st.button("Créer mon compte"):
            try:
                supabase.table("enseignants_auth").insert({"email": new_em, "nom_officiel": new_nom, "password_hash": hash_pw(new_ps)}).execute()
                st.success("Inscription réussie !")
            except: st.error("Erreur (Email déjà utilisé ?)")
            
    with tab_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Entrer en tant qu'Admin"):
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}
                st.rerun()
    st.stop()

# --- ESPACE CONNECTÉ ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 MODULE", ["📖 Emploi du Temps", "📅 Surveillances Examens"])
    st.divider()
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge)")
    if st.button("🚪 Déconnexion"): 
        st.session_state["user_data"] = None
        st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

# --- LOGIQUE MODULES ---
if portail == "📖 Emploi du Temps" and df_edt is not None:
    # (Logique EDT classique - Identique à votre version précédente)
    cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df_edt["Enseignants"].unique()))
    df_f = df_edt[df_edt["Enseignants"] == cible].copy()
    
    # Rendu du tableau EDT Enseignant
    def fmt_e(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
    grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt_e).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
    st.write(grid.to_html(escape=False), unsafe_allow_html=True)

elif portail == "📅 Surveillances Examens":
    if df_surv_global is not None:
        # Harmonisation colonnes
        if 'Heure' in df_surv_global.columns: df_surv_global['Horaire'] = df_surv_global['Heure']
        
        tab_p, tab_g = st.tabs(["👤 Mon Planning Personnel", "🌍 Planning Global (474 lignes)"])
        
        with tab_p:
            nom_user = user['nom_officiel']
            # Filtrage par nom (doit correspondre exactement à l'Excel)
            df_moi = df_surv_global[df_surv_global['Surveillant(s)'] == nom_user]
            
            if not df_moi.empty:
                st.success(f"Planning de surveillance pour M. {nom_user} ({len(df_moi)} séances)")
                grid_s = pd.DataFrame("", index=jours_list, columns=horaires_list)
                
                for _, r in df_moi.iterrows():
                    cell = f"<b>{r['Matière']}</b><br>📍 {r['Salle']}<br><small>🎓 {r['Promotion']}</small>"
                    j, h = str(r['Jour']).strip(), str(r['Horaire']).strip()
                    if j in grid_s.index and h in grid_s.columns:
                        grid_s.at[j, h] = cell
                
                st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)
            else:
                st.info("Aucune surveillance n'est enregistrée à votre nom dans le fichier actuel.")
        
        with tab_g:
            search = st.text_input("🔍 Rechercher un surveillant, une salle ou une matière :")
            if search:
                mask = df_surv_global.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)
                st.dataframe(df_surv_global[mask], use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_surv_global, use_container_width=True, hide_index=True, height=400)
    else:
        st.error("⚠️ Fichier 'surveillances.xlsx' manquant sur GitHub.")

# --- BOUTON IMPRESSION ---
components.html("<button onclick='window.parent.print()' style='width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer; margin-top:10px;'>🖨️ IMPRIMER LE PLANNING AFFICHÉ</button>", height=70)
