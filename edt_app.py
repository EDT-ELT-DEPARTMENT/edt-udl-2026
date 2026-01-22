import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="EDT UDL 2026",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONNEXION BASE DE DONNÉES ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- GESTION DU TEMPS ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
jours_semaine = [
    "Lundi", "Mardi", "Mercredi", 
    "Jeudi", "Vendredi", "Samedi", "Dimanche"
]
nom_jour_fr = jours_semaine[now.weekday()]

# --- STYLE CSS DÉTAILLÉ ---
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; 
        text-align: center; 
        font-family: 'serif'; 
        font-weight: bold; 
        border-bottom: 3px solid #D4AF37; 
        padding-bottom: 15px; 
        font-size: 18px; 
        margin-top: 5px;
    }}
    .portal-badge {{ 
        background-color: #D4AF37; 
        color: #1E3A8A; 
        padding: 5px 15px; 
        border-radius: 5px; 
        font-weight: bold; 
        text-align: center; 
        margin-bottom: 20px; 
    }}
    .date-badge {{ 
        background-color: #1E3A8A; 
        color: white; 
        padding: 5px 15px; 
        border-radius: 20px; 
        font-size: 12px; 
        float: right; 
    }}
    .metric-card {{ 
        background-color: #f8f9fa; 
        border: 1px solid #1E3A8A; 
        padding: 10px; 
        border-radius: 10px; 
        text-align: center; 
        height: 100%; 
    }}
    .stat-container {{ 
        display: flex; 
        justify-content: space-around; 
        margin: 20px 0; 
        gap: 10px; 
    }}
    .stat-box {{ 
        flex: 1; 
        padding: 15px; 
        border-radius: 12px; 
        color: white; 
        font-weight: bold; 
        text-align: center; 
        font-size: 16px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1); 
    }}
    .bg-cours {{ background: linear-gradient(135deg, #1E3A8A, #3B82F6); }}
    .bg-td {{ background: linear-gradient(135deg, #15803d, #22c55e); }}
    .bg-tp {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
    
    table {{ 
        width: 100%; 
        border-collapse: collapse; 
        table-layout: fixed; 
        margin-top: 10px; 
        background-color: white; 
    }}
    th {{ 
        background-color: #1E3A8A !important; 
        color: white !important; 
        border: 1px solid #000; 
        padding: 6px; 
        text-align: center; 
        font-size: 11px; 
    }}
    td {{ 
        border: 1px solid #000; 
        padding: 4px !important; 
        vertical-align: top; 
        text-align: center; 
        background-color: white; 
        height: 95px; 
        font-size: 11px; 
    }}
    .separator {{ 
        border-top: 1px dashed #bbb; 
        margin: 4px 0; 
    }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DES DONNÉES ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

def normalize(s):
    if not s or s == "Non défini": 
        return "vide"
    s = str(s).strip().lower()
    s = s.replace(" ", "").replace("-", "").replace("–", "")
    s = s.replace(":00", "").replace("h00", "h")
    return s

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    
    colonnes_cles = [
        'Enseignements', 
        'Code', 
        'Enseignants', 
        'Horaire', 
        'Jours', 
        'Lieu', 
        'Promotion'
    ]
    
    for col in colonnes_cles:
        if col in df.columns: 
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
            
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)

# --- SYSTÈME D'AUTH ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    t_conn, t_ins, t_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    
    with t_conn:
        email_input = st.text_input("Adresse Email", key="login_email")
        pass_input = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter au portail"):
            result = supabase.table("enseignants_auth").select("*").eq("email", email_input).eq("password_hash", hash_pw(pass_input)).execute()
            if result.data:
                st.session_state["user_data"] = result.data[0]
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect.")
                
    with t_ins:
        st.subheader("Créer un nouveau compte Enseignant")
        # On récupère la liste des noms depuis l'Excel pour éviter les erreurs de saisie
        noms_possibles = sorted(df["Enseignants"].unique()) if df is not None else []
        
        new_nom = st.selectbox("Sélectionnez votre nom (tel qu'il apparaît dans l'EDT)", noms_possibles)
        new_email = st.text_input("Votre adresse Email")
        new_pass = st.text_input("Choisissez un mot de passe", type="password")
        confirm_pass = st.text_input("Confirmez le mot de passe", type="password")
        
        if st.button("Créer mon compte"):
            if not new_email or not new_pass:
                st.warning("Veuillez remplir tous les champs.")
            elif new_pass != confirm_pass:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                # Vérifier si l'email existe déjà
                check = supabase.table("enseignants_auth").select("email").eq("email", new_email).execute()
                if check.data:
                    st.error("Cet email est déjà utilisé.")
                else:
                    data_ins = {
                        "nom_officiel": new_nom,
                        "email": new_email,
                        "password_hash": hash_pw(new_pass),
                        "role": "enseignant"
                    }
                    supabase.table("enseignants_auth").insert(data_ins).execute()
                    st.success("✅ Compte créé avec succès ! Vous pouvez maintenant vous connecter.")
                    st.balloons()

    with t_adm:
        code_admin = st.text_input("Code de sécurité Administration", type="password", key="admin_code")
        if st.button("Accès Administration"):
            if code_admin == "doctorat2026":
                st.session_state["user_data"] = {"nom_officiel": "ADMINISTRATEUR", "role": "admin"}
                st.rerun()
            else:
                st.error("Code admin incorrect.")
    st.stop()

# --- VARIABLES GLOBALES ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"

jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = [
    "8h - 9h30", 
    "9h30 - 11h", 
    "11h - 12h30", 
    "12h30 - 14h", 
    "14h - 15h30", 
    "15h30 - 17h"
]

map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Sélectionner Espace", [
        "📖 Emploi du Temps", 
        "📅 Surveillances Examens", 
        "🤖 Générateur Automatique", 
        "👥 Portail Enseignants", 
        "🎓 Portail Étudiants"
    ])
    st.divider()
    
    mode_view = "Personnel"
    poste_sup = False
    
    if portail == "📖 Emploi du Temps":
        if is_admin:
            mode_view = st.radio("Vue Administration :", [
                "Promotion", 
                "Enseignant", 
                "🏢 Planning Salles", 
                "🚩 Vérificateur"
            ])
        else:
            mode_view = "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge 3h)")
        
    if st.button("🚪 Déconnexion du compte"):
        st.session_state["user_data"] = None
        st.rerun()

# --- EN-TÊTE ---
st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE ACTIF : {portail.upper()}</div>", unsafe_allow_html=True)

# --- LOGIQUE PRINCIPALE ---
if df is not None:

    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            if mode_view == "Personnel":
                cible = user['nom_officiel']
            else:
                cible = st.selectbox("Sélectionner l'Enseignant :", sorted(df["Enseignants"].unique()))
            
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
            
            st.markdown(f"### 📊 Bilan Horaire : {cible}")
            st.markdown(f"""<div class="stat-container">
                <div class="stat-box bg-cours">📘 {len(df_u[df_u['Type'] == 'COURS'])} Séances Cours</div>
                <div class="stat-box bg-td">📗 {len(df_u[df_u['Type'] == 'TD'])} Séances TD</div>
                <div class="stat-box bg-tp">📙 {len(df_u[df_u['Type'] == 'TP'])} Séances TP</div>
            </div>""", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            charge_reelle = df_u['h_val'].sum()
            charge_reg = 3.0 if poste_sup else 6.0
            
            with c1:
                st.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
            
            h_sup = charge_reelle - charge_reg
            color_sup = "#e74c3c" if h_sup > 0 else "#27ae60"
            with c3:
                st.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup.<br><h2 style='color:{color_sup};'>{h_sup} h</h2></div>", unsafe_allow_html=True)

            def format_case(rows):
                items = []
                for _, r in rows.iterrows():
                    txt = f"<b>{get_nature(r['Code'])} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>"
                    items.append(txt)
                return "<div class='separator'></div>".join(items)
            
            if not df_f.empty:
                grid = df_f.groupby(['h_norm', 'j_norm']).apply(format_case, include_groups=False).unstack('j_norm')
                grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
                grid.index = [map_h.get(i, i) for i in grid.index]
                grid.columns = [map_j.get(c, c) for c in grid.columns]
                st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            
            def fmt_p(rows):
                items = []
                for _, r in rows.iterrows():
                    nat = '📘 COURS' if 'COURS' in str(r['Code']).upper() else '📗 TD' if 'TD' in str(r['Code']).upper() else '📙 TP'
                    items.append(f"<b>{nat} : {r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>")
                return "<div class='separator'></div>".join(items)
                
            grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
            grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_p.index = horaires_list
            grid_p.columns = jours_list
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Choisir Salle :", sorted(df["Lieu"].unique()))
            df_s = df[df["Lieu"] == s_sel]
            
            def fmt_s(rows):
                items = [f"<b>{r['Promotion']}</b><br>{r['Enseignements']}<br><i>{r['Enseignants']}</i>" for _, r in rows.iterrows()]
                return "<div class='separator'></div>".join(items)
                
            grid_s = df_s.groupby(['h_norm', 'j_norm']).apply(fmt_s, include_groups=False).unstack('j_norm')
            grid_s = grid_s.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_s.index = horaires_list
            grid_s.columns = jours_list
            st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🚩 Vérificateur":
            st.subheader("🚩 Analyse des Conflits Potentiels")
            errs = []
            
            # Conflit Salles
            s_c = df[df["Lieu"] != "Non défini"].groupby(['Jours', 'Horaire', 'Lieu']).filter(lambda x: len(x) > 1)
            for _, r in s_c.drop_duplicates(['Jours', 'Horaire', 'Lieu']).iterrows():
                errs.append(f"❌ **SALLE** : {r['Lieu']} occupée en double le {r['Jours']} à {r['Horaire']}")
            
            # Conflit Enseignants
            p_c = df[df["Enseignants"] != "Non défini"].groupby(['Jours', 'Horaire', 'Enseignants']).filter(lambda x: len(x) > 1)
            for _, r in p_c.drop_duplicates(['Jours', 'Horaire', 'Enseignants']).iterrows():
                errs.append(f"⚠️ **CONFLIT** : {r['Enseignants']} a deux cours simultanés le {r['Jours']} à {r['Horaire']}")
                
            if errs:
                for e in errs:
                    if "❌" in e: st.error(e)
                    else: st.warning(e)
            else:
                st.success("✅ Aucun conflit de salle ou d'enseignant détecté.")

    elif portail == "📅 Surveillances Examens":
        FILE_S = "surveillances_2026.xlsx"
        if os.path.exists(FILE_S):
            df_surv = pd.read_excel(FILE_S)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
            
            for c in df_surv.columns: 
                df_surv[c] = df_surv[c].fillna("").astype(str).str.strip()
                
            c_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_surv.columns else 'Enseignants'
            all_profs = []
            for entry in df_surv[c_prof].unique():
                for p in entry.split('&'):
                    clean_p = p.strip()
                    if clean_p and clean_p not in ["nan", "Non défini"]:
                        all_profs.append(clean_p)
            
            liste_profs = sorted(list(set(all_profs)))
            u_nom = user['nom_officiel']
            idx_p = liste_profs.index(u_nom) if u_nom in liste_profs else 0
            
            prof_sel = st.selectbox("🔍 Sélectionner un surveillant :", liste_profs, index=idx_p)
            df_u_surv = df_surv[df_surv[c_prof].str.contains(prof_sel, case=False, na=False)].sort_values(by='Date_Tri')
            
            st.markdown(f"### 📊 État des lieux : {prof_sel}")
            c1, c2, c3 = st.columns(3)
            nb_mat = len(df_u_surv[df_u_surv['Heure'].str.contains("08h|09h|10h", case=False)])
            
            c1.metric("Total Séances", f"{len(df_u_surv)}")
            c2.metric("Matinée", nb_mat)
            c3.metric("Après-midi", len(df_u_surv) - nb_mat)
            
            st.divider()
            t1, t2 = st.tabs(["📋 Mes surveillances", "🌐 Planning Global"])
            
            with t1:
                if not df_u_surv.empty:
                    for _, r in df_u_surv.iterrows():
                        st.markdown(f"""
                        <div style="background:#f0f2f6;padding:15px;border-radius:10px;border-left:5px solid #1E3A8A;margin-bottom:10px;">
                            <span style="font-weight:bold;color:#1E3A8A;">📅 {r['Jour']} {r['Date']}</span> | 🕒 {r['Heure']}<br>
                            <b>📖 {r['Matière']}</b><br>
                            <small>📍 {r['Salle']} | 🎓 {r['Promotion']} | 👥 {r[c_prof]}</small>
                        </div>""", unsafe_allow_html=True)
                    
                    buf = io.BytesIO()
                    df_u_surv.drop(columns=['Date_Tri']).to_excel(buf, index=False)
                    st.download_button("📥 Télécharger mes surveillances", buf.getvalue(), f"Surv_{prof_sel}.xlsx")
                else:
                    st.info("Aucune séance de surveillance n'est enregistrée pour vous.")
            
            with t2:
                st.dataframe(df_surv.drop(columns=['Date_Tri']), use_container_width=True, hide_index=True)
        else:
            st.error("Fichier source 'surveillances_2026.xlsx' manquant.")

    elif portail == "🤖 Générateur Automatique":
        if not is_admin:
            st.error("Accès réservé au Bureau des Examens.")
        else:
            st.header("⚙️ Moteur de Génération de Surveillances")
            if "df_genere" not in st.session_state: st.session_state.df_genere = None
            if "stats_charge" not in st.session_state: st.session_state.stats_charge = {}
            
            SRC = "surveillances_2026.xlsx"
            if not os.path.exists(SRC):
                st.error("Impossible de générer : Fichier source introuvable.")
            else:
                df_src = pd.read_excel(SRC)
                df_src.columns = [str(c).strip() for c in df_src.columns]
                for c in df_src.columns: df_src[c] = df_src[c].fillna("").astype(str).str.strip()
                
                c_prof_g = 'Surveillant(s)' if 'Surveillant(s)' in df_src.columns else 'Enseignants'
                liste_p_gen = sorted([p for p in df_src[c_prof_g].unique() if p not in ["", "Non défini", "nan"]])
                promos = sorted(df_src['Promotion'].unique()) if 'Promotion' in df_src.columns else []

                with st.expander("⚖️ Paramètres de Distribution & Plafonnement", expanded=True):
                    cl1, cl2 = st.columns(2)
                    with cl1: exc_p = st.multiselect("👤 Personnels à quota réduit :", liste_p_gen)
                    with cl2: m_base = st.number_input("Quota Max de base (100%)", min_value=1, value=10)
                    
                    pct = st.slider("Réduction pour les enseignants sélectionnés (%)", 10, 100, 50)
                    quota_limite = int(m_base * (pct / 100))
                    st.warning(f"🎯 Limite appliquée aux enseignants sélectionnés : **{quota_limite} séances**.")

                cp1, cp2 = st.columns(2)
                with cp1: p_cible = st.multiselect("🎓 Promotions concernées :", promos)
                with cp2: d_exam = st.multiselect("📅 Filtrer par Dates :", sorted(df_src['Date'].unique()))

                if st.button("🚀 LANCER LA GÉNÉRATION DES BINÔMES"):
                    if not p_cible:
                        st.warning("Veuillez sélectionner au moins une promotion.")
                    else:
                        stats = {p: 0 for p in liste_p_gen}
                        tracker = []
                        res_list = []
                        
                        for p_name in p_cible:
                            df_p = df_src[df_src['Promotion'] == p_name].copy()
                            if d_exam: df_p = df_p[df_p['Date'].isin(d_exam)]
                            
                            for _, row in df_p.iterrows():
                                pair = []
                                tri_prio = sorted(liste_p_gen, key=lambda x: stats[x])
                                
                                for p in tri_prio:
                                    if len(pair) < 2:
                                        if p in exc_p and stats[p] >= quota_limite: continue
                                        conflit = any(t for t in tracker if t['D']==row['Date'] and t['H']==row['Heure'] and t['N']==p)
                                        if not conflit:
                                            pair.append(p)
                                            stats[p] += 1
                                            tracker.append({'D': row['Date'], 'H': row['Heure'], 'N': p})
                                            
                                res_list.append({
                                    "Promotion": p_name,
                                    "Date": row['Date'],
                                    "Heure": row['Heure'],
                                    "Matière": row['Matière'],
                                    "Salle": row['Salle'],
                                    "Binôme": " & ".join(pair) if len(pair)==2 else "⚠️ MANQUE"
                                })
                                
                        st.session_state.stats_charge = stats
                        st.session_state.df_genere = pd.DataFrame(res_list)
                        st.rerun()

                if st.session_state.df_genere is not None:
                    st.divider()
                    p_verif = st.selectbox("📊 Voir occupation :", sorted(st.session_state.stats_charge.keys()))
                    val_q = st.session_state.stats_charge[p_verif]
                    
                    v1, v2, v3 = st.columns(3)
                    with v1: st.metric(f"Total {p_verif}", f"{val_q} séances")
                    with v2: st.metric("Type de quota", "Limité" if p_verif in exc_p else "Standard")
                    with v3: 
                        occup = (val_q / quota_limite * 100) if p_verif in exc_p else (val_q / m_base * 100)
                        st.progress(min(int(occup), 100))

                    for p_title in p_cible:
                        st.write(f"### 📋 Planning : {p_title}")
                        disp = st.session_state.df_genere[st.session_state.df_genere['Promotion'] == p_title]
                        st.table(disp.drop(columns=['Promotion']))
                    
                    xlsx_buf = io.BytesIO()
                    with pd.ExcelWriter(xlsx_buf, engine='xlsxwriter') as writer:
                        st.session_state.df_genere.to_excel(writer, index=False)
                    st.download_button("📥 EXPORTER TOUT LE PLANNING (.XLSX)", xlsx_buf.getvalue(), "EDT_Examens_Complet.xlsx")

    elif portail == "👥 Portail Enseignants":
        # --- 🛡️ VERROU DE SÉCURITÉ ADMIN ---
        if not is_admin:
            st.error("🚫 ACCÈS RESTREINT : Seule l'administration peut accéder à l'envoi des EDTs.")
            st.stop()

        st.header("🏢 Répertoire et Envoi Automatisé des EDTs")

        # 1. RÉCUPÉRATION DES DONNÉES (SUPABASE + EXCEL)
        # On récupère l'email ET le témoin last_sent
        res_auth = supabase.table("enseignants_auth").select("nom_officiel, email, last_sent").execute()
        
        # Création du dictionnaire de suivi
        dict_info = {
            str(row['nom_officiel']).strip().upper(): {
                "email": row['email'], 
                "statut": "✅ Envoyé" if row['last_sent'] else "⏳ En attente"
            } for row in res_auth.data
        } if res_auth.data else {}

        # 2. CONSTRUCTION DU TABLEAU D'AFFICHAGE POUR L'ADMIN
        noms_excel = sorted([e for e in df['Enseignants'].unique() if str(e) not in ["Non défini", "nan", ""]])
        donnees_finales = []
        
        for nom in noms_excel:
            nom_nettoye = str(nom).strip().upper()
            info = dict_info.get(nom_nettoye, {"email": "⚠️ Non inscrit", "statut": "❌ Absent"})
            donnees_finales.append({
                "Enseignant": nom, 
                "Email": info["email"], 
                "État d'envoi": info["statut"]
            })
        
        df_portail = pd.DataFrame(donnees_finales)
        
        # Statistiques rapides
        c1, c2 = st.columns(2)
        c1.metric("Total Enseignants (Excel)", len(noms_excel))
        en_attente = sum(1 for d in donnees_finales if d["État d'envoi"] == "⏳ En attente")
        c2.metric("EDTs à envoyer (En attente)", en_attente)

        st.dataframe(df_portail, use_container_width=True, hide_index=True)

        # 3. ACTIONS : RÉINITIALISATION & ENVOI
        col_reset, col_mail = st.columns(2)

        with col_reset:
            if st.button("🔄 Réinitialiser tous les témoins", use_container_width=True):
                # Remet à zéro la colonne last_sent pour recommencer un envoi général
                supabase.table("enseignants_auth").update({"last_sent": None}).neq("email", "").execute()
                st.success("Prêt pour un nouvel envoi général ! Le statut est repassé en 'En attente'.")
                st.rerun()

        with col_mail:
            if st.button("🚀 Lancer l'envoi (Uniquement 'En attente')", use_container_width=True):
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart

                try:
                    # Connexion SMTP
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])

                    progress_bar = st.progress(0)
                    status_msg = st.empty()
                    success_count = 0

                    for i, row in enumerate(donnees_finales):
                        # FILTRE : On n'envoie que si le statut est "En attente"
                        if row["État d'envoi"] == "⏳ En attente" and "@" in row["Email"]:
                            nom_prof = row['Enseignant']
                            status_msg.text(f"Envoi en cours vers : {nom_prof}...")

                            # Préparation de l'EDT avec la DISPOSITION DEMANDÉE
                            df_perso = df[df["Enseignants"].str.contains(nom_prof, case=False, na=False)]
                            # Ordre : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
                            df_mail = df_perso[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']]

                            # Construction de l'Email
                            msg = MIMEMultipart()
                            msg['From'] = f"Département Électrotechnique <{st.secrets['EMAIL_USER']}>"
                            msg['To'] = row["Email"]
                            msg['Subject'] = f"Votre Emploi du Temps S2-2026 - {nom_prof}"

                            corps_html = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif;">
                                <h2>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h2>
                                <p>Bonjour M. <b>{nom_prof}</b>,</p>
                                <p>Voici votre emploi du temps personnalisé pour le second semestre 2026 :</p>
                                {df_mail.to_html(index=False, border=1, justify='center')}
                                <p><br>Cordialement,<br>L'Administration</p>
                            </body>
                            </html>
                            """
                            msg.attach(MIMEText(corps_html, 'html'))
                            server.send_message(msg)
                            
                            # MISE À JOUR SUPABASE : Marquer comme envoyé
                            supabase.table("enseignants_auth").update({"last_sent": "now()"}).eq("email", row["Email"]).execute()
                            success_count += 1

                        # Barre de progression
                        progress_bar.progress((i + 1) / len(donnees_finales))

                    server.quit()
                    st.success(f"✅ Mission accomplie ! {success_count} emails envoyés.")
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"Erreur lors de l'envoi : {e}")

    elif portail == "🎓 Portail Étudiants":
        st.header("📚 Espace Étudiants")
        p_etu = st.selectbox("Choisir votre Promotion :", sorted(df["Promotion"].unique()))
        st.success(f"Affichage de l'emploi du temps pour : **{p_etu}**")
        disp_etu = df[df["Promotion"] == p_etu][['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu']]
        st.table(disp_etu.sort_values(by=["Jours", "Horaire"]))

# --- FIN DU CODE ---











