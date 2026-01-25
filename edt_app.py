import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client

# --- CONFIGURATION ET AUTHENTIFICATION (Identique à votre code global) ---
# ... (Gardez votre bloc de connexion Supabase et Hash_pw ici) ...

def run_advanced_editor(df_global):
    """
    Fonction isolée pour l'éditeur avancé.
    Titre : Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA
    """
    try:
        st.divider()
        st.subheader("✍️ Éditeur de données - Administration")
        
        # 1. Initialisation de l'état (Session State)
        cols_format = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
        
        if 'df_admin' not in st.session_state:
            temp_df = df_global.copy()
            for col in cols_format:
                if col not in temp_df.columns:
                    temp_df[col] = ""
            st.session_state.df_admin = temp_df[cols_format].fillna("")

        # 2. Préparation des références
        horaires_ref = ["8h - 9h30", "9h30 - 11h", "11h - 12h30", "12h30 - 14h00", "14h00 - 15h30", "15h30 - 17h00"]
        jours_std = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
        promos_std = sorted(list(st.session_state.df_admin["Promotion"].unique()))

        # 3. Filtre de recherche (Non-destructif)
        search_prof = st.text_input("🔍 Rechercher un enseignant pour filtrer l'édition :", "")
        
        if search_prof:
            df_to_show = st.session_state.df_admin[
                st.session_state.df_admin["Enseignants"].str.contains(search_prof, case=False, na=False)
            ]
        else:
            df_to_show = st.session_state.df_admin

        # 4. Formulaire d'ajout sécurisé
        with st.expander("➕ Ajouter une nouvelle séance"):
            with st.form("add_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    n_ens = st.text_input("Matière")
                    n_cod = st.text_input("Code")
                with c2:
                    n_prf = st.text_input("Enseignant")
                    n_hor = st.selectbox("Horaire", horaires_ref)
                with c3:
                    n_jou = st.selectbox("Jour", jours_std)
                    n_lie = st.text_input("Salle")
                n_pro = st.selectbox("Promotion", promos_std if promos_std else ["M1", "M2"])
                
                if st.form_submit_button("Vérifier et Insérer"):
                    # Vérification basique de conflit
                    conflict = st.session_state.df_admin[
                        (st.session_state.df_admin['Jours'] == n_jou) & 
                        (st.session_state.df_admin['Horaire'] == n_hor) & 
                        ((st.session_state.df_admin['Lieu'] == n_lie) | (st.session_state.df_admin['Enseignants'] == n_prf))
                    ]
                    if not conflict.empty:
                        st.error("⚠️ Conflit détecté (Salle ou Enseignant déjà occupé)")
                    else:
                        new_line = pd.DataFrame([[n_ens, n_cod, n_prf, n_hor, n_jou, n_lie, n_pro]], columns=cols_format)
                        st.session_state.df_admin = pd.concat([st.session_state.df_admin, new_line], ignore_index=True)
                        st.success("Ajouté !")
                        st.rerun()

        # 5. L'Éditeur dynamique
        edited_df = st.data_editor(
            df_to_show,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "Horaire": st.column_config.SelectboxColumn(options=horaires_ref),
                "Jours": st.column_config.SelectboxColumn(options=jours_std)
            },
            key="main_editor_s2"
        )

        # Synchronisation si modification
        if search_prof == "": # On ne synchronise le global que si on n'est pas filtré pour éviter les pertes
            st.session_state.df_admin = edited_df

        # 6. Sauvegarde
        st.write("---")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("💾 Enregistrer les modifications", type="primary"):
                st.session_state.df_admin.to_excel("dataEDT-ELT-S2-2026.xlsx", index=False)
                st.success("Fichier Excel mis à jour !")
        with col_s2:
            buffer = io.BytesIO()
            st.session_state.df_admin.to_excel(buffer, index=False)
            st.download_button("📥 Télécharger Excel", buffer.getvalue(), "EDT_S2_2026.xlsx")

    except Exception as e:
        st.error(f"Une erreur isolée est survenue dans l'éditeur : {e}")

# --- LOGIQUE D'APPEL DANS VOTRE CODE ---
# Remplacez votre ancien bloc "if mode_view == '✍️ Éditeur de données':" par :

if is_admin and mode_view == "✍️ Éditeur de données":
    run_advanced_editor(df)
    st.stop() # Empêche d'afficher le reste de la page en mode édition
