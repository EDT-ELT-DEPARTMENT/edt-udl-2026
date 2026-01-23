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
                # On force l'email ici pour activer vos droits maître
                st.session_state["user_data"] = {
                    "nom_officiel": "ADMINISTRATEUR", 
                    "role": "admin",
                    "email": "milouafarid@gmail.com"  # <--- AJOUTER CETTE LIGNE
                }
                st.rerun()
            else:
                st.error("Code admin incorrect.")
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
                "🚩 Vérificateur de conflits"
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

        elif is_admin and mode_view == "🚩 Vérificateur de conflits":
            st.subheader("🚩 Analyse détaillée des Conflits et Collisions")
            st.markdown("---")
            
            errs_text = []      
            errs_for_df = []    
            
            # --- 1. ANALYSE DES ENSEIGNANTS (Double vs Conflit) ---
            p_groups = df[df["Enseignants"] != "Non défini"].groupby(['Jours', 'Horaire', 'Enseignants'])

            for (jour, horaire, prof), group in p_groups:
                if len(group) > 1:
                    lieux_uniques = group['Lieu'].unique()
                    matieres_uniques = group['Enseignements'].unique()
                    promos_uniques = group['Promotion'].unique()
                    
                    if len(lieux_uniques) == 1 and len(matieres_uniques) == 1:
                        type_err = "🔵 DOUBLE"
                        msg = f"**{type_err}** : {prof} | {jour} {horaire} | {matieres_uniques[0]} ({', '.join(promos_uniques)})"
                        errs_text.append(("info", msg))
                        detail = "Fusion Groupes/Promotions"
                    elif len(lieux_uniques) > 1:
                        type_err = "❌ CONFLIT LIEU"
                        msg = f"**{type_err}** : {prof} attendu dans plusieurs salles ({', '.join(lieux_uniques)}) à {horaire}"
                        errs_text.append(("error", msg))
                        detail = f"Salles différentes : {', '.join(lieux_uniques)}"
                    else:
                        type_err = "⚠️ CONFLIT MATIÈRE"
                        msg = f"**{type_err}** : {prof} a deux matières différentes ({', '.join(matieres_uniques)}) à {horaire}"
                        errs_text.append(("warning", msg))
                        detail = "Matières différentes (Même salle)"

                    errs_for_df.append({
                        "Type": type_err, "Enseignant": prof, "Jour": jour, "Horaire": horaire, 
                        "Détail": detail, "Lieu": ", ".join(lieux_uniques), 
                        "Matières": ", ".join(matieres_uniques), "Promotions": ", ".join(promos_uniques)
                    })

            # --- 2. ANALYSE DES SALLES (Collision de profs différents) ---
            s_groups = df[df["Lieu"] != "Non défini"].groupby(['Jours', 'Horaire', 'Lieu'])
            for (jour, horaire, salle), group in s_groups:
                profs_uniques = group['Enseignants'].unique()
                if len(profs_uniques) > 1:
                    type_err = "🚫 COLLISION SALLE"
                    mats = group['Enseignements'].unique()
                    proms = group['Promotion'].unique()
                    msg = f"**{type_err}** : Salle **{salle}** occupée par **{', '.join(profs_uniques)}** ({jour} à {horaire})"
                    errs_text.append(("error", msg))
                    errs_for_df.append({
                        "Type": type_err, "Enseignant": "/".join(profs_uniques), "Jour": jour, "Horaire": horaire, 
                        "Détail": f"Collision salle {salle}", "Lieu": salle, 
                        "Matières": ", ".join(mats), "Promotions": ", ".join(proms)
                    })

            # --- AFFICHAGE ET EXPORT ---
            if errs_text:
                for style, m in errs_text:
                    if style == "info": st.info(m)
                    elif style == "warning": st.warning(m)
                    else: st.error(m)
                
                st.divider()
                # Création du DataFrame pour l'impression
                df_report = pd.DataFrame(errs_for_df)
                
                # Optionnel : Afficher le tableau récapitulatif avant impression
                with st.expander("👁️ Voir le tableau récapitulatif des erreurs"):
                    st.dataframe(df_report, use_container_width=True)

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                    df_report.to_excel(writer, index=False, sheet_name='Anomalies_EDT')
                
                st.download_button(
                    label="📥 Imprimer le Rapport Complet (Matières & Promos inclues)",
                    data=buf.getvalue(),
                    file_name="Rapport_Conflits_Detaillé_ELT.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.success("✅ Aucun conflit détecté dans l'emploi du temps.")
    elif portail == "📅 Surveillances Examens":
        FILE_S = "surveillances_2026.xlsx"
        if os.path.exists(FILE_S):
            df_surv = pd.read_excel(FILE_S)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
            
            for c in df_surv.columns: 
                df_surv[c] = df_surv[c].fillna("").astype(str).str.strip()
                
            c_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_surv.columns else 'Enseignants'
            u_nom = user['nom_officiel']
            u_email = user.get('email', '').lower().strip()

            # --- DÉTECTION DU SUPER-ADMIN ---
            is_master_admin = (u_email == "milouafarid@gmail.com")

            if is_master_admin:
                # On extrait tous les noms d'enseignants du fichier Excel
                tous_les_profs = []
                for entry in df_surv[c_prof].unique():
                    for p in entry.split('&'):
                        clean_p = p.strip()
                        if clean_p and clean_p not in ["nan", "Non défini", ""]:
                            tous_les_profs.append(clean_p)
                liste_profs = sorted(list(set(tous_les_profs)))
                
                st.success("🔓 Accès Maître : milouafarid@gmail.com")
                # L'admin peut choisir n'importe quel nom de la liste
                prof_sel = st.selectbox("🔍 Choisir un enseignant pour voir son planning :", liste_profs)
            else:
                # Un enseignant normal est limité à son nom
                prof_sel = u_nom
                st.info(f"👤 Espace Personnel : **{u_nom}**")

            # Filtrage final
            df_u_surv = df_surv[df_surv[c_prof].str.contains(prof_sel, case=False, na=False)].sort_values(by='Date_Tri')
            
            st.markdown(f"### 📋 Planning de : {prof_sel}")
            
            # Statistiques
            c1, c2, c3 = st.columns(3)
            nb_mat = len(df_u_surv[df_u_surv['Heure'].str.contains("08h|09h|10h", case=False)])
            c1.metric("Séances Total", len(df_u_surv))
            c2.metric("Matin", nb_mat)
            c3.metric("Après-midi", len(df_u_surv) - nb_mat)
            
            st.divider()

            if not df_u_surv.empty:
                for _, r in df_u_surv.iterrows():
                    st.markdown(f"""
                    <div style="background:#f9f9f9;padding:12px;border-radius:8px;border-left:5px solid #1E3A8A;margin-bottom:8px;box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                        <span style="font-weight:bold;color:#1E3A8A;">📅 {r['Jour']} {r['Date']}</span> | 🕒 {r['Heure']}<br>
                        <b>📖 {r['Matière']}</b><br>
                        <small>📍 {r['Salle']} | 🎓 {r['Promotion']} | 👥 {r[c_prof]}</small>
                    </div>""", unsafe_allow_html=True)
                
                buf = io.BytesIO()
                df_u_surv.drop(columns=['Date_Tri']).to_excel(buf, index=False)
                st.download_button(f"📥 Télécharger l'EDT de {prof_sel}", buf.getvalue(), f"Surv_{prof_sel}.xlsx")
            else:
                st.warning(f"⚠️ Aucune surveillance trouvée dans le fichier Excel pour : {prof_sel}")
        else:
            st.error("Le fichier 'surveillances_2026.xlsx' est absent.")
    elif portail == "🤖 Générateur Automatique":
            if not is_admin:
                st.error("Accès réservé au Bureau des Examens.")
            else:
                st.header("⚙️ Moteur de Génération de Surveillances")
                
                # 1. BASE DE DONNÉES DES EFFECTIFS RÉELS
                EFFECTIFS_PROMOS = {
                    "L1MCIL": 288, "L2MCIL": 109, "L2ELT": 90, "L3ELT": 70, 
                    "ING1": 50, "ING3EI": 40, "M1MCIL": 34, "MCIL3": 23, 
                    "ING2": 16, "ING3RSE": 16, "M1ER": 16, "M1RE": 15, 
                    "M1ME": 15, "ING4": 15
                }

                if "df_genere" not in st.session_state: st.session_state.df_genere = None
                if "stats_charge" not in st.session_state: st.session_state.stats_charge = {}
                
                SRC = "surveillances_2026.xlsx"
                if not os.path.exists(SRC):
                    st.error("Fichier 'surveillances_2026.xlsx' introuvable.")
                else:
                    df_src = pd.read_excel(SRC)
                    df_src.columns = [str(c).strip() for c in df_src.columns]
                    for c in df_src.columns: df_src[c] = df_src[c].fillna("").astype(str).str.strip()
                    
                    c_prof_g = 'Surveillant(s)' if 'Surveillant(s)' in df_src.columns else 'Enseignants'
                    liste_p_gen = sorted([p for p in df_src[c_prof_g].unique() if p not in ["", "Non défini", "nan"]])
                    promos_dispo = sorted(df_src['Promotion'].unique())

                    # --- INTERFACE DE CONFIGURATION ---
                    with st.expander("📏 Configuration des Capacités & Groupes", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        with col1: r_salle = st.number_input("Ratio SALLE :", min_value=1, value=25)
                        with col2: r_amphi = st.number_input("Ratio AMPHI :", min_value=1, value=40)
                        with col3: nb_groupes = st.number_input("Nb de Salles/Groupes :", min_value=1, value=1)

                    with st.expander("⚖️ Gestion des Plafonds & Urgence", expanded=True):
                        cl1, cl2, cl3 = st.columns(3)
                        with cl1: exc_p = st.multiselect("👤 Enseignants réduits :", liste_p_gen)
                        with cl2: m_base = st.number_input("Plafond Standard", min_value=1, value=10)
                        with cl3: tolerance = st.number_input("Dépassement d'urgence (+x)", min_value=0, value=2)
                        
                        pct = st.slider("Taux de réduction pour les sélectionnés (%)", 10, 100, 50)
                        quota_limite = int(m_base * (pct / 100))
                        st.info(f"Plafond Réduit : {quota_limite} | Plafond Standard : {m_base} | Max Urgence : {m_base + tolerance}")

                    cp1, cp2 = st.columns(2)
                    with cp1: p_cible = st.multiselect("🎓 Promotions concernées :", promos_dispo)
                    with cp2: d_exam = st.multiselect("📅 Filtrer par Dates :", sorted(df_src['Date'].unique()))

                    # --- LOGIQUE DE GÉNÉRATION ---
                    if st.button("🚀 LANCER LA GÉNÉRATION"):
                        if not p_cible:
                            st.warning("Sélectionnez au moins une promotion.")
                        else:
                            stats = {p: 0 for p in liste_p_gen}
                            tracker = [] 
                            res_list = []
                            
                            for p_name in p_cible:
                                df_p = df_src[df_src['Promotion'] == p_name].copy()
                                if d_exam: df_p = df_p[df_p['Date'].isin(d_exam)]
                                eff_total = EFFECTIFS_PROMOS.get(p_name, 30)
                                
                                for _, row in df_p.iterrows():
                                    for g_idx in range(1, int(nb_groupes) + 1):
                                        lieu = row['Salle'].upper()
                                        est_amphi = any(k in lieu for k in ["AMPHI", "A-", "AMPHITHÉÂTRE"])
                                        ratio = r_amphi if est_amphi else r_salle
                                        
                                        eff_salle = eff_total // nb_groupes
                                        nb_requis = max(2, (eff_salle // ratio) + (1 if eff_salle % ratio > 0 else 0))
                                        
                                        equipe = []
                                        # Tri par charge actuelle (Priorité aux moins occupés)
                                        tri_prio = sorted(liste_p_gen, key=lambda x: stats[x])
                                        
                                        for p in tri_prio:
                                            if len(equipe) < nb_requis:
                                                # 1. Vérification Anti-Conflit
                                                conflit = any(t for t in tracker if t['D']==row['Date'] and t['H']==row['Heure'] and t['N']==p)
                                                if conflit: continue

                                                # 2. Vérification des Plafonds avec Tolérance d'urgence
                                                limit = (quota_limite + tolerance) if p in exc_p else (m_base + tolerance)
                                                if stats[p] >= limit:
                                                    continue
                                                
                                                equipe.append(p)
                                                stats[p] += 1
                                                tracker.append({'D': row['Date'], 'H': row['Heure'], 'N': p})
                                        
                                        nom_final = f"{p_name} (G{g_idx})" if nb_groupes > 1 else p_name
                                        res_list.append({
                                            "Promotion": nom_final, "Lieu": lieu, "Effectif": eff_salle,
                                            "Date": row['Date'], "Heure": row['Heure'], "Matière": row['Matière'],
                                            "Surveillants": " & ".join(equipe) if len(equipe) >= 2 else "⚠️ MANQUE PERSONNEL"
                                        })
                            
                            st.session_state.stats_charge = stats
                            st.session_state.df_genere = pd.DataFrame(res_list)
                            st.rerun()

                    # --- AFFICHAGE ET EXPORT ---
                    if st.session_state.df_genere is not None:
                        st.divider()
                        st.subheader("📊 État des Plafonds après Génération")
                        p_check = st.selectbox("Vérifier un enseignant :", liste_p_gen)
                        c_actuelle = st.session_state.stats_charge[p_check]
                        c_max = (quota_limite + tolerance) if p_check in exc_p else (m_base + tolerance)
                        st.progress(min(c_actuelle / c_max, 1.0))
                        st.write(f"Charge : {c_actuelle} / {c_max} (Tolérance incluse)")

                        st.dataframe(st.session_state.df_genere, use_container_width=True)
                        
                        xlsx_buf = io.BytesIO()
                        with pd.ExcelWriter(xlsx_buf, engine='xlsxwriter') as writer:
                            st.session_state.df_genere.to_excel(writer, index=False)
                        st.download_button("📥 EXPORTER LE PLANNING", xlsx_buf.getvalue(), "Planning_Surveillances_2026.xlsx")
                    elif portail == "👥 Portail Enseignants":
            # --- 🛡️ VERROU DE SÉCURITÉ ADMIN (Indentation 12 espaces) ---
            if not is_admin:
                # (Indentation 16 espaces)
                st.error("🚫 ACCÈS RESTREINT : Seule l'administration peut accéder à l'envoi des EDTs.")
                st.stop()

            st.header("🏢 Répertoire et Envoi Automatisé des EDTs")

            # 1. RÉCUPÉRATION DES DONNÉES (SUPABASE + EXCEL)
            res_auth = supabase.table("enseignants_auth").select("nom_officiel, email, last_sent").execute()
            
            dict_info = {
                str(row['nom_officiel']).strip().upper(): {
                    "email": row['email'], 
                    "statut": "✅ Envoyé" if row['last_sent'] else "⏳ En attente"
                } for row in res_auth.data
            } if res_auth.data else {}

            # 2. CONSTRUCTION DU TABLEAU D'AFFICHAGE
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
            
            c1, c2 = st.columns(2)
            c1.metric("Total Enseignants (Excel)", len(noms_excel))
            en_attente = sum(1 for d in donnees_finales if d["État d'envoi"] == "⏳ En attente")
            c2.metric("EDTs à envoyer", en_attente)

            st.dataframe(df_portail, use_container_width=True, hide_index=True)

            # 3. ACTIONS : RÉINITIALISATION & ENVOI
            col_reset, col_mail = st.columns(2)

            with col_reset:
                if st.button("🔄 Réinitialiser tous les témoins", use_container_width=True):
                    supabase.table("enseignants_auth").update({"last_sent": None}).neq("email", "").execute()
                    st.success("Statuts réinitialisés !")
                    st.rerun()

            with col_mail:
                if st.button("🚀 Lancer l'envoi (Uniquement 'En attente')", use_container_width=True):
                    import smtplib
                    from email.mime.text import MIMEText
                    from email.mime.multipart import MIMEMultipart

                    try:
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])

                        progress_bar = st.progress(0)
                        status_msg = st.empty()
                        success_count = 0

                        for i, row in enumerate(donnees_finales):
                            if row["État d'envoi"] == "⏳ En attente" and "@" in row["Email"]:
                                nom_prof = row['Enseignant']
                                status_msg.text(f"Envoi vers : {nom_prof}...")

                                # Filtrage selon la DISPOSITION DEMANDÉE
                                df_perso = df[df["Enseignants"].str.contains(nom_prof, case=False, na=False)]
                                cols_ordre = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
                                df_mail = df_perso[cols_ordre]

                                # Construction de l'Email
                                msg = MIMEMultipart()
                                msg['From'] = f"Département Électrotechnique <{st.secrets['EMAIL_USER']}>"
                                msg['To'] = row["Email"]
                                msg['Subject'] = f"Votre Emploi du Temps S2-2026 - {nom_prof}"

                                corps_html = f"""
                                <html>
                                <body style="font-family: Arial, sans-serif;">
                                    <h3>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h3>
                                    <p>Bonjour M. <b>{nom_prof}</b>,</p>
                                    <p>Voici votre emploi du temps personnalisé pour le second semestre 2026 :</p>
                                    {df_mail.to_html(index=False, border=1, justify='center')}
                                    <p><br>Cordialement,<br>L'Administration</p>
                                </body>
                                </html>
                                """
                                msg.attach(MIMEText(corps_html, 'html'))
                                server.send_message(msg)
                                
                                # Marquer comme envoyé
                                supabase.table("enseignants_auth").update({"last_sent": "now()"}).eq("email", row["Email"]).execute()
                                success_count += 1

                            progress_bar.progress((i + 1) / len(donnees_finales))

                        server.quit()
                        st.success(f"✅ {success_count} emails envoyés avec succès.")
                        st.balloons()
                        st.rerun()

                    except Exception as e:
                        st.error(f"Erreur SMTP : {e}")

        elif portail == "🎓 Portail Étudiants":
            st.header("📚 Espace Étudiants")
            p_etu = st.selectbox("Choisir votre Promotion :", sorted(df["Promotion"].unique()))
            st.info(f"Emploi du temps : **{p_etu}**")
            
            # Disposition demandée : Enseignements, Code, Enseignants, Horaire, Jours, Lieu
            disp_etu = df[df["Promotion"] == p_etu][['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu']]
            st.table(disp_etu.sort_values(by=["Jours", "Horaire"]))
