// Gestion du formulaire d'ajout et de modification des équipements.
// Les données de référence et l'identifiant d'édition restent partagés avec app.js.

    function openNewMaterielModal() {
      editingMaterielId = null;
      const title = document.getElementById('modal-materiel-title');
      const submit = document.getElementById('mat-submit-btn');
      if (title) title.innerText = "Ajouter un équipement au parc";
      if (submit) submit.innerText = "Enregistrer l'équipement";

      // Réinitialiser d'abord le formulaire, puis charger les listes.
      // L'ancien ordre effaçait la liste des modèles juste après son alimentation.
      resetMaterielForm();
      populateMaterielForm();

      document.getElementById('modal-materiel').classList.remove('hidden');
    }

    async function openEditMaterielModal(matId) {
      try {
        const res = await fetch('/api/materiels/' + matId);
        if (!res.ok) throw new Error('Équipement introuvable');
        const mat = await res.json();
        editingMaterielId = mat.id_mat;

        const title = document.getElementById('modal-materiel-title');
        const submit = document.getElementById('mat-submit-btn');
        if (title) title.innerText = "Modifier l'équipement";
        if (submit) submit.innerText = 'Enregistrer les modifications';

        populateMaterielForm();
        document.getElementById('mat-num-inv').value = mat.num_inv || '';
        document.getElementById('mat-num-ser').value = mat.num_ser || '';
        document.getElementById('mat-marque').value = mat.marque_mat || '';
        document.getElementById('mat-type').value = mat.id_typ_mat || '';
        document.getElementById('mat-str').value = mat.id_str || '';
        filterMaterielModels();
        filterMaterielUsers();
        document.getElementById('mat-model').value = mat.id_model_mat || '';
        document.getElementById('mat-user').value = mat.id_uti || '';
        document.getElementById('mat-cpu').value = mat.cpu || '';
        document.getElementById('mat-se').value = mat.se || '';
        document.getElementById('mat-ram').value = mat.ram ?? '';
        const diskSel = document.getElementById('mat-disk');
        const diskValue = mat.disk ?? '';
        if (diskSel && diskValue !== '' && !Array.from(diskSel.options).some(o => String(o.value) === String(diskValue))) {
          diskSel.insertAdjacentHTML('beforeend', '<option value="' + escapeHtml(String(diskValue)) + '">' + escapeHtml(String(diskValue)) + ' Go (valeur actuelle)</option>');
        }
        if (diskSel) diskSel.value = diskValue;
        document.getElementById('modal-materiel').classList.remove('hidden');
      } catch (err) {
        showToast("Impossible de charger l'équipement", true);
      }
    }

    function resetMaterielForm() {
      ['mat-num-inv','mat-num-ser','mat-marque','mat-type','mat-model','mat-str','mat-user','mat-cpu','mat-se','mat-ram' ,'mat-disk'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      const modelSel = document.getElementById('mat-model');
      if (modelSel) { modelSel.innerHTML = "<option value=''>Choisir d'abord une marque...</option>"; modelSel.disabled = true; }
      const userSel = document.getElementById('mat-user');
      if (userSel) userSel.value = '';
    }

    function populateMaterielForm() {
      const brandSel = document.getElementById('mat-marque');
      const typeSel = document.getElementById('mat-type');
      const strSel = document.getElementById('mat-str');
      const userSel = document.getElementById('mat-user');
      const modelSel = document.getElementById('mat-model');
      const cpuSel = document.getElementById('mat-cpu');
      const seSel = document.getElementById('mat-se');
      const ramSel = document.getElementById('mat-ram');
      const diskSel = document.getElementById('mat-disk');
      if (!brandSel || !typeSel || !strSel || !userSel || !modelSel || !cpuSel || !seSel || !ramSel || !diskSel) return;

      const brands = (references.parametres || [])
        .filter(p => p.categorie === 'marque')
        .map(p => p.valeur)
        .filter(Boolean);
      brandSel.innerHTML = '<option value="">Sélectionner une marque...</option>' +
        [...new Set(brands)].sort().map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join('');

      typeSel.innerHTML = '<option value="">Sélectionner un type...</option>' +
        (references.types || []).map(t => `<option value="${t.id_typ_mat}">${escapeHtml(t.lib_typ_mat)} (${escapeHtml(t.cod_typ_mat || '')})</option>`).join('');

      strSel.innerHTML = '<option value="">Sélectionner une structure...</option>' +
        (references.structures || []).map(st => `<option value="${st.id_str}">[${escapeHtml(st.cod_str || '')}] ${escapeHtml(st.lib_str || '')}</option>`).join('');

      modelSel.innerHTML = "<option value=''>Choisir d'abord une marque...</option>";
      const cpuParams = getParamsByCategory('cpu');
      cpuSel.innerHTML = '<option value="">Sélectionner un processeur...</option>' + cpuParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + '</option>').join('');
      const seParams = getParamsByCategory('se');
      seSel.innerHTML = '<option value="">Sélectionner un système d’exploitation...</option>' + seParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + '</option>').join('');
      const ramParams = getParamsByCategory('ram');
      ramSel.innerHTML = '<option value="">Sélectionner la RAM...</option>' + ramParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + ' Go</option>').join('');
      const diskParams = getParamsByCategory('disk');
      diskSel.innerHTML = '<option value="">Sélectionner le stockage...</option>' + diskParams.map(p => '<option value="' + escapeHtml(p.valeur) + '">' + escapeHtml(p.valeur) + ' Go</option>').join('');
      userSel.innerHTML = '<option value="">Aucun (En stock DSI)</option>' +
        (references.utilisateurs || []).map(u => `<option value="${u.id_uti}">${escapeHtml((u.nom_uti || '') + ' ' + (u.pnom_uti || ''))}</option>`).join('');

      brandSel.onchange = filterMaterielModels;
      typeSel.onchange = filterMaterielModels;
      strSel.onchange = filterMaterielUsers;
      filterMaterielModels();
      filterMaterielUsers();
    }

    function filterMaterielModels() {
      const brand = document.getElementById('mat-marque')?.value || '';
      const typeId = document.getElementById('mat-type')?.value || '';
      const modelSel = document.getElementById('mat-model');
      if (!modelSel) return;

      // Les modèles définis dans Paramètres sont disponibles dès l'ajout.
      // Les modèles du référentiel restent filtrés par marque/type.
      const models = brand
        ? (references.modeles || []).filter(m =>
            m.marque_mat === brand && (!typeId || !m.id_typ_mat || String(m.id_typ_mat) === String(typeId))
          )
        : [];

      const parameterModels = (references.parametres || [])
        .filter(p => p.categorie === 'modele' && p.archiv !== 'O' && (p.valeur || '').trim())
        .map(p => ({ id_param: p.id_param, model_mat: p.valeur.trim() }));

      const existingNames = new Set(models.map(m => (m.model_mat || '').trim().toLowerCase()));
      const extraModels = parameterModels.filter(p => !existingNames.has(p.model_mat.toLowerCase()));

      modelSel.disabled = models.length === 0 && extraModels.length === 0;
      modelSel.innerHTML =
        '<option value="">' +
        (extraModels.length || models.length ? 'Sélectionner un modèle...' : 'Aucun modèle configuré...') +
        '</option>' +
        models.map(m => `<option value="${m.id_model_mat}">${escapeHtml(m.model_mat || '')}</option>`).join('') +
        extraModels.map(p => `<option value="param:${p.id_param}" data-model-name="${escapeHtml(p.model_mat)}">${escapeHtml(p.model_mat)} (Paramètre)</option>`).join('');
    }

    function filterMaterielUsers() {
      const structureId = document.getElementById('mat-str')?.value || '';
      const userSel = document.getElementById('mat-user');
      if (!userSel) return;
      const users = (references.utilisateurs || []).filter(u => !structureId || !u.id_str_mere || String(u.id_str_mere) === String(structureId));
      userSel.innerHTML = '<option value="">Aucun (En stock DSI)</option>' +
        users.map(u => `<option value="${u.id_uti}">${escapeHtml((u.nom_uti || '') + ' ' + (u.pnom_uti || ''))}</option>`).join('');
    }

    async function handleSaveMateriel(e) {
      e.preventDefault();
      const payload = {
        num_inv: document.getElementById('mat-num-inv').value.trim(),
        num_ser: document.getElementById('mat-num-ser').value.trim(),
        marque_mat: document.getElementById('mat-marque').value.trim(),
        id_model_mat: /^\d+$/.test(document.getElementById('mat-model').value) ? parseInt(document.getElementById('mat-model').value) : null,
        model_mat_name: (() => {
          const opt = document.getElementById('mat-model').selectedOptions[0];
          return opt?.dataset.modelName || '';
        })(),
        id_typ_mat: parseInt(document.getElementById('mat-type').value) || null,
        id_str: parseInt(document.getElementById('mat-str').value) || null,
        id_uti: parseInt(document.getElementById('mat-user').value) || null,
        cpu: document.getElementById('mat-cpu').value.trim(),
        se: document.getElementById('mat-se').value.trim(),
        ram: parseInt(document.getElementById('mat-ram').value) || null,
        disk: parseInt(document.getElementById('mat-disk').value) || null,
        image_url: ''
      };

      if (!payload.num_inv || !payload.num_ser || !payload.marque_mat || !payload.id_typ_mat || !payload.id_str) {
        showToast('Veuillez renseigner le N° inventaire, N° série, marque, type et structure.', true);
        return;
      }

      try {
        const url = editingMaterielId ? '/api/materiels/' + editingMaterielId : '/api/materiels';
        const method = editingMaterielId ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json().catch(() => ({}));
        if (res.ok) {
          closeModal('modal-materiel');
          showToast(editingMaterielId ? 'Équipement modifié avec succès !' : 'Équipement ajouté au parc avec succès !');
          editingMaterielId = null;
          await loadAllData();
        } else {
          showToast(result.error || "Erreur lors de l'enregistrement", true);
        }
      } catch (err) {
        showToast('Erreur serveur', true);
      }
    }
