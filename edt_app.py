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
    t1, t2 = st.tabs(["🔑 Connexion", "🛡️ Admin"])
    with t1:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
    with t2:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Accès Admin"): st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}; st.rerun()
    st.stop()

# --- INTERFACE DES PORTAILS ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    # --- SELECTEUR DE PORTAIL ---
    portail = st.selectbox("🚀 CHOISIR MODULE", ["📖 Emploi du Temps", "📅 Surveillances Examens"])
    st.divider()
    
    if portail == "📖 Emploi du Temps":
        if is_admin:
            mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"])
            poste_superieur = st.checkbox("Simuler Poste Supérieur (3h)")
        else:
            mode_view = "Personnel"
            poste_superieur = st.checkbox("Poste Supérieur (Décharge 50%)")
    else:
        # Options spécifiques au portail Surveillance
        mode_view = "Surveillance_Matiere"

    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    # ==========================================
    # PORTAIL 1 : EMPLOI DU TEMPS (COURS)
    # ==========================================
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            df_f = df[df["Enseignants"] == cible].copy()
            
            def get_type(t):
                t = str(t).upper()
                if "COURS" in t: return "COURS"
                elif "TD" in t: return "TD"
                elif "TP" in t: return "TP"
                return "AUTRE"

            df_f['Type'] = df_f['Enseignements'].apply(get_type)
            df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            df_u = df_f.drop_duplicates(subset=['Jours', 'Horaire'])
            
            charge_reelle = df_u['h_val'].sum()
            c_reg = 3.0 if poste_superieur else 6.0
            
            st.markdown(f"### 📊 Bilan de charge : {cible}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{c_reg} h</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'>Heures Sup<br><h2>{charge_reelle - c_reg} h</h2></div>", unsafe_allow_html=True)
            
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {len(df_u[df_u['Type'] == 'COURS'])} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {len(df_u[df_u['Type'] == 'TD'])} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {len(df_u[df_u['Type'] == 'TP'])} TP</div>", unsafe_allow_html=True)

            def fmt_ens(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt_ens).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "🏢 Planning Salles" and is_admin:
            liste_racines = sorted([r for r in df['Lieu_Racine'].unique() if r != "Non défini"])
            salle_racine = st.sidebar.selectbox("Choisir Salle (Racine) :", liste_racines)
            df_salle = df[df['Lieu_Racine'] == salle_racine].copy()
            def fmt_salle(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br>({r['Promotion']})" for _,r in rows.iterrows()])
            grid_salle = df_salle.groupby(['Horaire', 'Jours']).apply(fmt_salle).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(f"### 🏢 Occupation : {salle_racine}")
            st.write(grid_salle.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "🚩 Vérificateur" and is_admin:
            st.subheader("🚩 Analyse des Conflits")
            dup = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
            err = df[df['Enseignants'] != "Non défini"][dup]
            if err.empty: st.success("✅ Aucun conflit d'enseignant.")
            else: st.warning("Conflits détectés :"); st.dataframe(err)

    # ==========================================
    # PORTAIL 2 : SURVEILLANCES EXAMENS
    # ==========================================
    elif portail == "📅 Surveillances Examens":
        # Filtrage des examens (Mots-clés : EXAMEN, CONTRÔLE, RATTRAPAGE)
        df['Is_Examen'] = df['Enseignements'].str.contains("EXAMEN|CONTRÔLE|RATTRAPAGE", case=False, na=False)
        df_surv = df[df['Is_Examen'] == True].copy()
        
        if df_surv.empty:
            st.warning("⚠️ Aucune donnée de type 'EXAMEN' ou 'CONTRÔLE' n'a été trouvée dans le fichier source.")
        else:
            matiere_sel = st.selectbox("Sélectionnez la Matière d'Examen :", sorted(df_surv['Enseignements'].unique()))
            df_m = df_surv[df_surv['Enseignements'] == matiere_sel]
            
            # Entête Examen
            st.markdown(f"""
                <div class='welcome-box'>
                    <h3 style='margin:0;'>📝 {matiere_sel}</h3>
                    <b>Date :</b> {df_m['Jours'].iloc[0]} | <b>Horaire :</b> {df_m['Horaire'].iloc[0]}
                </div>
            """, unsafe_allow_html=True)
            
            # Tableau des surveillants
            st.write("#### 📋 Répartition des Surveillants et Salles")
            recap = df_m[['Lieu', 'Enseignants', 'Promotion']].rename(columns={'Enseignants': 'Surveillant Responsable'})
            st.table(recap)
            
            if is_admin and st.checkbox("Voir le calendrier global des examens"):
                def fmt_sv(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br><small>{r['Enseignants']}</small>" for _,r in rows.iterrows()])
                grid_sv = df_surv.groupby(['Horaire', 'Jours']).apply(fmt_sv).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
                st.write(grid_sv.to_html(escape=False), unsafe_allow_html=True)

    components.html("<button onclick='window.parent.print()' style='width:100%; padding:12px; background:#28a745; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:20px;'>🖨️ IMPRIMER CE PORTAIL</button>", height=70)
