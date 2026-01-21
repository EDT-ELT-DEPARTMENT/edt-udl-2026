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

    # ================= PORTAIL 3 : GÉNÉRATEUR AUTOMATIQUE (ADMIN) =================
elif portail == "🤖 Générateur Automatique":
    st.header("⚙️ Générateur de Surveillances par Promotion")
    st.info("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

    # --- CONFIGURATION DES QUOTAS ET EXCEPTIONS ---
    with st.expander("⚖️ Réglage des Exceptions (Postes Supérieurs / Vacataires)", expanded=True):
        col_exc1, col_exc2 = st.columns(2)
        with col_exc1:
            profs_exception = st.multiselect("👤 Enseignants à quota limité :", liste_profs_surv)
        with col_exc2:
            max_theorique = st.number_input("Nombre Max de surveillances (100%)", min_value=1, value=10)
        
        # Le curseur pilote directement le calcul
        pourcentage = st.slider("Pourcentage du quota autorisé (%)", 0, 100, 50, step=10)
        quota_limite = int(max_theorique * (pourcentage / 100))
        
        st.markdown(f"""
        > 💡 **Règle de calcul :** > Chaque enseignant sélectionné ne pourra pas dépasser **{quota_limite}** séances.  
        > Les séances excédentaires seront automatiquement redistribuées aux autres enseignants.
        """)

    # --- GÉNÉRATION ---
    if st.button("🚀 LANCER LA GÉNÉRATION DES FLUX"):
        if not promo_cible:
            st.error("Veuillez sélectionner des promotions.")
        else:
            stats = {p: 0 for p in liste_profs_surv}
            global_tracking = []
            results = []

            # Extraction des besoins
            df_besoins = df_src[df_src['Promotion'].isin(promo_cible)].copy()
            if dates_exam:
                df_besoins = df_besoins[df_besoins['Date'].isin(dates_exam)]

            for _, row in df_besoins.iterrows():
                binome = []
                
                # 1. Trier tous les enseignants par charge actuelle pour l'équité
                profs_tries = sorted(liste_profs_surv, key=lambda p: stats[p])

                for p in profs_tries:
                    if len(binome) < 2:
                        # VERIFICATION DU QUOTA (LA RELATION QUE VOUS AVEZ DEMANDÉE)
                        if p in profs_exception and stats[p] >= quota_limite:
                            continue # On passe au suivant, l'exception a atteint son max
                        
                        # Vérification anti-conflit (pas 2 salles en même temps)
                        deja_occupe = any(x for x in global_tracking if x['D']==row['Date'] and x['H']==row['Heure'] and x['N']==p)
                        
                        if not deja_occupe:
                            binome.append(p)
                            stats[p] += 1
                            global_tracking.append({'D': row['Date'], 'H': row['Heure'], 'N': p})

                results.append({
                    "Promotion": row['Promotion'], "Date": row['Date'], "Heure": row['Heure'],
                    "Matière": row['Matière'], "Salle": row['Salle'],
                    "Binôme": " & ".join(binome) if len(binome) == 2 else "⚠️ MANQUE EFFECTIF"
                })

            st.session_state.stats_charge = stats
            st.session_state.df_genere = pd.DataFrame(results)
            st.rerun()

    # --- AFFICHAGE NUMÉRIQUE ET TABLEAU INDIVIDUEL ---
    if st.session_state.df_genere is not None:
        st.divider()
        st.subheader("📊 Analyse des charges après redistribution")
        
        prof_sel = st.selectbox("Vérifier l'impact du curseur sur :", sorted(liste_profs_surv))
        charge_reelle = st.session_state.stats_charge[prof_sel]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Surveillances attribuées", f"{charge_reelle} séances")
        with c2:
            statut = "Limité (Poste Sup/Vac)" if prof_sel in profs_exception else "Normal"
            st.metric("Statut Enseignant", statut)
        with c3:
            limite_label = quota_limite if prof_sel in profs_exception else "∞"
            st.metric("Limite autorisée", limite_label)

        # Tableau individuel spécifique
        st.write(f"**📅 Planning personnel de {prof_sel} :**")
        df_perso = st.session_state.df_genere[st.session_state.df_genere['Binôme'].str.contains(prof_sel, na=False)]
        st.table(df_perso[["Date", "Heure", "Matière", "Salle", "Promotion"]])
