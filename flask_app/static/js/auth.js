// Contrôles d'interface liés au compte authentifié.
document.addEventListener('DOMContentLoaded', () => {
  const role = document.body.dataset.role;
  const username = document.body.dataset.username || '';
  const label = document.getElementById('current-admin-label');
  if (label) label.textContent = username + (role === 'super_admin' ? ' · Super admin' : ' · Admin');
  if (role !== 'super_admin') {
    document.querySelectorAll('.super-admin-only').forEach(node => node.classList.add('hidden'));
  }
  const logout = document.getElementById('logout-button');
  if (logout) logout.addEventListener('click', async () => {
    await fetch('/api/auth/logout', {method:'POST'});
    window.location.reload();
  });
});
