elif mode_view == "🔍 Locaux Non Occupés":
            st.subheader("🏢 Salles et Amphis vides par créneau")
            
            # Récupérer tous les lieux et filtrer uniquement les Salles et Amphis
            tous_lieux = [l for l in df['Lieu'].unique() if l not in ["Non défini", ""]]
            
            # Filtre : On garde si "salle", "amphi", "S" ou "A" est dans le nom (insensible à la casse)
            mots_cles = ["SALLE", "AMPHI", "S", "A"] 
            tous_locaux = sorted([l for l in tous_lieux if any(m in l.upper() for m in mots_cles)])
            
            def identifier_vides(group):
                locaux_occupes = group['Lieu'].unique()
                vides = [loc for loc in tous_locaux if loc not in locaux_occupes]
                if not vides:
                    return "<span style='color:red; font-size:9px;'>⚠️ Aucun local vide</span>"
                # Affichage en pastilles vertes
                return "".join([f"<span class='locaux-vides'>{v}</span>" for v in vides])

            grid_vides = df.groupby(['Horaire', 'Jours']).apply(identifier_vides).unstack('Jours').reindex(index=horaires, columns=jours).fillna("".join([f"<span class='locaux-vides'>{v}</span>" for v in tous_locaux]))
            st.write(grid_vides.to_html(escape=False), unsafe_allow_html=True)