// Gestion des comptes administrateurs (API réservée au super admin).
function adminEscape(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function adminFeedback(message, error=false) {
  const box = document.getElementById('admins-feedback');
  if (!box) return;
  box.textContent = message;
  box.className = 'text-sm p-3 rounded mb-3 ' + (error ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700');
}
async function loadAdmins() {
  const body = document.getElementById('admins-table-body');
  if (!body) return;
  const response = await fetch('/api/admins');
  const rows = await response.json();
  if (!response.ok) throw new Error(rows.error || 'Chargement impossible.');
  body.innerHTML = rows.map(admin => `
    <tr>
      <td>${adminEscape(admin.full_name)}</td><td class="font-mono">${adminEscape(admin.username)}</td>
      <td>${admin.role === 'super_admin' ? 'Super administrateur' : 'Administrateur'}</td>
      <td><span class="${admin.is_active ? 'text-emerald-700' : 'text-rose-700'} font-semibold">${admin.is_active ? 'Actif' : 'Désactivé'}</span></td>
      <td class="text-right whitespace-nowrap">
        ${admin.role === 'admin' ? `
          <button class="px-2 py-1 border rounded mr-1" onclick="toggleAdmin(${admin.id}, ${admin.is_active ? 'false' : 'true'})">${admin.is_active ? 'Désactiver' : 'Réactiver'}</button>
          <button class="px-2 py-1 border rounded" onclick="resetAdminPassword(${admin.id})">Mot de passe</button>
        ` : '<span class="text-slate-400">Compte principal</span>'}
      </td>
    </tr>`).join('') || '<tr><td colspan="5" class="p-5 text-center text-slate-400">Aucun compte.</td></tr>';
}
async function toggleAdmin(id, active) {
  if (!confirm(active ? 'Réactiver cet administrateur ?' : 'Désactiver cet administrateur ?')) return;
  const response = await fetch('/api/admins/' + id, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({is_active:active})});
  const data = await response.json();
  if (!response.ok) { adminFeedback(data.error || 'Modification impossible.', true); return; }
  await loadAdmins(); adminFeedback('Compte mis à jour.');
}
async function resetAdminPassword(id) {
  const password = prompt('Nouveau mot de passe (10 caractères minimum) :');
  if (password === null) return;
  const response = await fetch('/api/admins/' + id, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({password})});
  const data = await response.json();
  if (!response.ok) { adminFeedback(data.error || 'Modification impossible.', true); return; }
  adminFeedback('Mot de passe modifié.');
}
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('admin-create-form');
  if (!form) return;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const payload = {
      full_name:document.getElementById('admin-full-name').value.trim(),
      username:document.getElementById('admin-username').value.trim(),
      password:document.getElementById('admin-password').value
    };
    const response = await fetch('/api/admins', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) { adminFeedback(data.error || 'Création impossible.', true); return; }
    form.reset(); await loadAdmins(); adminFeedback('Administrateur créé.');
  });
});
