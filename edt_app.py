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
        em = st.text_input("Email Professionnel")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: 
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")
            
    with tab_ins:
        st.subheader("Créer un compte enseignant")
        new_nom = st.text_input("Nom Complet (ex: ZIDI)")
        new_em = st.text_input("Email")
        new_ps = st.text_input("Mot de passe", type="password")
        
        # --- MODIFICATIONS STATUT ET GRADE ---
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            new_statut = st.radio("Nature du contrat :", ["Permanent", "Vacataire"])
        with col_s2:
            new_grade = st.selectbox("Grade / Titre :", [
                "Professeur émérite", "Professeur", "MCA", "MCB", "MAA", "MAB", "Doctorant", "Mastérant"
            ])
            
        if st.button("Valider l'inscription"):
            if new_nom and new_em and new_ps:
                try:
                    supabase.table("enseignants_auth").insert({
                        "nom_officiel": new_nom.upper().strip(),
                        "email": new_em.strip(),
                        "password_hash": hash_pw(new_ps),
                        "role": "prof",
                        "statut_prof": new_statut,
                        "grade_prof": new_grade
                    }).execute()
                    st.success("Compte créé avec succès !")
                except: st.error("Erreur (Email déjà utilisé ?)")
            else: st.warning("Veuillez remplir tous les champs.")

    with tab_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Entrer en tant qu'Admin"):
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin", "grade_prof": "Chef de Département"}
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
    st.info(f"🎓 {user.get('grade_prof', 'Grade non défini')}\n\n💼 {user.get('statut_prof', 'Statut inconnu')}")
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
st.markdown(f"<div class='portal-badge'>PORTAIL : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    # --- PORTAIL 1 : EMPLOI DU TEMPS ---
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            df_f = df[df["Enseignants"].str.contains(cible, case=False, na=False)].copy()
            
            if not df_f.empty:
                df_f['Type'] = df_f['Code'].apply(lambda x: "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP"))
                df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
                df_u = df_f.drop_duplicates(subset=['j_norm', 'h_norm'])
                
                st.markdown(f"### 📊 Bilan Hebdomadaire : {cible}")
                c1, c2, c3 = st.columns(3)
                charge_reelle = df_u['h_val'].sum()
                charge_reg = 3.0 if poste_sup else (6.0 if user.get('statut_prof') == "Permanent" else 0.0)
                c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'>Base ({user.get('statut_prof')})<br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
                h_sup = charge_reelle - charge_reg
                c3.markdown(f"<div class='metric-card'>Différentiel<br><h2>{h_sup} h</h2></div>", unsafe_allow_html=True)

                def fmt_e(rows):
                    items = [f"<b>{r['Code']} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _, r in rows.iterrows()]
                    return "<div class='separator'></div>".join(items)
                
                grid = df_f.groupby(['h_norm', 'j_norm']).apply(fmt_e, include_groups=False).unstack('j_norm')
                grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
                grid.index = [map_h.get(i, i) for i in grid.index]; grid.columns = [map_j.get(c, c) for c in grid.columns]
                st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    # --- PORTAIL 4 : DONNÉES ENSEIGNANTS (ADMIN) ---
    elif portail == "👨‍🏫 Données Enseignants":
        if not is_admin:
            st.error("Accès réservé à l'administration.")
        else:
            st.header("🗂️ Annuaire du Corps Enseignant (S2-2026)")
            raw_profs = []
            for entry in df["Enseignants"].dropna().unique():
                for p in str(entry).split('&'):
                    name = p.strip()
                    if name and name.lower() not in ["non défini", "nan", "vide"]:
                        raw_profs.append(name)
            liste_officielle = sorted(list(set(raw_profs)))
            
            try:
                res_auth = supabase.table("enseignants_auth").select("nom_officiel, email, statut_prof, grade_prof").execute()
                dict_auth = {str(row['nom_officiel']).strip().upper(): row for row in res_auth.data} if res_auth.data else {}
            except: dict_auth = {}

            tableau_profs = []
            for prof in liste_officielle:
                nom_maj = prof.upper()
                info = dict_auth.get(nom_maj)
                tableau_profs.append({
                    "Enseignant": prof,
                    "Grade": info['grade_prof'] if info else "---",
                    "Statut": info['statut_prof'] if info else "Non inscrit",
                    "Email": info['email'] if info else "---"
                })
            st.dataframe(pd.DataFrame(tableau_profs), use_container_width=True, hide_index=True)

    # --- PORTAIL 5 : DONNÉES ÉTUDIANTS (ADMIN) ---
    elif portail == "🎓 Données Étudiants":
        if is_admin:
            up_file = st.file_uploader("📂 Charger Excel Étudiants", type=["xlsx"])
            if up_file:
                df_st = pd.read_excel(up_file)
                st.dataframe(df_st, use_container_width=True)
        else: st.error("Accès Admin requis.")

else:
    st.error("Fichier source 'dataEDT-ELT-S2-2026.xlsx' introuvable.")
