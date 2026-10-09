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
        port: parseInt(document.getElementById('ora-port').value) || 1521,
        sid: document.getElementById('ora-sid').value.trim(),
        username: document.getElementById('ora-schema').value.trim()
      };

      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Test en cours...';

      box.innerHTML += `\n<div class="text-cyan-400">[${new Date().toLocaleTimeString()}] Test de connexion vers ${payload.host}:${payload.port} (SID=${payload.sid})...</div>`;
      box.scrollTop = box.scrollHeight;

      try {
        const res = await fetch('/api/oracle-sync/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        resDiv.classList.remove('hidden');
        resDiv.className = 'mt-4 p-4 rounded-xl border bg-emerald-50 border-emerald-200 text-emerald-900';
        resDiv.innerHTML = `
          <div class="flex items-center gap-2 font-bold">
            <i class="fa-solid fa-circle-check text-emerald-600 text-base"></i> ${data.message || 'Connexion Oracle établie avec succès !'}
          </div>
          <div class="text-xs text-emerald-700 mt-1 flex flex-wrap gap-4 font-mono">
            <span>Bannière: ${data.oracleBanner || 'Oracle Database'}</span>
            <span>Latence: ${data.latencyMs || 10} ms</span>
            <span>Charset: ${data.characterSet || 'AL32UTF8'}</span>
          </div>
        `;

        box.innerHTML += `<div class="text-emerald-400">[${new Date().toLocaleTimeString()}] SUCCÈS: Connecté à ${data.oracleBanner} (${data.latencyMs}ms)</div>`;
        box.scrollTop = box.scrollHeight;
        showToast('Connexion Oracle validée avec succès !');
      } catch (err) {
        resDiv.classList.remove('hidden');
        resDiv.className = 'mt-4 p-4 rounded-xl border bg-rose-50 border-rose-200 text-rose-900';
        resDiv.innerHTML = `
          <div class="flex items-center gap-2 font-bold">
            <i class="fa-solid fa-triangle-exclamation text-rose-600 text-base"></i> Échec du test direct
          </div>
          <div class="text-xs text-rose-700 mt-1">Vérifiez que le listener Oracle est démarré sur le port spécifié.</div>
        `;
        showToast('Erreur de test Oracle', true);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-bolt"></i> Tester la connexion';
      }
    }

    async function runExecuteOracleSync() {
      const btn = document.getElementById('btn-oracle-exec');
      const box = document.getElementById('oracle-logs-box');

      const payload = {
        host: document.getElementById('ora-host').value.trim(),
        port: parseInt(document.getElementById('ora-port').value) || 1521,
        sid: document.getElementById('ora-sid').value.trim(),
        schema: document.getElementById('ora-schema').value.trim(),
        strategy: document.getElementById('ora-strategy').value
      };

      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Synchronisation en cours...';

      box.innerHTML += `\n<div class="text-amber-400 font-bold">[${new Date().toLocaleTimeString()}] DÉMARRAGE DE LA SYNCHRONISATION ORACLE (Mode ${payload.strategy})...</div>`;
      box.scrollTop = box.scrollHeight;

      try {
        const res = await fetch('/api/oracle-sync/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
          (data.logs || []).forEach(log => {
            let color = 'text-slate-300';
            if (log.level === 'success') color = 'text-emerald-400 font-semibold';
            if (log.level === 'warn') color = 'text-amber-400';
            if (log.level === 'error') color = 'text-rose-400';
            box.innerHTML += `<div class="${color}">[${log.timestamp}] ${log.message}</div>`;
          });
          box.scrollTop = box.scrollHeight;

          showToast(`Synchronisation Oracle réussie (+${data.totalRowsProcessed} lignes) !`);

          // Recharger toutes les données pour rafraîchir la grille du parc
          await loadAllData();
        } else {
          showToast('Erreur durant la synchronisation', true);
        }
      } catch (err) {
        box.innerHTML += `<div class="text-rose-400">[${new Date().toLocaleTimeString()}] ERREUR: Impossible de joindre l'API de synchronisation.</div>`;
        showToast('Erreur de synchronisation Oracle', true);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Démarrer l\'importation';
      }
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
