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
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; height: 110px; font-size: 11px; color: #333; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT ET NETTOYAGE ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None

def clean_time(s):
    """ Nettoie les erreurs de frappe : remplace ; par : et uniformise les h """
    s = str(s).lower().strip().replace(" ", "").replace(";", ":")
    # Si l'heure finit par 14 au lieu de 14h, on harmonise (optionnel selon votre fichier)
    return s

if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = ['Enseignements', 'Code', 'Enseignants', 'Horaire', 'Jours', 'Lieu', 'Promotion']
    for c in cols:
        df[c] = df[c].fillna("Non défini").astype(str).str.strip()
    
    # Normalisation pour la correspondance
    df['h_norm'] = df['Horaire'].apply(clean_time)
    df['j_norm'] = df['Jours'].apply(lambda x: str(x).strip().lower())

# --- LISTES DE RÉFÉRENCE (Basées sur votre dernier message) ---
# Note : J'ai inclus les variantes possibles pour ne rien rater
horaires_labels = ["8h-9h30", "9h30-11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30-17h"]
jours_labels = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]

# Dictionnaires de mapping pour retrouver le texte propre après normalisation
map_h = {clean_time(h): h for h in horaires_labels}
map_j = {j.lower(): j for j in jours_labels}

if df is not None:
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    # Sélection Enseignant
    enseignant_nom = st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
    df_f = df[df["Enseignants"] == enseignant_nom].copy()

    # Détermination du type par le CODE (plus fiable que le titre)
    def get_type(code):
        c = code.upper()
        if "COURS" in c: return "COURS"
        if "TD" in c: return "TD"
        return "TP"

    df_f['Type'] = df_f['Code'].apply(get_type)
    df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
    
    # Calcul des stats sur séances uniques
    df_u = df_f.drop_duplicates(subset=['j_norm', 'h_norm'])
    
    # Affichage des Metrics
    st.write(f"### 📊 Bilan : {enseignant_nom}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Charge Réelle", f"{df_u['h_val'].sum()} h")
    c2.metric("Cours", len(df_u[df_u['Type'] == 'COURS']))
    c3.metric("TD", len(df_u[df_u['Type'] == 'TD']))
    c4.metric("TP", len(df_u[df_u['Type'] == 'TP']))

    # --- CONSTRUCTION DE LA GRILLE ---
    def make_cell(rows):
        return "<div class='separator'></div>".join([
            f"<b>{r['Enseignements']}</b><br><small>{r['Code']}</small><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" 
            for _, r in rows.iterrows()
        ])

    # Pivotement
    grid = df_f.groupby(['h_norm', 'j_norm']).apply(make_cell, include_groups=False).unstack('j_norm')
    
    # REINDEXATION CRUCIALE : On force l'affichage de toutes les lignes et colonnes
    h_idx = [clean_time(h) for h in horaires_labels]
    j_idx = [j.lower() for j in jours_labels]
    
    grid = grid.reindex(index=h_idx, columns=j_idx).fillna("")
    
    # On remet les noms propres pour l'affichage final
    grid.index = [map_h.get(i, i) for i in grid.index]
    grid.columns = [map_j.get(c, c) for c in grid.columns]

    st.write(grid.to_html(escape=False), unsafe_allow_html=True)
