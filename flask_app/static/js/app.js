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
