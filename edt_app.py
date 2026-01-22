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
    if not s or s == "Non défini": return "vide"
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
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
    
    with tab_ins:
        st.subheader("Nouvelle Inscription")
        n_nom = st.text_input("Nom Complet (ex: ZIDI)")
        n_em = st.text_input("Email")
        n_ps = st.text_input("Mot de passe", type="password")
        n_statut = st.radio("Statut :", ["Permanent", "Vacataire"], horizontal=True)
        n_grade = st.selectbox("Grade :", ["Professeur émérite", "Professeur", "MCA", "MCB", "MAA", "MAB", "Doctorant", "Mastérant"])
        if st.button("S'inscrire"):
            try:
                supabase.table("enseignants_auth").insert({
                    "nom_officiel": n_nom.upper().strip(), "email": n_em, "password_hash": hash_pw(n_ps), 
                    "role": "prof", "statut_prof": n_statut, "grade_prof": n_grade
                }).execute()
                st.success("Inscription réussie ! Connectez-vous.")
            except: st.error("Erreur lors de l'inscription.")

    with tab_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Entrer en tant qu'Admin"):
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin", "statut_prof": "Direction", "grade_prof": "Chef Dépt"}
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
    st.header(f"👤 {user.get('nom_officiel', 'Utilisateur')}")
    st.write(f"**{user.get('grade_prof', '---')}** ({user.get('statut_prof', '---')})")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "👨‍🏫 Données Enseignants", "🎓 Données Étudiants", "📅 Surveillances Examens", "🤖 Générateur Automatique"])
    st.divider()
    mode_view = "Personnel"
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    # --- ESPACE EDT ---
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
                c1, c2, c3 = st.columns(3)
                charge_reelle = df_u['h_val'].sum()
                charge_reg = 6.0 if user.get('statut_prof') == "Permanent" else 0.0
                c1.metric("Charge Réelle", f"{charge_reelle} h")
                c2.metric("Base", f"{charge_reg} h")
                c3.metric("Heures Sup", f"{max(0, charge_reelle - charge_reg)} h")

                def fmt_e(rows):
                    items = [f"<b>{get_nature(r['Code'])} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _, r in rows.iterrows()]
                    return "<div class='separator'></div>".join(items)
                
                grid = df_f.groupby(['h_norm', 'j_norm']).apply(fmt_e, include_groups=False).unstack('j_norm')
                grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
                grid.index = [map_h.get(i, i) for i in grid.index]; grid.columns = [map_j.get(c, c) for c in grid.columns]
                st.write(grid.to_html(escape=False), unsafe_allow_html=True)
        
        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows):
                items = [f"<b>{r['Code']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _, r in rows.iterrows()]
                return "<div class='separator'></div>".join(items)
            grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
            grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_p.index = horaires_list; grid_p.columns = jours_list
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Salle :", sorted(df["Lieu"].unique()))
            df_s = df[df["Lieu"] == s_sel]
            grid_s = df_s.groupby(['h_norm', 'j_norm']).apply(lambda r: "<br>".join(r['Promotion']), include_groups=False).unstack('j_norm')
            st.dataframe(grid_s.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("-"))

        elif is_admin and mode_view == "🚩 Vérificateur":
            st.subheader("🚩 Analyse des conflits")
            s_c = df[df["Lieu"] != "Non défini"].groupby(['Jours', 'Horaire', 'Lieu']).filter(lambda x: len(x) > 1)
            if not s_c.empty: st.error("Conflits de salles détectés !")
            else: st.success("✅ Aucun conflit.")

    # --- ESPACE GÉNÉRATEUR AUTOMATIQUE ---
    elif portail == "🤖 Générateur Automatique":
        if is_admin:
            st.header("⚙️ Génération Intelligente des Surveillances")
            c1, c2 = st.columns(2)
            date_exam = c1.date_input("Date du début des examens")
            nb_surv_par_salle = c2.number_input("Surveillants par salle", 1, 5, 2)
            
            if st.button("🚀 Lancer la génération"):
                # Extraction de tous les enseignants du fichier EDT
                all_profs = []
                for p in df["Enseignants"].unique():
                    for name in str(p).split('&'):
                        if name.strip() and name.strip() != "Non défini": all_profs.append(name.strip())
                all_profs = sorted(list(set(all_profs)))
                
                # Exemple de structure de génération
                results = []
                for j in jours_list:
                    for h in horaires_list:
                        # On cherche qui N'A PAS cours à ce moment là
                        occupe = df[(df['j_norm'] == normalize(j)) & (df['h_norm'] == normalize(h))]["Enseignants"].tolist()
                        libres = [p for p in all_profs if not any(p in str(occ) for occ in occupe)]
                        
                        if libres:
                            results.append({
                                "Jour": j, "Horaire": h, 
                                "Enseignants Disponibles": ", ".join(libres[:nb_surv_par_salle]),
                                "Effectif Libre": len(libres)
                            })
                
                df_gen = pd.DataFrame(results)
                st.dataframe(df_gen, use_container_width=True)
                
                # Export Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_gen.to_excel(writer, index=False, sheet_name='Surveillances')
                st.download_button("📥 Télécharger le planning (.xlsx)", output.getvalue(), "Planning_Surv_S2_2026.xlsx")
        else:
            st.error("Accès Admin requis.")

    # --- AUTRES PORTAILS ---
    elif portail == "👨‍🏫 Données Enseignants":
        if is_admin:
            st.header("🗂️ Annuaire")
            try:
                res = supabase.table("enseignants_auth").select("*").execute()
                st.dataframe(pd.DataFrame(res.data)[['nom_officiel', 'email', 'statut_prof', 'grade_prof']], use_container_width=True)
            except: st.warning("Données Supabase indisponibles.")

    elif portail == "🎓 Données Étudiants":
        if is_admin:
            up = st.file_uploader("Excel Étudiants")
            if up: st.dataframe(pd.read_excel(up))
    
    elif portail == "📅 Surveillances Examens":
        if os.path.exists("surveillances_2026.xlsx"):
            st.dataframe(pd.read_excel("surveillances_2026.xlsx"))
        else: st.info("Aucun planning de surveillance publié pour le moment.")

else:
    st.error("Fichier source 'dataEDT-ELT-S2-2026.xlsx' introuvable.")
