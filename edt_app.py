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

# --- STYLE CSS COMPLET (VOTRE STYLE INITIAL) ---
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

# --- CHARGEMENT DU FICHIER EDT (INITIAL) ---
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
                st.success("Inscription réussie ! Connectez-vous.")
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
horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "📅 Surveillances Examens"])
    st.divider()
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge)")
    else:
        mode_view = "Surveillance_Matiere"
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    # ================= PORTAIL 1 : EDT (VOTRE CODE INITIAL) =================
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            df_f = df[df["Enseignants"] == cible].copy()
            
            def get_t(x): return "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP")
            df_f['Type'] = df_f['Enseignements'].apply(get_t)
            df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            df_u = df_f.drop_duplicates(subset=['Jours', 'Horaire'])
            
            charge_reelle = df_u['h_val'].sum()
            c_reg = 3.0 if poste_sup else 6.0
            
            st.markdown(f"### 📊 Bilan : {cible}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{c_reg} h</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'>Heures Sup<br><h2>{charge_reelle - c_reg} h</h2></div>", unsafe_allow_html=True)
            
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {len(df_u[df_u['Type'] == 'COURS'])} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {len(df_u[df_u['Type'] == 'TD'])} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {len(df_u[df_u['Type'] == 'TP'])} TP</div>", unsafe_allow_html=True)

            def fmt_e(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt_e).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid_p = df_p.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(f"### 📅 Emploi du Temps : {p_sel}")
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Choisir Salle (Racine) :", sorted([r for r in df['Lieu_Racine'].unique() if r != "Non défini"]))
            df_s = df[df['Lieu_Racine'] == s_sel]
            def fmt_s(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><small>{r['Lieu']}</small>" for _,r in rows.iterrows()])
            grid_s = df_s.groupby(['Horaire', 'Jours']).apply(fmt_s).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(f"### 🏢 Occupation : {s_sel}")
            st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🚩 Vérificateur":
            st.subheader("🚩 Vérification des chevauchements")
            dup = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
            err = df[df['Enseignants'] != "Non défini"][dup]
            if err.empty: st.success("✅ Aucun conflit détecté.")
            else: st.warning("Conflits d'enseignants détectés :"); st.dataframe(err)

# ================= PORTAIL 2 : SURVEILLANCES =================
    elif portail == "📅 Surveillances Examens":
        NOM_SURV = "surveillances_2026.xlsx"
        horaires_examens = ["08h30 – 10h30", "11h00 – 13h00", "13h30 – 15h30"]
        
        if os.path.exists(NOM_SURV):
            df_surv = pd.read_excel(NOM_SURV)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            
            # Nettoyage et conversion des dates pour le tri
            for col in df_surv.columns:
                df_surv[col] = df_surv[col].fillna("").astype(str).str.strip()
            
            liste_profs = sorted(df_surv['Surveillant(s)'].unique())
            prof_sel = st.selectbox("🔍 Sélectionner un enseignant :", liste_profs, index=liste_profs.index(user['nom_officiel']) if user['nom_officiel'] in liste_profs else 0)
            
            # Filtrage et Tri par Date
            df_u = df_surv[df_surv['Surveillant(s)'] == prof_sel].copy()
            # On s'assure que le tri par date fonctionne (format JJ/MM/AAAA)
            try:
                df_u['temp_date'] = pd.to_datetime(df_u['Date'], dayfirst=True)
                df_u = df_u.sort_values(by='temp_date')
            except:
                pass # En cas de format de date exotique

            st.metric("Nombre de séances", f"{len(df_u)} séance(s)")
            
            tab1, tab2 = st.tabs(["👤 Planning Individuel", "🌍 Vue Globale"])
            
            with tab1:
                if not df_u.empty:
                    # --- NOUVEAU : RÉCAPITULATIF PAR LIGNES (AVANT LE TABLEAU) ---
                    st.markdown("#### 📝 Résumé chronologique des missions")
                    for _, r in df_u.iterrows():
                        date_c = str(r['Date']).split(' ')[0]
                        st.markdown(f"""
                            <div style="background-color: #f1f4f9; padding: 10px; border-left: 5px solid #D4AF37; margin-bottom: 5px; border-radius: 5px;">
                                <span style="color: #1E3A8A; font-weight: bold;">📅 {r['Jour']} {date_c}</span> | 
                                <span style="color: #d35400; font-weight: bold;">🕒 {r['Heure']}</span><br>
                                📘 <b>Matière :</b> {r['Matière']} <br>
                                👤 <b>Responsable :</b> {r['Chargé de matière']} | 📍 <b>Salle :</b> {r['Salle']} | 🎓 <b>Promo :</b> {r['Promotion']}
                            </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br>#### 🗓️ Vue Calendrier", unsafe_allow_html=True)
                    
                    # --- TABLEAU VISUEL (GRILLE) ---
                    grid_s = pd.DataFrame("", index=horaires_examens, columns=jours_list)
                    for _, r in df_u.iterrows():
                        dt = str(r['Date']).split(' ')[0]
                        txt = f"<div style='font-size:11px; line-height:1.2;'><b>{r['Matière']}</b><br><span style='color:#d35400; font-weight:bold;'>📅 {dt}</span><br>📍 <b>{r['Salle']}</b><br><small>🎓 {r['Promotion']}</small></div>"
                        j, h = str(r['Jour']).strip().capitalize(), str(r['Heure']).strip()
                        if j in grid_s.columns and h in grid_s.index:
                            grid_s.at[h, j] += (f"<hr style='margin:5px 0;'>" if grid_s.at[h, j] != "" else "") + txt
                    
                    st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)
                    
                    # BOUTONS ACTIONS
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        components.html(f'<button onclick="window.parent.print()" style="width:100%; padding:12px; background:#1E3A8A; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">🖨️ IMPRIMER / PDF</button>', height=60)
                    with c2:
                        import io
                        out = io.BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as wr: df_u.to_excel(wr, index=False)
                        st.download_button("📥 TÉLÉCHARGER (.XLSX)", out.getvalue(), f"Surv_{prof_sel}.xlsx", "application/vnd.ms-excel", use_container_width=True)
                else:
                    st.warning("Aucune donnée trouvée.")
