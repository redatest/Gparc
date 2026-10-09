    async function openAffectationHistory(matId) {
      const content = document.getElementById('affect-history-content');
      const title = document.getElementById('affect-history-equipment');
      if (!content) return;

      const mat = allMateriels.find(m => String(m.id_mat) === String(matId));
      if (title && mat) {
        title.innerText = (mat.num_inv || 'Équipement') + ' — ' + (mat.marque_mat || '') + ' ' + (mat.model_mat || '');
      }

      content.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs"><i class="fa-solid fa-spinner fa-spin text-lg mb-2"></i><p>Chargement de l\'historique...</p></div>';
      document.getElementById('modal-affectation-history').classList.remove('hidden');

      try {
        const res = await fetch('/api/materiels/' + matId + '/historique');
        const history = await res.json().catch(() => []);
        if (!res.ok) throw new Error(history.error || 'Erreur de chargement');

        if (!history.length) {
          content.innerHTML = '<div class="text-center py-10 text-slate-400 text-xs"><i class="fa-solid fa-clock-rotate-left text-3xl mb-2"></i><p>Aucun événement enregistré pour cet équipement.</p><p class="mt-1">Les affectations, pannes et réformes seront automatiquement tracées ici.</p></div>';
          return;
        }

        content.innerHTML = history.map((h, index) => {
          let icon = 'fa-user-check';
          let iconClass = 'bg-emerald-100 text-emerald-700';
          let typeLabel = 'AFFECTATION';
          let detailHtml = escapeHtml(h.detail || '');
          let extraHtml = '';

          if (h.type_evenement === 'PANNE') {
            icon = 'fa-triangle-exclamation';
            iconClass = 'bg-rose-100 text-rose-700';
            typeLabel = 'PANNE';
            const p = h.procedure || {};
            extraHtml =
              '<div class="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">' +
                '<div><span class="text-slate-400">Statut :</span> <strong class="text-slate-700">' + escapeHtml(p.statut || '-') + '</strong></div>' +
                '<div><span class="text-slate-400">Type :</span> <strong class="text-slate-700">' + escapeHtml(p.type || '-') + '</strong></div>' +
                '<div><span class="text-slate-400">Technicien :</span> <strong class="text-slate-700">' + escapeHtml(p.technicien || '-') + '</strong></div>' +
                '<div><span class="text-slate-400">Coût :</span> <strong class="text-slate-700">' + '######' + '</strong></div>' +
              '</div>' +
              ((p.observation_reparation || p.pieces_remplacees || p.recommandations) ?
                '<div class="mt-2 pt-2 border-t border-slate-200 text-[11px] text-slate-600">' +
                  (p.observation_reparation ? '<div><span class="font-semibold">Réparation :</span> ' + escapeHtml(p.observation_reparation) + '</div>' : '') +
                  (p.pieces_remplacees ? '<div><span class="font-semibold">Pièces :</span> ' + '#######' + '</div>' : '') +
                  (p.recommandations ? '<div><span class="font-semibold">Recommandations :</span> ' + escapeHtml(p.recommandations) + '</div>' : '') +
                '</div>' : '');
          } else if (h.type_evenement === 'REFORME') {
            icon = 'fa-recycle';
            iconClass = h.reforme?.etat === 'REFORME' ? 'bg-slate-100 text-slate-700' : 'bg-amber-100 text-amber-700';
            typeLabel = 'RÉFORME';
            const r = h.reforme || {};
            detailHtml = escapeHtml(r.motif || h.detail || '');
            extraHtml =
              '<div class="mt-2 text-[11px]">' +
                '<span class="px-2 py-0.5 rounded-full font-bold ' + (r.etat === 'REFORME' ? 'bg-slate-100 text-slate-700' : 'bg-amber-100 text-amber-800') + '">' +
                  escapeHtml(h.libelle || '-') +
                '</span>' +
                '<span class="text-slate-400 ml-2">Avant : ' + escapeHtml(r.ancien_etat || 'AUCUNE') + '</span>' +
              '</div>';
          } else {
            if (h.libelle === 'Changement de structure') {
              icon = 'fa-sitemap';
              iconClass = 'bg-blue-100 text-blue-700';
            } else if (h.libelle === 'Changement d’utilisateur') {
              icon = 'fa-user-pen';
              iconClass = 'bg-amber-100 text-amber-700';
            }
          }

          const date = h.date_evenement
            ? new Date(String(h.date_evenement).replace(' ', 'T')).toLocaleString('fr-FR')
            : '-';

          return '<div class="relative flex gap-3 pb-5 ' + (index < history.length - 1 ? 'border-l-2 border-slate-200 ml-4 pl-5' : 'ml-4 pl-5') + '">' +
            '<div class="absolute -left-[13px] top-0 w-6 h-6 rounded-full ' + iconClass + ' flex items-center justify-center border-2 border-white shadow-sm"><i class="fa-solid ' + icon + ' text-[10px]"></i></div>' +
            '<div class="flex-1 bg-slate-50 border border-slate-200 rounded-xl p-3">' +
              '<div class="flex items-center justify-between gap-2">' +
                '<div class="text-xs font-bold text-slate-800">' + escapeHtml(h.libelle || 'Événement') + '</div>' +
                '<span class="text-[9px] font-bold tracking-wide text-slate-400">' + typeLabel + '</span>' +
              '</div>' +
              '<div class="text-[11px] text-slate-400 mt-0.5">' + escapeHtml(date) + '</div>' +
              '<div class="mt-2 text-xs text-slate-700">' + detailHtml + '</div>' +
              extraHtml +
            '</div>' +
          '</div>';
        }).join('');
      } catch (err) {
        content.innerHTML = '<div class="text-center py-8 text-rose-500 text-xs"><i class="fa-solid fa-circle-exclamation text-xl mb-2"></i><p>Impossible de charger l\'historique.</p><p class="mt-1 text-slate-400">' + escapeHtml(err.message || '') + '</p></div>';
      }
    }
