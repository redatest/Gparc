// Rendu du parc informatique, badges d’état et pagination.
// Les données et filtres sont partagés avec app.js.

    function equipmentStatusLabel(m) {
      const status = m.statut_mat || (m.etat_reforme === 'PROPOSEE' ? 'PR' : m.etat_reforme === 'REFORME' ? 'RF' : 'ES');
      return { ES: 'En service', PR: 'Proposé à la réforme', RF: 'Réformé' }[status] || 'En service';
    }

    function equipmentEtatLabel(m) {
      return { BON: 'Bon', PANNE: 'En panne', IRREPARABLE: 'Irréparable' }[m.etat_mat] || 'Bon';
    }

    function equipmentStatusBadge(m) {
      const status = m.statut_mat || 'ES';
      if (status === 'PR') return '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-orange-100 text-orange-800">Proposé à la réforme</span>';
      if (status === 'RF') return '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-200 text-slate-700">Réformé</span>';
      return '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-800">En service</span>';
    }

    function equipmentEtatBadge(m) {
      const etat = m.etat_mat || 'BON';
      if (etat === 'PANNE') return '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800">En panne</span>';
      if (etat === 'IRREPARABLE') return '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-200 text-slate-700">Irréparable</span>';
      return '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800">Bon</span>';
    }

    function renderMateriels() {
      const grid = document.getElementById('materiels-grid');
      const tableBody = document.getElementById('materiels-table-body');
      const countBadge = document.getElementById('materiels-count-badge');
      const query = document.getElementById('search-input') ? document.getElementById('search-input').value.toLowerCase().trim() : '';

      const filtered = allMateriels.filter(m => {
        const equipmentStatus = m.statut_mat || (m.etat_reforme === 'PROPOSEE' ? 'PR' : m.etat_reforme === 'REFORME' ? 'RF' : 'ES');
        const matchFilter = currentFilter === 'ALL' || equipmentStatus === currentFilter;
        const text = `${m.num_inv || ''} ${m.num_ser || ''} ${m.model_mat || ''} ${m.marque_mat || ''} ${m.nom_uti || ''} ${m.structure_nom || ''} ${m.ip || ''} ${m.cpu || ''} ${m.se || ''} ${m.ordi || ''}`.toLowerCase();
        const matchSearch = !query || text.includes(query);
        return matchFilter && matchSearch;
      });

      if (countBadge) {
        countBadge.innerText = `${filtered.length} équipement${filtered.length > 1 ? 's' : ''}`;
      }

      // 1. Rendu de la grille (Interface Simple)
      if (grid) {
        if (filtered.length === 0) {
          grid.innerHTML = `
            <div class="col-span-full p-8 text-center bg-white rounded-xl border border-slate-200 text-slate-500">
              <i class="fa-solid fa-inbox text-3xl mb-2 text-slate-400"></i>
              <p class="font-medium text-sm">Aucun équipement ne correspond à vos critères de recherche.</p>
            </div>
          `;
        } else {
          grid.innerHTML = filtered.map(m => {
            const badge = '<div class="flex flex-col items-end gap-1">' + equipmentStatusBadge(m) + equipmentEtatBadge(m) + '</div>';

            const typeLabel = (m.type_nom || '').toLowerCase();
            let equipmentIcon = 'fa-desktop';
            if (typeLabel.includes('imprim')) equipmentIcon = 'fa-print';
            else if (typeLabel.includes('serveur')) equipmentIcon = 'fa-server';
            else if (typeLabel.includes('réseau') || typeLabel.includes('switch') || typeLabel.includes('routeur')) equipmentIcon = 'fa-network-wired';
            else if (typeLabel.includes('téléphone')) equipmentIcon = 'fa-phone';
            else if (typeLabel.includes('écran') || typeLabel.includes('moniteur')) equipmentIcon = 'fa-display';
            else if (typeLabel.includes('portable')) equipmentIcon = 'fa-laptop';

            return `
              <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-md transition flex flex-col">
                <div class="relative h-40 bg-slate-100 overflow-hidden">
                  <div class="w-24 h-24 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-lg">
                    <i class="fa-solid ${equipmentIcon} text-5xl"></i>
                  </div>
                  <div class="absolute top-2.5 right-2.5">${badge}</div>
                  <div class="absolute bottom-2.5 left-2.5 bg-slate-900/80 backdrop-blur-xs text-white text-[11px] font-mono px-2 py-0.5 rounded">
                    ${m.num_inv || 'SANS-INV'}
                  </div>
                </div>
                <div class="p-4 flex-1 flex flex-col justify-between">
                  <div>
                    <h4 class="font-bold text-slate-900 text-base mb-0.5">${m.marque_mat || ''} ${m.model_mat || 'Équipement Standard'}</h4>
                    <p class="text-xs text-slate-500 font-medium mb-3">${m.type_nom || 'Matériel Informatique'}</p>
                    
                    <div class="space-y-1.5 text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <div class="flex justify-between">
                        <span class="text-slate-400">N° Série :</span>
                        <span class="font-mono font-medium text-slate-700">${m.num_ser || '-'}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-slate-400">Affecté à :</span>
                        <span class="font-semibold text-slate-800">${m.nom_uti ? (m.pnom_uti || '') + ' ' + m.nom_uti : 'Non assigné'}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-slate-400">Direction :</span>
                        <span class="text-slate-700">${m.structure_nom || 'DSI'}</span>
                      </div>
                      ${m.cpu ? `<div class="flex justify-between"><span class="text-slate-400">Processeur :</span><span class="text-slate-700">${m.cpu}</span></div>` : ''}
                      ${m.ram ? `<div class="flex justify-between"><span class="text-slate-400">Mémoire / Disque :</span><span class="text-slate-700">${m.ram} Go RAM / ${m.disk || 512} Go SSD</span></div>` : ''}
                    </div>
                  </div>

                  <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    <div class="flex items-center gap-3">
                      <button onclick="openAffectationHistory(${m.id_mat})" class="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 cursor-pointer" title="Historique de l’équipement">
                        <i class="fa-solid fa-clock-rotate-left"></i> Historique
                      </button>
                      <button onclick="quickPanneFor(${m.id_mat})" class="text-xs font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 cursor-pointer">
                        <i class="fa-solid fa-triangle-exclamation"></i> Panne
                      </button>
                    </div>
                    <div class="text-[11px] font-mono text-slate-400">${m.ip ? 'IP: ' + m.ip : ''}</div>
                  </div>
                </div>
              </div>
            `;
          }).join('');
        }
      }

      // 2. Rendu du tableau d'inventaire complet (Parc Équipements)
      if (tableBody) {
        const totalPages = Math.max(1, Math.ceil(filtered.length / materielsPageSize));
        if (materielsCurrentPage > totalPages) materielsCurrentPage = totalPages;
        const pageStart = (materielsCurrentPage - 1) * materielsPageSize;
        const pageItems = filtered.slice(pageStart, pageStart + materielsPageSize);

        if (filtered.length === 0) {
          tableBody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-400">Aucun équipement trouvé correspondant aux critères.</td></tr>`;
        } else {
          tableBody.innerHTML = pageItems.map(m => {
            const statusBadge = equipmentStatusBadge(m);
            const etatBadge = equipmentEtatBadge(m);

            const typeLabel = (m.type_nom || '').toLowerCase();
            let equipmentIcon = 'fa-desktop';
            if (typeLabel.includes('imprim')) equipmentIcon = 'fa-print';
            else if (typeLabel.includes('serveur')) equipmentIcon = 'fa-server';
            else if (typeLabel.includes('réseau') || typeLabel.includes('switch') || typeLabel.includes('routeur')) equipmentIcon = 'fa-network-wired';
            else if (typeLabel.includes('téléphone')) equipmentIcon = 'fa-phone';
            else if (typeLabel.includes('écran') || typeLabel.includes('moniteur')) equipmentIcon = 'fa-display';
            else if (typeLabel.includes('portable')) equipmentIcon = 'fa-laptop';

            return `
              <tr class="hover:bg-slate-50 transition text-xs">
                <td class="p-3">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center shrink-0">
                      <i class="fa-solid ${equipmentIcon} text-lg"></i>
                    </div>
                    <div>
                      <div class="font-bold text-slate-900">${m.marque_mat || ''} ${m.model_mat || 'Équipement'}</div>
                      <div class="text-[11px] text-slate-500">${m.type_nom || 'Matériel'} ${m.ordi ? `&bull; <span class="font-mono text-indigo-600">${m.ordi}</span>` : ''}</div>
                    </div>
                  </div>
                </td>
                <td class="p-3">
                  <div class="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded w-max">${m.num_inv || '-'}</div>
                  <div class="font-mono text-slate-400 text-[11px] mt-0.5">SN: ${m.num_ser || '-'}</div>
                </td>
                <td class="p-3">
                  <div class="font-semibold text-slate-800">${m.nom_uti ? (m.pnom_uti || '') + ' ' + m.nom_uti : '<span class="text-slate-400 italic">Non assigné</span>'}</div>
                  <div class="text-slate-500 text-[11px]">${m.structure_nom || 'Direction Non Spécifiée'}</div>
                </td>
                <td class="p-3">
                  <div class="text-slate-800 font-medium">${m.cpu || 'CPU Standard'}</div>
                  <div class="text-slate-500 text-[11px]">${m.ram || 16} Go RAM &bull; ${m.disk || 512} Go SSD &bull; ${m.se || 'Win 11'}</div>
                </td>
                <td class="p-3">
                  <div class="font-semibold text-slate-800">${m.structure_nom || '<span class="text-slate-400 italic">Structure non spécifiée</span>'}</div>
                </td>
                <td class="p-3">${statusBadge}</td>
                <td class="p-3">${etatBadge}</td>
                <td class="p-3 text-right">
                  <div class="flex items-center justify-end gap-1.5">
                    <button onclick="openEditMaterielModal(${m.id_mat})" class="px-2.5 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded text-[11px] font-semibold flex items-center gap-1 transition" title="Modifier l'équipement">
                      <i class="fa-solid fa-pen-to-square"></i> Modifier
                    </button>
                    <button onclick="openAffectationHistory(${m.id_mat})" class="px-2.5 py-1 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded text-[11px] font-semibold flex items-center gap-1 transition" title="Historique des affectations">
                       <i class="fa-solid fa-clock-rotate-left"></i> Historique
                     </button>
                     <button onclick="quickPanneFor(${m.id_mat})" class="px-2.5 py-1 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded text-[11px] font-semibold flex items-center gap-1 transition" title="Déclarer une panne">
                      <i class="fa-solid fa-triangle-exclamation"></i> Panne
                    </button>
                    <button onclick="openNewReformeModal(${m.id_mat})" class="px-2.5 py-1 bg-amber-50 text-amber-700 hover:bg-amber-100 rounded text-[11px] font-semibold flex items-center gap-1 transition" title="Déclarer une réforme">
                      <i class="fa-solid fa-recycle"></i> Réforme
                    </button>
                    <button onclick="deleteMateriel(${m.id_mat})" class="p-1.5 text-slate-400 hover:text-rose-600 rounded transition" title="Supprimer du parc">
                      <i class="fa-solid fa-trash-can"></i>
                    </button>
                  </div>
                </td>
              </tr>
            `;
          }).join('');
        }
      }

      updateMaterielsPagination(filtered.length);
    }

    function updateMaterielsPagination(totalItems) {
      const totalPages = Math.max(1, Math.ceil(totalItems / materielsPageSize));
      const info = document.getElementById('materiels-pagination-info');
      const infoTop = document.getElementById('materiels-pagination-info-top');
      const number = document.getElementById('materiels-page-number');
      const numberTop = document.getElementById('materiels-page-number-top');
      const prev = document.getElementById('materiels-page-prev');
      const next = document.getElementById('materiels-page-next');
      const start = totalItems === 0 ? 0 : ((materielsCurrentPage - 1) * materielsPageSize) + 1;
      const end = Math.min(materielsCurrentPage * materielsPageSize, totalItems);

      if (info) info.textContent = totalItems === 0
        ? 'Aucun équipement à afficher'
        : 'Affichage de ' + start + ' à ' + end + ' sur ' + totalItems + ' équipement' + (totalItems > 1 ? 's' : '');
      if (number) number.textContent = 'Page ' + materielsCurrentPage + ' / ' + totalPages;
      if (numberTop) numberTop.textContent = 'Page ' + materielsCurrentPage + ' / ' + totalPages;
      if (infoTop) infoTop.textContent = info ? info.textContent : '';
      if (prev) prev.disabled = materielsCurrentPage <= 1 || totalItems === 0;
      if (next) next.disabled = materielsCurrentPage >= totalPages || totalItems === 0;
    }

    function changeMaterielsPage(direction) {
      const query = document.getElementById('search-input')?.value.toLowerCase().trim() || '';
      const filteredCount = allMateriels.filter(m => {
        const equipmentStatus = m.statut_mat || (m.etat_reforme === 'PROPOSEE' ? 'PR' : m.etat_reforme === 'REFORME' ? 'RF' : 'ES');
        const matchFilter = currentFilter === 'ALL' || equipmentStatus === currentFilter;
        const text = (m.num_inv || '') + ' ' + (m.num_ser || '') + ' ' + (m.model_mat || '') + ' ' + (m.marque_mat || '') + ' ' + (m.nom_uti || '') + ' ' + (m.structure_nom || '') + ' ' + (m.ip || '') + ' ' + (m.cpu || '') + ' ' + (m.se || '') + ' ' + (m.ordi || '');
        return matchFilter && (!query || text.toLowerCase().includes(query));
      }).length;
      const totalPages = Math.max(1, Math.ceil(filteredCount / materielsPageSize));
      materielsCurrentPage = Math.min(Math.max(1, materielsCurrentPage + direction), totalPages);
      renderMateriels();
    }

    function changeMaterielsPageSize(value) {
      materielsPageSize = parseInt(value, 10) || 10;
      materielsCurrentPage = 1;
      renderMateriels();
    }

