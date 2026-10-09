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

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;',"\"":'&quot;'}[c]));
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
