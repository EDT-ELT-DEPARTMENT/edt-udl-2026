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
heure_str = now.strftime("%H:%M")
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
    @media print {{ section[data-testid="stSidebar"], .stActionButton, footer, header, button {{ display: none !important; }} }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU FICHIER EDT ---
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
    tab_conn, tab_ins, tab_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    with tab_conn:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
    with tab_ins:
        new_em = st.text_input("Email professionnel")
        noms_list = sorted(df['Enseignants'].unique()) if df is not None else []
        new_nom = st.selectbox("Sélectionnez votre nom (EDT)", noms_list)
        new_ps = st.text_input("Nouveau mot de passe", type="password")
        if st.button("Créer mon compte"):
            try:
                supabase.table("enseignants_auth").insert({"email": new_em, "nom_officiel": new_nom, "password_hash": hash_pw(new_ps)}).execute()
                st.success("Inscription réussie !")
            except: st.error("Erreur (Email utilisé ?)")
    with tab_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Entrer en tant qu'Admin"):
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}
                st.rerun()
    st.stop()

# --- INITIALISATION ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "📅 Surveillances Examens", "🤖 Générateur Automatique"])
    st.divider()
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    # ================= PORTAIL 1 : EDT =================
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            df_f = df[df["Enseignants"] == cible].copy()
            def get_t(x): return "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP")
            df_f['Type'] = df_f['Enseignements'].apply(get_t)
            df_u = df_f.drop_duplicates(subset=['Jours', 'Horaire'])
            def fmt_e(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt_e).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid_p = df_p.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

    # ================= PORTAIL 2 : SURVEILLANCES =================
    elif portail == "📅 Surveillances Examens":
        NOM_SURV = "surveillances_2026.xlsx"
        horaires_examens = ["08h30 – 10h30", "11h00 – 13h00", "13h30 – 15h30"]
        if os.path.exists(NOM_SURV):
            df_surv = pd.read_excel(NOM_SURV)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
            liste_profs = sorted(df_surv['Surveillant(s)'].fillna("").unique())
            prof_sel = st.selectbox("🔍 Enseignant :", liste_profs)
            df_u = df_surv[df_surv['Surveillant(s)'] == prof_sel].sort_values(by='Date_Tri')
            st.dataframe(df_u.drop(columns=['Date_Tri']), use_container_width=True)

    # ================= PORTAIL 3 : GÉNÉRATEUR (SIMULATION) =================
    elif portail == "🤖 Générateur Automatique" and is_admin:
        st.header("⚖️ Simulateur d'Équilibrage")
        NOM_SURV = "surveillances_2026.xlsx"
        if os.path.exists(NOM_SURV):
            df_manuel = pd.read_excel(NOM_SURV)
            df_manuel.columns = [str(c).strip() for c in df_manuel.columns]
            tous_les_ens = sorted([e for e in df['Enseignants'].unique() if e != "Non défini"])
            
            col1, col2 = st.columns(2)
            with col1: profs_alleger = st.multiselect("Alléger (Vacataires/Responsables) :", tous_les_ens)
            with col2:
                q_std = st.number_input("Quota Standard :", min_value=1, value=7)
                q_red = st.number_input("Quota Allégé :", min_value=0, value=3)

            if st.button("📊 Lancer la Comparaison"):
                counts_man = df_manuel['Surveillant(s)'].value_counts().to_dict()
                df_simu = df_manuel.copy()
                charges_simu = {ens: counts_man.get(ens, 0) for ens in tous_les_ens}
                
                mask_vide = (df_simu['Surveillant(s)'].isna()) | (df_simu['Surveillant(s)'] == "")
                indices_vides = df_simu[mask_vide].index.tolist()
                
                for idx in indices_vides:
                    j, h = str(df_simu.at[idx, 'Jour']).strip(), str(df_simu.at[idx, 'Heure']).strip()
                    file = sorted([p for p in tous_les_ens if p not in profs_alleger], key=lambda x: charges_simu[x]) + \
                           sorted([p for p in tous_les_ens if p in profs_alleger], key=lambda x: charges_simu[x])
                    
                    for prof in file:
                        lim = q_red if prof in prof_alleger else q_std
                        pris = not df_simu[(df_simu['Jour'] == j) & (df_simu['Heure'] == h) & (df_simu['Surveillant(s)'] == prof)].empty
                        if not pris and charges_simu[prof] < lim:
                            df_simu.at[idx, 'Surveillant(s)'] = prof
                            charges_simu[prof] += 1
                            break

                st.subheader("📈 Résultat de la Simulation")
                res_data = [{"Enseignant": p, "Manuel": counts_man.get(p,0), "Simulé": charges_simu[p], "Diff": charges_simu[p]-counts_man.get(p,0)} for p in tous_les_ens]
                df_res = pd.DataFrame(res_data).sort_values("Diff", ascending=False)
                st.dataframe(df_res.style.background_gradient(subset=['Diff'], cmap='Blues'), use_container_width=True)
                st.bar_chart(df_res.set_index("Enseignant")[["Manuel", "Simulé"]])
                
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_simu.to_excel(wr, index=False)
                st.download_button("💾 Télécharger la simulation", buf.getvalue(), "simulation.xlsx")
