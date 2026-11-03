async function deleteMateriel(matId) {
  if (!confirm('Êtes-vous sûr de vouloir retirer cet équipement du parc ?')) return;
  try {
    const res = await fetch('/api/materiels/' + matId, {method:'DELETE'});
    if (res.ok) {
      showToast('Équipement retiré du parc');
      await loadAllData();
    } else {
      const data = await res.json().catch(() => ({}));
      showToast(data.error || 'Erreur lors de la suppression', true);
    }
  } catch (error) {
    showToast('Erreur de connexion', true);
  }
}
