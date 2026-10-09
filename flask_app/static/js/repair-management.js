// Gestion du traitement et du cycle de réparation des pannes.
// Utilise les données et utilitaires globaux définis dans app.js.

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

