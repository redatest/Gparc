    function filterParamCategory(cat) {
      currentParamCat = cat;
      document.querySelectorAll('.param-cat-btn').forEach(btn => {
        btn.classList.remove('bg-indigo-50', 'text-indigo-700', 'border', 'border-indigo-200');
        btn.classList.add('text-slate-600');
      });
      const activeBtn = document.getElementById('btn-param-' + cat);
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-600');
        activeBtn.classList.add('bg-indigo-50', 'text-indigo-700', 'border', 'border-indigo-200');
      }

      const actionsTop = document.getElementById('parametres-actions-top');
      const btnParam = document.getElementById('btn-new-param');
      const btnParamLabel = document.getElementById('btn-new-param-label');
      const btnCpu = document.getElementById('btn-new-cpu');
      const btnSe = document.getElementById('btn-new-se');
      const btnType = document.getElementById('btn-new-type');
      const btnStructure = document.getElementById('btn-new-structure');
      const btnUtilisateur = document.getElementById('btn-new-utilisateur');
      const btnLot = document.getElementById('btn-new-lot');

      // Masquer tous les boutons individuels par défaut
      if (btnParam) btnParam.classList.add('hidden');
      if (btnCpu) btnCpu.classList.add('hidden');
      if (btnSe) btnSe.classList.add('hidden');
      if (btnType) btnType.classList.add('hidden');
      if (btnStructure) btnStructure.classList.add('hidden');
      if (btnUtilisateur) btnUtilisateur.classList.add('hidden');
      if (btnLot) btnLot.classList.add('hidden');

      if (cat === 'all') {
        // Sur le volet "Tous les paramètres" : aucun bouton d'ajout affiché
        if (actionsTop) actionsTop.classList.add('hidden');
      } else {
        // Sur les volets individuels : afficher le conteneur et le bouton individuel adéquat
        if (actionsTop) actionsTop.classList.remove('hidden');

        if (cat === 'cpu') {
          if (btnCpu) btnCpu.classList.remove('hidden');
        } else if (cat === 'se') {
          if (btnSe) btnSe.classList.remove('hidden');
        } else if (cat === 'types') {
          if (btnType) btnType.classList.remove('hidden');
        } else if (cat === 'structures') {
          if (btnStructure) btnStructure.classList.remove('hidden');
        } else if (cat === 'utilisateurs') {
          if (btnUtilisateur) btnUtilisateur.classList.remove('hidden');
        } else if (cat === 'lot_reforme') {
          if (btnLot) btnLot.classList.remove('hidden');
        } else if (['marque', 'ram', 'disk', 'modele'].includes(cat)) {
          if (btnParam) {
            btnParam.classList.remove('hidden');
            btnParam.onclick = openNewParamModal;
          }
          if (btnParamLabel) {
            btnParamLabel.textContent =
              cat === 'marque' ? 'Nouvelle Marque' :
              cat === 'ram' ? 'Nouvelle Capacité RAM' :
              cat === 'disk' ? 'Nouveau Stockage (Disque)' :
              cat === 'modele' ? 'Nouveau Modèle' :
              'Nouveau Paramètre';
          }
        }
      }

      renderParametres();
    }

    function openNewLotReformeModal() {
      document.getElementById('lot-reforme-val').value = '';
      document.getElementById('lot-reforme-desc').value = '';
      document.getElementById('modal-lot-reforme').classList.remove('hidden');
    }

    async function handleSaveLotReforme(e) {
      e.preventDefault();
      const valeur = document.getElementById('lot-reforme-val').value.trim();
      const description = document.getElementById('lot-reforme-desc').value.trim();

      if (!valeur) {
        showToast('Le N° de lot est obligatoire.', true);
        return;
      }

      try {
        const res = await fetch('/api/parametres', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            categorie: 'lot_reforme',
            valeur: valeur,
            description: description,
            ordre: 1
          })
        });
        const result = await res.json().catch(() => ({}));

        if (!res.ok) {
          showToast(result.error || 'Erreur lors de l’enregistrement du lot.', true);
          return;
        }

        allParametres = await fetch('/api/parametres').then(r => r.json());
        references.parametres = allParametres;
        renderParametres();
        populateMaterielForm();
        populateReformeLotSelect();
        closeModal('modal-lot-reforme');
        showToast('Lot de réforme ajouté avec succès !');
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

    function resetParametreModal() {
      document.getElementById('param-id').value = '';
      document.getElementById('param-cat').value = currentParamCat !== 'all' ? currentParamCat : 'marque';
      document.getElementById('param-cat').disabled = false;
      document.getElementById('param-val').value = '';
      document.getElementById('param-desc').value = '';
      document.getElementById('param-ordre').value = '1';
      document.getElementById('param-modal-title').textContent = 'Ajouter un paramètre matériel';
    }

    function openNewParamModal() {
      resetParametreModal();
      document.getElementById('modal-parametre').classList.remove('hidden');
    }

    function editParametre(id) {
      const p = (allParametres || []).find(x => String(x.id_param) === String(id));
      if (!p || !['marque', 'modele', 'ram', 'disk', 'lot_reforme'].includes((p.categorie || '').toLowerCase())) return;

      document.getElementById('param-id').value = p.id_param;
      document.getElementById('param-cat').value = p.categorie || '';
      document.getElementById('param-cat').disabled = true;
      document.getElementById('param-val').value = p.valeur || '';
      document.getElementById('param-desc').value = p.description || '';
      document.getElementById('param-ordre').value = p.ordre || 1;
      document.getElementById('param-modal-title').textContent = 'Modifier le paramètre';
      document.getElementById('modal-parametre').classList.remove('hidden');
    }

    async function handleSaveParametre(e) {
      e.preventDefault();
      const id = document.getElementById('param-id').value;
      const payload = {
        categorie: document.getElementById('param-cat').value,
        valeur: document.getElementById('param-val').value.trim(),
        description: document.getElementById('param-desc').value.trim(),
        ordre: parseInt(document.getElementById('param-ordre').value) || 1
      };

      if (!payload.valeur) {
        showToast('La valeur est obligatoire.', true);
        return;
      }

      try {
        const res = await fetch(id ? '/api/parametres/' + id : '/api/parametres', {
          method: id ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const result = await res.json().catch(() => ({}));
        if (!res.ok) {
          showToast(result.error || "Erreur lors de l'enregistrement", true);
          return;
        }

        showToast(id ? 'Paramètre modifié avec succès !' : 'Paramètre matériel ajouté avec succès !');
        closeModal('modal-parametre');
        resetParametreModal();

        const updated = await fetch('/api/parametres').then(r => r.json());
        allParametres = updated;
        references.parametres = updated;
        renderParametres();
        populateMaterielForm();
        populateReformeLotSelect();
      } catch (err) {
        showToast('Erreur serveur Flask', true);
      }
    }

    async function deleteParametre(id) {
      if (!confirm('Voulez-vous supprimer ce paramètre ?')) return;
      try {
        const res = await fetch('/api/parametres/' + id, { method: 'DELETE' });
        if (res.ok) {
          showToast('Paramètre supprimé');
          allParametres = allParametres.filter(p => p.id_param !== id);
          renderParametres();
        }
      } catch (err) {
        showToast('Erreur lors de la suppression', true);
      }
    }

    function renderParametres() {
      const tbody = document.getElementById('parametres-table-body');
      const typePanel = document.getElementById('types-param-panel');
      const structurePanel = document.getElementById('structures-param-panel');
      const utilisateurPanel = document.getElementById('utilisateurs-param-panel');
      const cpuPanel = document.getElementById('cpu-param-panel');
      const sePanel = document.getElementById('se-param-panel');
      const isTypes = currentParamCat === 'types';
      const isStructures = currentParamCat === 'structures';
      const isUtilisateurs = currentParamCat === 'utilisateurs';
      const isCpu = currentParamCat === 'cpu';
      const isSe = currentParamCat === 'se';

      if (typePanel) typePanel.classList.toggle('hidden', !isTypes);
      if (structurePanel) structurePanel.classList.toggle('hidden', !isStructures);
      if (utilisateurPanel) utilisateurPanel.classList.toggle('hidden', !isUtilisateurs);
      if (cpuPanel) cpuPanel.classList.toggle('hidden', !isCpu);
      if (sePanel) sePanel.classList.toggle('hidden', !isSe);
      if (tbody) {
        const paramTable = tbody.closest('table');
        const paramContainer = paramTable ? paramTable.parentElement : null;
        if (paramContainer) paramContainer.classList.toggle('hidden', isTypes || isStructures || isUtilisateurs || isCpu || isSe);
      }

      if (isTypes) {
        renderTypesMateriel();
        return;
      }

      if (isStructures) {
        renderStructures();
        return;
      }
      if (isUtilisateurs) {
        renderUtilisateurs();
        return;
      }
      if (isCpu) {
        renderCpuParams();
        return;
      }
      if (isSe) {
        renderSeParams();
        return;
      }

      if (!tbody) return;

      const filtered = allParametres.filter(p => {
        if (currentParamCat === 'all') return true;
        return (p.categorie || '').toLowerCase() === currentParamCat.toLowerCase();
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400">Aucun paramètre configuré pour cette sélection.</td></tr>`;
        return;
      }

      tbody.innerHTML = filtered.map(p => {
        let catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800">CPU</span>';
        if (p.categorie === 'marque') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-800">Marque</span>';
        if (p.categorie === 'ram') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800">RAM</span>';
        if (p.categorie === 'disk') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">Disque</span>';
        if (p.categorie === 'se') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-100 text-purple-800">Système (SE)</span>';
        if (p.categorie === 'modele') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-indigo-100 text-indigo-800">Modèle</span>';
        if (p.categorie === 'lot_reforme') catBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">Lot de réforme</span>';

        return `
          <tr class="hover:bg-slate-50 transition">
            <td class="p-3">${catBadge}</td>
            <td class="p-3 font-semibold text-slate-800">${escapeHtml(p.valeur || '')}</td>
            <td class="p-3 text-slate-500">${escapeHtml(p.description || '-')}</td>
            <td class="p-3 text-center font-mono text-slate-500">${p.ordre || 1}</td>
            <td class="p-3 text-right whitespace-nowrap">
              ${['marque', 'modele', 'ram', 'disk', 'lot_reforme'].includes((p.categorie || '').toLowerCase()) ? `
                <button onclick="editParametre(${p.id_param})" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier">
                  <i class="fa-solid fa-pen-to-square"></i>
                </button>
              ` : ''}
              <button onclick="deleteParametre(${p.id_param})" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Supprimer">
                <i class="fa-solid fa-trash-can"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }
