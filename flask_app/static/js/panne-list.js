// Rendu et filtres de la liste des pannes
// Dépend des données globales chargées par app.js et de formatReportDate().

    function getPanneUserDisplay(p) {
      const clean = value => {
        const text = String(value || '').trim();
        return /^(non identifié|prénom inconnu)$/i.test(text) ? '' : text;
      };
      const nom = clean(p.nom_uti);
      const prenom = clean(p.pnom_uti);
      const hasFullName = Boolean(nom && prenom);
      return {
        hasFullName,
        label: hasFullName ? prenom + ' ' + nom : ''
      };
    }

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

      const panneLabels = {
        EP: 'En panne', ER: 'En réparation', RP: 'Réparé', IR: 'Irréparable',
        EC: 'En panne', AT: 'En réparation', NR: 'Irréparable'
      };
      const panneStatusLabel = eta => panneLabels[eta] || eta || 'En panne';
      const query = (document.getElementById('pannes-search-input')?.value || '').toLowerCase().trim();
      const columnValue = id => (document.getElementById(id)?.value || '').toLowerCase().trim();
      const columnFilters = {
        date: columnValue('pannes-filter-date'),
        materiel: columnValue('pannes-filter-materiel'),
        inventaire: columnValue('pannes-filter-inventaire'),
        diagnostic: columnValue('pannes-filter-diagnostic'),
        utilisateur: columnValue('pannes-filter-utilisateur'),
        technicien: columnValue('pannes-filter-technicien'),
        statut: document.getElementById('pannes-filter-statut')?.value || 'ALL',
        actions: document.getElementById('pannes-filter-actions')?.value || 'ALL'
      };
      const contains = (value, filter) => !filter || String(value || '').toLowerCase().includes(filter);
      const filteredPannes = allPannes.filter(p => {
        const code = getPanneFilterCode(p.eta_pan);
        // Le filtre « Irréparable » exclut les équipements déjà réformés,
        // afin de ne conserver que ceux pour lesquels une décision reste à prendre.
        const matchFilter = currentPanneFilter === 'ALL'
          || (code === currentPanneFilter
            && !(currentPanneFilter === 'IR' && p.etat_reforme === 'REFORME'));
        const materiel = [p.marque_mat, p.model_mat, p.type_nom].filter(Boolean).join(' ');
        const inventaire = [p.num_inv, p.num_ser].filter(Boolean).join(' ');
        const utilisateur = [p.nom_uti, p.pnom_uti].filter(Boolean).join(' ');
        const technicien = [p.technicien, p.lieu_reparation, p.obs_rep].filter(Boolean).join(' ');
        const statusText = [p.eta_pan, panneStatusLabel(p.eta_pan), p.etat_reforme,
          p.etat_reforme === 'PROPOSEE' ? 'proposé réforme' : '',
          p.etat_reforme === 'REFORME' ? 'réformé' : ''].filter(Boolean).join(' ');
        const matchColumnFilters =
          contains(p.dat_pan, columnFilters.date) &&
          contains(materiel, columnFilters.materiel) &&
          contains(inventaire, columnFilters.inventaire) &&
          contains(p.diag_pan, columnFilters.diagnostic) &&
          contains(utilisateur, columnFilters.utilisateur) &&
          contains(technicien, columnFilters.technicien) &&
          (columnFilters.statut === 'ALL' ||
            (columnFilters.statut === 'PROPOSEE' && p.etat_reforme === 'PROPOSEE') ||
            (columnFilters.statut === 'REFORME' && p.etat_reforme === 'REFORME') ||
            (['EP', 'ER', 'RP', 'IR'].includes(columnFilters.statut) && code === columnFilters.statut));
        const hasRepairAction = p.eta_pan !== 'RP' && p.eta_pan !== 'IR';
        const matchActions = columnFilters.actions === 'ALL' ||
          (columnFilters.actions === 'REPARER' && hasRepairAction) ||
          (columnFilters.actions === 'SANS_REPARER' && !hasRepairAction);
        const text = [
          p.dat_pan, p.num_inv, p.num_ser, p.marque_mat, p.model_mat,
          p.type_nom, p.diag_pan, p.nom_uti, p.pnom_uti, p.technicien,
          p.lieu_reparation, p.obs_rep, p.eta_pan, p.etat_reforme
        ].filter(Boolean).join(' ').toLowerCase();
        return matchFilter && matchColumnFilters && matchActions && (!query || text.includes(query));
      });

      if (filteredPannes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="p-6 text-center text-slate-400 text-xs">Aucune panne ne correspond aux critères de recherche ou de filtre.</td></tr>';
        return;
      }



      tbody.innerHTML = filteredPannes.map(p => {
        const state = panneLabels[p.eta_pan] || p.eta_pan || 'En panne';
        let statusBadge = '<span class="flat-status-pill bg-rose-50 text-rose-700 border border-rose-200"><span class="status-dot bg-rose-600 animate-pulse"></span>En panne</span>';
        if (p.eta_pan === 'ER' || p.eta_pan === 'AT') statusBadge = '<span class="flat-status-pill bg-amber-50 text-amber-800 border border-amber-200"><span class="status-dot bg-amber-500"></span>En réparation</span>';
        if (p.eta_pan === 'RP') statusBadge = '<span class="flat-status-pill bg-emerald-50 text-emerald-700 border border-emerald-200"><span class="status-dot bg-emerald-500"></span>Réparé</span>';
        if (p.eta_pan === 'IR' || p.eta_pan === 'NR') statusBadge = '<span class="flat-status-pill bg-slate-100 text-slate-700 border border-slate-300"><span class="status-dot bg-slate-500"></span>Irréparable</span>';

        let reformBadge = '';
        if (p.etat_reforme === 'PROPOSEE') {
          reformBadge = '<span class="flat-status-pill bg-amber-50 text-amber-700 border border-amber-200 text-[10px]" title="Équipement proposé à la réforme"><i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i>Proposé réforme</span>';
        } else if (p.etat_reforme === 'REFORME') {
          reformBadge = '<span class="flat-status-pill bg-slate-100 text-slate-700 border border-slate-300 text-[10px]" title="Équipement réformé"><i class="fa-solid fa-ban text-slate-500 mr-1"></i>Réformé</span>';
        }

        const lieu = p.lieu_reparation || '-';
        const dates = [
          p.dat_env_rep ? 'Envoi: ' + formatReportDate(p.dat_env_rep) : '',
          p.dat_ret_rep ? 'Retour: ' + formatReportDate(p.dat_ret_rep) : ''
        ].filter(Boolean).join(' • ');

        return `
          <tr class="hover:bg-slate-50/80 transition-colors duration-150 text-xs">
            <td class="p-3 font-mono text-slate-500 tabular-nums">${p.dat_pan || '-'}</td>
            <td class="p-3">
              <div class="font-bold text-slate-900 leading-snug">${p.marque_mat || ''} ${p.model_mat || ''}</div>
              <div class="text-[11px] text-slate-500 mt-0.5">${p.type_nom || ''}</div>
            </td>
            <td class="p-3">
              <div><span class="flat-inv-tag">${p.num_inv || 'SANS-INV'}</span></div>
              <div class="font-mono text-slate-500 text-[11px] mt-1 tracking-tight">SN: ${p.num_ser || '-'}</div>
            </td>
            <td class="p-3 max-w-xs text-slate-700 leading-snug">${p.diag_pan || ''}</td>
            <td class="p-3 text-slate-700">
              <div class="font-semibold text-slate-900">${getPanneUserDisplay(p).hasFullName ? '<i class="fa-solid fa-user text-blue-600 text-[10px] mr-1" title="Utilisateur identifié" aria-label="Utilisateur identifié"></i>' + getPanneUserDisplay(p).label : '<span class="text-slate-400 italic">Non assigné</span>'}</div>
            </td>
            <td class="p-3 text-slate-600">
              <div class="font-medium text-slate-800">${p.technicien || 'Tech DSI'}</div>
              <div class="text-[11px] text-slate-500 mt-0.5">${lieu}</div>
              ${dates ? `<div class="text-[11px] text-slate-500 mt-0.5 tabular-nums">${dates}</div>` : ''}
            </td>
            <td class="p-3 whitespace-nowrap">
              <div class="flex flex-col items-start gap-1">
                ${statusBadge}
                ${reformBadge}
              </div>
              ${p.obs_rep ? `<div class="text-[11px] text-slate-500 mt-1 max-w-[160px] truncate" title="${p.obs_rep}">${p.obs_rep}</div>` : ''}
            </td>
            <td class="p-3 text-right min-w-[155px] whitespace-nowrap">
              <div class="grid grid-cols-2 gap-1.5 w-full max-w-[155px] ml-auto">
                <button onclick="openRepairModal(${p.id_pan})" class="col-span-2 w-full px-2 py-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded text-[11px] font-semibold flex items-center justify-center gap-1 transition" title="Gérer le traitement de la panne">
                  <i class="fa-solid fa-screwdriver-wrench text-indigo-600"></i> Traitement
                </button>
                ${p.eta_pan !== 'RP' && p.eta_pan !== 'IR' ? `
                <button onclick="markRepaired(${p.id_pan})" class="w-full px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold flex items-center justify-center gap-1 transition" title="Marquer comme réparé">
                  <i class="fa-solid fa-check"></i> Réparé
                </button>
              ` : ''}
                <button onclick="viewReport(${p.id_pan})" class="w-full px-2 py-1 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded text-[11px] font-semibold flex items-center justify-center gap-1 transition" title="Imprimer fiche">
                  <i class="fa-solid fa-print text-blue-600"></i> Fiche
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
