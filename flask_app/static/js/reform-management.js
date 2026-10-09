    // RENDU DU SUIVI DES RÉFORMES
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

// Gestion de la déclaration et des filtres de réforme

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
