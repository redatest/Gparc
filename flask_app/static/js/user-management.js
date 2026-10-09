    function renderUtilisateurs() {
      const tbody = document.getElementById('utilisateurs-table-body');
      if (!tbody) return;
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O');
      tbody.innerHTML = users.length ? users.map(u => `
        <tr class="hover:bg-slate-50 transition">
          <td class="p-3 font-semibold text-slate-800">${escapeHtml(u.nom_uti || '')}</td>
          <td class="p-3 text-slate-700">${escapeHtml(u.pnom_uti || '')}</td>
          <td class="p-3 text-slate-500">${escapeHtml(u.mail_uti || '—')}</td>
          <td class="p-3 text-slate-600">${escapeHtml(u.lib_str || '—')}</td>
          <td class="p-3 text-center font-mono text-slate-400">${u.id_uti}</td>
          <td class="p-3 text-right whitespace-nowrap">
            <button onclick="editUtilisateur(${u.id_uti})" class="p-1.5 text-slate-400 hover:text-blue-600 rounded" title="Modifier"><i class="fa-solid fa-pen-to-square"></i></button>
            <button onclick="deleteUtilisateur(${u.id_uti})" class="p-1.5 text-slate-400 hover:text-rose-600 rounded" title="Archiver"><i class="fa-solid fa-trash-can"></i></button>
          </td>
        </tr>`).join('') : '<tr><td colspan="6" class="p-6 text-center text-slate-400">Aucun utilisateur configuré.</td></tr>';
    }

    function populateUtilisateurStructures(selectedId = '') {
      const select = document.getElementById('utilisateur-structure');
      if (!select) return;
      select.innerHTML = '<option value="">Aucune structure</option>' + (allStructures || []).map(s => `<option value="${s.id_str}">${escapeHtml(s.cod_str || '')} — ${escapeHtml(s.lib_str || '')}</option>`).join('');
      select.value = selectedId || '';
    }

    function populateUtilisateurAutocomplete() {
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O');
      const names = [...new Set(users.map(u => (u.nom_uti || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fr'));
      const firstNames = [...new Set(users.map(u => (u.pnom_uti || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fr'));
      const emails = [...new Set(users.map(u => (u.mail_uti || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fr'));
      const fill = (id, values) => {
        const list = document.getElementById(id);
        if (!list) return;
        list.innerHTML = values.map(v => '<option value="' + escapeHtml(v) + '"></option>').join('');
      };
      fill('utilisateurs-noms-list', names);
      fill('utilisateurs-prenoms-list', firstNames);
      fill('utilisateurs-emails-list', emails);
    }

    function checkUtilisateurAutocomplete(field) {
      const warning = document.getElementById('utilisateur-duplicate-warning');
      if (!warning) return;
      const inputId = field === 'nom' ? 'utilisateur-nom' : field === 'prenom' ? 'utilisateur-prenom' : 'utilisateur-mail';
      const value = (document.getElementById(inputId)?.value || '').trim().toLowerCase();
      const currentId = document.getElementById('utilisateur-id')?.value || '';
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O' && String(u.id_uti) !== String(currentId));
      const matches = users.filter(u => field === 'nom'
        ? String(u.nom_uti || '').trim().toLowerCase() === value
        : field === 'prenom'
          ? String(u.pnom_uti || '').trim().toLowerCase() === value
          : String(u.mail_uti || '').trim().toLowerCase() === value);
      const nom = (document.getElementById('utilisateur-nom')?.value || '').trim().toLowerCase();
      const prenom = (document.getElementById('utilisateur-prenom')?.value || '').trim().toLowerCase();
      const mail = (document.getElementById('utilisateur-mail')?.value || '').trim().toLowerCase();
      const sameIdentity = users.some(u =>
        nom && prenom &&
        String(u.nom_uti || '').trim().toLowerCase() === nom &&
        String(u.pnom_uti || '').trim().toLowerCase() === prenom &&
        (!mail || String(u.mail_uti || '').trim().toLowerCase() === mail)
      );
      if (sameIdentity) {
        warning.textContent = 'Cet utilisateur existe déjà dans la base de données. Vérifiez les informations saisies avant de continuer.';
        warning.classList.remove('hidden');
      } else if (value && matches.length) {
        const label = field === 'nom' ? 'nom' : field === 'prenom' ? 'prénom' : 'adresse e-mail';
        warning.textContent = 'Cette ' + label + ' existe déjà dans la base. Sélectionnez une valeur existante si elle correspond à la personne recherchée.';
        warning.classList.remove('hidden');
      } else {
        warning.classList.add('hidden');
        warning.textContent = '';
      }
    }

    function openNewUtilisateurModal() {
      document.getElementById('utilisateur-id').value = '';
      document.getElementById('utilisateur-nom').value = '';
      document.getElementById('utilisateur-prenom').value = '';
      document.getElementById('utilisateur-mail').value = '';
      const warning = document.getElementById('utilisateur-duplicate-warning');
      if (warning) { warning.classList.add('hidden'); warning.textContent = ''; }
      populateUtilisateurStructures();
      populateUtilisateurAutocomplete();
      document.getElementById('utilisateur-modal-title').innerHTML = '<i class="fa-solid fa-user text-indigo-600"></i> Nouvel utilisateur';
      document.getElementById('modal-utilisateur').classList.remove('hidden');
    }

    function editUtilisateur(id) {
      const u = (references.utilisateurs || []).find(x => String(x.id_uti) === String(id));
      if (!u) return;
      document.getElementById('utilisateur-id').value = u.id_uti;
      document.getElementById('utilisateur-nom').value = u.nom_uti || '';
      document.getElementById('utilisateur-prenom').value = u.pnom_uti || '';
      document.getElementById('utilisateur-mail').value = u.mail_uti || '';
      const warning = document.getElementById('utilisateur-duplicate-warning');
      if (warning) { warning.classList.add('hidden'); warning.textContent = ''; }
      populateUtilisateurStructures(u.id_str_mere || '');
      populateUtilisateurAutocomplete();
      document.getElementById('utilisateur-modal-title').innerHTML = '<i class="fa-solid fa-pen-to-square text-indigo-600"></i> Modifier l’utilisateur';
      document.getElementById('modal-utilisateur').classList.remove('hidden');
    }

    async function refreshUtilisateurs() {
      const users = await fetch('/api/utilisateurs').then(r => r.json());
      references.utilisateurs = users || [];
      renderUtilisateurs();
      populateMaterielForm();
    }

    async function handleSaveUtilisateur(e) {
      e.preventDefault();
      const id = document.getElementById('utilisateur-id').value;
      const nom = document.getElementById('utilisateur-nom').value.trim();
      const prenom = document.getElementById('utilisateur-prenom').value.trim();
      const mail = document.getElementById('utilisateur-mail').value.trim();
      const users = (references.utilisateurs || []).filter(u => u.archiv !== 'O' && String(u.id_uti) !== String(id));
      const duplicateEmail = mail && users.some(u => String(u.mail_uti || '').trim().toLowerCase() === mail.toLowerCase());
      const duplicatePerson = users.some(u =>
        String(u.nom_uti || '').trim().toLowerCase() === nom.toLowerCase() &&
        String(u.pnom_uti || '').trim().toLowerCase() === prenom.toLowerCase() &&
        (!mail || String(u.mail_uti || '').trim().toLowerCase() === mail.toLowerCase())
      );
      if (duplicateEmail || duplicatePerson) {
        checkUtilisateurAutocomplete(duplicateEmail ? 'email' : 'nom');
        showToast('Cet utilisateur existe déjà ou utilise une adresse e-mail déjà enregistrée.', true);
        return;
      }
      const payload = {
        nom_uti: document.getElementById('utilisateur-nom').value.trim(),
        pnom_uti: document.getElementById('utilisateur-prenom').value.trim(),
        mail_uti: document.getElementById('utilisateur-mail').value.trim(),
        id_str_mere: document.getElementById('utilisateur-structure').value || null
      };
      try {
        const res = await fetch(id ? '/api/utilisateurs/' + id : '/api/utilisateurs', { method: id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) { showToast(result.error || 'Erreur lors de l’enregistrement', true); return; }
        showToast(id ? 'Utilisateur modifié avec succès !' : 'Utilisateur ajouté avec succès !');
        closeModal('modal-utilisateur');
        await refreshUtilisateurs();
      } catch (err) { showToast('Erreur serveur Flask', true); }
    }

    async function deleteUtilisateur(id) {
      if (!confirm('Voulez-vous archiver cet utilisateur ? Les affectations historiques seront conservées.')) return;
      try {
        const res = await fetch('/api/utilisateurs/' + id, { method: 'DELETE' });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) { showToast(result.error || 'Erreur lors de l’archivage', true); return; }
        showToast('Utilisateur archivé');
        await refreshUtilisateurs();
      } catch (err) { showToast('Erreur serveur Flask', true); }
    }
