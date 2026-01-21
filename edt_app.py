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
    .stat-box {{ 
        flex: 1; padding: 15px; border-radius: 12px; color: white; 
        font-weight: bold; text-align: center; font-size: 16px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }}
    .bg-cours {{ background: linear-gradient(135deg, #1E3A8A, #3B82F6); }}
    .bg-td {{ background: linear-gradient(135deg, #15803d, #22c55e); }}
    .bg-tp {{ background: linear-gradient(135deg, #b45309, #f59e0b); }}
    
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 8px; text-align: center; font-size: 12px; }}
    td {{ border: 1px solid #000; padding: 6px !important; text-align: center; background-color: white; font-size: 12px; }}
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

# --- INITIALISATION ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h", "14h - 15h30", "15h30 - 17h"]

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "📅 Surveillances Examens", "🤖 Générateur Automatique"])
    st.divider()
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

# ================= PORTAIL 1 : EMPLOI DU TEMPS =================
if portail == "📖 Emploi du Temps":
    if df is not None:
        cible = user['nom_officiel'] if not is_admin else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
        df_f = df[df["Enseignants"].str.contains(cible, case=False, na=False)].copy()
        
        if not df_f.empty:
            cols_dispo = ["Enseignements", "Code", "Enseignants", "Horaire", "Jours", "Lieu", "Promotion"]
            st.table(df_f[cols_dispo])
        else:
            st.warning("Aucun cours trouvé.")

# ================= PORTAIL 2 : SURVEILLANCES INDIVIDUELLES =================
elif portail == "📅 Surveillances Examens":
    st.subheader(f"📋 Mes Surveillances - {user['nom_officiel']}")
    if 'resultats_gen' in st.session_state:
        df_res = st.session_state['resultats_gen']
        # Recherche si le nom de l'utilisateur est dans la colonne Enseignants (qui contient le binôme)
        ma_surv = df_res[df_res["Enseignants"].str.contains(user['nom_officiel'], case=False, na=False)]
        if not ma_surv.empty:
            st.table(ma_surv)
        else:
            st.info("Aucune surveillance ne vous a été attribuée par l'algorithme.")
    else:
        st.warning("Le planning des surveillances n'a pas encore été généré par l'administrateur.")

# ================= PORTAIL 3 : GÉNÉRATEUR AUTOMATIQUE (ADMIN) =================
elif portail == "🤖 Générateur Automatique":
    if not is_admin:
        st.error("Accès réservé à l'administration.")
    else:
        st.header("⚙️ Générateur de Surveillances par Promotion")
        NOM_SURV_SRC = "surveillances_2026.xlsx"

        if not os.path.exists(NOM_SURV_SRC):
            st.error(f"❌ Le fichier '{NOM_SURV_SRC}' est introuvable.")
        else:
            df_src = pd.read_excel(NOM_SURV_SRC)
            df_src.columns = [str(c).strip() for c in df_src.columns]
            for c in df_src.columns: df_src[c] = df_src[c].fillna("").astype(str).str.strip()

            liste_profs_surv = sorted([p for p in df_src['Surveillant(s)'].unique() if p not in ["", "nan"]])
            
            st.subheader("📋 Configuration")
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                profs_decharge = st.multiselect("👤 Décharges (50%) :", liste_profs_surv)
            with col_cfg2:
                vacataires = st.multiselect("🎓 Vacataires :", liste_profs_surv)
            
            coef_decharge = st.slider("Coefficient d'allègement", 0.1, 0.9, 0.5)
            promo_cible = st.multiselect("🎓 Promotions :", sorted(df_src['Promotion'].unique()))

            if st.button("🚀 GÉNÉRER LA RÉPARTITION ÉQUITABLE"):
                if not promo_cible:
                    st.warning("Sélectionnez au moins une promotion.")
                else:
                    stats_charge = {p: 0 for p in liste_profs_surv}
                    global_tracking = []
                    all_final_data = []

                    for promo in promo_cible:
                        df_p = df_src[df_src['Promotion'] == promo].copy()
                        for _, row in df_p.iterrows():
                            binome = []
                            for _ in range(2):
                                # Tri par charge pondérée (Equité)
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
                            
                            # DISPOSITION : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
                            all_final_data.append({
                                "Enseignements": row.get('Matière', ''),
                                "Code": row.get('N°', ''),
                                "Enseignants": " & ".join(binome),
                                "Horaire": row.get('Heure', ''),
                                "Jours": row.get('Jour', ''),
                                "Lieu": row.get('Salle', ''),
                                "Promotion": promo
                            })

                    st.session_state['resultats_gen'] = pd.DataFrame(all_final_data)
                    st.session_state['stats_gen'] = stats_charge
                    st.success("Génération terminée !")

            if 'resultats_gen' in st.session_state:
                st.table(st.session_state['resultats_gen'])
                
                # Téléchargement
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    st.session_state['resultats_gen'].to_excel(writer, index=False)
                st.download_button("📥 Télécharger le Planning", output.getvalue(), "Planning_2026.xlsx")
