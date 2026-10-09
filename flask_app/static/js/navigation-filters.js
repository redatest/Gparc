// Navigation entre les vues et filtres du parc informatique.
// Les états et fonctions métier restent définis dans app.js et les autres modules.
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

