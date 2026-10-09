    // RENDU DU SUIVI DES RÉFORMES
    function renderReformes() {
      const tbody = document.getElementById('reformes-table-body');
      if (!tbody) return;
      const filter = currentReformeFilter;
      const query = (document.getElementById('reforme-search-input')?.value || '').toLowerCase().trim();

      // Dénombrer le total des équipements affectés à chaque lot de réforme
      const lotEquipmentCounts = {};
      (allMateriels || []).forEach(item => {
        if (item.lot_reforme) {
          const key = String(item.lot_reforme).trim();
          if (key) {
            lotEquipmentCounts[key] = (lotEquipmentCounts[key] || 0) + 1;
          }
        }
      });

      const rows = allMateriels.filter(m => {
        const matchState = (m.etat_reforme === 'PROPOSEE' || m.etat_reforme === 'REFORME') && (filter === 'ALL' || m.etat_reforme === filter);
        const text = [
          m.num_inv, m.num_ser, m.marque_mat, m.model_mat, m.type_nom,
          m.nom_uti, m.pnom_uti, m.structure_nom, m.motif_reforme,
          m.annee_reforme, m.lot_reforme
        ].filter(Boolean).join(' ').toLowerCase();
        return matchState && (!query || text.includes(query));
      });
      const badge = document.getElementById('reformes-count-badge');
      if (badge) badge.innerText = rows.length + ' équipement' + (rows.length > 1 ? 's' : '');
      if (!rows.length) { tbody.innerHTML = '<tr><td colspan="8" class="p-8 text-center text-slate-400">Aucun équipement dans cette sélection.</td></tr>'; return; }
      tbody.innerHTML = rows.map(m => {
        const stateBadge = m.etat_reforme === 'REFORME' ? '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700">Réformé</span>' : '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">Proposé à la réforme</span>';
        const lotVal = m.lot_reforme ? String(m.lot_reforme).trim() : '';
        const lotTotal = lotVal ? (lotEquipmentCounts[lotVal] || 1) : 0;
        const lotDisplay = lotVal ? (escapeHtml(lotVal) + ' (' + lotTotal + ')')  : '—';

        return '<tr class="hover:bg-slate-50 transition text-xs">' +
          '<td class="p-3"><div class="font-bold text-slate-900">' + escapeHtml((m.marque_mat || '') + ' ' + (m.model_mat || 'Équipement')) + '</div><div class="text-[11px] text-slate-500">' + escapeHtml(m.type_nom || 'Matériel') + '</div></td>' +
          '<td class="p-3"><div class="font-mono font-bold text-blue-700">' + escapeHtml(m.num_inv || '-') + '</div><div class="font-mono text-slate-400 text-[11px]">SN: ' + escapeHtml(m.num_ser || '-') + '</div></td>' +
          '<td class="p-3"><div class="font-semibold text-slate-800">' + escapeHtml(m.nom_uti ? ((m.pnom_uti || '') + ' ' + m.nom_uti).trim() : 'Non assigné') + '</div><div class="text-slate-500 text-[11px]">' + escapeHtml(m.structure_nom || 'Direction Non Spécifiée') + '</div></td>' +
          '<td class="p-3">' + stateBadge + '</td>' +
          '<td class="p-3"><div>' + escapeHtml(m.motif_reforme || '—') + '</div><div class="text-[10px] text-slate-400 mt-1">Date : ' + escapeHtml(m.date_reforme ? new Date(m.date_reforme + 'T00:00:00').toLocaleDateString('fr-FR') : '—') + '</div></td>' +
          '<td class="p-3 font-semibold text-slate-700">' + escapeHtml(m.annee_reforme || '—') + '</td>' +
          '<td class="p-3 font-mono font-semibold text-slate-700">' + lotDisplay + '</td>' +
          '<td class="p-3 text-right"><button onclick="openNewReformeModal(' + m.id_mat + ')" class="px-2.5 py-1 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded text-[11px] font-semibold"><i class="fa-solid fa-pen-to-square"></i> Modifier</button></td>' +
          '</tr>';
      }).join('');
    }
