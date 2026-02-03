import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
# Assurez-vous que supabase est installé et configuré
# from supabase import create_client

NOM_FICHIER_FIXE = "EDT_S2_2026.xlsx"

# --- CHARGEMENT DE DONNÉES ---
if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
else:
    df = pd.DataFrame(columns=['Enseignements','Code','Enseignants','Horaire','Jours','Lieu','Promotion','Chevauchement'])

# --- VARIABLES GÉNÉRALES ---
jours_std = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
liste_horaires = ["08h-09h","09h-10h","10h-11h","11h-12h","12h-13h","13h-14h","14h-15h","15h-16h","16h-17h"]
promos_existantes = df['Promotion'].dropna().unique().tolist() if not df.empty else ["M2RE"]
date_str = datetime.now().strftime("%d/%m/%Y")
nom_jour_fr = datetime.now().strftime("%A")
portail = st.sidebar.selectbox("Choisir Portail", ["📖 Emploi du Temps","📅 Surveillances Examens","🤖 Générateur Automatique","👥 Portail Enseignants","🎓 Portail Étudiants"])
mode_view = st.sidebar.selectbox("Mode de Vue", ["Personnel","Enseignant","Promotion","🏢 Planning Salles","🚩 Vérificateur de conflits"])
is_admin = True  # Exemple: définir selon login

# --- EN-TÊTE ---
col_logo, col_titre, col_date = st.columns([1,5,1])
with col_logo:
    try: st.image("logo.PNG", width=90)
    except: st.markdown("🏛️")
with col_titre:
    st.markdown(f"<h1 style='border-bottom:none;margin-top:0;'>Plateforme EDTs-S2-2026 - Département Électrotechnique</h1>", unsafe_allow_html=True)
with col_date:
    st.markdown(f"<div style='float:right;'>📅 {nom_jour_fr}<br>{date_str}</div>", unsafe_allow_html=True)
st.markdown("<div style='border-bottom:3px solid #D4AF37;margin-bottom:10px;'></div>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE ACTIF : {portail.upper()}</div>", unsafe_allow_html=True)

# --- FONCTIONS UTILES ---
def get_nature(code):
    val = str(code).upper()
    if "COURS" in val: return "📘 COURS"
    if "TD" in val: return "📗 TD"
    if "TP" in val: return "📙 TP"
    return "📑"

# --- EDT / BILAN HORAIRES ---
if portail == "📖 Emploi du Temps":
    cible = "Prof Test"  # Exemple; remplacer par login ou selectbox
    df_f = df[df["Enseignants"].str.contains(cible, case=False, na=False)].copy()
    df_f['Type'] = df_f['Code'].apply(lambda x: "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP"))
    df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x=="COURS" else 1.0)
    df_u = df_f.drop_duplicates(subset=['Jours','Horaire'])

    st.markdown(f"### 📊 Bilan Horaire : {cible}")
    st.markdown(f"""<div style='display:flex;gap:10px;'>
        <div style='background:#3498db;padding:10px;border-radius:5px;'>📘 {len(df_u[df_u['Type']=='COURS'])} Séances Cours</div>
        <div style='background:#2ecc71;padding:10px;border-radius:5px;'>📗 {len(df_u[df_u['Type']=='TD'])} Séances TD</div>
        <div style='background:#f39c12;padding:10px;border-radius:5px;'>📙 {len(df_u[df_u['Type']=='TP'])} Séances TP</div>
    </div>""", unsafe_allow_html=True)

    charge_reelle = df_u['h_val'].sum()
    charge_reg = 6.0
    h_sup = charge_reelle - charge_reg
    color_sup = "#e74c3c" if h_sup>0 else "#27ae60"

    col1, col2, col3 = st.columns(3)
    col1.markdown(f"Charge Réelle: {charge_reelle} h")
    col2.markdown(f"Réglementaire: {charge_reg} h")
    col3.markdown(f"Heures Sup.: {h_sup} h", unsafe_allow_html=True)

    # --- ÉDITEUR DE TABLEAU ---
    st.subheader("✍️ Éditeur de Données")
    search_query = st.text_input("🔍 Rechercher une ligne :")
    cols_format = ['Enseignements','Code','Enseignants','Horaire','Jours','Lieu','Promotion','Chevauchement']
    for col in cols_format:
        if col not in df.columns: df[col] = ""
    df_to_edit = df[df[cols_format].apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)].copy() if search_query else df[cols_format].copy()
    edited_df = st.data_editor(df_to_edit, use_container_width=True, num_rows="dynamic", key="admin_master_editor")
    if st.button("💾 Sauvegarder les modifications"):
        try:
            if search_query: df.update(edited_df)
            else: df = edited_df
            df[cols_format].to_excel(NOM_FICHIER_FIXE, index=False)
            st.success("✅ Modifications enregistrées !")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- Ajoute ici les autres portails (Surveillances, Générateur, Enseignants, Étudiants) de ton script original ---
