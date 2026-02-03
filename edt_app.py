import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
from supabase import create_client
import io

# ============================================================
# 0️⃣ CONFIGURATION DE LA PAGE
# ============================================================
st.set_page_config(
    page_title="EDT UDL 2026",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 1️⃣ CONNEXION À SUPABASE
# ============================================================
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# ============================================================
# 2️⃣ GESTION DU TEMPS
# ============================================================
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
jours_semaine = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
nom_jour_fr = jours_semaine[now.weekday()]

# ============================================================
# 3️⃣ STYLE CSS
# ============================================================
st.markdown("""
<style>
.main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px; }
.portal-badge { background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }
.date-badge { background-color: #1E3A8A; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; float: right; }
.metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }
.stat-container { display: flex; justify-content: space-around; margin: 20px 0; gap: 10px; }
.stat-box { flex: 1; padding: 15px; border-radius: 12px; color: white; font-weight: bold; text-align: center; font-size: 16px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
.bg-cours { background: linear-gradient(135deg, #1E3A8A, #3B82F6); }
.bg-td { background: linear-gradient(135deg, #15803d, #22c55e); }
.bg-tp { background: linear-gradient(135deg, #b45309, #f59e0b); }
table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }
td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }
.separator { border-top: 1px dashed #bbb; margin: 4px 0; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 4️⃣ CHARGEMENT DES DONNÉES
# ============================================================
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
    colonnes_cles = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
    for col in colonnes_cles:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()
        else:
            df[col] = "Non défini"
    df['h_norm'] = df['Horaire'].apply(normalize)
    df['j_norm'] = df['Jours'].apply(normalize)

# ============================================================
# 5️⃣ AUTHENTIFICATION UTILISATEUR
# ============================================================
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    t_conn, t_ins, t_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    
    with t_conn:
        email_input = st.text_input("Adresse Email", key="login_email")
        pass_input = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter au portail", use_container_width=True):
            result = supabase.table("enseignants_auth").select("*").eq("email", email_input).eq("password_hash", hash_pw(pass_input)).execute()
            if result.data:
                st.session_state["user_data"] = result.data[0]
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect.")
                
    with t_ins:
        st.subheader("📝 Créer un nouveau compte Enseignant")
        noms_possibles = sorted(df["Enseignants"].unique()) if df is not None else []
        new_nom = st.selectbox("Sélectionnez votre nom (tel qu'il apparaît dans l'EDT)", noms_possibles)
        new_email = st.text_input("Votre adresse Email")
        new_pass = st.text_input("Choisissez un mot de passe", type="password")
        confirm_pass = st.text_input("Confirmez le mot de passe", type="password")
        
        if st.button("Créer mon compte", use_container_width=True):
            if not new_email or not new_pass:
                st.warning("Veuillez remplir tous les champs.")
            elif new_pass != confirm_pass:
                st.error("Les mots de passe ne correspondent pas.")
            else:
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
                    st.success("✅ Compte créé avec succès ! Connectez-vous maintenant.")
                    st.balloons()

    with t_adm:
        code_admin = st.text_input("Code de sécurité Administration", type="password", key="admin_code")
        if st.button("Accès Administration", use_container_width=True):
            if code_admin == "doctorat2026":
                st.session_state["user_data"] = {"nom_officiel": "ADMINISTRATEUR", "role": "admin", "email": "admin@udl.edu"}
                st.rerun()
            else:
                st.error("Code admin incorrect.")

# ============================================================
# 6️⃣ GARDIEN DE SESSION
# ============================================================
user = st.session_state.get("user_data")
if user is None:
    st.stop()

is_admin = user.get("role") == "admin"

# ============================================================
# 7️⃣ BARRE LATÉRALE
# ============================================================
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]
map_h = {normalize(h): h for h in horaires_list}
map_j = {normalize(j): j for j in jours_list}

with st.sidebar:
    st.header(f"👤 {user.get('nom_officiel', 'Utilisateur')}")
    portail = st.selectbox("🚀 Sélectionner Espace", ["📖 Emploi du Temps", "📅 Surveillances Examens", "🤖 Générateur Automatique", "👥 Portail Enseignants", "🎓 Portail Étudiants"])
    st.divider()
    mode_view = "Personnel"
    poste_sup = False

    if portail == "📖 Emploi du Temps":
        if is_admin:
            mode_view = st.radio("Vue Administration :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur de conflits", "✍️ Éditeur de données"])
        else:
            mode_view = "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge 3h)")

    if st.button("🚪 Déconnexion du compte"):
        st.session_state["user_data"] = None
        st.rerun()

# ============================================================
# 8️⃣ LOGIQUE PRINCIPALE : EMPLOI DU TEMPS / ADMIN
# ============================================================

# === Bloc Enseignant / Personnel ===
if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
    cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Sélectionner l'Enseignant :", sorted(df["Enseignants"].unique()))
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
    charge_reelle = df_u['h_val'].sum()
    charge_reg = 3.0 if poste_sup else 6.0
    h_sup = charge_reelle - charge_reg
    color_sup = "#e74c3c" if h_sup > 0 else "#27ae60"

# ============================================================
# 9️⃣ ONGLETS EMPLOI DU TEMPS / T6
# ============================================================
tab_view, tab_t6 = st.tabs(["📅 Mon Emploi du Temps", "📝 Suivi de Séance (T6)"])

with tab_view:
    st.markdown(f"### 📊 Bilan Horaire : {cible}")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup.<br><h2 style='color:{color_sup};'>{h_sup} h</h2></div>", unsafe_allow_html=True)

    def format_case(rows):
        return "<div class='separator'></div>".join(
            f"<b>{get_nature(r['Code'])} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>"
            for _, r in rows.iterrows()
        )

    if not df_f.empty:
        grid = df_f.groupby(['h_norm', 'j_norm']).apply(format_case, include_groups=False).unstack('j_norm')
        grid = grid.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
        grid.index = [map_h.get(i, i) for i in grid.index]
        grid.columns = [map_j.get(c, c) for c in grid.columns]
        st.write(grid.to_html(escape=False), unsafe_allow_html=True)

with tab_t6:
    st.subheader("📝 Registre Numérique de Séance (T6)")
    st.info(f"Enseignant : **{cible}** | S2-2026")
    pwd_t6 = st.text_input("🔑 Code Session :", type="password", key="secu_t6")
    if pwd_t6 == "2026":
        if not df_f.empty:
            mat_t6 = st.selectbox("📚 Séance de :", sorted(df_f["Enseignements"].unique()))
            promo_t6 = df_f[df_f["Enseignements"] == mat_t6]["Promotion"].iloc[0]
            if st.button("🚀 Valider la séance (Supabase)", use_container_width=True):
                try:
                    supabase.table("rapports_assiduite").insert({"expediteur": cible, "promotion": promo_t6, "matiere": mat_t6}).execute()
                    st.success("✅ Séance enregistrée !")
                except Exception as e:
                    st.error(f"Erreur : {e}")
        else:
            st.warning("Aucune donnée disponible pour cet enseignant.")
    else:
        st.warning("Veuillez saisir le code '2026'.")

# ============================================================
# 🔟 VUE ADMIN : PROMOTION
# ============================================================
if is_admin and mode_view == "Promotion":
    st.subheader("📋 Vue par Promotion")
    promos_dispo = sorted(df["Promotion"].unique())
    p_sel = st.selectbox("Choisir Promotion :", promos_dispo)
    df_p = df[df["Promotion"] == p_sel]

    def fmt_p(rows):
        return "<div class='separator'></div>".join(
            f"<b>{'📘 COURS' if 'COURS' in str(r['Code']).upper() else '📗 TD' if 'TD' in str(r['Code']).upper() else '📙 TP'} : {r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>"
            for _, r in rows.iterrows()
        )

    if not df_p.empty:
        grid_p = df_p.groupby(['h_norm', 'j_norm']).apply(fmt_p, include_groups=False).unstack('j_norm')
        grid_p = grid_p.reindex(index=[normalize(h) for h in horaires_list], columns=[normalize(j) for j in jours_list]).fillna("")
        grid_p.index = horaires_list
        grid_p.columns = jours_list
        st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)
