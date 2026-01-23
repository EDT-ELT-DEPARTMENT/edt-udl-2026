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
    ], key="sidebar_navigation_unique_2026") # Ajout de la clé unique ici
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
            st.error("Le fichier 'surveillances_2026.xlsx' est absent.")

    # --- CET ALIGNEMENT EST CRUCIAL ---
    elif portail == "🤖 Générateur Automatique":
        if not is_admin:
            st.error("Accès réservé au Bureau des Examens.")
        else:
            st.header("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")
            st.subheader("⚙️ Moteur de Génération Automatique")
            # ... reste du code ...

            # --- 1. LECTURE DU FICHIER SOURCE ---
            FILE_SOURCE = "dataEDT-ELT-S2-2026.xlsx"
            
            if not os.path.exists(FILE_SOURCE):
                st.error(f"Fichier '{FILE_SOURCE}' introuvable.")
            else:
                df_source = pd.read_excel(FILE_SOURCE)
                df_source.columns = [str(c).strip() for c in df_source.columns]
                
                # FILTRAGE : Uniquement 'Cours' et une seule fois par binôme Prof/Matière
                df_unique = df_source[df_source["Enseignements"].str.contains("Cours", case=False, na=False)].copy()
                df_unique = df_unique.drop_duplicates(subset=["Enseignements", "Enseignants", "Promotion"])
                
                liste_profs_reels = sorted(df_unique["Enseignants"].dropna().unique().tolist())

                # --- 2. CONFIGURATION DES EFFECTIFS ---
                if "db_promos" not in st.session_state:
                    promos_fich = df_unique["Promotion"].unique()
                    st.session_state.db_promos = {p: [40, 1] for p in promos_fich}

                with st.expander("📦 Config Effectifs & Groupes", expanded=False):
                    data_prep = [{"Promotion": k, "Effectif": v[0], "Nb de Salles": v[1]} for k, v in st.session_state.db_promos.items()]
                    edited_df = st.data_editor(pd.DataFrame(data_prep), use_container_width=True, hide_index=True, key="editor_gen_auto")
                    
                    if st.button("💾 Sauvegarder Config", key="btn_save_gen_auto"):
                        st.session_state.db_promos = {r["Promotion"]: [r["Effectif"], r["Nb de Salles"]] for _, r in edited_df.iterrows()}
                        st.success("Configuration enregistrée.")

                # --- 3. PARAMÈTRES DE SURVEILLANCE ---
                with st.expander("⚖️ Plafonnement & Calendrier", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        date_debut = st.date_input("Début des examens", datetime(2026, 5, 17), key="date_gen_auto")
                        m_base = st.number_input("Max séances par prof", 1, 25, 10, key="max_s_gen_auto")
                    with c2:
                        ratio_etu = st.number_input("Ratio Étudiants/Surv.", 10, 50, 25, key="ratio_gen_auto")
                        exc_p = st.multiselect("👤 Profs Plafonnés :", liste_profs_reels, key="profs_excl_gen_auto")
                        reduc = st.slider("Réduction charge (%)", 10, 100, 50, key="slider_reduc_gen_auto")
                        quota_reduit = int(m_base * (reduc / 100))

                # --- 4. EXÉCUTION ---
                promos_cibles = st.multiselect("🎓 Choisir les promotions :", list(st.session_state.db_promos.keys()), key="select_target_gen_auto")

                if st.button("🚀 GÉNÉRER LE PLANNING", key="btn_run_gen_auto"):
                    if not promos_cibles:
                        st.warning("Sélectionnez au moins une promotion.")
                    else:
                        stats_charge = {p: 0 for p in liste_profs_reels}
                        resultats = []
                        collision_map = [] 
                        creneaux = ["08:30 - 10:30", "11:00 - 13:00", "13:30 - 15:30"]

                        for p_name in promos_cibles:
                            config = st.session_state.db_promos[p_name]
                            eff_total, nb_salles = config[0], config[1]
                            
                            cours_promo = df_unique[df_unique["Promotion"] == p_name].to_dict('records')
                            exam_date = date_debut
                            
                            for i, row in enumerate(cours_promo):
                                while exam_date.weekday() in [4, 5]: # Sauter vendredi et samedi
                                    exam_date += timedelta(days=1)
                                
                                horaire = creneaux[i % 3]
                                
                                for s_idx in range(1, nb_salles + 1):
                                    cap_salle = eff_total // nb_salles
                                    nb_req = max(2, (cap_salle // ratio_etu) + (1 if cap_salle % ratio_etu > 0 else 0))
                                    equipe = []
                                    profs_dispos = sorted(liste_profs_reels, key=lambda x: stats_charge[x])
                                    
                                    for p in profs_dispos:
                                        if len(equipe) < nb_req:
                                            limit = quota_reduit if p in exc_p else m_base
                                            if stats_charge[p] >= limit: continue
                                            if (exam_date, horaire, p) not in collision_map:
                                                equipe.append(p)
                                                stats_charge[p] += 1
                                                collision_map.append((exam_date, horaire, p))

                                    resultats.append({
                                        "Enseignements": row["Enseignements"],
                                        "Code": "S2-2026",
                                        "Enseignants": " & ".join(equipe) if len(equipe) >= 2 else "⚠️ BESOIN RENFORT",
                                        "Horaire": horaire,
                                        "Jours": exam_date.strftime("%A %d/%m/%Y"),
                                        "Lieu": f"Salle {s_idx} ({p_name})",
                                        "Promotion": p_name
                                    })
                                
                                if (i + 1) % 3 == 0:
                                    exam_date += timedelta(days=1)

                        st.session_state.df_genere = pd.DataFrame(resultats)
                        st.session_state.stats_charge = stats_charge
                        st.rerun()

                if st.session_state.get("df_genere") is not None:
                    st.divider()
                    st.dataframe(st.session_state.df_genere, use_container_width=True, hide_index=True)
                    xlsx_buf = io.BytesIO()
                    with pd.ExcelWriter(xlsx_buf, engine='xlsxwriter') as writer:
                        st.session_state.df_genere.to_excel(writer, index=False)
                    st.download_button("📥 TÉLÉCHARGER (.XLSX)", xlsx_buf.getvalue(), "Planning_S2_2026.xlsx")

    elif portail == "👥 Portail Enseignants":
        if not is_admin:
            st.error("🚫 ACCÈS RESTREINT : Seule l'administration peut accéder à l'envoi des EDTs.")
        else:
            st.header("🏢 Répertoire et Envoi Automatisé des EDTs")
            res_auth = supabase.table("enseignants_auth").select("nom_officiel, email, last_sent").execute()
            
            dict_info = {
                str(row['nom_officiel']).strip().upper(): {
                    "email": row['email'], 
                    "statut": "✅ Envoyé" if row['last_sent'] else "⏳ En attente"
                } for row in res_auth.data
            } if res_auth.data else {}

            noms_excel = sorted([e for e in df['Enseignants'].unique() if str(e) not in ["Non défini", "nan", ""]])
            donnees_finales = []
            for nom in noms_excel:
                nom_nettoye = str(nom).strip().upper()
                info = dict_info.get(nom_nettoye, {"email": "⚠️ Non inscrit", "statut": "❌ Absent"})
                donnees_finales.append({"Enseignant": nom, "Email": info["email"], "État d'envoi": info["statut"]})
            
            st.dataframe(pd.DataFrame(donnees_finales), use_container_width=True, hide_index=True)

            if st.button("🚀 Lancer l'envoi (Uniquement 'En attente')", use_container_width=True):
                # (Le code d'envoi SMTP reste le même, assurez-vous qu'il soit indenté ici)
                st.info("Traitement des emails...")

    elif portail == "🎓 Portail Étudiants":
        st.header("📚 Espace Étudiants")
        p_etu = st.selectbox("Choisir votre Promotion :", sorted(df["Promotion"].unique()))
        disp_etu = df[df["Promotion"] == p_etu][['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu']]
        st.table(disp_etu.sort_values(by=["Jours", "Horaire"]))

