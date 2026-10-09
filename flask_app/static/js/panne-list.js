// Rendu et filtres de la liste des pannes
// Dépend des données globales chargées par app.js et de formatReportDate().

    function getPanneFilterCode(eta) {
      if (eta === 'EC') return 'EP';
      if (eta === 'AT') return 'ER';
      if (eta === 'NR') return 'IR';
      return eta || 'EP';
    }

    function setPanneFilter(filter) {
      currentPanneFilter = filter;
      document.querySelectorAll('.panne-filter-btn').forEach(b => {
        b.classList.remove('bg-slate-900', 'text-white');
        b.classList.add('bg-slate-100', 'text-slate-700');
      });
      const active = document.getElementById(filter === 'ALL' ? 'panne-filter-all' : 'panne-filter-' + filter);
      if (active) {
        active.classList.remove('bg-slate-100', 'text-slate-700');
        active.classList.add('bg-slate-900', 'text-white');
      }
      renderPannes();
    }

    function applyPanneFilters() {
      renderPannes();
    }

    function renderPannes() {
      const tbody = document.getElementById('pannes-table-body');
      if (!tbody) return;

      const query = (document.getElementById('pannes-search-input')?.value || '').toLowerCase().trim();
      const filteredPannes = allPannes.filter(p => {
        const code = getPanneFilterCode(p.eta_pan);
        const matchFilter = currentPanneFilter === 'ALL' || code === currentPanneFilter;
        const text = [
          p.dat_pan, p.num_inv, p.num_ser, p.marque_mat, p.model_mat,
          p.type_nom, p.diag_pan, p.nom_uti, p.pnom_uti, p.technicien,
          p.lieu_reparation, p.obs_rep, p.eta_pan
        ].filter(Boolean).join(' ').toLowerCase();
        return matchFilter && (!query || text.includes(query));
      });

      if (filteredPannes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="p-6 text-center text-slate-400 text-xs">Aucune panne ne correspond aux critères de recherche ou de filtre.</td></tr>';
        return;
      }

      const panneLabels = {
        EP: 'En panne', ER: 'En réparation', RP: 'Réparé', IR: 'Irréparable',
        EC: 'En panne', AT: 'En réparation', NR: 'Irréparable'
      };

      tbody.innerHTML = filteredPannes.map(p => {
        const state = panneLabels[p.eta_pan] || p.eta_pan || 'En panne';
        let statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800">En panne</span>';
        if (p.eta_pan === 'ER' || p.eta_pan === 'AT') statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">En réparation</span>';
        if (p.eta_pan === 'RP') statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">Réparé</span>';
        if (p.eta_pan === 'IR' || p.eta_pan === 'NR') statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-slate-200 text-slate-700">Irréparable</span>';

        const lieu = p.lieu_reparation || '-';
        const dates = [
          p.dat_env_rep ? 'Envoi: ' + formatReportDate(p.dat_env_rep) : '',
          p.dat_ret_rep ? 'Retour: ' + formatReportDate(p.dat_ret_rep) : ''
        ].filter(Boolean).join(' • ');

        return `
          <tr class="hover:bg-slate-50 transition text-xs">
            <td class="p-3 font-mono text-slate-500">${p.dat_pan || '-'}</td>
            <td class="p-3">
              <div class="font-bold text-slate-800">${p.marque_mat || ''} ${p.model_mat || ''}</div>
              <div class="text-[11px] text-slate-400">${p.type_nom || ''}</div>
            </td>
            <td class="p-3 font-mono text-[11px] text-slate-600">
              <div><span class="text-slate-400">Inv:</span> ${p.num_inv || '-'}</div>
              <div><span class="text-slate-400">Série:</span> ${p.num_ser || '-'}</div>
            </td>
            <td class="p-3 max-w-xs text-slate-700 leading-snug">${p.diag_pan || ''}</td>
            <td class="p-3 text-slate-700">
              <div class="font-semibold">${p.nom_uti ? ((p.pnom_uti || '') + ' ' + p.nom_uti).trim() : 'Non assigné'}</div>
            </td>
            <td class="p-3 text-slate-600">
              <div>${p.technicien || 'Tech DSI'}</div>
              <div class="text-[11px] text-slate-400 mt-1">${lieu}</div>
              <div class="text-[11px] text-slate-400 mt-1">${dates}</div>
            </td>
            <td class="p-3">
              ${statusBadge}
              <div class="text-[11px] text-slate-500 mt-1">${p.obs_rep || ''}</div>
            </td>
            <td class="p-3 text-right min-w-[155px]">
              <div class="grid grid-cols-2 gap-1.5 w-full max-w-[150px] ml-auto">
                <button onclick="openRepairModal(${p.id_pan})" class="col-span-2 w-full px-2 py-1 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded text-[11px] font-semibold" title="Gérer le traitement de la panne">
                  <i class="fa-solid fa-screwdriver-wrench"></i> Traitement
                </button>
                            ${p.eta_pan !== 'RP' && p.eta_pan !== 'IR' ? `
                <button onclick="markRepaired(${p.id_pan})" class="w-full px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold" title="Marquer comme réparé">
                  <i class="fa-solid fa-check"></i> Réparé
                </button>
              ` : ''}
                <button onclick="viewReport(${p.id_pan})" class="w-full px-2 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded text-[11px] font-semibold" title="Imprimer fiche">
                  <i class="fa-solid fa-print"></i> Fiche
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    function populatePanneSelect() {
      const sel = document.getElementById('panne-mat-id');
      if (!sel) return;
      sel.innerHTML = allMateriels.map(m => `
        <option value="${m.id_mat}">${m.num_inv} - ${m.marque_mat || ''} ${m.model_mat || ''} (${m.nom_uti || 'Non assigné'})</option>
      `).join('');
    }
