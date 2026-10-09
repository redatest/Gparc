    // GESTION DES TYPES DE MATÉRIEL
    function renderTypesMateriel() {
      const tbody = document.getElementById('types-table-body');
      if (!tbody) return;
      const types = allTypes || [];
      if (!types.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="p-6 text-center text-slate-400">Aucun type de matériel configuré.</td></tr>';
        return;
      }
      tbody.innerHTML = types.map(t =>
        '<tr class="hover:bg-slate-50 transition">' +
          '<td class="p-3 font-mono font-bold text-indigo-700">' + escapeHtml(t.cod_typ_mat || '') + '</td>' +
          '<td class="p-3 font-semibold text-slate-800">' + escapeHtml(t.lib_typ_mat || '') + '</td>' +
          '<td class="p-3 text-center font-mono text-slate-500">' + (t.nb_materiels || 0) + '</td>' +
          '<td class="p-3 text-center font-mono text-slate-400">' + t.id_typ_mat + '</td>' +
          '<td class="p-3 text-right whitespace-nowrap">' +
            '<button onclick="editTypeMateriel(' + t.id_typ_mat + ')" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier"><i class="fa-solid fa-pen-to-square"></i></button>' +
            '<button onclick="deleteTypeMateriel(' + t.id_typ_mat + ')" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Archiver"><i class="fa-solid fa-trash-can"></i></button>' +
          '</td>' +
        '</tr>'
      ).join('');
    }

    function openNewTypeMaterielModal() {
      document.getElementById('type-materiel-id').value = '';
      document.getElementById('type-materiel-code').value = '';
      document.getElementById('type-materiel-libelle').value = '';
      document.getElementById('type-materiel-modal-title').innerHTML = '<i class="fa-solid fa-desktop text-indigo-600"></i> Nouveau type de matériel';
      document.getElementById('modal-type-materiel').classList.remove('hidden');
    }

    function editTypeMateriel(id) {
      const t = (allTypes || []).find(x => String(x.id_typ_mat) === String(id));
      if (!t) return;
      document.getElementById('type-materiel-id').value = t.id_typ_mat;
      document.getElementById('type-materiel-code').value = t.cod_typ_mat || '';
      document.getElementById('type-materiel-libelle').value = t.lib_typ_mat || '';
      document.getElementById('type-materiel-modal-title').innerHTML = '<i class="fa-solid fa-pen-to-square text-indigo-600"></i> Modifier le type de matériel';
      document.getElementById('modal-type-materiel').classList.remove('hidden');
    }

    async function refreshTypesMateriel() {
      const res = await fetch('/api/types-materiel');
      if (!res.ok) throw new Error('Erreur lors du chargement des types');
      allTypes = await res.json();
      references.types = allTypes;
      renderTypesMateriel();
      populateMaterielForm();
    }

    async function handleSaveTypeMateriel(e) {
      e.preventDefault();
      const id = document.getElementById('type-materiel-id').value;
      const payload = {
        cod_typ_mat: document.getElementById('type-materiel-code').value.trim(),
        lib_typ_mat: document.getElementById('type-materiel-libelle').value.trim()
      };
      try {
        const res = await fetch(id ? '/api/types-materiel/' + id : '/api/types-materiel', {
          method: id ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          showToast(result.error || 'Erreur lors de l’enregistrement du type', true);
          return;
        }
        showToast(id ? 'Type de matériel modifié avec succès !' : 'Type de matériel ajouté avec succès !');
        closeModal('modal-type-materiel');
        await refreshTypesMateriel();
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

    async function deleteTypeMateriel(id) {
      if (!confirm('Voulez-vous archiver ce type de matériel ?')) return;
      try {
        const res = await fetch('/api/types-materiel/' + id, { method: 'DELETE' });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          showToast(result.error || 'Impossible d’archiver ce type', true);
          return;
        }
        showToast('Type de matériel archivé');
        await refreshTypesMateriel();
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

