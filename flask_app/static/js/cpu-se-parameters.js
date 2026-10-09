    function getParamsByCategory(category) {
      return (allParametres || []).filter(p => p.categorie === category && p.archiv !== 'O' && (p.valeur || '').trim())
        .sort((a, b) => (Number(a.ordre) || 1) - (Number(b.ordre) || 1) || String(a.valeur).localeCompare(String(b.valeur)));
    }

    function renderCpuParams() {
      const tbody = document.getElementById('cpu-param-table-body'); if (!tbody) return;
      const rows = getParamsByCategory('cpu');
      tbody.innerHTML = rows.length ? rows.map(p => '<tr class="hover:bg-slate-50 transition"><td class="p-3 font-semibold text-slate-800">' + escapeHtml(p.valeur) + '</td><td class="p-3 text-slate-500">' + escapeHtml(p.description || '—') + '</td><td class="p-3 text-center font-mono text-slate-500">' + (p.ordre || 1) + '</td><td class="p-3 text-right whitespace-nowrap"><button onclick="editCpuParam(' + p.id_param + ')" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier"><i class="fa-solid fa-pen-to-square"></i></button><button onclick="deleteCpuParam(' + p.id_param + ')" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Archiver"><i class="fa-solid fa-trash-can"></i></button></td></tr>').join('') : '<tr><td colspan="4" class="p-6 text-center text-slate-400">Aucun processeur configuré.</td></tr>';
    }

    function renderSeParams() {
      const tbody = document.getElementById('se-param-table-body'); if (!tbody) return;
      const rows = getParamsByCategory('se');
      tbody.innerHTML = rows.length ? rows.map(p => '<tr class="hover:bg-slate-50 transition"><td class="p-3 font-semibold text-slate-800">' + escapeHtml(p.valeur) + '</td><td class="p-3 text-slate-500">' + escapeHtml(p.description || '—') + '</td><td class="p-3 text-center font-mono text-slate-500">' + (p.ordre || 1) + '</td><td class="p-3 text-right whitespace-nowrap"><button onclick="editSeParam(' + p.id_param + ')" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier"><i class="fa-solid fa-pen-to-square"></i></button><button onclick="deleteSeParam(' + p.id_param + ')" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Archiver"><i class="fa-solid fa-trash-can"></i></button></td></tr>').join('') : '<tr><td colspan="4" class="p-6 text-center text-slate-400">Aucun système d’exploitation configuré.</td></tr>';
    }

    function openNewCpuModal() {
      document.getElementById('cpu-param-id').value = ''; document.getElementById('cpu-param-val').value = ''; document.getElementById('cpu-param-desc').value = ''; document.getElementById('cpu-param-ordre').value = '1';
      document.getElementById('cpu-modal-title').innerHTML = '<i class="fa-solid fa-microchip text-indigo-600"></i> Nouveau processeur';
      document.getElementById('modal-cpu').classList.remove('hidden');
    }

    function openNewSeModal() {
      document.getElementById('se-param-id').value = ''; document.getElementById('se-param-val').value = ''; document.getElementById('se-param-desc').value = ''; document.getElementById('se-param-ordre').value = '1';
      document.getElementById('se-modal-title').innerHTML = '<i class="fa-brands fa-windows text-indigo-600"></i> Nouveau système d’exploitation';
      document.getElementById('modal-se').classList.remove('hidden');
    }

    function editCpuParam(id) {
      const p = (allParametres || []).find(x => String(x.id_param) === String(id) && x.categorie === 'cpu'); if (!p) return;
      document.getElementById('cpu-param-id').value = p.id_param; document.getElementById('cpu-param-val').value = p.valeur || ''; document.getElementById('cpu-param-desc').value = p.description || ''; document.getElementById('cpu-param-ordre').value = p.ordre || 1;
      document.getElementById('cpu-modal-title').innerHTML = '<i class="fa-solid fa-pen-to-square text-indigo-600"></i> Modifier le processeur';
      document.getElementById('modal-cpu').classList.remove('hidden');
    }

    function editSeParam(id) {
      const p = (allParametres || []).find(x => String(x.id_param) === String(id) && x.categorie === 'se'); if (!p) return;
      document.getElementById('se-param-id').value = p.id_param; document.getElementById('se-param-val').value = p.valeur || ''; document.getElementById('se-param-desc').value = p.description || ''; document.getElementById('se-param-ordre').value = p.ordre || 1;
      document.getElementById('se-modal-title').innerHTML = '<i class="fa-solid fa-pen-to-square text-indigo-600"></i> Modifier le système d’exploitation';
      document.getElementById('modal-se').classList.remove('hidden');
    }

    async function saveDedicatedParametre(id, category, valeur, description, ordre, modalId, successMessage) {
      if (!valeur) { showToast('La valeur est obligatoire.', true); return; }
      try {
        const res = await fetch(id ? '/api/parametres/' + id : '/api/parametres', { method: id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({categorie:category, valeur, description, ordre}) });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) { showToast(result.error || 'Erreur lors de l’enregistrement.', true); return; }
        allParametres = await fetch('/api/parametres').then(r => r.json()); references.parametres = allParametres;
        renderParametres(); populateMaterielForm(); closeModal(modalId); showToast(successMessage);
      } catch (err) { showToast('Erreur serveur Flask', true); }
    }

    async function handleSaveCpu(e) { e.preventDefault(); await saveDedicatedParametre(document.getElementById('cpu-param-id').value, 'cpu', document.getElementById('cpu-param-val').value.trim(), document.getElementById('cpu-param-desc').value.trim(), parseInt(document.getElementById('cpu-param-ordre').value) || 1, 'modal-cpu', 'Processeur enregistré avec succès !'); }
    async function handleSaveSe(e) { e.preventDefault(); await saveDedicatedParametre(document.getElementById('se-param-id').value, 'se', document.getElementById('se-param-val').value.trim(), document.getElementById('se-param-desc').value.trim(), parseInt(document.getElementById('se-param-ordre').value) || 1, 'modal-se', 'Système d’exploitation enregistré avec succès !'); }

    async function deleteDedicatedParametre(id, category, message) {
      try { const res = await fetch('/api/parametres/' + id, {method:'DELETE'}); if (!res.ok) { const r = await res.json().catch(() => ({})); showToast(r.error || 'Erreur lors de l’archivage.', true); return; }
        allParametres = allParametres.filter(p => !(String(p.id_param) === String(id) && p.categorie === category)); references.parametres = allParametres; renderParametres(); populateMaterielForm(); showToast(message);
      } catch (err) { showToast('Erreur lors de l’archivage.', true); }
    }
    async function deleteCpuParam(id) { if (!confirm('Voulez-vous archiver ce processeur ?')) return; await deleteDedicatedParametre(id, 'cpu', 'Processeur archivé.'); }
    async function deleteSeParam(id) { if (!confirm('Voulez-vous archiver ce système d’exploitation ?')) return; await deleteDedicatedParametre(id, 'se', 'Système d’exploitation archivé.'); }