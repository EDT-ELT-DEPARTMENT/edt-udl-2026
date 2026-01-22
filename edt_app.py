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
    # Ordre imposé : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
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
    # Ajout des deux nouveaux espaces dans le selectbox
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
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
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

            df_f['Type'] = df_f['Code'].apply(lambda x: "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP"))
            df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            df_u = df_f.drop_duplicates(subset=['j_norm', 'h_norm'])
            
            st.markdown(f"### 📊 Bilan : {cible}")
            st.markdown(f"""<div class="stat-container">
                <div class="stat-box bg-cours">📘 {len(df_u[df_u['Type'] == 'COURS'])} COURS</div>
                <div class="stat-box bg-td">📗 {len(df_u[df_u['Type'] == 'TD'])} TD</div>
                <div class="stat-box bg-tp">📙 {len(df_u[df_u['Type'] == 'TP'])} TP</div>
            </div>""", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            charge_reelle = df_u['h_val'].sum()
            charge_reg = 3.0 if poste_sup else 6.0
            c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
            h_sup = charge_reelle - charge_reg
            color_sup = "#e74c3c" if h_sup > 0 else "#27ae60"
            c3.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup<br><h2 style='color:{color_sup};'>{h_sup} h</h2></div>", unsafe_allow_html=True)

            def fmt_e(rows):
                items = [f"<b>{get_nature(r['Code'])} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _, r in rows.iterrows()]
                return "<div class='separator'></div>".join(items)
            
            if not df_f.empty:
                grid = df_f.groupby(['h_norm', 'j_norm']).apply(fmt_e, include_groups=False).unstack('j_norm')
                grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
                grid.index = [map_h.get(i, i) for i in grid.index]; grid.columns = [map_j.get(c, c) for c in grid.columns]
                st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows):
                items = [f"<b>{('📘 COURS' if 'COURS' in str(r['Code']).upper() else '📗 TD' if 'TD' in str(r['Code']).upper() else '📙 TP')} : {r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _, r in rows.iterrows()]
                return "<div class='separator'></div>".join(items)
            grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
            grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_p.index = horaires_list; grid_p.columns = jours_list
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Choisir Salle :", sorted(df["Lieu"].unique()))
            df_s = df[df["Lieu"] == s_sel]
            def fmt_s(rows):
                items = [f"<b>{r['Promotion']}</b><br>{r['Enseignements']}<br><i>{r['Enseignants']}</i>" for _, r in rows.iterrows()]
                return "<div class='separator'></div>".join(items)
            grid_s = df_s.groupby(['h_norm', 'j_norm']).apply(fmt_s, include_groups=False).unstack('j_norm')
            grid_s = grid_s.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_s.index = horaires_list; grid_s.columns = jours_list
            st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🚩 Vérificateur":
            st.subheader("🚩 Analyse des conflits")
            errs = []
            # Salles
            s_c = df[df["Lieu"] != "Non défini"].groupby(['Jours', 'Horaire', 'Lieu']).filter(lambda x: len(x) > 1)
            for _, r in s_c.drop_duplicates(['Jours', 'Horaire', 'Lieu']).iterrows():
                errs.append(f"❌ **SALLE** : {r['Lieu']} occupée en double le {r['Jours']} à {r['Horaire']}")
            # Enseignants
            p_c = df[df["Enseignants"] != "Non défini"].groupby(['Jours', 'Horaire', 'Enseignants']).filter(lambda x: len(x) > 1)
            for _, r in p_c.drop_duplicates(['Jours', 'Horaire', 'Enseignants']).iterrows():
                errs.append(f"⚠️ **CONFLIT** : {r['Enseignants']} a deux cours le {r['Jours']} à {r['Horaire']}")
            
            if errs:
                for e in errs:
                    if "❌" in e: st.error(e)
                    else: st.warning(e)
            else:
                st.success("✅ Aucun conflit détecté.")

    elif portail == "📅 Surveillances Examens":
        NOM_SURV = "surveillances_2026.xlsx"
        if os.path.exists(NOM_SURV):
            df_surv = pd.read_excel(NOM_SURV)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
            for c in df_surv.columns: df_surv[c] = df_surv[c].fillna("").astype(str).str.strip()
            
            col_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_surv.columns else 'Enseignants'
            all_profs = []
            for entry in df_surv[col_prof].unique():
                for p in entry.split('&'):
                    p_clean = p.strip()
                    if p_clean and p_clean not in ["nan", "Non défini"]: all_profs.append(p_clean)
            liste_profs = sorted(list(set(all_profs)))
            
            u_nom = user['nom_officiel']
            idx_p = liste_profs.index(u_nom) if u_nom in liste_profs else 0
            prof_sel = st.selectbox("🔍 Sélectionner un enseignant :", liste_profs, index=idx_p)
            df_u = df_surv[df_surv[col_prof].str.contains(prof_sel, case=False, na=False)].sort_values(by='Date_Tri')
            
            st.markdown(f"### 📊 Bilan numérique : {prof_sel}")
            c1, c2, c3 = st.columns(3)
            nb_matin = len(df_u[df_u['Heure'].str.contains("08h|09h|10h", case=False)])
            with c1: st.metric("Total Surveillances", f"{len(df_u)} séances")
            with c2: st.metric("Séances Matin", nb_matin)
            with c3: st.metric("Séances Après-midi", len(df_u) - nb_matin)
            
            st.divider()
            tab_p, tab_g = st.tabs(["📋 Ma Feuille de Route", "🌐 Planning Complet"])
            with tab_p:
                if not df_u.empty:
                    for _, r in df_u.iterrows():
                        st.markdown(f"""<div style="background:#f0f2f6;padding:15px;border-radius:10px;border-left:5px solid #1E3A8A;margin-bottom:10px;">
                            <span style="font-weight:bold;color:#1E3A8A;">📅 {r['Jour']} {r['Date']}</span> | 🕒 {r['Heure']}<br>
                            <b>📖 {r['Matière']}</b><br><small>📍 {r['Salle']} | 🎓 {r['Promotion']} | 👥 {r[col_prof]}</small></div>""", unsafe_allow_html=True)
                    out = io.BytesIO()
                    df_u.drop(columns=['Date_Tri']).to_excel(out, index=False)
                    st.download_button("📥 Télécharger mon planning", out.getvalue(), f"Surv_{prof_sel}.xlsx", use_container_width=True)
                else: st.info("Aucune surveillance affectée.")
            with tab_g: st.dataframe(df_surv.drop(columns=['Date_Tri']), use_container_width=True, hide_index=True)
        else: st.error("Fichier 'surveillances_2026.xlsx' manquant.")

    # ================= PORTAIL 3 : GÉNÉRATEUR AUTOMATIQUE (ADMIN) =================
    elif portail == "🤖 Générateur Automatique":
        if not is_admin:
            st.error("Accès réservé à l'administration.")
        else:
            st.header("⚙️ Générateur de Surveillances par Promotion")
            st.info("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

            if "df_genere" not in st.session_state: st.session_state.df_genere = None
            if "stats_charge" not in st.session_state: st.session_state.stats_charge = {}

            NOM_SURV_SRC = "surveillances_2026.xlsx"

            if not os.path.exists(NOM_SURV_SRC):
                st.error(f"❌ Fichier '{NOM_SURV_SRC}' introuvable.")
            else:
                df_src = pd.read_excel(NOM_SURV_SRC)
                df_src.columns = [str(c).strip() for c in df_src.columns]
                for c in df_src.columns: df_src[c] = df_src[c].fillna("").astype(str).str.strip()

                col_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_src.columns else 'Enseignants'
                liste_profs_surv = sorted([p for p in df_src[col_prof].unique() if p not in ["", "Non défini", "nan"]])
                promo_dispo = sorted(df_src['Promotion'].unique()) if 'Promotion' in df_src.columns else []

                # --- CONFIGURATION STRICTE DES QUOTAS ---
                with st.expander("⚖️ Réglage des Exceptions (Postes Supérieurs / Vacataires)", expanded=True):
                    c_cfg1, c_cfg2 = st.columns(2)
                    with c_cfg1:
                        profs_exception = st.multiselect("👤 Enseignants avec Quota limité :", liste_profs_surv)
                    with c_cfg2:
                        max_base = st.number_input("Nombre Max de surveillances (100%)", min_value=1, value=10)
                    
                    pourcentage = st.slider("Pourcentage du quota autorisé (%)", 10, 100, 50)
                    quota_calcule = int(max_base * (pourcentage / 100))
                    st.warning(f"🎯 Les enseignants sélectionnés seront limités à **{quota_calcule} surveillances** maximum.")

                col_p, col_d = st.columns(2)
                with col_p: promo_cible = st.multiselect("🎓 Promotions :", promo_dispo)
                with col_d: dates_exam = st.multiselect("📅 Dates :", sorted(df_src['Date'].unique()))

                if st.button("🚀 GÉNÉRER AVEC PLAFONNEMENT"):
                    if not promo_cible:
                        st.warning("Sélectionnez au moins une promotion.")
                    else:
                        stats = {p: 0 for p in liste_profs_surv}
                        global_tracking = []
                        results = []

                        for promo in promo_cible:
                            df_p = df_src[df_src['Promotion'] == promo].copy()
                            if dates_exam: df_p = df_p[df_p['Date'].isin(dates_exam)]

                            for _, row in df_p.iterrows():
                                binome = []
                                # On trie les profs par charge actuelle (équité)
                                prio = sorted(liste_profs_surv, key=lambda p: stats[p])

                                for p in prio:
                                    if len(binome) < 2:
                                        # CONDITION 1 : Pas de dépassement de quota pour les exceptions
                                        if p in profs_exception and stats[p] >= quota_calcule:
                                            continue
                                        
                                        # CONDITION 2 : Disponibilité temporelle
                                        conflit = any(x for x in global_tracking if x['D']==row['Date'] and x['H']==row['Heure'] and x['N']==p)
                                        
                                        if not conflit:
                                            binome.append(p)
                                            stats[p] += 1
                                            global_tracking.append({'D': row['Date'], 'H': row['Heure'], 'N': p})
                                
                                results.append({
                                    "Promotion": promo, "Date": row['Date'], "Heure": row['Heure'],
                                    "Matière": row['Matière'], "Salle": row['Salle'],
                                    "Binôme": " & ".join(binome) if len(binome)==2 else "MANQUE SURVEILLANT"
                                })
                        
                        st.session_state.stats_charge = stats
                        st.session_state.df_genere = pd.DataFrame(results)
                        st.rerun()

                # --- AFFICHAGE DES RÉSULTATS ---
                if st.session_state.df_genere is not None:
                    st.divider()
                    
                    # Analyse numérique
                    prof_sel = st.selectbox("📊 Vérifier un quota :", sorted(st.session_state.stats_charge.keys()))
                    q = st.session_state.stats_charge[prof_sel]
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric(f"Total {prof_sel}", f"{q} / {quota_calcule if prof_sel in profs_exception else max_base}")
                    with c2: st.metric("Statut", "Limité" if prof_sel in profs_exception else "Normal")
                    with c3: 
                        rempli = (q / quota_calcule * 100) if prof_sel in profs_exception else (q / max_base * 100)
                        st.metric("Taux d'occupation", f"{int(rempli)}%")

                    # Tableau Individuel
                    df_p_ind = st.session_state.df_genere[st.session_state.df_genere['Binôme'].str.contains(prof_sel, na=False)]
                    st.dataframe(df_p_ind[["Date", "Heure", "Matière", "Salle"]], use_container_width=True)

                    st.divider()
                    # Affichage par promo
                    for p in promo_cible:
                        st.write(f"### 📋 Planning : {p}")
                        st.table(st.session_state.df_genere[st.session_state.df_genere['Promotion'] == p].drop(columns=['Promotion']))

                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        st.session_state.df_genere.to_excel(writer, index=False)
                    st.download_button("📥 TÉLÉCHARGER (.XLSX)", buffer.getvalue(), "EDT_Surv_S2.xlsx", use_container_width=True)
# ================= PORTAIL 4 & 5 : ADMINISTRATION DES DONNÉES =================

# --- ESPACE 4 : DONNÉES ENSEIGNANTS (ADMIN) ---
elif portail == "👨‍🏫 Données Enseignants":
    if not is_admin:
        st.error("Accès réservé à l'administration.")
    else:
        st.header("🗂️ Gestion du Corps Enseignant")
        st.info("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("➕ Nouvel Enseignant")
            with st.form("form_prof"):
                nom_p = st.text_input("Nom et Prénom")
                email_p = st.text_input("Email Professionnel")
                grade_p = st.selectbox("Grade", ["Prof", "MCA", "MCB", "MAA", "MAB", "Vacataire"])
                if st.form_submit_button("✅ Enregistrer"):
                    if nom_p and email_p:
                        data = {
                            "nom_officiel": nom_p.upper(), 
                            "email": email_p.lower(), 
                            "role": "user", 
                            "password_hash": hash_pw("SBA2026")
                        }
                        try:
                            supabase.table("enseignants_auth").insert(data).execute()
                            st.success(f"Enregistré ! (MDP: SBA2026)")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")
                    else:
                        st.warning("Veuillez remplir tous les champs.")

        with col2:
            st.subheader("📋 Liste des Enseignants")
            res = supabase.table("enseignants_auth").select("nom_officiel, email").execute()
            if res.data:
                df_profs = pd.DataFrame(res.data)
                df_profs.columns = ["Nom Officiel", "Email"]
                st.dataframe(df_profs, use_container_width=True, hide_index=True)
                
                # Export de l'annuaire
                csv = df_profs.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Télécharger l'annuaire (CSV)", csv, "annuaire_enseignants.csv")

# --- ESPACE 5 : DONNÉES ÉTUDIANTS (ADMIN) ---
elif portail == "🎓 Données Étudiants":
    if not is_admin:
        st.error("Accès réservé à l'administration.")
    else:
        st.header("📊 Base de Données des Étudiants")
        st.info("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

        st.markdown("""
        > **Note :** Le fichier Excel doit contenir les colonnes : **Matricule**, **Nom**, **Prénom**, **Promotion**.
        """)

        uploaded_stu = st.file_uploader("📤 Importer la liste globale (Excel)", type=["xlsx"])
        
        if uploaded_stu:
            df_stu = pd.read_excel(uploaded_stu)
            # Nettoyage des colonnes
            df_stu.columns = [str(c).strip() for c in df_stu.columns]
            
            if 'Promotion' in df_stu.columns:
                promos_dispo = sorted(df_stu['Promotion'].unique())
                
                c1, c2 = st.columns([1, 3])
                with c1:
                    p_view = st.radio("Sélectionner Promotion :", promos_dispo)
                
                with c2:
                    df_filtered = df_stu[df_stu['Promotion'] == p_view].copy()
                    st.subheader(f"📜 Liste : {p_view}")
                    st.metric("Nombre d'étudiants", len(df_filtered))
                    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
                    
                    # Bouton de téléchargement pour la liste filtrée
                    buffer_stu = io.BytesIO()
                    with pd.ExcelWriter(buffer_stu, engine='xlsxwriter') as writer:
                        df_filtered.to_excel(writer, index=False, sheet_name=p_view)
                    
                    st.download_button(
                        label=f"📥 Télécharger la liste {p_view} (.xlsx)",
                        data=buffer_stu.getvalue(),
                        file_name=f"Liste_Etudiants_{p_view}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("La colonne 'Promotion' est manquante dans votre fichier.")
        else:
            st.info("Veuillez charger un fichier Excel pour afficher les listes par promotion.")




