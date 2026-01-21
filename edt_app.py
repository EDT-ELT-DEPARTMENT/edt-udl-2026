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

# ================= PORTAIL 2 : SURVEILLANCES EXAMENS =================
    elif portail == "📅 Surveillances Examens":
        NOM_SURV = "surveillances_2026.xlsx"
        
        if os.path.exists(NOM_SURV):
            df_surv = pd.read_excel(NOM_SURV)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            
            # Nettoyage et conversion des dates pour le tri
            df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
            for c in df_surv.columns:
                df_surv[c] = df_surv[c].fillna("").astype(str).str.strip()

            # Liste des enseignants présents dans le fichier
            col_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_surv.columns else 'Enseignants'
            # Si les surveillants sont stockés en binômes "Nom A & Nom B", on les sépare pour la liste
            all_profs = []
            for entry in df_surv[col_prof].unique():
                for p in entry.split('&'):
                    p_clean = p.strip()
                    if p_clean and p_clean not in ["nan", "Non défini"]:
                        all_profs.append(p_clean)
            liste_profs = sorted(list(set(all_profs)))

            # Sélection de l'enseignant
            u_nom = user['nom_officiel']
            idx_p = liste_profs.index(u_nom) if u_nom in liste_profs else 0
            prof_sel = st.selectbox("🔍 Sélectionner un enseignant pour voir ses statistiques :", liste_profs, index=idx_p)

            # Filtrage des données pour l'enseignant sélectionné
            # On cherche le nom dans la colonne (gère les binômes)
            df_u = df_surv[df_surv[col_prof].str.contains(prof_sel, case=False, na=False)].sort_values(by='Date_Tri')

            # --- AFFICHAGE NUMÉRIQUE (STATISTIQUES) ---
            st.markdown(f"### 📊 Bilan numérique : {prof_sel}")
            
            nb_total = len(df_u)
            
            # Calcul de la répartition par semaine (optionnel mais utile)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric(label="Total Surveillances", value=f"{nb_total} séances")
            with c2:
                # Exemple : Compte les matinées (08h30 ou 09h00)
                matin = len(df_u[df_u['Heure'].str.contains("08h|09h|10h", case=False)])
                st.metric(label="Séances Matin", value=matin)
            with c3:
                apres_midi = nb_total - matin
                st.metric(label="Séances Après-midi", value=apres_midi)

            st.divider()

            # --- DÉTAILS DES MISSIONS ---
            tab_perso, tab_global = st.tabs(["📋 Ma Feuille de Route", "🌐 Planning Complet"])
            
            with tab_perso:
                if not df_u.empty:
                    for _, r in df_u.iterrows():
                        st.markdown(f"""
                            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1E3A8A; margin-bottom: 10px;">
                                <span style="font-size: 18px; font-weight: bold; color: #1E3A8A;">📅 {r['Jour']} {r['Date']}</span>
                                <span style="float: right; background: #1E3A8A; color: white; padding: 2px 10px; border-radius: 20px;">🕒 {r['Heure']}</span>
                                <br><b style="font-size: 16px;">📖 {r['Matière']}</b>
                                <br><small>📍 Salle : <b>{r['Salle']}</b> | 🎓 Promotion : <b>{r['Promotion']}</b></small>
                                <br><small>👥 Partenaire(s) : {r[col_prof]}</small>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    # Bouton d'export individuel
                    out = io.BytesIO()
                    df_u.drop(columns=['Date_Tri']).to_excel(out, index=False)
                    st.download_button(f"📥 Télécharger mon planning ({prof_sel})", out.getvalue(), f"Surv_{prof_sel}.xlsx", use_container_width=True)
                else:
                    st.info("Aucune surveillance affectée pour le moment.")

            with tab_global:
                st.dataframe(df_surv.drop(columns=['Date_Tri']), use_container_width=True, hide_index=True)
        else:
            st.error("Le fichier 'surveillances_2026.xlsx' est manquant.")
    # ================= PORTAIL 3 : GÉNÉRATEUR AUTOMATIQUE (ADMIN) =================
    elif portail == "🤖 Générateur Automatique":
        if not is_admin:
            st.error("Accès réservé à l'administration.")
        else:
            st.header("⚙️ Générateur de Surveillances par Promotion")
            st.info("Configuration de la Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

            # 1. FILTRES DE GÉNÉRATION
            col_a, col_b = st.columns(2)
            with col_a:
                promo_dispo = sorted(df['Promotion'].unique()) if 'Promotion' in df.columns else []
                promo_cible = st.multiselect("🎓 Choisir les Promotions :", promo_dispo)
            with col_b:
                # Dates personnalisables
                dates_exam = st.multiselect("📅 Dates de la session :", 
                                           ["Dimanche 25/01", "Lundi 26/01", "Mardi 27/01", "Mercredi 28/01", "Jeudi 29/01"],
                                           default=["Dimanche 25/01"])

            # 2. GESTION DES ENSEIGNANTS
            liste_profs_edt = sorted([str(e).strip() for e in df['Enseignants'].unique() if str(e).strip() not in ["nan", "None", "Non défini"]])
            profs_alleger = st.multiselect("👤 Enseignants avec décharge (Poste Sup) :", liste_profs_edt)
            coef = st.slider("Intensité de charge pour les décharges (%)", 10, 100, 50) / 100

            if st.button("🚀 LANCER LA RÉPARTITION"):
                NOM_SURV_SRC = "surveillances_2026.xlsx"
                if not os.path.exists(NOM_SURV_SRC):
                    st.error("❌ Fichier source 'surveillances_2026.xlsx' introuvable. Veuillez l'uploader.")
                elif not promo_cible:
                    st.warning("⚠️ Veuillez sélectionner au moins une promotion.")
                else:
                    try:
                        df_src = pd.read_excel(NOM_SURV_SRC)
                        stats_charge = {e: 0 for e in liste_profs_edt}
                        global_tracking = [] # Pour éviter les doubles surveillances au même moment
                        
                        for promo in promo_cible:
                            st.markdown(f"### 📋 Tableau d'Examen : **{promo}**")
                            df_p = df_src[df_src['Promotion'].astype(str).str.contains(promo)].copy()
                            
                            if df_p.empty:
                                st.write(f"∅ Aucune donnée trouvée pour {promo}")
                                continue

                            final_rows_promo = []
                            for _, row in df_p.iterrows():
                                salle = str(row['Salle']).upper()
                                # Règle : Amphi = 3 surveillants, Salle = 2
                                nb_besoin = 3 if any(a in salle for a in ["A", "AMPHI"]) else 2
                                
                                surv_attribues = []
                                # Tri des profs par charge pondérée pour l'équité
                                for _ in range(nb_besoin):
                                    prio = sorted(liste_profs_edt, key=lambda e: (stats_charge[e] / (coef if e in profs_alleger else 1.0)))
                                    
                                    for p in prio:
                                        # Vérifier si le prof n'est pas déjà occupé sur cette Date/Heure
                                        conflit = any(x for x in global_tracking if x['Date']==row['Date'] and x['Heure']==row['Heure'] and x['Nom']==p)
                                        if not conflit:
                                            surv_attribues.append(p)
                                            stats_charge[p] += 1
                                            global_tracking.append({'Date': row['Date'], 'Heure': row['Heure'], 'Nom': p})
                                            break
                                
                                final_rows_promo.append({
                                    "Date": row['Date'],
                                    "Heure": row['Heure'],
                                    "Matière": row['Matière'],
                                    "Salle": row['Salle'],
                                    "Surveillants": " / ".join(surv_attribues)
                                })
                            
                            # Affichage du tableau final pour la promo
                            st.table(pd.DataFrame(final_rows_promo))
                        
                        st.success("✅ Répartition équitable terminée avec succès.")
                        
                        # Affichage du bilan de charge
                        with st.expander("📊 Voir le bilan des charges par enseignant"):
                            bilan_df = pd.DataFrame([{"Enseignant": k, "Nombre": v} for k, v in stats_charge.items()])
                            st.bar_chart(bilan_df.set_index("Enseignant"))

                    except Exception as e:
                        st.error(f"Erreur lors de la génération : {e}")
else:
    st.error("Le fichier 'dataEDT-ELT-S2-2026.xlsx' est introuvable au démarrage.")

