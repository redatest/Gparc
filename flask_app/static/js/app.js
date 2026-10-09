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

