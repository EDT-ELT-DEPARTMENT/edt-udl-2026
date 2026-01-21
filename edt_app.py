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
    
    /* STYLE DES BOITES DE STATISTIQUES */
    .stat-container {{ display: flex; justify-content: space-around; margin: 20px 0; gap: 10px; }}
    .stat-box {{ 
        flex: 1; padding: 15px; border-radius: 12px; color: white; 
        font-weight: bold; text-align: center; font-size: 16px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }}
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
    for col in ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']:
        if col in df.columns: 
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
    
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
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]

map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "📅 Surveillances Examens", "🤖 Générateur Automatique"])
    st.divider()
    mode_view = "Personnel"
    poste_sup = False
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge)")
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            
            # FILTRE FLEXIBLE
            df_f = df[df["Enseignants"].str.contains(cible, case=False, na=False)].copy()
            
            def get_t(x): 
                val = str(x).upper()
                if "COURS" in val: return "COURS"
                if "TD" in val: return "TD"
                return "TP"
            
            df_f['Type'] = df_f['Code'].apply(get_t)
            df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            df_u = df_f.drop_duplicates(subset=['j_norm', 'h_norm'])
            
            charge_reelle = df_u['h_val'].sum()
            charge_reglementaire = 3.0 if poste_sup else 6.0
            heures_sup = charge_reelle - charge_reglementaire
            
            # --- INTERFACE DES COMPTEURS ---
            nb_cours = len(df_u[df_u['Type'] == 'COURS'])
            nb_td = len(df_u[df_u['Type'] == 'TD'])
            nb_tp = len(df_u[df_u['Type'] == 'TP'])

            st.markdown(f"### 📊 Bilan : {cible}")
            
            # Affichage des boites colorées
            st.markdown(f"""
                <div class="stat-container">
                    <div class="stat-box bg-cours">📘 {nb_cours} COURS</div>
                    <div class="stat-box bg-td">📗 {nb_td} TD</div>
                    <div class="stat-box bg-tp">📙 {nb_tp} TP</div>
                </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reglementaire} h</h2></div>", unsafe_allow_html=True)
            color_sup = "#e74c3c" if heures_sup > 0 else "#27ae60"
            c3.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup<br><h2 style='color:{color_sup};'>{heures_sup} h</h2></div>", unsafe_allow_html=True)

            def fmt_e(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            
            if not df_f.empty:
                grid = df_f.groupby(['h_norm', 'j_norm']).apply(fmt_e, include_groups=False).unstack('j_norm')
                grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
                grid.index = [map_h.get(i, i) for i in grid.index]
                grid.columns = [map_j.get(c, c) for c in grid.columns]
                st.write(grid.to_html(escape=False), unsafe_allow_html=True)
            else:
                st.warning(f"Aucune donnée trouvée pour {cible}")

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
            grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_p.index = horaires_list; grid_p.columns = jours_list
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

    elif portail == "📅 Surveillances Examens":
        st.subheader(f"📋 Surveillances - {user['nom_officiel']}")
        st.info("Session normale S2 - Juin 2026")
        data_s = {"Date": ["15/06", "17/06"], "Heure": ["09h00", "13h00"], "Module": ["Electrot.", "IA"], "Lieu": ["Amphi A", "S06"]}
        st.table(pd.DataFrame(data_s))

import streamlit as st
import pandas as pd
import os
import io

# ================= PORTAIL 3 : GÉNÉRATEUR AUTOMATIQUE (ADMIN) =================
elif portail == "🤖 Générateur Automatique":
    if not is_admin:
        st.error("Accès réservé à l'administration.")
    else:
        st.header("⚙️ Générateur de Surveillances par Promotion")
        st.info("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

        NOM_SURV_SRC = "surveillances_2026.xlsx"

        if not os.path.exists(NOM_SURV_SRC):
            st.error(f"❌ Le fichier '{NOM_SURV_SRC}' est introuvable.")
        else:
            df_src = pd.read_excel(NOM_SURV_SRC)
            df_src.columns = [str(c).strip() for c in df_src.columns]
            for c in df_src.columns:
                df_src[c] = df_src[c].fillna("").astype(str).str.strip()

            # Extraction des enseignants
            col_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_src.columns else 'Enseignants'
            liste_profs_surv = sorted([p for p in df_src[col_prof].unique() if p not in ["", "Non défini", "nan"]])
            promo_dispo = sorted(df_src['Promotion'].unique()) if 'Promotion' in df_src.columns else []

            # --- CONFIGURATION DES GROUPES ---
            st.subheader("📋 Configuration des Groupes")
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                profs_decharge = st.multiselect("👤 Enseignants avec décharge (50%) :", liste_profs_surv)
            with col_cfg2:
                vacataires = st.multiselect("🎓 Vacataires (Quota réduit) :", liste_profs_surv)
            
            coef_decharge = st.slider("Coefficient de charge pour décharge/vacataire", 0.1, 0.9, 0.5)

            col1, col2 = st.columns(2)
            with col1:
                promo_cible = st.multiselect("🎓 Promotions à générer :", promo_dispo)
            with col2:
                dates_exam = st.multiselect("📅 Sélectionner les dates :", sorted(df_src['Date'].unique()))

            if st.button("🚀 GÉNÉRER LA RÉPARTITION ÉQUITABLE"):
                if not promo_cible:
                    st.warning("Veuillez choisir au moins une promotion.")
                else:
                    stats_charge = {p: 0 for p in liste_profs_surv}
                    global_tracking = []
                    all_promos_df = []

                    # Algorithme de sélection par binôme avec pondération
                    for promo in promo_cible:
                        st.markdown(f"#### 📋 Tableau : {promo}")
                        df_p = df_src[df_src['Promotion'] == promo].copy()
                        if dates_exam:
                            df_p = df_p[df_p['Date'].isin(dates_exam)]

                        final_rows = []
                        for _, row in df_p.iterrows():
                            binome = []
                            
                            # On cherche 2 surveillants
                            for _ in range(2):
                                prio = sorted(liste_profs_surv, key=lambda p: (
                                    stats_charge[p] / (coef_decharge if (p in profs_decharge or p in vacataires) else 1.0)
                                ))

                                for p in prio:
                                    if p not in binome:
                                        occupe = any(x for x in global_tracking if x['D'] == row['Date'] and x['H'] == row['Heure'] and x['N'] == p)
                                        if not occupe:
                                            binome.append(p)
                                            stats_charge[p] += 1
                                            global_tracking.append({'D': row['Date'], 'H': row['Heure'], 'N': p})
                                            break
                            
                            # Respect de la disposition demandée pour l'affichage
                            row_data = {
                                "Enseignements": row.get('Matière', ''),
                                "Code": row.get('N°', ''),
                                "Enseignants": row.get('Chargé de matière', ''),
                                "Horaire": row.get('Heure', ''),
                                "Jours": row.get('Jour', ''),
                                "Lieu": row.get('Salle', ''),
                                "Promotion": promo,
                                "Binôme": " & ".join(binome)
                            }
                            final_rows.append(row_data)
                            all_promos_df.append(row_data)

                        # Affichage du tableau avec votre disposition
                        cols_order = ["Enseignements", "Code", "Enseignants", "Horaire", "Jours", "Lieu", "Promotion", "Binôme"]
                        st.table(pd.DataFrame(final_rows)[cols_order])

                    # --- ANALYSE NUMÉRIQUE ---
                    st.divider()
                    st.subheader("🔍 Analyse numérique des charges")
                    
                    prof_analyse = st.selectbox("Sélectionner un enseignant :", liste_profs_surv)
                    quota = stats_charge.get(prof_analyse, 0)
                    
                    c_met1, c_met2, c_met3 = st.columns(3)
                    with c_met1:
                        st.metric(label=f"Quota {prof_analyse}", value=f"{quota} séances")
                    with c_met2:
                        st.metric(label="Type", value="Décharge/Vacataire" if (prof_analyse in profs_decharge or prof_analyse in vacataires) else "Normal")
                    with c_met3:
                        moyenne = sum(stats_charge.values()) / len(liste_profs_surv) if liste_profs_surv else 0
                        st.metric(label="Moyenne globale", value=f"{moyenne:.1f}")

                    if all_promos_df:
                        df_export = pd.DataFrame(all_promos_df)
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_export.to_excel(writer, index=False)
                        st.download_button("📥 TÉLÉCHARGER LE PLANNING FINAL", buffer.getvalue(), "Planning_Surv_Equitable.xlsx", use_container_width=True)

