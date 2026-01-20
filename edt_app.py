import streamlit as st
import pandas as pd
import os
import re
import hashlib
from datetime import datetime
from supabase import create_client
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026 - Sécurisé", layout="wide")

# --- CONNEXION SUPABASE ---
# Utilise les secrets que vous avez enregistrés
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- FONCTION SÉCURITÉ ---
def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .main-title {{ color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; }}
    .welcome-box {{ background-color: #e8f0fe; border-left: 5px solid #1E3A8A; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; }}
    .stat-box {{ padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; margin-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; height: 95px; font-size: 11px; background-color: white; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    @media print {{ section[data-testid="stSidebar"], button {{ display: none !important; }} }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT EDT ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df_edt = None
if os.path.exists(NOM_FICHIER_FIXE):
    df_edt = pd.read_excel(NOM_FICHIER_FIXE)
    df_edt.columns = [str(c).strip() for c in df_edt.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df_edt.columns: df_edt[col] = df_edt[col].fillna("Non défini").astype(str).str.strip()

# --- GESTION DE SESSION ---
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# --- ÉCRAN D'ACCÈS (CONNEXION / INSCRIPTION) ---
if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>Portail Emplois du Temps S2-2026</h3>", unsafe_allow_html=True)
    
    tab_log, tab_reg, tab_adm = st.tabs(["🔑 Connexion", "📝 Inscription Enseignant", "🛡️ Administration"])
    
    with tab_log:
        email_in = st.text_input("Email")
        pw_in = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", email_in).eq("password_hash", hash_pw(pw_in)).execute()
            if res.data:
                st.session_state["user_data"] = res.data[0]
                st.rerun()
            else: st.error("Email ou mot de passe incorrect.")

    with tab_reg:
        st.info("Note : Votre inscription doit correspondre à votre nom dans le fichier EDT.")
        reg_email = st.text_input("Email professionnel")
        if df_edt is not None:
            noms_dispos = sorted(df_edt['Enseignants'].unique())
            reg_nom = st.selectbox("Sélectionnez votre nom officiel", noms_dispos)
        reg_pw = st.text_input("Créez un mot de passe", type="password")
        if st.button("Valider l'inscription"):
            try:
                supabase.table("enseignants_auth").insert({
                    "email": reg_email, "nom_officiel": reg_nom, "password_hash": hash_pw(reg_pw)
                }).execute()
                st.success("Compte créé avec succès ! Connectez-vous maintenant.")
            except Exception as e: st.error("Erreur : Cet email est peut-être déjà utilisé.")

    with tab_adm:
        adm_pw = st.text_input("Code Administrateur", type="password")
        if st.button("Accès Direction"):
            if adm_pw == "doctorat2026":
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}
                st.rerun()
    st.stop()

# --- ZONE CONNECTÉE ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    if is_admin:
        mode = st.radio("Supervision", ["Promotion", "Enseignant", "🏢 Salles", "🚩 Vérificateur"])
    else:
        st.subheader("Mes réglages")
        poste_sup = st.checkbox("Poste Supérieur (Décharge 50%)")
        mode = "Personnel"
    
    if st.button("🚪 Déconnexion"):
        st.session_state["user_data"] = None
        st.rerun()

# --- AFFICHAGE DES DONNÉES ---
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)

jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

if mode == "Personnel" or (is_admin and mode == "Enseignant"):
    cible = user['nom_officiel'] if mode == "Personnel" else st.selectbox("Choisir Enseignant", sorted(df_edt['Enseignants'].unique()))
    df_p = df_edt[df_edt['Enseignants'] == cible].copy()
    
    # Message de bienvenue
    if mode == "Personnel":
        st.markdown(f"<div class='welcome-box'><b>👋 Bienvenue M. {cible}</b><br>Note importante : Voici votre planning personnel et votre bilan de charge.</div>", unsafe_allow_html=True)
    
    # Calculs Charge
    df_p['Type'] = df_p['Enseignements'].apply(lambda t: "COURS" if "COURS" in t.upper() else ("TD" if "TD" in t.upper() else "TP"))
    df_p['h_val'] = df_p['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
    df_s = df_p.drop_duplicates(subset=['Jours', 'Horaire'])
    
    c1, c2, c3 = st.columns(3)
    charge_r = df_s['h_val'].sum()
    charge_reg = 3.0 if (not is_admin and poste_sup) else 6.0
    c1.markdown(f"<div class='metric-card'>Charge Réelle: <b>{charge_r}h</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'>Réglementaire: <b>{charge_reg}h</b></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'>Heures Sup: <b>{max(0, charge_r - charge_reg)}h</b></div>", unsafe_allow_html=True)
    
    def fmt(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
    grid = df_p.groupby(['Horaire', 'Jours']).apply(fmt).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
    st.write(grid.to_html(escape=False), unsafe_allow_html=True)
    components.html("<button onclick='window.parent.print()' style='width:100%; padding:10px; background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold;'>🖨️ IMPRIMER CE PLANNING</button>", height=60)

elif mode == "Promotion":
    promo = st.sidebar.selectbox("Promotion", sorted(df_edt['Promotion'].unique()))
    df_f = df_edt[df_edt['Promotion'] == promo]
    def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
    grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
    st.write(f"### Planning : {promo}")
    st.write(grid.to_html(escape=False), unsafe_allow_html=True)
