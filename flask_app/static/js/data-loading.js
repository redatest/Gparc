// Chargement des données de l'application.
async function loadAllData() {
  const refreshIcon = document.getElementById('refresh-icon');
  if (refreshIcon) refreshIcon.classList.add('fa-spin');
  try {
    const [statsRes, matRes, panRes, paramRes, structuresRes, referencesRes, oraHistRes] = await Promise.all([
      fetch('/api/stats').then(r => r.json()),
      fetch('/api/materiels').then(r => r.json()),
      fetch('/api/pannes').then(r => r.json()),
      fetch('/api/parametres').then(r => r.ok ? r.json() : []),
      fetch('/api/structures').then(r => r.ok ? r.json() : []),
      fetch('/api/references').then(r => r.ok ? r.json() : ({structures:[], types:[], modeles:[], utilisateurs:[], parametres:[]})),
      fetch('/api/oracle-sync/history').then(r => r.ok ? r.json() : []).catch(() => [])
    ]);
    allMateriels = Array.isArray(matRes) ? matRes : [];
    allPannes = Array.isArray(panRes) ? panRes : [];
    allParametres = Array.isArray(paramRes) ? paramRes : [];
    allStructures = referencesRes?.structures || structuresRes || [];
    allTypes = referencesRes?.types || [];
    references = referencesRes || references;
    allOracleHistory = Array.isArray(oraHistRes) ? oraHistRes : [];

    document.getElementById('kpi-total').innerText = statsRes.totalEquipements || allMateriels.length;
    document.getElementById('kpi-op').innerText = statsRes.operationnels ?? allMateriels.filter(m => m.etat_mat === 'BON').length;
    document.getElementById('kpi-pa').innerText = allPannes.filter(p => ['EP', 'EC', 'ER', 'AT'].includes(p.eta_pan)).length;
    document.getElementById('kpi-re').innerText = allMateriels.filter(m =>
      ['RF', 'REFORME'].includes(String(m.statut_mat || '').trim().toUpperCase()) ||
      String(m.etat_reforme || '').trim().toUpperCase() === 'REFORME'
    ).length;

    const panneNavCount = document.getElementById('panne-nav-count');
    const reparationNavCount = document.getElementById('reparation-nav-count');
    const activePanneCount = allPannes.filter(p => ['EP', 'EC', 'ER', 'AT'].includes(p.eta_pan)).length;
    const activeRepairCount = allPannes.filter(p => ['ER', 'AT'].includes(p.eta_pan)).length;
    if (panneNavCount) panneNavCount.textContent = String(activePanneCount);
    if (reparationNavCount) reparationNavCount.textContent = String(activeRepairCount);

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

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', loadAllData);
} else {
  loadAllData();
}
