// Navigation entre les vues et filtres du parc informatique.
function switchView(view) {
  const role = document.body.dataset.role;
  if ((view === 'admins' || view === 'oracle') && role !== 'super_admin') return;
  currentView = view;
  document.querySelectorAll('.view-panel').forEach(panel => panel.classList.add('hidden'));
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.classList.remove('bg-blue-600', 'text-white');
    tab.classList.add('text-slate-300');
  });
  const activeTab = document.getElementById('tab-' + view);
  if (activeTab) {
    activeTab.classList.remove('text-slate-300');
    activeTab.classList.add('bg-blue-600', 'text-white');
  }
  const panel = document.getElementById('view-' + view);
  if (panel) panel.classList.remove('hidden');
  if (view === 'admins' && typeof loadAdmins === 'function') {
    loadAdmins().catch(error => adminFeedback(error.message, true));
  }
}

function toggleView() { switchView('materiels'); }

function setFilter(filter) {
  currentFilter = filter;
  materielsCurrentPage = 1;
  document.querySelectorAll('.filter-btn').forEach(button => {
    button.classList.remove('bg-slate-900', 'text-white');
    button.classList.add('bg-slate-100', 'text-slate-700');
  });
  const ids = { ALL: 'filter-all', ES: 'filter-es', PR: 'filter-pr', RF: 'filter-rf' };
  const active = document.getElementById(ids[filter] || 'filter-all');
  if (active) {
    active.classList.remove('bg-slate-100', 'text-slate-700');
    active.classList.add('bg-slate-900', 'text-white');
  }
  renderMateriels();
}

function applyFilters() {
  materielsCurrentPage = 1;
  renderMateriels();
}
