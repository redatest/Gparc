    let allMateriels = [];
    let allPannes = [];
    let allParametres = [];
    let allStructures = [];
    let allTypes = [];
    let references = { structures: [], types: [], modeles: [], utilisateurs: [], parametres: [] };
    let allOracleHistory = [];
    let currentFilter = 'ES';
    let materielsCurrentPage = 1;
    let materielsPageSize = 10;
    let currentView = 'materiels';
    let currentParamCat = 'all';
    let editingMaterielId = null;
    let currentReformeFilter = 'ALL';
    let currentPanneFilter = 'ALL';

    // Chargement initial
    window.addEventListener('DOMContentLoaded', () => {
      loadAllData();
    });

    async function loadAllData() {
      const refreshIcon = document.getElementById('refresh-icon');
      if (refreshIcon) refreshIcon.classList.add('fa-spin');
      try {
        const [statsRes, matRes, panRes, paramRes, structuresRes, referencesRes, oraHistRes] = await Promise.all([
          fetch('/api/stats').then(r => r.json()),
          fetch('/api/materiels').then(r => r.json()),
          fetch('/api/pannes').then(r => r.json()),
          fetch('/api/parametres').then(r => r.json()).catch(() => []),
          fetch('/api/structures').then(r => r.json()).catch(() => []),
          fetch('/api/references').then(r => r.json()).catch(() => ({ structures: [], types: [], modeles: [], utilisateurs: [], parametres: [] })),
          fetch('/api/oracle-sync/history').then(r => r.json()).catch(() => [])
        ]);

        allMateriels = matRes || [];
        allPannes = panRes || [];
        allParametres = paramRes || [];
        allStructures = referencesRes?.structures || structuresRes || [];
        allTypes = referencesRes?.types || [];
        references = referencesRes || references;
        allOracleHistory = oraHistRes || [];

        // Mise à jour des KPI
        document.getElementById('kpi-total').innerText = statsRes.totalEquipements || allMateriels.length;
        document.getElementById('kpi-op').innerText = statsRes.operationnels ?? allMateriels.filter(m => m.etat_mat === 'BON').length;
        document.getElementById('kpi-pa').innerText = statsRes.enPanne ?? allMateriels.filter(m => m.etat_mat === 'PANNE').length;
        document.getElementById('kpi-re').innerText = statsRes.enReparation ?? allMateriels.filter(m => m.etat_mat === 'IRREPARABLE').length;

        // Compteurs rapides dans le menu "Pannes & Interventions"
        const panneNavCount = document.getElementById('panne-nav-count');
        const reparationNavCount = document.getElementById('reparation-nav-count');
        if (panneNavCount) panneNavCount.textContent = String(statsRes.enPanne ?? allMateriels.filter(m => m.etat_mat === 'PANNE').length);
        if (reparationNavCount) reparationNavCount.textContent = String(statsRes.enReparation ?? 0);

        // Rendu des vues
        renderMateriels();
        renderReformes();
        renderPannes();
        renderStats(statsRes);
        renderParametres();
        populateMaterielForm();
        renderOracleHistory();
        populatePanneSelect();
      } catch (err) {
        console.error('Erreur de chargement:', err);
        showToast('Erreur de connexion au serveur Flask', true);
      } finally {
        if (refreshIcon) refreshIcon.classList.remove('fa-spin');
      }
    }

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

    function renderStats(stats) {
      const typesDiv = document.getElementById('stats-types');
      const strDiv = document.getElementById('stats-structures');

      if (stats.repartitionTypes) {
        typesDiv.innerHTML = stats.repartitionTypes.map(t => `
          <div class="flex items-center justify-between text-xs p-2 bg-slate-50 rounded border border-slate-100">
            <span class="font-medium text-slate-700">${t.type}</span>
            <span class="font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">${t.count}</span>
          </div>
        `).join('');
      }

      if (stats.repartitionStructures) {
        strDiv.innerHTML = stats.repartitionStructures.map(s => `
          <div class="flex items-center justify-between text-xs p-2 bg-slate-50 rounded border border-slate-100">
            <span class="font-medium text-slate-700">${s.label} (${s.code})</span>
            <span class="font-bold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full">${s.count}</span>
          </div>
        `).join('');
      }
    }

    function populatePanneSelect() {
      const sel = document.getElementById('panne-mat-id');
      if (!sel) return;
      sel.innerHTML = allMateriels.map(m => `
        <option value="${m.id_mat}">${m.num_inv} - ${m.marque_mat || ''} ${m.model_mat || ''} (${m.nom_uti || 'Non assigné'})</option>
      `).join('');
    }

    function switchView(view) {
      currentView = view;
      document.querySelectorAll('.view-panel').forEach(p => p.classList.add('hidden'));
      document.querySelectorAll('.nav-tab').forEach(t => {
        t.classList.remove('bg-blue-600', 'text-white');
        t.classList.add('text-slate-300');
      });

      const activeTab = document.getElementById('tab-' + view);
      if (activeTab) {
        activeTab.classList.remove('text-slate-300');
        activeTab.classList.add('bg-blue-600', 'text-white');
      }

      const panel = document.getElementById('view-' + view);
      if (panel) panel.classList.remove('hidden');

    }

    function toggleView() {
      switchView('materiels');
    }

    function setFilter(filter) {
      currentFilter = filter;
      materielsCurrentPage = 1;
      document.querySelectorAll('.filter-btn').forEach(b => {
        b.classList.remove('bg-slate-900', 'text-white');
        b.classList.add('bg-slate-100', 'text-slate-700');
      });
      const filterButtonIds = { ALL: 'filter-all', ES: 'filter-es', PR: 'filter-pr', RF: 'filter-rf' };
      const activeBtn = document.getElementById(filterButtonIds[filter] || 'filter-all');
      if (activeBtn) {
        activeBtn.classList.remove('bg-slate-100', 'text-slate-700');
        activeBtn.classList.add('bg-slate-900', 'text-white');
      }
      renderMateriels();
    }

    function applyFilters() {
      materielsCurrentPage = 1;
      renderMateriels();
    }

    function populateReformeSelect(selectedId = '') {
      const sel = document.getElementById('reforme-mat-id');
      if (!sel) return;
      sel.innerHTML = '<option value="">Sélectionner un équipement...</option>' + allMateriels.map(m => '<option value="' + m.id_mat + '">' + escapeHtml((m.num_inv || 'Sans inventaire') + ' — ' + (m.marque_mat || '') + ' ' + (m.model_mat || '') + ' — ' + (m.structure_nom || 'Sans structure')) + '</option>').join('');
      if (selectedId) sel.value = String(selectedId);
    }

    function populateReformeLotSelect(selectedLot = '') {
      const sel = document.getElementById('reforme-lot');
      if (!sel) return;

      const lots = (allParametres || [])
        .filter(p => (p.categorie || '').toLowerCase() === 'lot_reforme')
        .sort((a, b) => (Number(a.ordre) || 0) - (Number(b.ordre) || 0) || String(a.valeur || '').localeCompare(String(b.valeur || '')));

      sel.innerHTML = '<option value="">Sélectionner un N° de lot...</option>' +
        lots.map(p => '<option value="' + escapeHtml(p.valeur || '') + '">' + escapeHtml(p.valeur || '') + '</option>').join('');

      // Préserver un lot déjà enregistré s'il n'existe plus dans le référentiel.
      if (selectedLot && !lots.some(p => String(p.valeur) === String(selectedLot))) {
        sel.insertAdjacentHTML('beforeend', '<option value="' + escapeHtml(selectedLot) + '">' + escapeHtml(selectedLot) + ' (lot actuel)</option>');
      }
      if (selectedLot) sel.value = String(selectedLot);
    }

    function updateReformeDeclarationFields() {
      const state = document.getElementById('reforme-etat')?.value || 'AUCUNE';
      const date = document.getElementById('reforme-date');
      const motif = document.getElementById('reforme-motif');
      const annee = document.getElementById('reforme-annee');
      const lot = document.getElementById('reforme-lot');
      const identification = document.getElementById('reforme-identification-fields');
      const isReforme = state === 'REFORME';
      if (date) date.required = isReforme;
      if (motif) motif.required = isReforme;
      if (annee) annee.required = isReforme;
      if (lot) lot.required = isReforme;
      if (identification) identification.classList.toggle('hidden', !isReforme);
      if (isReforme && annee && !annee.value) annee.value = String(new Date().getFullYear());
      if (!isReforme) {
        if (date) date.value = '';
        if (motif) motif.value = '';
        if (annee) annee.value = '';
        if (lot) lot.value = '';
      }
    }

    function updateReformeMotif() {
      const irreparable = document.getElementById('reforme-motif-irreparable');
      const obsolete = document.getElementById('reforme-motif-obsolete');
      const motif = document.getElementById('reforme-motif');
      if (!motif) return;

      const values = [];
      if (irreparable?.checked) values.push('Irréparable');
      if (obsolete?.checked) values.push('Obsolète');
      motif.value = values.join(' / ');
    }

    function syncReformeMotifShortcuts(value) {
      const text = (value || '').toLowerCase();
      const irreparable = document.getElementById('reforme-motif-irreparable');
      const obsolete = document.getElementById('reforme-motif-obsolete');
      if (irreparable) irreparable.checked = text.includes('irréparable');
      if (obsolete) obsolete.checked = text.includes('obsolète');
    }

    function openNewReformeModal(matId = '') {
      populateReformeSelect(matId);
      const mat = matId ? allMateriels.find(m => String(m.id_mat) === String(matId)) : null;
      document.getElementById('reforme-etat').value = mat?.etat_reforme || 'PROPOSEE';
      document.getElementById('reforme-date').value = mat?.date_reforme || '';
      document.getElementById('reforme-annee').value = mat?.annee_reforme || '';
      populateReformeLotSelect(mat?.lot_reforme || '');
      document.getElementById('reforme-motif').value = mat?.motif_reforme || '';
      syncReformeMotifShortcuts(mat?.motif_reforme || '');
      updateReformeDeclarationFields();
      document.getElementById('modal-reforme').classList.remove('hidden');
    }

    function openReformeFromPanne(panneId) {
      const panne = allPannes.find(p => String(p.id_pan) === String(panneId));
      if (!panne || !panne.id_mat) {
        showToast('Équipement de la panne introuvable.', true);
        return;
      }

      openNewReformeModal(panne.id_mat);

      const state = document.getElementById('reforme-etat');
      const date = document.getElementById('reforme-date');
      const motif = document.getElementById('reforme-motif');
      if (state) state.value = 'PROPOSEE';
      if (date) date.value = '';
      if (motif) motif.value = '';
      syncReformeMotifShortcuts('');
      updateReformeDeclarationFields();
    }

    async function handleSaveReforme(e) {
      e.preventDefault();
      const id = parseInt(document.getElementById('reforme-mat-id').value);
      const state = document.getElementById('reforme-etat').value;
      const date = document.getElementById('reforme-date').value || null;
      const annee = parseInt(document.getElementById('reforme-annee').value, 10) || null;
      const lot = document.getElementById('reforme-lot').value.trim() || null;
      const motif = document.getElementById('reforme-motif').value.trim() || null;
      if (!id) { showToast('Sélectionnez un équipement.', true); return; }
      if (state === 'REFORME' && (!date || !annee || !lot || !motif)) {
        showToast("La date, l'année, le N° de lot et le motif de réforme sont obligatoires.", true);
        return;
      }
      if (state === 'REFORME') {
        const lotExists = (allParametres || []).some(p =>
          (p.categorie || '').toLowerCase() === 'lot_reforme' &&
          String(p.valeur || '').trim() === lot
        );
        if (!lotExists) {
          showToast("Le N° de lot sélectionné n'existe pas dans le référentiel des lots de réforme.", true);
          return;
        }
      }
      try {
        const res = await fetch('/api/materiels/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
          etat_reforme: state,
          date_reforme: state === 'REFORME' ? date : null,
          annee_reforme: state === 'REFORME' ? annee : null,
          lot_reforme: state === 'REFORME' ? lot : null,
          motif_reforme: state === 'REFORME' ? motif : null
        }) });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) { showToast(result.error || 'Erreur lors de la déclaration de réforme.', true); return; }
        closeModal('modal-reforme');
        showToast(state === 'REFORME' ? 'Équipement réformé.' : state === 'PROPOSEE' ? 'Équipement proposé à la réforme.' : 'Équipement remis en service.');
        await loadAllData();
      } catch (err) { showToast('Erreur serveur.', true); }
    }

    function setReformeFilter(filter) {
      currentReformeFilter = filter;
      document.querySelectorAll('.reforme-filter-btn').forEach(b => {
        b.classList.remove('bg-slate-900', 'text-white');
        b.classList.add('bg-slate-100', 'text-slate-700');
      });
      const active = document.getElementById(filter === 'ALL' ? 'reforme-filter-all' : 'reforme-filter-' + filter.toLowerCase());
      if (active) {
        active.classList.remove('bg-slate-100', 'text-slate-700');
        active.classList.add('bg-slate-900', 'text-white');
      }
      renderReformes();
    }

    function applyReformeFilters() {
      renderReformes();
    }

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

    function openNewMaterielModal() {
      editingMaterielId = null;
      const title = document.getElementById('modal-materiel-title');
      const submit = document.getElementById('mat-submit-btn');
      if (title) title.innerText = "Ajouter un équipement au parc";
      if (submit) submit.innerText = "Enregistrer l'équipement";

      // Réinitialiser d'abord le formulaire, puis charger les listes.
      // L'ancien ordre effaçait la liste des modèles juste après son alimentation.
      resetMaterielForm();
      populateMaterielForm();

      document.getElementById('modal-materiel').classList.remove('hidden');
    }

    async function openEditMaterielModal(matId) {
      try {
        const res = await fetch('/api/materiels/' + matId);
        if (!res.ok) throw new Error('Équipement introuvable');
        const mat = await res.json();
        editingMaterielId = mat.id_mat;

        const title = document.getElementById('modal-materiel-title');
        const submit = document.getElementById('mat-submit-btn');
        if (title) title.innerText = "Modifier l'équipement";
        if (submit) submit.innerText = 'Enregistrer les modifications';

        populateMaterielForm();
        document.getElementById('mat-num-inv').value = mat.num_inv || '';
        document.getElementById('mat-num-ser').value = mat.num_ser || '';
        document.getElementById('mat-marque').value = mat.marque_mat || '';
        document.getElementById('mat-type').value = mat.id_typ_mat || '';
        document.getElementById('mat-str').value = mat.id_str || '';
        filterMaterielModels();
        filterMaterielUsers();
        document.getElementById('mat-model').value = mat.id_model_mat || '';
        document.getElementById('mat-user').value = mat.id_uti || '';
        document.getElementById('mat-cpu').value = mat.cpu || '';
        document.getElementById('mat-se').value = mat.se || '';
        document.getElementById('mat-ram').value = mat.ram ?? '';
        const diskSel = document.getElementById('mat-disk');
        const diskValue = mat.disk ?? '';
        if (diskSel && diskValue !== '' && !Array.from(diskSel.options).some(o => String(o.value) === String(diskValue))) {
          diskSel.insertAdjacentHTML('beforeend', '<option value="' + escapeHtml(String(diskValue)) + '">' + escapeHtml(String(diskValue)) + ' Go (valeur actuelle)</option>');
        }
        if (diskSel) diskSel.value = diskValue;
        document.getElementById('modal-materiel').classList.remove('hidden');
      } catch (err) {
        showToast("Impossible de charger l'équipement", true);
      }
    }

    function resetMaterielForm() {
      ['mat-num-inv','mat-num-ser','mat-marque','mat-type','mat-model','mat-str','mat-user','mat-cpu','mat-se','mat-ram' ,'mat-disk'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      const modelSel = document.getElementById('mat-model');
      if (modelSel) { modelSel.innerHTML = "<option value=''>Choisir d'abord une marque...</option>"; modelSel.disabled = true; }
      const userSel = document.getElementById('mat-user');
      if (userSel) userSel.value = '';
    }

    function populateMaterielForm() {
      const brandSel = document.getElementById('mat-marque');
      const typeSel = document.getElementById('mat-type');
      const strSel = document.getElementById('mat-str');
      const userSel = document.getElementById('mat-user');
      const modelSel = document.getElementById('mat-model');
      const cpuSel = document.getElementById('mat-cpu');
      const seSel = document.getElementById('mat-se');
      const ramSel = document.getElementById('mat-ram');
      const diskSel = document.getElementById('mat-disk');
      if (!brandSel || !typeSel || !strSel || !userSel || !modelSel || !cpuSel || !seSel || !ramSel || !diskSel) return;

      const brands = (references.parametres || [])
        .filter(p => p.categorie === 'marque')
        .map(p => p.valeur)
        .filter(Boolean);
      brandSel.innerHTML = '<option value="">Sélectionner une marque...</option>' +
        [...new Set(brands)].sort().map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join('');

      typeSel.innerHTML = '<option value="">Sélectionner un type...</option>' +
        (references.types || []).map(t => `<option value="${t.id_typ_mat}">${escapeHtml(t.lib_typ_mat)} (${escapeHtml(t.cod_typ_mat || '')})</option>`).join('');

      strSel.innerHTML = '<option value="">Sélectionner une structure...</option>' +
        (references.structures || []).map(st => `<option value="${st.id_str}">[${escapeHtml(st.cod_str || '')}] ${escapeHtml(st.lib_str || '')}</option>`).join('');

      modelSel.innerHTML = "<option value=''>Choisir d'abord une marque...</option>";
      const cpuParams = getParamsByCategory('cpu');
      cpuSel.innerHTML = '<option value="">Sélectionner un processeur...</option>' + cpuParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + '</option>').join('');
      const seParams = getParamsByCategory('se');
      seSel.innerHTML = '<option value="">Sélectionner un système d’exploitation...</option>' + seParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + '</option>').join('');
      const ramParams = getParamsByCategory('ram');
      ramSel.innerHTML = '<option value="">Sélectionner la RAM...</option>' + ramParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + ' Go</option>').join('');
      const diskParams = getParamsByCategory('disk');
      diskSel.innerHTML = '<option value="">Sélectionner le stockage...</option>' + diskParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + ' Go</option>').join('');
      userSel.innerHTML = '<option value="">Aucun (En stock DSI)</option>' +
        (references.utilisateurs || []).map(u => `<option value="${u.id_uti}">${escapeHtml((u.nom_uti || '') + ' ' + (u.pnom_uti || ''))}</option>`).join('');

      brandSel.onchange = filterMaterielModels;
      typeSel.onchange = filterMaterielModels;
      strSel.onchange = filterMaterielUsers;
      filterMaterielModels();
      filterMaterielUsers();
    }

    function filterMaterielModels() {
      const brand = document.getElementById('mat-marque')?.value || '';
      const typeId = document.getElementById('mat-type')?.value || '';
      const modelSel = document.getElementById('mat-model');
      if (!modelSel) return;

      // Les modèles définis dans Paramètres sont disponibles dès l'ajout.
      // Les modèles du référentiel restent filtrés par marque/type.
      const models = brand
        ? (references.modeles || []).filter(m =>
            m.marque_mat === brand && (!typeId || !m.id_typ_mat || String(m.id_typ_mat) === String(typeId))
          )
        : [];

      const parameterModels = (references.parametres || [])
        .filter(p => p.categorie === 'modele' && p.archiv !== 'O' && (p.valeur || '').trim())
        .map(p => ({ id_param: p.id_param, model_mat: p.valeur.trim() }));

      const existingNames = new Set(models.map(m => (m.model_mat || '').trim().toLowerCase()));
      const extraModels = parameterModels.filter(p => !existingNames.has(p.model_mat.toLowerCase()));

      modelSel.disabled = models.length === 0 && extraModels.length === 0;
      modelSel.innerHTML =
        '<option value="">' +
        (extraModels.length || models.length ? 'Sélectionner un modèle...' : 'Aucun modèle configuré...') +
        '</option>' +
        models.map(m => `<option value="${m.id_model_mat}">${escapeHtml(m.model_mat || '')}</option>`).join('') +
        extraModels.map(p => `<option value="param:${p.id_param}" data-model-name="${escapeHtml(p.model_mat)}">${escapeHtml(p.model_mat)} (Paramètre)</option>`).join('');
    }

    function filterMaterielUsers() {
      const structureId = document.getElementById('mat-str')?.value || '';
      const userSel = document.getElementById('mat-user');
      if (!userSel) return;
      const users = (references.utilisateurs || []).filter(u => !structureId || !u.id_str_mere || String(u.id_str_mere) === String(structureId));
      userSel.innerHTML = '<option value="">Aucun (En stock DSI)</option>' +
        users.map(u => `<option value="${u.id_uti}">${escapeHtml((u.nom_uti || '') + ' ' + (u.pnom_uti || ''))}</option>`).join('');
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;',"\"":'&quot;'}[c]));
    }

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

    function resetPanneForm() {
      const form = document.querySelector('#modal-panne form');
      if (form) form.reset();

      const date = document.getElementById('panne-date');
      const type = document.getElementById('panne-type');
      const tech = document.getElementById('panne-tech');
      const diag = document.getElementById('panne-diag');

      if (date) date.value = new Date().toISOString().slice(0, 10);
      if (type) type.value = 'MAT';
      if (tech) tech.value = 'Support DSI Interne';
      if (diag) diag.value = '';
    }

    function openNewPanneModal() {
      resetPanneForm();
      populatePanneSelect();
      document.getElementById('modal-panne').classList.remove('hidden');
      setTimeout(() => document.getElementById('panne-diag')?.focus(), 50);
    }

    function quickPanneFor(matId) {
      openNewPanneModal();
      document.getElementById('panne-mat-id').value = matId;
    }

    function closeModal(id) {
      document.getElementById(id).classList.add('hidden');
    }

    async function deleteMateriel(matId) {
      if (!confirm('Êtes-vous sûr de vouloir retirer cet équipement du parc ?')) return;
      try {
        const res = await fetch('/api/materiels/' + matId, { method: 'DELETE' });
        if (res.ok) {
          showToast('Équipement retiré du parc');
          await loadAllData();
        } else {
          showToast('Erreur lors de la suppression', true);
        }
      } catch (e) {
        showToast('Erreur de connexion', true);
      }
    }

    async function handleSaveMateriel(e) {
      e.preventDefault();
      const payload = {
        num_inv: document.getElementById('mat-num-inv').value.trim(),
        num_ser: document.getElementById('mat-num-ser').value.trim(),
        marque_mat: document.getElementById('mat-marque').value.trim(),
        id_model_mat: /^\d+$/.test(document.getElementById('mat-model').value) ? parseInt(document.getElementById('mat-model').value) : null,
        model_mat_name: (() => {
          const opt = document.getElementById('mat-model').selectedOptions[0];
          return opt?.dataset.modelName || '';
        })(),
        id_typ_mat: parseInt(document.getElementById('mat-type').value) || null,
        id_str: parseInt(document.getElementById('mat-str').value) || null,
        id_uti: parseInt(document.getElementById('mat-user').value) || null,
        cpu: document.getElementById('mat-cpu').value.trim(),
        se: document.getElementById('mat-se').value.trim(),
        ram: parseInt(document.getElementById('mat-ram').value) || null,
        disk: parseInt(document.getElementById('mat-disk').value) || null,
        image_url: ''
      };

      if (!payload.num_inv || !payload.num_ser || !payload.marque_mat || !payload.id_typ_mat || !payload.id_str) {
        showToast('Veuillez renseigner le N° inventaire, N° série, marque, type et structure.', true);
        return;
      }

      try {
        const url = editingMaterielId ? '/api/materiels/' + editingMaterielId : '/api/materiels';
        const method = editingMaterielId ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json().catch(() => ({}));
        if (res.ok) {
          closeModal('modal-materiel');
          showToast(editingMaterielId ? 'Équipement modifié avec succès !' : 'Équipement ajouté au parc avec succès !');
          editingMaterielId = null;
          await loadAllData();
        } else {
          showToast(result.error || "Erreur lors de l'enregistrement", true);
        }
      } catch (err) {
        showToast('Erreur serveur', true);
      }
    }

    async function handleSavePanne(e) {
      e.preventDefault();
      const payload = {
        id_mat: parseInt(document.getElementById('panne-mat-id').value),
        dat_pan: document.getElementById('panne-date').value,
        tp: document.getElementById('panne-type').value,
        technicien: document.getElementById('panne-tech').value.trim(),
        diag_pan: document.getElementById('panne-diag').value.trim()
      };

      try {
        const res = await fetch('/api/pannes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal('modal-panne');
          resetPanneForm();
          showToast('Panne enregistrée : matériel passé en statut En Panne !');
          loadAllData();
        } else {
          showToast('Erreur lors de l\'enregistrement', true);
        }
      } catch (err) {
        showToast('Erreur serveur', true);
      }
    }

    function populateRepairLocationSelect(selectedId = '') {
      const sel = document.getElementById('repair-lieu');
      if (!sel) return;
      const lieux = references?.lieuxReparation || [];
      const local = lieux.filter(l => (l.categorie_lieu || '').toUpperCase() === 'LOCAL');
      const external = lieux.filter(l => (l.categorie_lieu || '').toUpperCase() !== 'LOCAL');
      let html = '<option value="">Sélectionner un lieu...</option>';
      if (local.length) {
        html += '<optgroup label="Atelier local de la DSI">' +
          local.map(l => '<option value="' + l.id_lieu_rep + '">' + escapeHtml(l.nom_lieu_rep) + '</option>').join('') +
          '</optgroup>';
      }
      if (external.length) {
        html += '<optgroup label="Réparateurs extérieurs">' +
          external.map(l => '<option value="' + l.id_lieu_rep + '">' + escapeHtml(l.nom_lieu_rep) + '</option>').join('') +
          '</optgroup>';
      }
      sel.innerHTML = html;
      if (selectedId) sel.value = String(selectedId);
    }

    function setRepairStateFields() {
      const state = document.getElementById('repair-state')?.value || 'EP';
      const send = document.getElementById('repair-date-send');
      const retour = document.getElementById('repair-date-return');
      const detail = document.getElementById('repair-detail');
      if (send) send.required = state !== 'EP';
      if (retour) retour.required = state === 'RP' || state === 'IR';
      if (detail) detail.required = state === 'RP';
      if (state === 'RP' && retour && !retour.value) retour.value = new Date().toISOString().slice(0,10);
    }

    function openRepairModal(panneId, forcedState = '') {
      const panne = allPannes.find(p => String(p.id_pan) === String(panneId));
      if (!panne) {
        showToast("Panne introuvable", true);
        return;
      }

      document.getElementById('repair-panne-id').value = panneId;

      const setRepairInfo = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value || '-';
      };
      setRepairInfo('repair-info-type', panne.type_nom);
      setRepairInfo('repair-info-brand', panne.marque_mat);
      setRepairInfo('repair-info-model', panne.model_mat);
      setRepairInfo('repair-info-serial', panne.num_ser);
      setRepairInfo('repair-info-user', panne.nom_uti ? ((panne.pnom_uti || '') + ' ' + panne.nom_uti).trim() : 'Non assigné');

      document.getElementById('repair-date-send').value = panne.dat_env_rep || '';
      document.getElementById('repair-date-return').value = panne.dat_ret_rep || '';
      document.getElementById('repair-detail').value = panne.obs_rep || '';
      document.getElementById('repair-observation').value = panne.recommandations || '';
      document.getElementById('repair-obs-ras').checked = false;
      document.getElementById('repair-obs-remis').checked = false;
      document.getElementById('repair-obs-piece').checked = false;
      populateRepairLocationSelect(panne.id_lieu_rep || '');
      document.getElementById('repair-state').value = forcedState || panne.eta_pan || 'EP';
      setRepairStateFields();
      document.getElementById('modal-repair').classList.remove('hidden');
      setTimeout(() => document.getElementById('repair-detail')?.focus(), 50);
    }

    function updateRepairObservation() {
      const ras = document.getElementById('repair-obs-ras');
      const remis = document.getElementById('repair-obs-remis');
      const piece = document.getElementById('repair-obs-piece');
      const observation = document.getElementById('repair-observation');
      if (!observation) return;
      const values = [];
      if (ras?.checked) values.push('R.A.S');
      if (remis?.checked) values.push('Réparé et remis en service');
      if (piece?.checked) values.push('Pièce de rechange introuvable');
      observation.value = values.join(' / ');
    }

    async function handleRepairConfirmation(e) {
      e.preventDefault();
      const panneId = document.getElementById('repair-panne-id').value;
      const state = document.getElementById('repair-state').value;
      const dateSend = document.getElementById('repair-date-send').value || null;
      const dateReturn = document.getElementById('repair-date-return').value || null;
      const lieuId = parseInt(document.getElementById('repair-lieu').value) || null;
      const detail = document.getElementById('repair-detail').value.trim();
      const observation = document.getElementById('repair-observation').value.trim();

      if (state !== 'EP' && !dateSend) {
        showToast("La date d'envoi à la réparation est obligatoire.", true);
        return;
      }
      if ((state === 'RP' || state === 'IR') && !dateReturn) {
        showToast("La date de retour est obligatoire pour cet état.", true);
        return;
      }
      if (state !== 'EP' && !lieuId) {
        showToast("Sélectionnez le lieu de réparation.", true);
        return;
      }
      if (state === 'RP' && !detail) {
        showToast("Veuillez renseigner le détail de la réparation.", true);
        document.getElementById('repair-detail')?.focus();
        return;
      }

      try {
        const res = await fetch('/api/pannes/' + panneId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            eta_pan: state,
            dat_env_rep: dateSend,
            id_lieu_rep: lieuId,
            dat_ret_rep: dateReturn,
            obs_rep: detail,
            recommandations: observation
          })
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          showToast(result.error || 'Erreur lors de la mise à jour', true);
          return;
        }

        closeModal('modal-repair');
        const messages = {
          EP: 'Panne enregistrée.',
          ER: 'Matériel envoyé en réparation.',
          RP: 'Panne réparée : matériel remis en état Bon.',
          IR: 'Panne déclarée irréparable : état du matériel mis à Irréparable.'
        };
        showToast(messages[state] || 'Traitement enregistré.');
        await loadAllData();
      } catch (err) {
        showToast("Erreur lors de la mise à jour", true);
      }
    }

    async function markRepaired(panneId) {
      openRepairModal(panneId, 'RP');
    }

    async function resetData() {
      if (confirm('Voulez-vous réinitialiser toutes les données de test SQLite ?')) {
        await fetch('/api/reset-data', { method: 'POST' });
        showToast('Base SQLite réinitialisée avec succès !');
        loadAllData();
      }
    }

    function showToast(text, isError = false) {
      const toast = document.getElementById('toast');
      const toastText = document.getElementById('toast-text');
      toastText.innerText = text;
      toast.classList.remove('translate-y-16', 'opacity-0');
      if (isError) {
        toast.classList.add('border-rose-500');
      } else {
        toast.classList.remove('border-rose-500');
      }
      setTimeout(() => {
        toast.classList.add('translate-y-16', 'opacity-0');
      }, 3500);
    }

    // GESTION DES PARAMÈTRES MATÉRIELS
    function renderParametres() {
      const tbody = document.getElementById('parametres-table-body');
      const typePanel = document.getElementById('types-param-panel');
      const structurePanel = document.getElementById('structures-param-panel');
      const utilisateurPanel = document.getElementById('utilisateurs-param-panel');
      const cpuPanel = document.getElementById('cpu-param-panel');
      const sePanel = document.getElementById('se-param-panel');
      const isTypes = currentParamCat === 'types';
      const isStructures = currentParamCat === 'structures';
      const isUtilisateurs = currentParamCat === 'utilisateurs';
      const isCpu = currentParamCat === 'cpu';
      const isSe = currentParamCat === 'se';

      if (typePanel) typePanel.classList.toggle('hidden', !isTypes);
      if (structurePanel) structurePanel.classList.toggle('hidden', !isStructures);
      if (utilisateurPanel) utilisateurPanel.classList.toggle('hidden', !isUtilisateurs);
      if (cpuPanel) cpuPanel.classList.toggle('hidden', !isCpu);
      if (sePanel) sePanel.classList.toggle('hidden', !isSe);
      if (tbody) {
        const paramTable = tbody.closest('table');
        const paramContainer = paramTable ? paramTable.parentElement : null;
        if (paramContainer) paramContainer.classList.toggle('hidden', isTypes || isStructures || isUtilisateurs || isCpu || isSe);
      }

      if (isTypes) {
        renderTypesMateriel();
        return;
      }

      if (isStructures) {
        renderStructures();
        return;
      }
      if (isUtilisateurs) {
        renderUtilisateurs();
        return;
      }
      if (isCpu) {
        renderCpuParams();
        return;
      }
      if (isSe) {
        renderSeParams();
        return;
      }

      if (!tbody) return;

      const filtered = allParametres.filter(p => {
        if (currentParamCat === 'all') return true;
        return (p.categorie || '').toLowerCase() === currentParamCat.toLowerCase();
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400">Aucun paramètre configuré pour cette sélection.</td></tr>`;
        return;
      }

      tbody.innerHTML = filtered.map(p => {
        let catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800">CPU</span>';
        if (p.categorie === 'marque') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-800">Marque</span>';
        if (p.categorie === 'ram') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800">RAM</span>';
        if (p.categorie === 'disk') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">Disque</span>';
        if (p.categorie === 'se') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-100 text-purple-800">Système (SE)</span>';
        if (p.categorie === 'modele') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-indigo-100 text-indigo-800">Modèle</span>';
        if (p.categorie === 'lot_reforme') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">Lot de réforme</span>';

        return `
          <tr class="hover:bg-slate-50 transition">
            <td class="p-3">${catBadge}</td>
            <td class="p-3 font-semibold text-slate-800">${escapeHtml(p.valeur || '')}</td>
            <td class="p-3 text-slate-500">${escapeHtml(p.description || '-')}</td>
            <td class="p-3 text-center font-mono text-slate-500">${p.ordre || 1}</td>
            <td class="p-3 text-right whitespace-nowrap">
              ${['marque', 'modele', 'ram', 'disk', 'lot_reforme'].includes((p.categorie || '').toLowerCase()) ? `
                <button onclick="editParametre(${p.id_param})" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier">
                  <i class="fa-solid fa-pen-to-square"></i>
                </button>
              ` : ''}
              <button onclick="deleteParametre(${p.id_param})" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Supprimer">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    function renderStructures() {
      const tbody = document.getElementById('structures-table-body');
      if (!tbody) return;

      if (!allStructures || allStructures.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400">Aucune structure configurée.</td></tr>`;
        return;
      }

      tbody.innerHTML = allStructures.map(s => `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-3 font-mono font-bold text-indigo-700">${escapeHtml(s.cod_str || '')}</td>
          <td class="p-3 font-semibold text-slate-800">${escapeHtml(s.lib_str || '')}</td>
          <td class="p-3 text-slate-500">${escapeHtml(s.structure_mere_nom || '—')}</td>
          <td class="p-3 text-center font-mono text-slate-400">${s.id_str}</td>
          <td class="p-3 text-right whitespace-nowrap">
            <button onclick="editStructure(${s.id_str})" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier">
              <i class="fa-solid fa-pen-to-square"></i>
            </button>
            <button onclick="deleteStructure(${s.id_str})" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Archiver">
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </td>
        </tr>
      `).join('');
    }

    function renderUtilisateurs() {
      const tbody = document.getElementById('utilisateurs-table-body');
      if (!tbody) return;
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O');
      tbody.innerHTML = users.length ? users.map(u => `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-3 font-semibold text-slate-800">${escapeHtml(u.nom_uti || '')}</td>
          <td class="p-3 text-slate-700">${escapeHtml(u.pnom_uti || '')}</td>
          <td class="p-3 text-slate-500">${escapeHtml(u.mail_uti || '—')}</td>
          <td class="p-3 text-slate-600">${escapeHtml(u.lib_str || '—')}</td>
          <td class="p-3 text-center font-mono text-slate-400">${u.id_uti}</td>
          <td class="p-3 text-right whitespace-nowrap">
            <button onclick="editUtilisateur(${u.id_uti})" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier"><i class="fa-solid fa-pen-to-square"></i></button>
            <button onclick="deleteUtilisateur(${u.id_uti})" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Archiver"><i class="fa-solid fa-trash-can"></i></button>
          </td>
        </tr>`).join('') : '<tr><td colspan="6" class="p-6 text-center text-slate-400">Aucun utilisateur configuré.</td></tr>';
    }

    function populateUtilisateurStructures(selectedId = '') {
      const select = document.getElementById('utilisateur-structure');
      if (!select) return;
      select.innerHTML = '<option value="">Aucune structure</option>' + (allStructures || []).map(s => `<option value="${s.id_str}">${escapeHtml(s.cod_str || '')} — ${escapeHtml(s.lib_str || '')}</option>`).join('');
      select.value = selectedId || '';
    }

    function populateUtilisateurAutocomplete() {
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O');
      const names = [...new Set(users.map(u => (u.nom_uti || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fr'));
      const firstNames = [...new Set(users.map(u => (u.pnom_uti || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fr'));
      const emails = [...new Set(users.map(u => (u.mail_uti || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fr'));
      const fill = (id, values) => {
        const list = document.getElementById(id);
        if (!list) return;
        list.innerHTML = values.map(v => '<option value="' + escapeHtml(v) + '"></option>').join('');
      };
      fill('utilisateurs-noms-list', names);
      fill('utilisateurs-prenoms-list', firstNames);
      fill('utilisateurs-emails-list', emails);
    }

    function checkUtilisateurAutocomplete(field) {
      const warning = document.getElementById('utilisateur-duplicate-warning');
      if (!warning) return;
      const inputId = field === 'nom' ? 'utilisateur-nom' : field === 'prenom' ? 'utilisateur-prenom' : 'utilisateur-mail';
      const value = (document.getElementById(inputId)?.value || '').trim().toLowerCase();
      const currentId = document.getElementById('utilisateur-id')?.value || '';
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O' && String(u.id_uti) !== String(currentId));
      const matches = users.filter(u => field === 'nom'
        ? String(u.nom_uti || '').trim().toLowerCase() === value
        : field === 'prenom'
          ? String(u.pnom_uti || '').trim().toLowerCase() === value
          : String(u.mail_uti || '').trim().toLowerCase() === value);
      const nom = (document.getElementById('utilisateur-nom')?.value || '').trim().toLowerCase();
      const prenom = (document.getElementById('utilisateur-prenom')?.value || '').trim().toLowerCase();
      const mail = (document.getElementById('utilisateur-mail')?.value || '').trim().toLowerCase();
      const sameIdentity = users.some(u =>
        nom && prenom &&
        String(u.nom_uti || '').trim().toLowerCase() === nom &&
        String(u.pnom_uti || '').trim().toLowerCase() === prenom &&
        (!mail || String(u.mail_uti || '').trim().toLowerCase() === mail)
      );
      if (sameIdentity) {
        warning.textContent = 'Cet utilisateur existe déjà dans la base de données. Vérifiez les informations saisies avant de continuer.';
        warning.classList.remove('hidden');
      } else if (value && matches.length) {
        const label = field === 'nom' ? 'nom' : field === 'prenom' ? 'prénom' : 'adresse e-mail';
        warning.textContent = 'Cette ' + label + ' existe déjà dans la base. Sélectionnez une valeur existante si elle correspond à la personne recherchée.';
        warning.classList.remove('hidden');
      } else {
        warning.classList.add('hidden');
        warning.textContent = '';
      }
    }

    function openNewUtilisateurModal() {
      document.getElementById('utilisateur-id').value = '';
      document.getElementById('utilisateur-nom').value = '';
      document.getElementById('utilisateur-prenom').value = '';
      document.getElementById('utilisateur-mail').value = '';
      const warning = document.getElementById('utilisateur-duplicate-warning');
      if (warning) { warning.classList.add('hidden'); warning.textContent = ''; }
      populateUtilisateurStructures();
      populateUtilisateurAutocomplete();
      document.getElementById('utilisateur-modal-title').innerHTML = '<i class="fa-solid fa-user text-indigo-600"></i> Nouvel utilisateur';
      document.getElementById('modal-utilisateur').classList.remove('hidden');
    }

    function editUtilisateur(id) {
      const u = (references.utilisateurs || []).find(x => String(x.id_uti) === String(id));
      if (!u) return;
      document.getElementById('utilisateur-id').value = u.id_uti;
      document.getElementById('utilisateur-nom').value = u.nom_uti || '';
      document.getElementById('utilisateur-prenom').value = u.pnom_uti || '';
      document.getElementById('utilisateur-mail').value = u.mail_uti || '';
      const warning = document.getElementById('utilisateur-duplicate-warning');
      if (warning) { warning.classList.add('hidden'); warning.textContent = ''; }
      populateUtilisateurStructures(u.id_str_mere || '');
      populateUtilisateurAutocomplete();
      document.getElementById('utilisateur-modal-title').innerHTML = '<i class="fa-solid fa-pen-to-square text-indigo-600"></i> Modifier l’utilisateur';
      document.getElementById('modal-utilisateur').classList.remove('hidden');
    }

    async function refreshUtilisateurs() {
      const users = await fetch('/api/utilisateurs').then(r => r.json());
      references.utilisateurs = users || [];
      renderUtilisateurs();
      populateMaterielForm();
    }

    async function handleSaveUtilisateur(e) {
      e.preventDefault();
      const id = document.getElementById('utilisateur-id').value;
      const nom = document.getElementById('utilisateur-nom').value.trim();
      const prenom = document.getElementById('utilisateur-prenom').value.trim();
      const mail = document.getElementById('utilisateur-mail').value.trim();
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O' && String(u.id_uti) !== String(id));
      const duplicateEmail = mail && users.some(u => String(u.mail_uti || '').trim().toLowerCase() === mail.toLowerCase());
      const duplicatePerson = users.some(u =>
        String(u.nom_uti || '').trim().toLowerCase() === nom.toLowerCase() &&
        String(u.pnom_uti || '').trim().toLowerCase() === prenom.toLowerCase() &&
        (!mail || String(u.mail_uti || '').trim().toLowerCase() === mail.toLowerCase())
      );
      if (duplicateEmail || duplicatePerson) {
        checkUtilisateurAutocomplete(duplicateEmail ? 'email' : 'nom');
        showToast('Cet utilisateur existe déjà ou utilise une adresse e-mail déjà enregistrée.', true);
        return;
      }
      const payload = {
        nom_uti: document.getElementById('utilisateur-nom').value.trim(),
        pnom_uti: document.getElementById('utilisateur-prenom').value.trim(),
        mail_uti: document.getElementById('utilisateur-mail').value.trim(),
        id_str_mere: document.getElementById('utilisateur-structure').value || null
      };
      try {
        const res = await fetch(id ? '/api/utilisateurs/' + id : '/api/utilisateurs', { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) { showToast(result.error || 'Erreur lors de l’enregistrement', true); return; }
        showToast(id ? 'Utilisateur modifié avec succès !' : 'Utilisateur ajouté avec succès !');
        closeModal('modal-utilisateur');
        await refreshUtilisateurs();
      } catch (err) { showToast('Erreur serveur Flask', true); }
    }

    async function deleteUtilisateur(id) {
      if (!confirm('Voulez-vous archiver cet utilisateur ? Les affectations historiques seront conservées.')) return;
      try {
        const res = await fetch('/api/utilisateurs/' + id, { method: 'DELETE' });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) { showToast(result.error || 'Erreur lors de l’archivage', true); return; }
        showToast('Utilisateur archivé');
        await refreshUtilisateurs();
      } catch (err) { showToast('Erreur serveur Flask', true); }
    }

    function filterParamCategory(cat) {
      currentParamCat = cat;
      document.querySelectorAll('.param-cat-btn').forEach(btn => {
        btn.classList.remove('bg-indigo-50', 'text-indigo-700', 'border', 'border-indigo-200');
        btn.classList.add('text-slate-600');
      });
      const activeBtn = document.getElementById('btn-param-' + cat);
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-600');
        activeBtn.classList.add('bg-indigo-50', 'text-indigo-700', 'border', 'border-indigo-200');
      }

      const actionsTop = document.getElementById('parametres-actions-top');
      const btnParam = document.getElementById('btn-new-param');
      const btnParamLabel = document.getElementById('btn-new-param-label');
      const btnCpu = document.getElementById('btn-new-cpu');
      const btnSe = document.getElementById('btn-new-se');
      const btnType = document.getElementById('btn-new-type');
      const btnStructure = document.getElementById('btn-new-structure');
      const btnUtilisateur = document.getElementById('btn-new-utilisateur');
      const btnLot = document.getElementById('btn-new-lot');

      // Masquer tous les boutons individuels par défaut
      if (btnParam) btnParam.classList.add('hidden');
      if (btnCpu) btnCpu.classList.add('hidden');
      if (btnSe) btnSe.classList.add('hidden');
      if (btnType) btnType.classList.add('hidden');
      if (btnStructure) btnStructure.classList.add('hidden');
      if (btnUtilisateur) btnUtilisateur.classList.add('hidden');
      if (btnLot) btnLot.classList.add('hidden');

      if (cat === 'all') {
        // Sur le volet "Tous les paramètres" : aucun bouton d'ajout affiché
        if (actionsTop) actionsTop.classList.add('hidden');
      } else {
        // Sur les volets individuels : afficher le conteneur et le bouton individuel adéquat
        if (actionsTop) actionsTop.classList.remove('hidden');

        if (cat === 'cpu') {
          if (btnCpu) btnCpu.classList.remove('hidden');
        } else if (cat === 'se') {
          if (btnSe) btnSe.classList.remove('hidden');
        } else if (cat === 'types') {
          if (btnType) btnType.classList.remove('hidden');
        } else if (cat === 'structures') {
          if (btnStructure) btnStructure.classList.remove('hidden');
        } else if (cat === 'utilisateurs') {
          if (btnUtilisateur) btnUtilisateur.classList.remove('hidden');
        } else if (cat === 'lot_reforme') {
          if (btnLot) btnLot.classList.remove('hidden');
        } else if (['marque', 'ram', 'disk', 'modele'].includes(cat)) {
          if (btnParam) {
            btnParam.classList.remove('hidden');
            btnParam.onclick = openNewParamModal;
          }
          if (btnParamLabel) {
            btnParamLabel.textContent =
              cat === 'marque' ? 'Nouvelle Marque' :
              cat === 'ram' ? 'Nouvelle Capacité RAM' :
              cat === 'disk' ? 'Nouveau Stockage (Disque)' :
              cat === 'modele' ? 'Nouveau Modèle' :
              'Nouveau Paramètre';
          }
        }
      }

      renderParametres();
    }

    function openNewLotReformeModal() {
      document.getElementById('lot-reforme-val').value = '';
      document.getElementById('lot-reforme-desc').value = '';
      document.getElementById('modal-lot-reforme').classList.remove('hidden');
    }

    async function handleSaveLotReforme(e) {
      e.preventDefault();
      const valeur = document.getElementById('lot-reforme-val').value.trim();
      const description = document.getElementById('lot-reforme-desc').value.trim();

      if (!valeur) {
        showToast('Le N° de lot est obligatoire.', true);
        return;
      }

      try {
        const res = await fetch('/api/parametres', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            categorie: 'lot_reforme',
            valeur: valeur,
            description: description,
            ordre: 1
          })
        });
        const result = await res.json().catch(() => ({}));

        if (!res.ok) {
          showToast(result.error || 'Erreur lors de l’enregistrement du lot.', true);
          return;
        }

        allParametres = await fetch('/api/parametres').then(r => r.json());
        references.parametres = allParametres;
        renderParametres();
        populateMaterielForm();
        populateReformeLotSelect();
        closeModal('modal-lot-reforme');
        showToast('Lot de réforme ajouté avec succès !');
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

    function resetParametreModal() {
      document.getElementById('param-id').value = '';
      document.getElementById('param-cat').value = currentParamCat !== 'all' ? currentParamCat : 'marque';
      document.getElementById('param-cat').disabled = false;
      document.getElementById('param-val').value = '';
      document.getElementById('param-desc').value = '';
      document.getElementById('param-ordre').value = '1';
      document.getElementById('param-modal-title').textContent = 'Ajouter un paramètre matériel';
    }

    function openNewParamModal() {
      resetParametreModal();
      document.getElementById('modal-parametre').classList.remove('hidden');
    }

    function editParametre(id) {
      const p = (allParametres || []).find(x => String(x.id_param) === String(id));
      if (!p || !['marque', 'modele', 'ram', 'disk', 'lot_reforme'].includes((p.categorie || '').toLowerCase())) return;

      document.getElementById('param-id').value = p.id_param;
      document.getElementById('param-cat').value = p.categorie || '';
      document.getElementById('param-cat').disabled = true;
      document.getElementById('param-val').value = p.valeur || '';
      document.getElementById('param-desc').value = p.description || '';
      document.getElementById('param-ordre').value = p.ordre || 1;
      document.getElementById('param-modal-title').textContent = 'Modifier le paramètre';
      document.getElementById('modal-parametre').classList.remove('hidden');
    }

    async function handleSaveParametre(e) {
      e.preventDefault();
      const id = document.getElementById('param-id').value;
      const payload = {
        categorie: document.getElementById('param-cat').value,
        valeur: document.getElementById('param-val').value.trim(),
        description: document.getElementById('param-desc').value.trim(),
        ordre: parseInt(document.getElementById('param-ordre').value) || 1
      };

      if (!payload.valeur) {
        showToast('La valeur est obligatoire.', true);
        return;
      }

      try {
        const res = await fetch(id ? '/api/parametres/' + id : '/api/parametres', {
          method: id ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          showToast(result.error || "Erreur lors de l'enregistrement", true);
          return;
        }

        showToast(id ? 'Paramètre modifié avec succès !' : 'Paramètre matériel ajouté avec succès !');
        closeModal('modal-parametre');
        resetParametreModal();

        const updated = await fetch('/api/parametres').then(r => r.json());
        allParametres = updated;
        references.parametres = updated;
        renderParametres();
        populateMaterielForm();
        populateReformeLotSelect();
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

    async function deleteParametre(id) {
      if (!confirm('Voulez-vous supprimer ce paramètre ?')) return;
      try {
        const res = await fetch('/api/parametres/' + id, { method: 'DELETE' });
        if (res.ok) {
          showToast('Paramètre supprimé');
          allParametres = allParametres.filter(p => p.id_param !== id);
          renderParametres();
        }
      } catch (err) {
        showToast('Erreur lors de la suppression', true);
      }
    }



    // GESTION DES STRUCTURES
    function openNewStructureModal() {
      document.getElementById('structure-id').value = '';
      document.getElementById('structure-code').value = '';
      document.getElementById('structure-libelle').value = '';
      populateStructureParents();
      document.getElementById('structure-parent').value = '';
      document.getElementById('structure-modal-title').innerHTML =
        '<i class="fa-solid fa-sitemap text-indigo-600"></i> Nouvelle structure';
      document.getElementById('modal-structure').classList.remove('hidden');
    }

    function populateStructureParents(excludeId = null) {
      const select = document.getElementById('structure-parent');
      if (!select) return;
      const current = select.value;
      select.innerHTML = '<option value="">Aucune — structure racine</option>' +
        (allStructures || [])
          .filter(s => !excludeId || String(s.id_str) !== String(excludeId))
          .map(s => `<option value="${s.id_str}">${escapeHtml(s.cod_str || '')} — ${escapeHtml(s.lib_str || '')}</option>`)
          .join('');
      if (current) select.value = current;
    }

    function editStructure(id) {
      const s = (allStructures || []).find(x => String(x.id_str) === String(id));
      if (!s) return;
      document.getElementById('structure-id').value = s.id_str;
      document.getElementById('structure-code').value = s.cod_str || '';
      document.getElementById('structure-libelle').value = s.lib_str || '';
      populateStructureParents(s.id_str);
      document.getElementById('structure-parent').value = s.id_str_mere || '';
      document.getElementById('structure-modal-title').innerHTML =
        '<i class="fa-solid fa-pen-to-square text-indigo-600"></i> Modifier la structure';
      document.getElementById('modal-structure').classList.remove('hidden');
    }

    async function handleSaveStructure(e) {
      e.preventDefault();
      const id = document.getElementById('structure-id').value;
      const payload = {
        cod_str: document.getElementById('structure-code').value.trim(),
        lib_str: document.getElementById('structure-libelle').value.trim(),
        id_str_mere: document.getElementById('structure-parent').value || null
      };

      try {
        const res = await fetch(id ? '/api/structures/' + id : '/api/structures', {
          method: id ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          showToast(data.error || 'Erreur lors de l’enregistrement de la structure', true);
          return;
        }

        allStructures = await fetch('/api/structures').then(r => r.json());
        references.structures = allStructures;
        renderStructures();
        populateStructureParents();
        closeModal('modal-structure');
        showToast(id ? 'Structure modifiée avec succès' : 'Structure ajoutée avec succès');
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

    async function deleteStructure(id) {
      const s = (allStructures || []).find(x => String(x.id_str) === String(id));
      if (!s) return;
      if (!confirm(`Archiver la structure « ${s.cod_str} — ${s.lib_str} » ?`)) return;

      try {
        const res = await fetch('/api/structures/' + id, { method: 'DELETE' });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          showToast(data.error || 'Impossible d’archiver la structure', true);
          return;
        }
        allStructures = await fetch('/api/structures').then(r => r.json());
        references.structures = allStructures;
        renderStructures();
        showToast('Structure archivée');
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

    // Exposer explicitement sur window pour tous les onclick HTML
    window.switchView = switchView;
    window.toggleView = toggleView;
    window.setFilter = setFilter;
    window.applyFilters = applyFilters;
    window.loadAllData = loadAllData;
    window.openNewMaterielModal = openNewMaterielModal;
    window.openNewPanneModal = openNewPanneModal;
    window.resetPanneForm = resetPanneForm;
    window.openNewReformeModal = openNewReformeModal;
    window.handleSaveReforme = handleSaveReforme;
    window.updateReformeDeclarationFields = updateReformeDeclarationFields;
    window.quickPanneFor = quickPanneFor;
    window.closeModal = closeModal;
    window.deleteMateriel = deleteMateriel;
    window.handleSaveMateriel = handleSaveMateriel;
    window.renderReformes = renderReformes;
    window.openAffectationHistory = openAffectationHistory;
    window.handleSavePanne = handleSavePanne;
    window.markRepaired = markRepaired;
    window.openRepairModal = openRepairModal;
    window.updateRepairObservation = updateRepairObservation;
    window.setRepairStateFields = setRepairStateFields;
    window.handleRepairConfirmation = handleRepairConfirmation;
    window.viewReport = viewReport;
    window.resetData = resetData;
    window.showToast = showToast;
    window.filterParamCategory = filterParamCategory;
    window.openNewLotReformeModal = openNewLotReformeModal;
    window.handleSaveLotReforme = handleSaveLotReforme;
    window.populateUtilisateurAutocomplete = populateUtilisateurAutocomplete;
    window.checkUtilisateurAutocomplete = checkUtilisateurAutocomplete;
    window.openNewParamModal = openNewParamModal;
    window.handleSaveParametre = handleSaveParametre;
    window.deleteParametre = deleteParametre;
    window.runTestOracleConnection = runTestOracleConnection;
    window.runExecuteOracleSync = runExecuteOracleSync;
    window.openOracleSqlModal = openOracleSqlModal;
    window.copyOracleSqlScript = copyOracleSqlScript;

    // Déclenchement garanti du chargement
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', loadAllData);
    } else {
      loadAllData();
    }
