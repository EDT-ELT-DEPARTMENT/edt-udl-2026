 # ================= PORTAIL 3 : GÉNÉRATEUR AUTOMATIQUE (ADMIN) =================
    elif portail == "🤖 Générateur Automatique":
        if not is_admin:
            st.error("Accès réservé à l'administration.")
        else:
            st.header("⚙️ Générateur de Surveillances par Promotion")
            st.info("Plateforme de gestion des EDTs-S2-2026-Département d'Électrotechnique-Faculté de génie électrique-UDL-SBA")

            if "df_genere" not in st.session_state: st.session_state.df_genere = None
            if "stats_charge" not in st.session_state: st.session_state.stats_charge = {}

            NOM_SURV_SRC = "surveillances_2026.xlsx"

            if not os.path.exists(NOM_SURV_SRC):
                st.error(f"❌ Fichier '{NOM_SURV_SRC}' introuvable.")
            else:
                df_src = pd.read_excel(NOM_SURV_SRC)
                df_src.columns = [str(c).strip() for c in df_src.columns]
                for c in df_src.columns: df_src[c] = df_src[c].fillna("").astype(str).str.strip()

                col_prof = 'Surveillant(s)' if 'Surveillant(s)' in df_src.columns else 'Enseignants'
                liste_profs_surv = sorted([p for p in df_src[col_prof].unique() if p not in ["", "Non défini", "nan"]])
                promo_dispo = sorted(df_src['Promotion'].unique()) if 'Promotion' in df_src.columns else []

                # --- CONFIGURATION STRICTE DES QUOTAS ---
                with st.expander("⚖️ Réglage des Exceptions (Postes Supérieurs / Vacataires)", expanded=True):
                    c_cfg1, c_cfg2 = st.columns(2)
                    with c_cfg1:
                        profs_exception = st.multiselect("👤 Enseignants avec Quota limité :", liste_profs_surv)
                    with c_cfg2:
                        max_base = st.number_input("Nombre Max de surveillances (100%)", min_value=1, value=10)
                    
                    pourcentage = st.slider("Pourcentage du quota autorisé (%)", 10, 100, 50)
                    quota_calcule = int(max_base * (pourcentage / 100))
                    st.warning(f"🎯 Les enseignants sélectionnés seront limités à **{quota_calcule} surveillances** maximum.")

                col_p, col_d = st.columns(2)
                with col_p: promo_cible = st.multiselect("🎓 Promotions :", promo_dispo)
                with col_d: dates_exam = st.multiselect("📅 Dates :", sorted(df_src['Date'].unique()))

                if st.button("🚀 GÉNÉRER AVEC PLAFONNEMENT"):
                    if not promo_cible:
                        st.warning("Sélectionnez au moins une promotion.")
                    else:
                        stats = {p: 0 for p in liste_profs_surv}
                        global_tracking = []
                        results = []

                        for promo in promo_cible:
                            df_p = df_src[df_src['Promotion'] == promo].copy()
                            if dates_exam: df_p = df_p[df_p['Date'].isin(dates_exam)]

                            for _, row in df_p.iterrows():
                                binome = []
                                # On trie les profs par charge actuelle (équité)
                                prio = sorted(liste_profs_surv, key=lambda p: stats[p])

                                for p in prio:
                                    if len(binome) < 2:
                                        # CONDITION 1 : Pas de dépassement de quota pour les exceptions
                                        if p in profs_exception and stats[p] >= quota_calcule:
                                            continue
                                        
                                        # CONDITION 2 : Disponibilité temporelle
                                        conflit = any(x for x in global_tracking if x['D']==row['Date'] and x['H']==row['Heure'] and x['N']==p)
                                        
                                        if not conflit:
                                            binome.append(p)
                                            stats[p] += 1
                                            global_tracking.append({'D': row['Date'], 'H': row['Heure'], 'N': p})
                                
                                results.append({
                                    "Promotion": promo, "Date": row['Date'], "Heure": row['Heure'],
                                    "Matière": row['Matière'], "Salle": row['Salle'],
                                    "Binôme": " & ".join(binome) if len(binome)==2 else "MANQUE SURVEILLANT"
                                })
                        
                        st.session_state.stats_charge = stats
                        st.session_state.df_genere = pd.DataFrame(results)
                        st.rerun()

                # --- AFFICHAGE DES RÉSULTATS ---
                if st.session_state.df_genere is not None:
                    st.divider()
                    
                    # Analyse numérique
                    prof_sel = st.selectbox("📊 Vérifier un quota :", sorted(st.session_state.stats_charge.keys()))
                    q = st.session_state.stats_charge[prof_sel]
                    
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric(f"Total {prof_sel}", f"{q} / {quota_calcule if prof_sel in profs_exception else max_base}")
                    with c2: st.metric("Statut", "Limité" if prof_sel in profs_exception else "Normal")
                    with c3: 
                        rempli = (q / quota_calcule * 100) if prof_sel in profs_exception else (q / max_base * 100)
                        st.metric("Taux d'occupation", f"{int(rempli)}%")

                    # Tableau Individuel
                    df_p_ind = st.session_state.df_genere[st.session_state.df_genere['Binôme'].str.contains(prof_sel, na=False)]
                    st.dataframe(df_p_ind[["Date", "Heure", "Matière", "Salle"]], use_container_width=True)

                    st.divider()
                    # Affichage par promo
                    for p in promo_cible:
                        st.write(f"### 📋 Planning : {p}")
                        st.table(st.session_state.df_genere[st.session_state.df_genere['Promotion'] == p].drop(columns=['Promotion']))

                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        st.session_state.df_genere.to_excel(writer, index=False)
                    st.download_button("📥 TÉLÉCHARGER (.XLSX)", buffer.getvalue(), "EDT_Surv_S2.xlsx", use_container_width=True)

