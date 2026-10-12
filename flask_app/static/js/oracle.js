// GESTION DU CONNECTEUR ORACLE
    function renderOracleHistory() {
      const histDiv = document.getElementById('oracle-history-list');
      if (!histDiv) return;

      if (allOracleHistory.length === 0) {
        histDiv.innerHTML = '<div class="text-slate-400 py-3 text-center">Aucune synchronisation précédente enregistrée.</div>';
        return;
      }

      histDiv.innerHTML = allOracleHistory.map(h => `
        <div class="py-2.5 flex items-center justify-between">
          <div>
            <div class="font-bold text-slate-800 flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
              Oracle SID: ${h.sid || 'ORCL'} (${h.host || 'localhost'})
            </div>
            <div class="text-[11px] text-slate-400">${h.timestamp || '-'} &bull; ${h.total_rows || 0} lignes traitées</div>
          </div>
          <div class="text-right">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">${h.status || 'OK'}</span>
            <div class="text-[10px] font-mono text-slate-400">${h.duration_ms || 0} ms</div>
          </div>
        </div>
      `).join('');
    }

    async function runTestOracleConnection() {
      const btn = document.getElementById('btn-oracle-test');
      const box = document.getElementById('oracle-logs-box');
      const resDiv = document.getElementById('oracle-test-result');
      const payload = {
        host: document.getElementById('ora-host').value.trim(),
        port: parseInt(document.getElementById('ora-port').value, 10) || 1521,
        sid: document.getElementById('ora-sid').value.trim(),
        connectType: document.getElementById('ora-connect-type').value,
        username: document.getElementById('ora-schema').value.trim(),
        password: document.getElementById('ora-password').value
      };
      if (!payload.host || !payload.sid || !payload.username || !payload.password) {
        showToast('Renseignez l’hôte, la base, l’utilisateur et le mot de passe Oracle.', true);
        return;
      }
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Test en cours...';
      box.innerHTML += `\n<div class="text-cyan-400">[${new Date().toLocaleTimeString()}] Test d’authentification Oracle vers ${payload.host}:${payload.port}...</div>`;
      box.scrollTop = box.scrollHeight;
      try {
        const res = await fetch('/api/oracle-sync/test', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await res.json();
        resDiv.classList.remove('hidden');
        if (!res.ok || !data.success) {
          resDiv.className = 'mt-4 p-4 rounded-xl border bg-rose-50 border-rose-200 text-rose-900';
          resDiv.innerHTML = `<div class="flex items-center gap-2 font-bold"><i class="fa-solid fa-triangle-exclamation text-rose-600 text-base"></i> ${data.message || 'Échec de l’authentification Oracle.'}</div>${data.oracleCode ? `<div class="text-xs mt-1">Code Oracle : ${data.oracleCode}</div>` : ''}`;
          box.innerHTML += `<div class="text-rose-400">[${new Date().toLocaleTimeString()}] ÉCHEC : ${data.message || 'Connexion Oracle refusée.'}</div>`;
          showToast('Échec du test Oracle', true);
          return;
        }
        resDiv.className = 'mt-4 p-4 rounded-xl border bg-emerald-50 border-emerald-200 text-emerald-900';
        resDiv.innerHTML = `<div class="flex items-center gap-2 font-bold"><i class="fa-solid fa-circle-check text-emerald-600 text-base"></i> ${data.message}</div><div class="text-xs text-emerald-700 mt-1 flex flex-wrap gap-4 font-mono"><span>Base : ${data.databaseName || '-'}</span><span>Service : ${data.serviceName || '-'}</span><span>Utilisateur connecté : ${data.username || payload.username}</span><span>Latence : ${data.latencyMs} ms</span></div>`;
        box.innerHTML += `<div class="text-emerald-400">[${new Date().toLocaleTimeString()}] SUCCÈS : session Oracle authentifiée (${data.latencyMs} ms).</div>`;
        box.scrollTop = box.scrollHeight;
        showToast('Authentification Oracle validée.');
      } catch (err) {
        resDiv.classList.remove('hidden');
        resDiv.className = 'mt-4 p-4 rounded-xl border bg-rose-50 border-rose-200 text-rose-900';
        resDiv.textContent = 'Impossible de joindre l’API Gparc. Vérifiez que le serveur Flask est démarré.';
        box.innerHTML += `<div class="text-rose-400">[${new Date().toLocaleTimeString()}] ERREUR : API Gparc inaccessible.</div>`;
        showToast('Erreur de test Oracle', true);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-bolt"></i> Tester la connexion';
      }
    }

    async function runExecuteOracleSync() {
      showToast('Importation désactivée : le connecteur doit être configuré pour lire les vraies tables Oracle.', true);
      const box = document.getElementById('oracle-logs-box');
      box.innerHTML += `<div class="text-amber-400">[${new Date().toLocaleTimeString()}] Importation bloquée : aucune donnée fictive ne sera écrite dans SQLite.</div>`;
      box.scrollTop = box.scrollHeight;
    }

    async function openOracleSqlModal() {
      const schema = document.getElementById('ora-schema').value.trim() || 'GPARC_USER';
      try {
        const res = await fetch('/api/oracle-sync/sql-script', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ schema: schema })
        });
        const data = await res.json();
        document.getElementById('oracle-sql-textarea').value = data.script || '';
        document.getElementById('modal-oracle-sql').classList.remove('hidden');
      } catch (err) {
        showToast('Impossible de générer le script SQL', true);
      }
    }

    function copyOracleSqlScript() {
      const txt = document.getElementById('oracle-sql-textarea');
      txt.select();
      navigator.clipboard.writeText(txt.value).then(() => {
        showToast('Script SQL copié dans le presse-papier !');
      }).catch(() => {
        showToast('Veuillez copier le texte manuellement');
      });
    }
