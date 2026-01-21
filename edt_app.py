import streamlit as st
import pandas as pd
import os
import hashlib
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

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }
    .portal-badge { background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; height: 100px; font-size: 11px; }
    .separator { border-top: 1px dashed #bbb; margin: 4px 0; }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT ET NETTOYAGE ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Disposition : Enseignements, Code, Enseignants, Horaire, Jours, Lieu, Promotion
    cols = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
    for c in cols:
        df[c] = df[c].fillna("Non défini").astype(str).str.strip()

# --- LISTES DE RÉFÉRENCE ---
# Ces listes définissent l'ORDRE et le CONTENU de la grille
horaires_ref = ["8h-9h30", "9h30-11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30-17h"]
jours_ref = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]

if df is not None:
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    # Sélection de l'enseignant
    enseignant_nom = st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
    df_f = df[df["Enseignants"] == enseignant_nom].copy()

    # --- LOGIQUE TYPE VIA LE CODE ---
    def get_type_by_code(code):
        c = code.upper()
        if "COURS" in c: return "COURS"
        if "TD" in c: return "TD"
        return "TP"

    df_f['Type'] = df_f['Code'].apply(get_type_by_code)
    df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
    
    # Stats sur les séances uniques (Jours + Horaire)
    df_u = df_f.drop_duplicates(subset=['Jours', 'Horaire'])
    
    # Affichage Bilan
    st.write(f"### 📊 Bilan : {enseignant_nom}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Charge Réelle", f"{df_u['h_val'].sum()} h")
    c2.metric("Cours", len(df_u[df_u['Type'] == 'COURS']))
    c3.metric("TD", len(df_u[df_u['Type'] == 'TD']))
    c4.metric("TP", len(df_u[df_u['Type'] == 'TP']))

    # --- GÉNÉRATION DE LA GRILLE ---
    def fmt_cell(rows):
        return "<div class='separator'></div>".join([
            f"<b>{r['Enseignements']}</b><br><small>{r['Code']}</small><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" 
            for _, r in rows.iterrows()
        ])

    # Création du pivot
    grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt_cell, include_groups=False).unstack('Jours')
    
    # RÉINDEXATION STRICTE : C'est ici que l'on force l'affichage de tous les créneaux
    # On utilise les listes de référence pour reconstruire le tableau dans l'ordre
    grid = grid.reindex(index=horaires_ref, columns=jours_ref).fillna("")

    # Affichage HTML
    st.write(grid.to_html(escape=False), unsafe_allow_html=True)
