import streamlit as st
import pandas as pd
import io
import os
import streamlit.components.v1 as components

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="EDT & Charge UDL", layout="wide")

# --- STYLE CSS (Design & Force One Page) ---
st.markdown("""
    <style>
    /* Style Global */
    .main-title { color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; border-bottom: 3px solid #D4AF37; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }
    th { background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 5px; text-align: center; font-size: 11px; }
    td { border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 75px; }
    .cours-title { color: #1E3A8A; font-weight: bold; display: block; font-size: 11px; }
    .enseignant-name { color: #333; display: block; font-size: 10px; }
    .lieu-name { color: #666; font-style: italic; display: block; font-size: 9px; }
    .separator { border-top: 1px dashed #bbb; margin: 3px 0; }
    .metric-card { background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 8px; border-radius: 10px; text-align: center; }
    .stat-box { background-color: #e9ecef; border-radius: 5px; padding: 5px; margin-top: 2px; font-weight: bold; color: #1E3A8A; text-align: center; font-size: 12px;}
    .conflit-alert { background-color: #ffcccc; color: #cc0000; padding: 8px; border-radius: 5px; border-left: 5px solid #cc0000; margin-bottom: 5px; font-size: 13px; }

    /* RÈGLES D'IMPRESSION STRICTES : UNE SEULE PAGE */
    @media print {
        @page { size: A4 landscape; margin: 5mm; }
        
        /* Cacher tout sauf le titre et le tableau */
        section[data-testid="stSidebar"], .stActionButton, footer, header, [data-testid="stHeader"], .no-print { 
            display: none !important; 
        }
        
        .stApp { 
            height: auto !important; 
            background-color: white !important;
        }

        /* Forcer le contenu à tenir sur une seule page */
        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        /* Ajustement de l'échelle si nécessaire */
        table { 
            page-break-inside: avoid; 
            width: 100% !important;
            font-size: 9pt !important;
        }

        /* Suppression des espaces vides de Streamlit */
        div[data-testid="stVerticalBlock"] > div { padding: 0 !important; margin: 0 !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- MOT DE PASSE ---
if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    st.markdown("<h1 class='main-title'>🔐 ACCÈS RÉSERVÉ</h1>", unsafe_allow_html=True)
    pw = st.text_input("Code d'accès :", type="password")
    if pw == "doctorat2026":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- HEADER ---
st.markdown("<h1 class='main-title'>🏛️ Département d'Électrotechnique - SBA</h1>", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png")
    st.header("⚙️ Menu")
    file = st.file_uploader("Fichier Excel", type=['xlsx'])
    if st.button("🚪 Déconnexion"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if file:
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns:
            df[col] = df[col].fillna("Non défini").astype(str).str.replace('\n', ' ').str.strip()

    # CONFLITS
    mask_ens = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
    df_err_ens = df[df['Enseignants'] != "Non défini"][mask_ens]
    mask_salle = df[df['Lieu'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Lieu'], keep=False)
    df_err_salle = df[df['Lieu'] != "Non défini"][mask_salle]

    st.sidebar.markdown("---")
    mode_view = st.sidebar.radio("Vue :", ["Promotion", "Enseignant", "🚩 Conflits"])
    
    try:
        if mode_view == "🚩 Conflits":
            st.subheader("Analyse des Conflits")
            if df_err_ens.empty and df_err_salle.empty: st.success("✅ Aucun conflit.")
            else:
                for _, r in df_err_salle.iterrows():
                    st.markdown(f"<div class='conflit-alert'>📍 <b>{r['Lieu']}</b> : Double occupation ({r['Jours']} - {r['Horaire']})</div>", unsafe_allow_html=True)
                for _, r in df_err_ens.iterrows():
                    st.markdown(f"<div class='conflit-alert' style='background-color:#fff3cd; color:#856404;'>👤 <b>{r['Enseignants']}</b> : Conflit horaire ({r['Jours']} - {r['Horaire']})</div>", unsafe_allow_html=True)
        else:
            col_target = "Promotion" if mode_view == "Promotion" else "Enseignants"
            options = sorted([str(x) for x in df[col_target].unique() if x])
            selection = st.sidebar.selectbox(f"Choisir {mode_view} :", options)
            df_filtered = df[df[col_target] == selection].copy()

            if mode_view == "Enseignant":
                # CHARGE HORAIRE
                def get_type(t):
                    t = t.upper()
                    if "COURS" in t: return "COURS"
                    elif "TD" in t: return "TD"
                    elif "TP" in t: return "TP"
                    return "AUTRE"
                df_filtered['Type'] = df_filtered['Enseignements'].apply(get_type)
                df_filtered['h_val'] = df_filtered['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
                c_tot = df_filtered['h_val'].sum()
                
                st.markdown(f"### 📊 Bilan : {selection}")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='metric-card'><b>Charge Total</b><br><h2>{c_tot}h</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-card'><b>Quota</b><br><h2>9h</h2></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='metric-card'><b>Sup</b><br><h2>{max(0, c_tot-9)}h</h2></div>", unsafe_allow_html=True)
                
                s1, s2, s3 = st.columns(3)
                s1.markdown(f"<div class='stat-box'>📚 Cours: {len(df_filtered[df_filtered['Type']=='COURS'])}</div>", unsafe_allow_html=True)
                s2.markdown(f"<div class='stat-box'>📝 TD: {len(df_filtered[df_filtered['Type']=='TD'])}</div>", unsafe_allow_html=True)
                s3.markdown(f"<div class='stat-box'>🔬 TP: {len(df_filtered[df_filtered['Type']=='TP'])}</div>", unsafe_allow_html=True)

            # --- BOUTON IMPRESSION (FORCE ONE PAGE) ---
            st.write("")
            components.html("""
                <button onclick="window.parent.print()" style="
                    background-color: #28a745; color: white; padding: 10px; 
                    border: none; border-radius: 5px; font-weight: bold; 
                    cursor: pointer; width: 100%;">
                    🖨️ Générer PDF (Format une seule page)
                </button>
            """, height=45)

            # --- GRILLE ---
            def format_cell(rows):
                items = []
                for _, row in rows.iterrows():
                    err = "border: 1px solid red; background:#fff0f0;" if row.name in df_err_ens.index or row.name in df_err_salle.index else ""
                    p_info = f"<br>({row['Promotion']})" if mode_view == "Enseignant" else ""
                    items.append(f"<div style='{err}'><span class='cours-title'>{row['Enseignements']}</span><span class='enseignant-name'>{row['Enseignants']}</span><span class='lieu-name'>{row['Lieu']}{p_info}</span></div>")
                return "<div class='separator'></div>".join(items)

            jours = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
            horaires = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]
            grid = df_filtered.groupby(['Horaire', 'Jours']).apply(format_cell).unstack('Jours').reindex(index=horaires, columns=jours).fillna("")
            
            st.write(f"**Emploi du temps : {selection}**")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

    except Exception as e: st.error(f"Erreur : {e}")
else: st.info("Chargez un fichier Excel.")