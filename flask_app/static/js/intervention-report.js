function formatReportDate(value) {
      if (!value) return '';
      const d = new Date(String(value).replace(' ', 'T'));
      if (Number.isNaN(d.getTime())) return String(value);
      return d.toLocaleDateString('fr-FR');
    }

    async function viewReport(panneId) {
      try {
        const res = await fetch('/api/pannes/' + panneId + '/report');
        if (!res.ok) throw new Error('Rapport introuvable');
        const rpt = await res.json();

        const set = (id, value) => {
          const el = document.getElementById(id);
          if (el) el.innerText = value ?? '';
        };

        // Champs présents dans le modèle et correspondants à notre base.
        set('rpt-ref', '............/SSSI/2026');
        set('rpt-bon', '');
        set('rpt-dps', '');
        // La date DPS correspond à la date saisie lors de la déclaration de la panne.
        set('rpt-date-dps', formatReportDate(rpt.intervention?.datePanne));
        set('rpt-structure', rpt.utilisateur?.service || '');
        set('rpt-date-arrivee', '');

        set('rpt-ser', rpt.equipement?.numSerie || '');
        set('rpt-type', rpt.equipement?.type || '');
        set('rpt-brand', rpt.equipement?.marque || '');
        set('rpt-model', rpt.equipement?.modele || '');

        set('rpt-date-reparation', formatReportDate(rpt.intervention?.dateReparation));
        set('rpt-date-retour', formatReportDate(rpt.intervention?.dateRetour));
        set('rpt-lieu-reparation', rpt.intervention?.lieuReparation || '');
        // Le code à barre correspond au N° d'inventaire enregistré dans le parc.
        set('rpt-barcode', rpt.equipement?.numInventaire || '');

        set('rpt-diag', rpt.intervention?.diagnostic || '');
        // Feedback utilisateur : champ volontairement vierge pour saisie manuelle après impression.
        set('rpt-observation', '');
        set('rpt-tech', rpt.intervention?.technicien || '');
        set('rpt-travaux', rpt.intervention?.travaux || '');
        // La base ne possède pas de nouveau code à barre ni de PV numérisé.
        set('rpt-new-barcode', '');

        // Aucun champ correspondant n'existe dans la base : laissé vide pour saisie manuelle.
        set('rpt-date-generation', '');

        document.getElementById('modal-report').classList.remove('hidden');
      } catch (e) {
        console.error(e);
        showToast("Impossible d'afficher la fiche", true);
      }
    }
