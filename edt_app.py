import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

# --- CONSTANTES ET FICHIERS ---
NOM_FICHIER_FIXE = "EDT_S2_2026.xlsx"
FILE_SURV = "surveillances_2026.xlsx"
FILE_ETUDIANTS = "Liste des étudiants-2025-2026.xlsx"

jours_std = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
liste_horaires = ["08h00-09h30","09h45-11h15","11h30-13h00","14h00-15h30","15h45-17h15","17h30-19h00"]

# Mapping horaires/jours pour affichage
map_h = {h:h for h in liste_horaires}
map_j = {j:j for j in jours_std}

# --- SESSION & UTILISATEUR ---
if "df_admin" not in st.session_state: st.session_state.df_admin = None
user = {"nom_officiel": "Prof Test", "email": "test@exemple.com"}
is_admin = True
mode_view = "Personnel"  # Personnel / Enseignant / Promotion / Planning Salles / Vérificateur
portail = "📖 Emploi du Temps"  # Choix de portail

# --- CHARGEMENT DONNÉES EDT ---
if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    for c in df.columns: df[c] = df[c].fillna("").astype(str).str.strip()
else:
    df = pd.DataFrame(columns=['Enseignements','Code','Enseignants','Horaire','Jours','Lieu','Promotion','Chevauchement'])

# --- FONCTIONS UTILES ---
def get_type_seance(code):
    val = str(code).upper()
    if "COURS" in val: return "COURS"
    if "TD" in val: return "TD"
    if "TP" in val: return "TP"
    return "AUTRE"

def format_case(rows):
    items = []
    for _, r in rows.iterrows():
        items.append(f"<b>{get_type_seance(r['Code'])} : {r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>")
    return "<div class='separator'></div>".join(items)

# --- ÉDITEUR ADMIN ---
def admin_editor(df_to_edit):
    st.subheader("✍️ Éditeur de Données")
    search_query = st.text_input("🔍 Rechercher une ligne :")
    cols_format = ['Enseignements','Code','Enseignants','Horaire','Jours','Lieu','Promotion','Chevauchement']
    for col in cols_format:
        if col not in df_to_edit.columns: df_to_edit[col] = ""
    
    df_filtered = df_to_edit[df_to_edit[cols_format].apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)] if search_query else df_to_edit.copy()
    edited_df = st.data_editor(df_filtered, use_container_width=True, num_rows="dynamic", key="admin_editor")
    
    if st.button("💾 Sauvegarder les modifications"):
        try:
            df.update(edited_df)
            df.to_excel(NOM_FICHIER_FIXE, index=False)
            st.success("✅ Modifications enregistrées !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- PORTAIL EMPLOI DU TEMPS ---
if portail == "📖 Emploi du Temps":
    st.header("📅 Emploi du Temps S2-2026")
    
    # Choix utilisateur ou admin
    if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
        cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Sélectionner Enseignant :", sorted(df["Enseignants"].unique()))
        df_f = df[df["Enseignants"].str.contains(cible, case=False, na=False)].copy()
        df_f['Type'] = df_f['Code'].apply(get_type_seance)
        df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x=="COURS" else 1.0)
        df_u = df_f.drop_duplicates(subset=['Jours','Horaire'])

        st.markdown(f"### 📊 Bilan Horaire : {cible}")
        st.markdown(f"""
        <div class="stat-container">
            <div class="stat-box bg-cours">📘 {len(df_u[df_u['Type']=="COURS"])} Séances Cours</div>
            <div class="stat-box bg-td">📗 {len(df_u[df_u['Type']=="TD"])} Séances TD</div>
            <div class="stat-box bg-tp">📙 {len(df_u[df_u['Type']=="TP"])} Séances TP</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Affichage EDT sous forme de grille
        if not df_f.empty:
            grid = df_f.groupby(['Horaire','Jours']).apply(format_case, include_groups=False).unstack('Jours')
            grid = grid.reindex(index=liste_horaires, columns=jours_std).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    # Admin mode : Éditeur complet
    if is_admin:
        admin_editor(df)

# --- PORTAIL SURVEILLANCES ---
elif portail == "📅 Surveillances Examens":
    st.header("📋 Surveillances Examens")
    if os.path.exists(FILE_SURV):
        df_surv = pd.read_excel(FILE_SURV)
        df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
        prof_sel = user['nom_officiel']
        df_u_surv = df_surv[df_surv['Surveillant(s)'].str.contains(prof_sel, case=False, na=False)].sort_values(by='Date_Tri')
        st.dataframe(df_u_surv)
    else:
        st.error("Fichier de surveillances introuvable.")

# --- PORTAIL ÉTUDIANTS ---
elif portail == "🎓 Portail Étudiants":
    st.header("📚 Portail Étudiants")
    p_etu = st.selectbox("Choisir votre Promotion :", sorted(df["Promotion"].unique()))
    disp_etu = df[df["Promotion"] == p_etu][['Enseignements','Code','Enseignants','Horaire','Jours','Lieu']]
    st.table(disp_etu.sort_values(by=["Jours","Horaire"]))
    if is_admin: admin_editor(df)

# --- PORTAIL GÉNÉRATEUR AUTOMATIQUE ---
elif portail == "🤖 Générateur Automatique" and is_admin:
    st.header("⚙️ Générateur de Surveillances")
    st.info("Interface réservée au Bureau des Examens.")
    # Ici on peut intégrer le moteur automatique de répartition (comme dans ton code)

# --- PORTAIL ENSEIGNANTS ---
elif portail == "👥 Portail Enseignants" and is_admin:
    st.header("🏢 Portail Enseignants")
    st.info("Gestion individuelle et envoi automatique des EDTs par email.")
    # Ici on peut intégrer le système d'envoi email et suivi Supabase
