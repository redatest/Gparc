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
          resDiv.innerHTML = `<div class="flex items-center gap-2 font-bold"><i class="fa-solid fa-triangle-exclamation text-rose-600 text-base"></i> ${data.message || 'Échec de l’authentification Oracle.'}</div>${data.oracleCode ? `<div class="text-xs mt-1 font-mono">Code : ${data.oracleCode}</div>` : ''}${data.details ? `<div class="text-xs mt-2 whitespace-pre-wrap break-words">Détail technique : ${String(data.details).replace(/[&<>"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[ch]))}</div>` : ''}`;
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

    function escapeOracleHtml(value) {
      return String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[ch]));
    }

    async function inspectOracleSchema() {
      const btn = document.getElementById('btn-oracle-schema');
      const result = document.getElementById('oracle-schema-result');
      const summary = document.getElementById('oracle-schema-summary');
      const tables = document.getElementById('oracle-schema-tables');
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
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Exploration...';
      result.classList.remove('hidden');
      summary.textContent = 'Lecture du dictionnaire Oracle en cours...';
      tables.innerHTML = '';
      try {
        const res = await fetch('/api/oracle-sync/schema', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
          summary.innerHTML = '<span class="text-rose-700 font-semibold">' +
            escapeOracleHtml(data.message || 'Échec de l’exploration') + '</span>' +
            (data.details ? '<div class="mt-1 whitespace-pre-wrap">' + escapeOracleHtml(data.details) + '</div>' : '');
          showToast('Exploration du schéma Oracle échouée.', true);
          return;
        }
        summary.textContent = data.message + ' Utilisateur : ' + data.username + '.';
        if (!data.objects || data.objects.length === 0) {
          tables.textContent = 'Aucune table ou vue visible pour cet utilisateur. Il faudra vérifier le schéma propriétaire et les droits d’accès.';
        } else {
          tables.innerHTML = data.objects.map(obj => {
            const cols = obj.columns.map(col =>
              '<tr class="border-t border-indigo-100">' +
              '<td class="px-2 py-1 font-mono">' + escapeOracleHtml(col.name) + '</td>' +
              '<td class="px-2 py-1">' + escapeOracleHtml(col.dataType) +
              (col.length ? ' (' + escapeOracleHtml(col.length) + ')' : '') + '</td>' +
              '<td class="px-2 py-1">' + (col.nullable ? 'Oui' : 'Non') + '</td>' +
              '<td class="px-2 py-1">' + escapeOracleHtml(col.comment) + '</td></tr>'
            ).join('');
            return '<details class="bg-white border border-indigo-100 rounded-lg" open>' +
              '<summary class="cursor-pointer px-3 py-2 text-xs font-bold">' +
              escapeOracleHtml(obj.name) + ' <span class="text-slate-500 font-normal">(' +
              escapeOracleHtml(obj.type) + ', ' + obj.columns.length + ' colonnes)</span>' +
              (obj.comment ? ' — ' + escapeOracleHtml(obj.comment) : '') + '</summary>' +
              '<div class="overflow-auto"><table class="w-full text-[11px]"><thead><tr class="bg-slate-50 text-left">' +
              '<th class="px-2 py-1">Colonne</th><th class="px-2 py-1">Type</th><th class="px-2 py-1">Nullable</th>' +
              '<th class="px-2 py-1">Commentaire</th></tr></thead><tbody>' + cols +
              '</tbody></table></div></details>';
          }).join('');
        }
        document.getElementById('oracle-logs-box').innerHTML +=
          '<div class="text-indigo-300">[' + new Date().toLocaleTimeString() +
          '] Schéma Oracle exploré en lecture seule : ' + Number(data.objectCount || 0) + ' objets.</div>';
        showToast('Exploration Oracle terminée.');
      } catch (err) {
        summary.textContent = 'Impossible de joindre l’API Gparc. Vérifiez que Flask est démarré.';
        showToast('Erreur pendant l’exploration Oracle.', true);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-table-list"></i> Explorer les tables';
      }
    }

    async function runExecuteOracleSync() {
      const btn = document.getElementById('btn-oracle-exec');
      const box = document.getElementById('oracle-logs-box');
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
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Prévisualisation...';
      box.innerHTML += '<div class="text-cyan-300">[' + new Date().toLocaleTimeString() + '] Lecture des volumes Oracle et vérification des références...</div>';
      box.scrollTop = box.scrollHeight;
      try {
        const previewRes = await fetch('/api/oracle-sync/preview', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const previewData = await previewRes.json();
        if (!previewRes.ok || !previewData.success) {
          throw new Error(previewData.message || 'La prévisualisation Oracle a échoué.' + (previewData.details || ''));
        }
        const p = previewData.preview;
        const countText = Object.entries(p.counts || {}).map(([table, count]) => table + ': ' + count).join('\n');
        const warnings = (p.warnings || []).map(w => '- ' + w.label + ' : ' + w.count).join('\n');
        const confirmation = 'PRÉVISUALISATION ORACLE\n\n' + countText +
          '\n\nTotal : ' + p.totalRows + ' lignes sources.' +
          '\n\n' + (warnings ? 'Anomalies détectées :\n' + warnings : 'Aucune anomalie détectée par les contrôles automatiques.') +
          '\n\nLes données de démonstration seront remplacées. Une sauvegarde SQLite sera créée et toutes les lignes Oracle brutes seront archivées. Continuer ?';
        if (!window.confirm(confirmation)) {
          box.innerHTML += '<div class="text-amber-300">[' + new Date().toLocaleTimeString() + '] Import annulé par l’utilisateur après prévisualisation. Aucune donnée locale modifiée.</div>';
          return;
        }
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Importation...';
        box.innerHTML += '<div class="text-cyan-300">[' + new Date().toLocaleTimeString() + '] Import transactionnel démarré...</div>';
        const res = await fetch('/api/oracle-sync/execute', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
          throw new Error((data.message || 'Échec de l’import Oracle.') + (data.details ? '\n' + data.details : ''));
        }
        const localCounts = Object.entries(data.operationalCounts || {}).map(([table, count]) => table + ': ' + count).join(' | ');
        box.innerHTML += '<div class="text-emerald-300">[' + new Date().toLocaleTimeString() + '] IMPORT TERMINÉ. Sauvegarde : ' +
          escapeOracleHtml(data.backupPath || 'aucune (base vide)') + '</div><div class="text-emerald-200">' +
          escapeOracleHtml(localCounts) + '</div><div class="text-slate-400">Lot : ' + escapeOracleHtml(data.batchId) + '</div>';
        showToast('Import Oracle terminé. Vérifiez le parc, les utilisateurs et l’historique des pannes.');
        if (typeof loadOracleHistory === 'function') loadOracleHistory();
        if (typeof loadMateriels === 'function') loadMateriels();
      } catch (err) {
        box.innerHTML += '<div class="text-rose-300 whitespace-pre-wrap">[' + new Date().toLocaleTimeString() + '] ERREUR : ' + escapeOracleHtml(err.message) + '</div>';
        showToast('Import Oracle échoué. La base locale n’a pas été partiellement importée.', true);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Prévisualiser et importer';
        box.scrollTop = box.scrollHeight;
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
