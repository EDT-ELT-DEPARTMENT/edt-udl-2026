import streamlit as st
import pandas as pd
import os
import hashlib
import io
from datetime import datetime
from supabase import create_client
import streamlit.components.v1 as components

# --- CONFIGURATION ---
st.set_page_config(page_title="EDT UDL 2026", layout="wide")

# --- CONNEXION SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def hash_pw(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATE ET HEURE ---
now = datetime.now()
date_str = now.strftime("%d/%m/%Y")
nom_jour_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][now.weekday()]

# --- STYLE CSS ---
st.markdown(f"""
    <style>
    .main-title {{ 
        color: #1E3A8A; text-align: center; font-family: 'serif'; font-weight: bold; 
        border-bottom: 3px solid #D4AF37; padding-bottom: 15px; font-size: 18px; margin-top: 5px;
    }}
    .portal-badge {{ background-color: #D4AF37; color: #1E3A8A; padding: 5px 15px; border-radius: 5px; font-weight: bold; text-align: center; margin-bottom: 20px; }}
    .date-badge {{ background-color: #1E3A8A; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; float: right; }}
    .metric-card {{ background-color: #f8f9fa; border: 1px solid #1E3A8A; padding: 10px; border-radius: 10px; text-align: center; height: 100%; }}
    .stat-box {{ padding: 10px; border-radius: 5px; color: white; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 5px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; background-color: white; }}
    th {{ background-color: #1E3A8A !important; color: white !important; border: 1px solid #000; padding: 6px; text-align: center; font-size: 11px; }}
    td {{ border: 1px solid #000; padding: 4px !important; vertical-align: top; text-align: center; background-color: white; height: 95px; font-size: 11px; }}
    .separator {{ border-top: 1px dashed #bbb; margin: 4px 0; }}
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DU FICHIER EDT ---
NOM_FICHIER_FIXE = "dataEDT-ELT-S2-2026.xlsx"
df = None
if os.path.exists(NOM_FICHIER_FIXE):
    df = pd.read_excel(NOM_FICHIER_FIXE)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ['Enseignements', 'Enseignants', 'Lieu', 'Promotion', 'Horaire', 'Jours']:
        if col in df.columns: df[col] = df[col].fillna("Non défini").astype(str).str.strip()
    df['Lieu_Racine'] = df['Lieu'].apply(lambda x: x.split('/')[0].strip() if x != "Non défini" else "Non défini")

# --- AUTHENTIFICATION ---
if "user_data" not in st.session_state: st.session_state["user_data"] = None

if not st.session_state["user_data"]:
    st.markdown("<h1 class='main-title'>🏛️ DÉPARTEMENT D'ÉLECTROTECHNIQUE - UDL SBA</h1>", unsafe_allow_html=True)
    tab_conn, tab_ins, tab_adm = st.tabs(["🔑 Connexion", "📝 Inscription", "🛡️ Admin"])
    with tab_conn:
        em = st.text_input("Email")
        ps = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter"):
            res = supabase.table("enseignants_auth").select("*").eq("email", em).eq("password_hash", hash_pw(ps)).execute()
            if res.data: st.session_state["user_data"] = res.data[0]; st.rerun()
            else: st.error("Identifiants incorrects.")
    with tab_adm:
        if st.text_input("Code Admin", type="password") == "doctorat2026":
            if st.button("Entrer en tant qu'Admin"):
                st.session_state["user_data"] = {"nom_officiel": "ADMIN", "role": "admin"}
                st.rerun()
    st.stop()

# --- INITIALISATION PARAMÈTRES ---
user = st.session_state["user_data"]
is_admin = user.get("role") == "admin"
jours_list = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi"]
horaires_list = ["8h-9h30", "9h30 -11h", "11h-12h30", "12h30-14h", "14h-15h30", "15h30 -17h00"]

with st.sidebar:
    st.header(f"👤 {user['nom_officiel']}")
    portail = st.selectbox("🚀 Espace", ["📖 Emploi du Temps", "📅 Surveillances Examens", "🤖 Générateur Automatique"])
    st.divider()
    if portail == "📖 Emploi du Temps":
        mode_view = st.radio("Vue :", ["Promotion", "Enseignant", "🏢 Planning Salles", "🚩 Vérificateur"]) if is_admin else "Personnel"
        poste_sup = st.checkbox("Poste Supérieur (Décharge)")
    if st.button("🚪 Déconnexion"): st.session_state["user_data"] = None; st.rerun()

st.markdown(f"<div class='date-badge'>📅 {nom_jour_fr} {date_str}</div>", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='portal-badge'>MODE : {portail.upper()}</div>", unsafe_allow_html=True)

if df is not None:
    # ================= PORTAIL 1 : EMPLOI DU TEMPS =================
    if portail == "📖 Emploi du Temps":
        if mode_view == "Personnel" or (is_admin and mode_view == "Enseignant"):
            cible = user['nom_officiel'] if mode_view == "Personnel" else st.selectbox("Choisir Enseignant :", sorted(df["Enseignants"].unique()))
            df_f = df[df["Enseignants"] == cible].copy()
            
            def get_t(x): return "COURS" if "COURS" in str(x).upper() else ("TD" if "TD" in str(x).upper() else "TP")
            df_f['Type'] = df_f['Enseignements'].apply(get_t)
            df_f['h_val'] = df_f['Type'].apply(lambda x: 1.5 if x == "COURS" else 1.0)
            df_u = df_f.drop_duplicates(subset=['Jours', 'Horaire'])
            
            # --- CALCULS ---
            charge_reelle = df_u['h_val'].sum()
            charge_reglementaire = 3.0 if poste_sup else 6.0
            heures_sup = charge_reelle - charge_reglementaire
            
            st.markdown(f"### 📊 Bilan : {cible}")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-card'>Charge Réelle<br><h2>{charge_reelle} h</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-card'>Réglementaire<br><h2>{charge_reglementaire} h</h2></div>", unsafe_allow_html=True)
            
            # Affichage dynamique : rouge si positif (plus de travail), vert si négatif (sous-charge)
            color_sup = "#e74c3c" if heures_sup > 0 else "#27ae60"
            c3.markdown(f"<div class='metric-card' style='border-color:{color_sup};'>Heures Sup<br><h2 style='color:{color_sup};'>{heures_sup} h</h2></div>", unsafe_allow_html=True)
            
            st.write("") 
            s1, s2, s3 = st.columns(3)
            s1.markdown(f"<div class='stat-box' style='background-color:#1E3A8A;'>📘 {len(df_u[df_u['Type'] == 'COURS'])} COURS</div>", unsafe_allow_html=True)
            s2.markdown(f"<div class='stat-box' style='background-color:#28a745;'>📗 {len(df_u[df_u['Type'] == 'TD'])} TD</div>", unsafe_allow_html=True)
            s3.markdown(f"<div class='stat-box' style='background-color:#e67e22;'>📙 {len(df_u[df_u['Type'] == 'TP'])} TP</div>", unsafe_allow_html=True)

            def fmt_e(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid = df_f.groupby(['Horaire', 'Jours']).apply(fmt_e, include_groups=False).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "Promotion":
            p_sel = st.selectbox("Choisir Promotion :", sorted(df["Promotion"].unique()))
            df_p = df[df["Promotion"] == p_sel]
            def fmt_p(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>{r['Enseignants']}<br><i>{r['Lieu']}</i>" for _,r in rows.iterrows()])
            grid_p = df_p.groupby(['Horaire', 'Jours']).apply(fmt_p, include_groups=False).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(f"### 📅 Emploi du Temps : {p_sel}")
            st.write(grid_p.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🏢 Planning Salles":
            s_sel = st.selectbox("Choisir Salle (Racine) :", sorted([r for r in df['Lieu_Racine'].unique() if r != "Non défini"]))
            df_s = df[df['Lieu_Racine'] == s_sel]
            def fmt_s(rows): return "<div class='separator'></div>".join([f"<b>{r['Enseignements']}</b><br>({r['Promotion']})<br><small>{r['Lieu']}</small>" for _,r in rows.iterrows()])
            grid_s = df_s.groupby(['Horaire', 'Jours']).apply(fmt_s, include_groups=False).unstack('Jours').reindex(index=horaires_list, columns=jours_list).fillna("")
            st.write(grid_s.to_html(escape=False), unsafe_allow_html=True)

        elif is_admin and mode_view == "🚩 Vérificateur":
            dup = df[df['Enseignants'] != "Non défini"].duplicated(subset=['Jours', 'Horaire', 'Enseignants'], keep=False)
            err = df[df['Enseignants'] != "Non défini"][dup]
            if err.empty: st.success("✅ Aucun conflit détecté.")
            else: st.warning("Conflits d'enseignants détectés :"); st.dataframe(err)

  # ================= PORTAIL 2 : SURVEILLANCES EXAMENS =================
    elif portail == "📅 Surveillances Examens":
        NOM_SURV = "surveillances_2026.xlsx"
        horaires_examens = ["08h30 – 10h30", "11h00 – 13h00", "13h30 – 15h30"]
        
        if os.path.exists(NOM_SURV):
            df_surv = pd.read_excel(NOM_SURV)
            df_surv.columns = [str(c).strip() for c in df_surv.columns]
            df_surv['Date_Tri'] = pd.to_datetime(df_surv['Date'], dayfirst=True, errors='coerce')
            
            # Nettoyage
            for c in ['Surveillant(s)', 'Jour', 'Heure', 'Matière', 'Salle']:
                if c in df_surv.columns: df_surv[c] = df_surv[c].fillna("").astype(str).str.strip()

            liste_profs = sorted(df_surv['Surveillant(s)'].unique())
            u_nom = user['nom_officiel']
            idx_p = liste_profs.index(u_nom) if u_nom in liste_profs else 0
            prof_sel = st.selectbox("🔍 Sélectionner un enseignant :", liste_profs, index=idx_p)
            
            df_u = df_surv[df_surv['Surveillant(s)'] == prof_sel].sort_values(by='Date_Tri')
            st.metric("Total surveillances", f"{len(df_u)} séance(s)")
            
            tab1, tab2 = st.tabs(["👤 Mon Planning", "🌍 Liste Globale"])
            
            with tab1:
                if not df_u.empty:
                    # Affichage des cartes de surveillance
                    for _, r in df_u.iterrows():
                        dt_disp = pd.to_datetime(r['Date'], dayfirst=True).strftime('%d/%m/%Y') if r['Date'] else "Date ND"
                        st.markdown(f"""
                            <div style="background-color: #f8f9fa; padding: 10px; border-left: 5px solid #1E3A8A; margin-bottom: 5px; border: 1px solid #ddd; border-radius: 5px;">
                                <small>📅 {r['Jour']} {dt_disp} | 🕒 {r['Heure']}</small><br>
                                <b>{r['Matière']}</b><br>
                                <small>📍 Salle: {r['Salle']} | 🎓 {r['Promotion']}</small>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    # Grille visuelle
                    st.markdown("#### 🗓️ Vue Calendrier")
                    grid_surv = pd.DataFrame("", index=horaires_examens, columns=jours_list)
                    for _, r in df_u.iterrows():
                        j, h = str(r['Jour']).strip().capitalize(), str(r['Heure']).strip()
                        if j in grid_surv.columns and h in grid_surv.index:
                            grid_surv.at[h, j] = f"<b>{r['Matière']}</b><br><small>{r['Salle']}</small>"
                    st.write(grid_surv.to_html(escape=False), unsafe_allow_html=True)

                    # Exportations
                    st.divider()
                    ex1, ex2 = st.columns(2)
                    with ex1: components.html('<button onclick="window.parent.print()" style="width:100%; padding:10px; background:#1E3A8A; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">🖨️ IMPRIMER / PDF</button>', height=60)
                    with ex2:
                        out = io.BytesIO()
                        df_u.drop(columns=['Date_Tri']).to_excel(out, index=False)
                        st.download_button("📥 EXCEL (.XLSX)", out.getvalue(), f"Surv_{prof_sel}.xlsx", use_container_width=True)
                else:
                    st.info("Aucune surveillance trouvée.")

            with tab2:
                st.dataframe(df_surv.drop(columns=['Date_Tri']), use_container_width=True, hide_index=True)

# ================= PORTAIL 3 : GÉNÉRATEUR AUTOMATIQUE (ADMIN) =================
elif portail == "🤖 Générateur Automatique" and is_admin:
    st.header("⚙️ Répartition Équitable (Duo/Trio)")
    
    # --- DIAGNOSTIC ÉTAPE 1 : Les Enseignants ---
    if df is not None:
        tous_les_ens = sorted([str(e).strip() for e in df['Enseignants'].unique() if str(e).strip() not in ["nan", "Non défini", "À définir"]])
        st.success(f"✅ Étape 1 : {len(tous_les_ens)} enseignants trouvés dans l'EDT.")
    else:
        st.error("❌ Étape 1 : Aucun enseignant trouvé (Fichier EDT absent).")
        st.stop()

    NOM_SURV = "surveillances_2026.xlsx"
    
    # --- DIAGNOSTIC ÉTAPE 2 : Le fichier Surveillances ---
    if not os.path.exists(NOM_SURV):
        st.warning(f"⚠️ Étape 2 : Le fichier '{NOM_SURV}' n'existe pas. Création automatique...")
        # Création d'un fichier de test pour débloquer l'affichage
        df_test = pd.DataFrame({
            'Date': ['07/01/2026', '08/01/2026'],
            'Heure': ['08h30 – 10h30', '11h00 – 13h00'],
            'Salle': ['Salle 01', 'Amphi A'],
            'Matière': ['Examen Test 1', 'Examen Test 2'],
            'Jour': ['Dimanche', 'Lundi']
        })
        df_test.to_excel(NOM_SURV, index=False)
        st.rerun()

    # --- ÉTAPE 3 : Chargement et Calcul ---
    df_base = pd.read_excel(NOM_SURV)
    st.write("📊 Contenu du fichier source détecté :", df_base.head(2))

    profs_alleger = st.multiselect("Enseignants avec décharge :", tous_les_ens)
    coef = st.slider("Charge pour décharge (%)", 10, 100, 50) / 100

    if st.button("🚀 GÉNÉRER LA RÉPARTITION MAINTENANT"):
        st.write("⏳ Calcul en cours...")
        
        # Nettoyage des colonnes
        df_base.columns = [str(c).strip() for c in df_base.columns]
        
        rows_final = []
        stats_charge = {ens: 0 for ens in tous_les_ens}
        
        # Algorithme
        for _, r in df_base.iterrows():
            salle_txt = str(r.get('Salle', r.get('SALLE', ''))).upper()
            nb_besoin = 3 if "AMPHI" in salle_txt else 2
            
            for _ in range(nb_besoin):
                # Tri par charge pondérée
                file_prio = sorted(tous_les_ens, key=lambda e: (stats_charge[e] / (coef if e in profs_alleger else 1.0)))
                
                for prof in file_prio:
                    # Anti-conflit sur Date et Heure
                    conflit = any(x for x in rows_final if x['Date'] == r['Date'] and x['Heure'] == r['Heure'] and x['Surveillant(s)'] == prof)
                    
                    if not conflit:
                        new_row = r.to_dict()
                        new_row['Surveillant(s)'] = prof
                        rows_final.append(new_row)
                        stats_charge[prof] += 1
                        break

        if rows_final:
            df_res = pd.DataFrame(rows_final)
            st.subheader("✅ RÉSULTAT")
            
            # Affichage du bilan
            st.write("### 📊 Bilan des charges")
            st.table(pd.DataFrame([{"Nom": k, "Missions": v} for k, v in stats_charge.items()]).sort_values("Missions", ascending=False))
            
            # Download
            buf = io.BytesIO()
            df_res.to_excel(buf, index=False)
            st.download_button("📥 TÉLÉCHARGER LE PLANNING", buf.getvalue(), "Planning_Final.xlsx", use_container_width=True)
            
            # Aperçu
            st.dataframe(df_res)
        else:
            st.error("❌ L'algorithme n'a trouvé aucune solution. Vérifiez les noms des colonnes 'Date', 'Heure' et 'Salle'.")
