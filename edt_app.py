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
    for col in ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']:
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
            if res.data: 
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Identifiants incorrects.")
    
    with tab_ins:
        st.subheader("📝 Créer votre compte Enseignant")
        new_em = st.text_input("Email (Identifiant Unique)")
        liste_noms_edt = sorted(df["Enseignants"].unique()) if df is not None else []
        new_nom = st.selectbox("Sélectionnez votre nom dans l'EDT :", liste_noms_edt)
        c1, c2 = st.columns(2)
        with c1: new_statut = st.selectbox("Votre Statut :", ["Permanent", "Vacataire"])
        with c2: new_grade = st.selectbox("Votre Grade :", ["Professeur", "MCA", "MCB", "MAA", "MAB", "Doctorant"])
        new_ps = st.text_input("Définir un mot de passe", type="password", key="reg_ps")
        if st.button("Confirmer l'inscription"):
            data_ins = {"email": new_em, "nom_officiel": new_nom, "password_hash": hash_pw(new_ps), "statut_prof": new_statut, "grade_prof": new_grade, "role": "user"}
            try:
                supabase.table("enseignants_auth").insert(data_ins).execute()
                st.success(f"Compte créé pour {new_nom} !")
            except Exception: st.error("Erreur lors de l'inscription.")

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
    options_menu = ["📖 Emploi du Temps", "📅 Surveillances Examens", "🤖 Générateur Automatique"]
    if is_admin: options_menu.extend(["👥 Enseignants Permanents", "📝 Enseignants Vacataires"])
    portail = st.selectbox("🚀 Espace", options_menu)
    st.divider()
    mode_view = "Personnel"
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge)")
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None
        st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    if portail == "📖 Emploi du Temps":
        # --- PLANNING SALLES ---
        if mode_view == "🏢 Planning Salles":
            salle_sel = st.selectbox("Choisir une salle :", sorted(df["Lieu"].unique()))
            df_salle = df[df["Lieu"] == salle_sel]
            def fmt_s(rows):
                is_err = len(rows) > 1
                bg = "background-color: #ffcccc;" if is_err else ""
                items = [f"<b>{r['Enseignants']}</b><br>{r['Enseignements']}<br>({r['Promotion']})" for _, r in rows.iterrows()]
                return f"<div style='{bg} padding:5px;'>{'<div class=separator></div>'.join(items)}</div>"
            grid_s = df_salle.groupby(['h_norm', 'j_norm']).apply(fmt_s, include_groups=False).unstack('j_norm')
            grid_s = grid_s.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
            grid_s.index = horaires_list; grid_s.columns = jours_list
            st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)

        # --- VÉRIFICATEUR ---
        elif mode_view == "🚩 Vérificateur":
            conf = []
            for (j, h, l), g in df.groupby(['Jours', 'Horaire', 'Lieu']):
                if len(g) > 1 and l != "Non défini": conf.append({"Type": "SALLE", "Détail": l, "Moment": f"{j} {h}", "Profs": ", ".join(g['Enseignants'].unique())})
            for (j, h, p), g in df.groupby(['Jours', 'Horaire', 'Enseignants']):
                if len(g) > 1 and p != "Non défini": conf.append({"Type": "ENSEIGNANT", "Détail": p, "Moment": f"{j} {h}", "Cours": ", ".join(g['Enseignements'].unique())})
            if conf: st.warning(f"{len(conf)} Conflits trouvés"); st.table(pd.DataFrame(conf))
            else: st.success("Aucun conflit détecté.")

        # --- VUE INDIVIDUELLE / PROMO ---
        elif mode_view in ["Personnel", "Enseignant", "Promotion"]:
            # (Ici votre code de génération de grille existant que vous avez déjà)
            st.info("Sélectionnez les critères dans la barre latérale pour afficher la grille.")

    # ================= PORTAIL 4 & 5 (SOURCE EXCEL) =================
    elif portail == "👥 Enseignants Permanents":
        st.header("🏢 Liste des Enseignants du Département")
        profs = sorted(df["Enseignants"].unique())
        st.dataframe(pd.DataFrame({"Nom": profs}), use_container_width=True, hide_index=True)

    elif portail == "📝 Enseignants Vacataires":
        st.header("📋 Affectations des Enseignants")
        # Disposition : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
        df_aff = df[['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']].drop_duplicates()
        st.dataframe(df_aff.sort_values(by="Enseignants"), use_container_width=True, hide_index=True)
