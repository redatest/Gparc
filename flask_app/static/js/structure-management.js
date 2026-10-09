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
