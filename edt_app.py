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
    .logo-container { display: flex; justify-content: center; margin-bottom: 0px; }
    .main-title { 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 20px; margin-top: 5px;
    }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; }
    .separator { border-top: 1px dashed #bbb; margin: 4px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }
    .stat-box { padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }
    
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
    mode_view = st.sidebar.radio("Vue :", ["Promotion", "Enseignant", "🏢 Emploi du Temps par Local", "🚩 Vérificateur"])
    
    poste_superieur = False
    if mode_view == "Enseignant":
        st.markdown("---")
        st.subheader("👤 Statut Enseignant")
        poste_sup_choice = st.radio("Poste Supérieur (Décharge 50%) ?", ["Non", "Oui"])
        poste_superieur = (poste_sup_choice == "Oui")

if df is not None:
    if os.path.exists("logo.png"):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("logo.png", width=120)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
    
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.strip()

    jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
    horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

    try:
        if mode_view == "🏢 Emploi du Temps par Local":
            lieux_disponibles = sorted([l for l in df['Lieu'].unique() if l not in ["Non défini", ""]])
            selection_local = st.sidebar.selectbox("Sélectionnez le local (Salle/Amphi/Labo) :", lieux_disponibles)
            
            st.subheader(f"📍 Planning d'occupation : {selection_local}")
            df_filtered = df[df["Lieu"] == selection_local].copy()

            def fmt_local(rows):
                return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><small>({r['Promotion']})</small>" for _, r in rows.iterrows()])

            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_local).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "Enseignant":
            options = sorted([str(x) for x in df["Enseignants"].unique() if x != "Non défini"])
            selection = st.sidebar.selectbox("Choisir Enseignant :", options)
            df_filtered = df[df["Enseignants"] == selection].copy()

            # --- CALCULS DE CHARGE ET STATS ---
            def get_type(t):
                t = t.upper()
                if "COURS" in t: return "COURS"
                elif "TD" in t: return "TD"
                elif "TP" in t: return "TP"
                return "AUTRE"

            df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
            df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            
            # Pour la charge, on ne compte qu'une fois les cours communs (même créneau, même enseignant)
            df_stats = df_filtered.drop_duplicates(subset=['Jours', 'Horaire'])
            
            charge_reelle = df_stats['h_val'].sum()
            charge_reg = (3.0 if poste_superieur else 6.0)
            h_sup = charge_reelle - charge_reg
            
            n_c = len(df_stats[df_stats['Type'] == "COURS"])
            n_td = len(df_stats[df_stats['Type'] == "TD"])
            n_tp = len(df_stats[df_stats['Type'] == "TP"])

            st.markdown(f"### 📊 Bilan : {selection}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'><b>Charge Réelle</b><br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'><b>Charge Réglementaire</b><br><h2>{charge_reg} h</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-card'><b>Heures Sup</b><br><h2>{h_sup} h</h2></div>", unsafe_allow_html=True)
            
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {n_c} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {n_td} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {n_tp} TP</div>", unsafe_allow_html=True)

            def fmt_ens(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_ens).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "Promotion":
            options = sorted([str(x) for x in df["Promotion"].unique() if x != "Non défini"])
            selection = st.sidebar.selectbox("Choisir Promotion :", options)
            df_filtered = df[df["Promotion"] == selection].copy()
            def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(fmt_p).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif mode_view == "🚩 Vérificateur":
            dup_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
            pot_err_ens = df[df['Enseignants'] != "Non défini"][dup_ens]
            real_err_ens_idx = [idx for idx, row in pot_err_ens.iterrows() if pot_err_ens[(pot_err_ens['Jours']==row['Jours']) & (pot_err_ens['Horaire']==row['Horaire']) & (pot_err_ens['Enseignants']==row['Enseignants'])]['Enseignements'].nunique() > 1]
            if not real_err_ens_idx:
                st.success("✅ Aucun chevauchement réel détecté.")
            else:
                for _, r in df.loc[real_err_ens_idx].drop_duplicates(subset=['Jours', 'Horaire', 'Enseignants']).iterrows():
                    st.warning(f"👤 Conflit : **{r['Enseignants']}** a deux matières différentes le {r['Jours']} à {r['Horaire']}")

        components.html("<button onclick='window.parent.print()' style='width:100%; padding:10px; background:#28a745; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; margin-top:20px;'>🖨️ IMPRIMER CE PLANNING</button>", height=70)

    except Exception as e: st.error(f"Erreur : {e}")