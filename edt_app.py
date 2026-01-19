import streamlit as st
import pandas as pd
import io
import os
import glob
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 20px; margin-top: 10px;
    }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 85px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 11px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 9px; }
    .separator { border-top: 1px dashed #bbb; margin: 4px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }
    .stat-box { padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }
    .conflit-alert { background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; border: 1px solid #f5c6cb; margin-bottom: 5px; font-size: 14px; }
    
    @media print {
        @page { size: A4 landscape; margin: 0.5cm; }
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print, button { display: none !important; }
        .stApp { height: auto !important; background-color: white !important; }
        table { page-break-inside: avoid; width: 100% !important; border: 1px solid black !important; }
        th { background-color: #1E3A8A !important; color: white !important; -webkit-print-color-adjust: exact; }
    }
    </style>
""", unsafe_allow_html=True)

# --- AUTHENTIFICATION ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ</h1>", unsafe_allow_html=True)
    pw = st.text_input("Code d'accès :", type="password")
    if pw == "doctorat2026":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- CHARGEMENT DU FICHIER ---
excel_files = glob.glob("*.xlsx")
default_file = excel_files[0] if excel_files else None
df = None

with st.sidebar:
    st.header("⚙️ Configuration")
    uploaded_file = st.file_uploader("Mettre à jour l'Excel", type=['xlsx'])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
    elif default_file:
        df = pd.read_excel(default_file)
    
    st.markdown("---")
    mode_view = st.sidebar.radio("Vue :", ["Promotion", "Enseignant", "🚩 Vérificateur"])
    
    poste_superieur = False
    if mode_view == "Enseignant":
        st.markdown("---")
        st.subheader("👤 Statut Enseignant")
        poste_sup_choice = st.radio("Poste Supérieur (Décharge 50%) ?", ["Non", "Oui"])
        poste_superieur = (poste_sup_choice == "Oui")

if df is not None:
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    # Nettoyage
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()

    # --- LOGIQUE DE CONFLITS INTELLIGENTE ---
    # On ne considère un conflit que si l'ENSEIGNEMENT est différent pour un même créneau
    dup_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
    pot_err_ens = df[df['Enseignants'] != "Non défini"][dup_ens]
    real_err_ens_idx = []
    
    for name, group in pot_err_ens.groupby(['Jours', 'Horaire', 'Enseignants']):
        # Si le nombre de matières uniques > 1, alors il y a conflit (chevauchement réel)
        if group['Enseignements'].nunique() > 1:
            real_err_ens_idx.extend(group.index.tolist())
    df_err_ens = df.loc[real_err_ens_idx]

    # Pour les salles, on garde la logique : une salle ne peut avoir deux matières différentes en même temps
    dup_salle = df[df['Lieu'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Lieu'], keep=False)
    pot_err_salle = df[df['Lieu'] != "Non défini"][dup_salle]
    real_err_salle_idx = []
    for name, group in pot_err_salle.groupby(['Jours', 'Horaire', 'Lieu']):
        if group['Enseignements'].nunique() > 1:
            real_err_salle_idx.extend(group.index.tolist())
    df_err_salle = df.loc[real_err_salle_idx]

    try:
        if mode_view == "🚩 Vérificateur":
            st.subheader("🔍 Analyse des Chevauchements")
            if df_err_ens.empty and df_err_salle.empty:
                st.success("✅ Aucun chevauchement réel détecté (Les cours communs sont acceptés).")
            else:
                if not df_err_salle.empty:
                    st.error("📍 Conflits de Salles :")
                    for _, r in df_err_salle.drop_duplicates(subset=['Jours', 'Horaire', 'Lieu']).iterrows():
                        st.markdown(f"<div class='conflit-alert'><b>{r['Lieu']}</b> : Plusieurs matières différentes à {r['Horaire']}</div>", unsafe_allow_html=True)
                if not df_err_ens.empty:
                    st.warning("👤 Conflits d'Enseignants (Matières différentes au même moment) :")
                    for _, r in df_err_ens.drop_duplicates(subset=['Jours', 'Horaire', 'Enseignants']).iterrows():
                        st.markdown(f"<div class='conflit-alert' style='background-color:#fff3cd; color:#856404;'><b>{r['Enseignants']}</b> : Conflit réel le {r['Jours']} à {r['Horaire']}</div>", unsafe_allow_html=True)

        elif mode_view == "Enseignant":
            options = sorted([str(x) for x in df["Enseignants"].unique() if x and x != "Non défini"])
            selection = st.sidebar.selectbox("Choisir Enseignant :", options)
            df_filtered = df[df["Enseignants"] == selection].copy()

            # CALCULS CHARGE
            def get_type(t):
                t = t.upper()
                if "COURS" in t: return "COURS"
                elif "TD" in t: return "TD"
                elif "TP" in t: return "TP"
                return "AUTRE"

            df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
            df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            
            # Important : Drop duplicates sur le temps pour ne compter qu'une seule fois les cours communs
            df_stats = df_filtered.drop_duplicates(subset=['Jours', 'Horaire'])
            
            charge_reelle = df_stats['h_val'].sum()
            charge_reglementaire = 3.0 if poste_superieur else 6.0
            h_sup = charge_reelle - charge_reglementaire
            
            n_cours = len(df_stats[df_stats['Type'] == "COURS"])
            n_td = len(df_stats[df_stats['Type'] == "TD"])
            n_tp = len(df_stats[df_stats['Type'] == "TP"])

            st.markdown(f"### 📊 Bilan : {selection}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'><b>Charge Réelle</b><br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><b>Charge Réglementaire</b><br><h2>{charge_reglementaire} h</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'><b>Heures Sup</b><br><h2>{h_sup} h</h2></div>", unsafe_allow_html=True)
            
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {n_cours} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {n_td} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {n_tp} TP</div>", unsafe_allow_html=True)

            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
            
            def fmt(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "Promotion":
            options = sorted([str(x) for x in df["Promotion"].unique() if x and x != "Non défini"])
            selection = st.sidebar.selectbox("Choisir Promotion :", options)
            df_filtered = df[df["Promotion"] == selection].copy()
            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
            def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        components.html("<button onclick='window.parent.print()' style='width:100%; padding:10px; background:#28a745; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:20px;'>🖨️ IMPRIMER L'EMPLOI DU TEMPS</button>", height=70)

    except Exception as e:
        st.error(f"Erreur : {e}")