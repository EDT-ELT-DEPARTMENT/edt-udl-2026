import streamlit as st
import pandas as pd
import io
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT & Charge UDL", layout="wide")

# --- STYLE CSS (Optimisé pour PDF) ---
st.markdown("""
    <style>
    .main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 20px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 10px; text-align: center; }
    td { border: 1px solid #000; padding: 8px !important; vertical-align: top; text-align: center; background-color: white; height: 80px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 12px; }
    .enseignant-name { color: #333; display: block; font-size: 11px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 10px; }
    .separator { border-top: 1px dashed #bbb; margin: 5px 0; }
    
    /* BOUTON IMPRIMER STYLE */
    .btn-print {
        background-color: #28a745;
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 5px;
        font-weight: bold;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        margin-bottom: 20px;
    }

    /* RÈGLES D'IMPRESSION STRICTES */
    @media print {
        /* Masquer tout sauf le titre et le tableau */
        section[data-testid="stSidebar"], 
        .stActionButton, 
        .no-print,
        button,
        header { 
            display: none !important; 
        }
        .main-title { margin-top: 0; }
        table { width: 100% !important; border: 1px solid black !important; }
        th { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        td { word-wrap: break-word; }
    }
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTIFICATION (Identique à avant) ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ</h1>", unsafe_allow_html=True)
    pw = st.text_input("Code d'accès :", type="password")
    if pw == "doctorat2026":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- INTERFACE ---
st.markdown("<h1 class='main-title'>🏛️ Département d'Électrotechnique - SBA</h1>", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png")
    file = st.file_uploader("Charger le fichier Excel", type=['xlsx'])
    if st.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if file:
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Nettoyage
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.replace('\n', ' ').str.strip()

    st.sidebar.markdown("---")
    mode = st.sidebar.radio("Mode :", ["Promotion", "Enseignant"])
    
    options = sorted([str(x) for x in df[mode].unique() if x])
    selection = st.sidebar.selectbox(f"Choisir {mode} :", options)
    df_filtered = df[df[mode] == selection].copy()

    # --- BOUTON D'IMPRESSION (CORRIGÉ) ---
    st.markdown('<button class="btn-print no-print" onclick="window.print()">📥 Télécharger / Imprimer l\'EDT en PDF</button>', unsafe_allow_html=True)

    # --- CONSTRUCTION DU TABLEAU ---
    def format_cell(rows):
        items = []
        for _, row in rows.iterrows():
            promo = f"<br>({row['Promotion']})" if mode == "Enseignant" else ""
            html = f"<div><span class='cours-title'>{row['Enseignements']}</span><span class='enseignant-name'>{row['Enseignants']}</span><span class='lieu-name'>{row['Lieu']}{promo}</span></div>"
            items.append(html)
        return "<div class='separator'></div>".join(items)

    jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
    
    grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours')
    grid = grid.reindex(index=horaires, columns=jours).fillna("")
    
    # Affichage
    st.markdown(f"### 📋 Emploi du Temps : {selection}")
    st.write(grid.to_html(escape=False), unsafe_allow_html=True)