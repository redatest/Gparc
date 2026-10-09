// Gestion du formulaire de déclaration des pannes.
// Les fonctions partagées (closeModal, showToast, loadAllData et populatePanneSelect)
// restent fournies par les autres modules chargés dans index.html.

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
