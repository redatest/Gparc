"""Importateur Oracle vers le schéma SQLite de GPARC.

Les lignes Oracle brutes sont archivées avant toute normalisation afin que les
champs sans équivalent fonctionnel dans GPARC ne soient jamais perdus.
"""
import json
import os
import re
import sqlite3
import uuid
from datetime import date, datetime
from decimal import Decimal

try:
    from .database import DB_PATH
    from .database_reference_sync import sync_reference_data
except ImportError:
    from database import DB_PATH
    from database_reference_sync import sync_reference_data


SOURCE_TABLES = (
    "STRUCTURE", "UTI", "TYPE_MAT", "MODEL_MAT", "CARA_MAT",
    "LIEU_REP", "MATERIEL", "AFFECT_MAT", "PANNE", "ETUDIANT", "TASKS",
)
OPERATIONAL_TABLES = (
    "historique_reforme", "panne", "affect_mat", "materiel",
    "utilisateurs", "lieu_rep", "model_mat", "type_mat", "structures",
)


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _archived(value):
    return str(value or "").strip().upper() in {"O", "Y", "1", "S", "T", "TRUE", "YES"}


def _text(value, fallback=""):
    if value is None:
        return fallback
    return str(value).strip() or fallback


def _split_user_name(nom_value, prenom_value):
    """Sépare les valeurs Oracle de type « NOM.Prénom » lors de l'import."""
    nom = _text(nom_value)
    prenom = _text(prenom_value)

    # Dans l'ancien GPARC, certains utilisateurs sont enregistrés dans NOM_UTI
    # sous la forme « nom.prénom ». Dans ce cas, la partie après le premier
    # point devient le prénom, comme lors de la normalisation SQL manuelle.
    if "." in nom:
        nom, prenom = nom.split(".", 1)
        nom = nom.strip()
        prenom = prenom.strip()

    return nom or "Nom inconnu", prenom or "Prénom inconnu"


def _date(value, fallback=None):
    if value is None:
        return fallback
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    value = str(value).strip()
    return value[:10] if value else fallback


def _int_or_none(value):
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _number_or_none(value):
    try:
        return float(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _equipment_state(value):
    code = _text(value).upper()
    if code in {"OP", "BON", "OK", "SO", "ES"}:
        return "BON"
    if code in {"PA", "RE", "EP", "ER", "EC", "AT", "PANNE", "EN PANNE"}:
        return "PANNE"
    if code in {"IR", "NR", "IRREPARABLE"}:
        return "IRREPARABLE"
    # Preserve an unknown code in the raw archive; keep the UI in a known state.
    return "BON"


def _panne_state(value):
    code = _text(value).upper()
    return {
        "EC": "EP", "PA": "EP", "EP": "EP",
        "AT": "ER", "RE": "ER", "ER": "ER",
        "RP": "RP", "OK": "RP", "IR": "IR", "NR": "IR",
    }.get(code, code if code in {"EP", "ER", "RP", "IR"} else "EP")


def _read_source(connection):
    cursor = connection.cursor()
    available = set()
    cursor.execute("SELECT table_name FROM user_tables")
    available = {str(row[0]).upper() for row in cursor.fetchall()}
    missing = [name for name in SOURCE_TABLES if name not in available]
    if missing:
        raise ValueError(
            "Tables Oracle manquantes ou invisibles pour ce compte : " + ", ".join(missing)
        )
    data = {}
    for table in SOURCE_TABLES:
        cursor.execute('SELECT * FROM "' + table + '"')
        columns = [item[0].upper() for item in cursor.description]
        rows = []
        for values in cursor.fetchall():
            rows.append({columns[i]: _json_value(values[i]) for i in range(len(columns))})
        data[table] = rows
    cursor.close()
    return data


def _index(rows, key):
    return {row.get(key): row for row in rows if row.get(key) is not None}


def _match_equipment(row, by_inventory, by_serial):
    inv = row.get("NUM_INV")
    serial = row.get("NUM_SER")
    inv_matches = by_inventory.get(inv, []) if inv is not None else []
    serial_matches = by_serial.get(serial, []) if serial is not None else []
    if not isinstance(inv_matches, list):
        inv_matches = [inv_matches]
    if not isinstance(serial_matches, list):
        serial_matches = [serial_matches]
    if inv_matches and serial_matches:
        serial_ids = {item.get("ID_MAT") for item in serial_matches}
        common = [item for item in inv_matches if item.get("ID_MAT") in serial_ids]
        if common:
            return common[0]
    if len(inv_matches) == 1:
        return inv_matches[0]
    if len(serial_matches) == 1:
        return serial_matches[0]
    if inv_matches:
        return inv_matches[0]
    if serial_matches:
        return serial_matches[0]
    return None


def preview_source(data):
    """Produit un bilan et les anomalies détectables sans écrire dans SQLite."""
    equipment = data["MATERIEL"]
    structures = _index(data["STRUCTURE"], "ID_STR")
    types = _index(data["TYPE_MAT"], "ID_TYP_MAT")
    models = _index(data["MODEL_MAT"], "ID_MODEL_MAT")
    users = _index(data["UTI"], "ID_UTI")
    inventory_counts = {}
    serial_counts = {}
    for row in equipment:
        inv = row.get("NUM_INV")
        serial = row.get("NUM_SER")
        if inv:
            inventory_counts[inv] = inventory_counts.get(inv, 0) + 1
        if serial:
            serial_counts[serial] = serial_counts.get(serial, 0) + 1

    missing_inventory = sum(not row.get("NUM_INV") for row in equipment)
    duplicate_inventory = sum(count - 1 for count in inventory_counts.values() if count > 1)
    duplicate_serial = sum(count - 1 for count in serial_counts.values() if count > 1)
    missing_structure = sum(row.get("ID_STR") is not None and row.get("ID_STR") not in structures for row in equipment)
    missing_type = sum(row.get("ID_TYP_MAT") is not None and row.get("ID_TYP_MAT") not in types for row in equipment)
    missing_model = sum(row.get("ID_MODEL_MAT") is not None and row.get("ID_MODEL_MAT") not in models for row in equipment)
    missing_user = sum(row.get("ID_UTI") is not None and row.get("ID_UTI") not in users for row in equipment)
    by_inventory = {r.get("NUM_INV"): r for r in equipment if r.get("NUM_INV") is not None}
    by_serial = {r.get("NUM_SER"): r for r in equipment if r.get("NUM_SER") is not None}
    orphan_affect = sum(_match_equipment(r, by_inventory, by_serial) is None for r in data["AFFECT_MAT"])
    orphan_panne = sum(_match_equipment(r, by_inventory, by_serial) is None for r in data["PANNE"])

    counts = {table: len(rows) for table, rows in data.items()}
    warnings = []
    for label, count in (
        ("Matériels sans numéro d’inventaire (un numéro technique sera créé)", missing_inventory),
        ("Numéros d’inventaire dupliqués (un numéro technique sera créé pour les doublons)", duplicate_inventory),
        ("Numéros de série dupliqués", duplicate_serial),
        ("Références de structure absentes", missing_structure),
        ("Références de type absentes", missing_type),
        ("Références de modèle absentes", missing_model),
        ("Références d’utilisateur absentes", missing_user),
        ("Affectations sans matériel correspondant (archivées sans entrée active)", orphan_affect),
        ("Pannes sans matériel correspondant (archivées sans entrée active)", orphan_panne),
    ):
        if count:
            warnings.append({"label": label, "count": count})
    return {
        "counts": counts,
        "totalRows": sum(counts.values()),
        "warnings": warnings,
        "willReplaceDemoData": True,
        "rawArchiveTables": list(SOURCE_TABLES),
    }


def _ensure_archive_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS oracle_source_archive (
            id_archive INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_key TEXT,
            payload_json TEXT NOT NULL,
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_oracle_archive_batch ON oracle_source_archive(import_batch)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_oracle_archive_table ON oracle_source_archive(source_table)")


def _backup_database():
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH + ".pre_oracle_" + stamp + ".bak"
    source = sqlite3.connect(DB_PATH, timeout=15)
    target = sqlite3.connect(backup_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return backup_path


def import_source(data):
    """Remplace les données opérationnelles dans une transaction, en conservant tout le brut."""
    backup_path = _backup_database()
    batch_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.cursor()
        _ensure_archive_table(cur)

        # Preserve every source row, including tables/fields not yet represented in the UI.
        for table, rows in data.items():
            for index, row in enumerate(rows):
                key_fields = {
                    "STRUCTURE": "ID_STR", "UTI": "ID_UTI", "TYPE_MAT": "ID_TYP_MAT",
                    "MODEL_MAT": "ID_MODEL_MAT", "CARA_MAT": "ID_CARA_MAT",
                    "LIEU_REP": "ID_LIEU_REP", "MATERIEL": "ID_MAT",
                    "AFFECT_MAT": "ID_AFF_MAT", "PANNE": "ID_PAN", "ETUDIANT": "ID_ETU",
                }
                source_key = row.get(key_fields.get(table, "")) if key_fields.get(table) else None
                cur.execute(
                    "INSERT INTO oracle_source_archive (import_batch, source_table, source_key, payload_json) VALUES (?, ?, ?, ?)",
                    (batch_id, table, None if source_key is None else str(source_key),
                     json.dumps(row, ensure_ascii=False, default=_json_value)),
                )

        # Empty demo/operational rows only; keep the application's extended schema and configuration tables.
        for table in OPERATIONAL_TABLES:
            cur.execute("DELETE FROM " + table)

        structures = data["STRUCTURE"]
        users = data["UTI"]
        types = data["TYPE_MAT"]
        models = data["MODEL_MAT"]
        chars = data["CARA_MAT"]
        places = data["LIEU_REP"]
        equipment = data["MATERIEL"]
        assignments = data["AFFECT_MAT"]
        incidents = data["PANNE"]

        type_ids = {r.get("ID_TYP_MAT") for r in types}
        structure_ids = {r.get("ID_STR") for r in structures}
        user_ids = {r.get("ID_UTI") for r in users}
        model_ids = {r.get("ID_MODEL_MAT") for r in models}
        place_ids = {r.get("ID_LIEU_REP") for r in places}

        for r in structures:
            cur.execute("""INSERT INTO structures
                (id_str, cod_str, lib_str, id_str_mere, archiv, dat_cre)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (r.get("ID_STR"), _text(r.get("COD_STR"), "NC"), _text(r.get("LIB_STR"), "Structure sans libellé"),
                 r.get("ID_STR_MERE") if r.get("ID_STR_MERE") in structure_ids else None,
                 "O" if _archived(r.get("ARCHIV")) else "N", _date(r.get("DAT_CRE"))))

        for r in types:
            cur.execute("""INSERT INTO type_mat (id_typ_mat, cod_typ_mat, lib_typ_mat, archiv, dat_cre)
                VALUES (?, ?, ?, ?, ?)""",
                (r.get("ID_TYP_MAT"), _text(r.get("COD_TYP_MAT"), "N")[:1],
                 _text(r.get("LIB_TYP_MAT"), "Type sans libellé"),
                 "O" if _archived(r.get("ARCHIV")) else "N", _date(r.get("DAT_CRE"))))

        model_type = {}
        for r in equipment:
            if r.get("ID_MODEL_MAT") is not None and r.get("ID_TYP_MAT") in type_ids:
                model_type.setdefault(r.get("ID_MODEL_MAT"), r.get("ID_TYP_MAT"))
        for r in assignments:
            if r.get("ID_MODEL_MAT") is not None and r.get("ID_TYP_MAT") in type_ids:
                model_type.setdefault(r.get("ID_MODEL_MAT"), r.get("ID_TYP_MAT"))
        for r in models:
            cur.execute("""INSERT INTO model_mat
                (id_model_mat, marque_mat, model_mat, id_typ_mat, archiv, dat_cre)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (r.get("ID_MODEL_MAT"), _text(r.get("MARQUE_MAT"), "Marque inconnue"),
                 _text(r.get("MODEL_MAT"), "Modèle sans libellé"), model_type.get(r.get("ID_MODEL_MAT")),
                 "O" if _archived(r.get("ARCHIV")) else "N", _date(r.get("DAT_CRE"))))

        for r in places:
            name = _text(r.get("NOM_LIEU_REP"), "Lieu de réparation sans nom")
            category = "LOCAL" if any(word in name.lower() for word in ("atelier", "interne", "dsi")) else "EXTERIEUR"
            cur.execute("""INSERT INTO lieu_rep
                (id_lieu_rep, nom_lieu_rep, adr_lieu_rep, archiv, dat_cre, categorie_lieu)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (r.get("ID_LIEU_REP"), name, r.get("ADR_LIEU_REP"),
                 "O" if _archived(r.get("ARCHIV")) else "N", _date(r.get("DAT_CRE")), category))

        for r in users:
            structure_id = r.get("ID_STR_MERE")
            cur.execute("""INSERT INTO utilisateurs
                (id_uti, nom_uti, pnom_uti, mail_uti, id_str_mere, archiv, dat_cre)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (r.get("ID_UTI"), *_split_user_name(r.get("NOM_UTI"), r.get("PNOM_UTI")), r.get("MAIL_UTI"),
                 structure_id if structure_id in structure_ids else None,
                 "O" if _archived(r.get("ARCHIV")) else "N", _date(r.get("DAT_CRE"))))

        # Build a unique inventory key for operational tables. Duplicates stay intact in the raw archive.
        by_inventory = {}
        by_serial = {}
        equipment_items = []
        seen_inventory = set()
        seen_serial = set()
        generated_inventory = set()
        for r in equipment:
            original_id = r.get("ID_MAT")
            inv = _text(r.get("NUM_INV"))
            if not inv or inv in seen_inventory:
                inv = "ORACLE-MAT-" + _text(original_id, str(len(seen_inventory) + 1))
                suffix = 2
                base = inv
                while inv in generated_inventory or inv in seen_inventory:
                    inv = base + "-" + str(suffix)
                    suffix += 1
                generated_inventory.add(inv)
            seen_inventory.add(inv)
            serial = _text(r.get("NUM_SER"), "SANS-SERIE-" + _text(original_id, "0"))
            if serial in seen_serial:
                serial = serial + "-ORACLE-" + _text(original_id, str(len(seen_serial) + 1))
            seen_serial.add(serial)
            item = dict(r)
            item["_GPARC_NUM_INV"] = inv
            item["_GPARC_NUM_SER"] = serial
            equipment_items.append(item)
            if r.get("NUM_INV") is not None:
                by_inventory.setdefault(r.get("NUM_INV"), []).append(item)
            if r.get("NUM_SER") is not None:
                by_serial.setdefault(r.get("NUM_SER"), []).append(item)
        items_by_id = {item.get("ID_MAT"): item for item in equipment_items}

        char_by_id = _index(chars, "ID_CARA_MAT")
        def char_value(value):
            row = char_by_id.get(value)
            return _text(row.get("LIB_CARA_MAT")) if row else ("" if value is None else str(value))

        def character_number(value):
            # RAM/DISK are legacy NUMBER references in many installations; resolve
            # them through CARA_MAT before treating a number as a literal capacity.
            row = char_by_id.get(value)
            label = _text(row.get("LIB_CARA_MAT")) if row else ""
            if label:
                match = re.search(r"(\d+(?:[.,]\d+)?)\s*(ko|mo|go|to|kb|mb|gb|tb)?", label, re.IGNORECASE)
                if not match:
                    return None
                amount = float(match.group(1).replace(",", "."))
                unit = (match.group(2) or "").lower()
                if unit in {"to", "tb"}:
                    amount *= 1000
                elif unit in {"ko", "kb"}:
                    amount = amount / 1000000
                elif unit in {"mo", "mb"}:
                    amount = amount / 1000
                return int(round(amount))
            return _int_or_none(value)

        for r in equipment:
            item = items_by_id.get(r.get("ID_MAT"))
            if item is None:
                item = dict(r)
                item["_GPARC_NUM_INV"] = "ORACLE-MAT-" + _text(r.get("ID_MAT"), "0")
                item["_GPARC_NUM_SER"] = "SANS-SERIE-" + _text(r.get("ID_MAT"), "0")
            state = _equipment_state(r.get("ETAT_MAT"))
            archived = _archived(r.get("ARCHIV"))
            retired = bool(r.get("DAT_SORTIE") or r.get("MOTIF_SORTIE"))
            lifecycle = "RF" if retired else "ES"
            reform_state = "REFORME" if retired else "AUCUNE"
            cpu_text = char_value(r.get("CPU"))
            if r.get("FREQ_CPU") is not None:
                cpu_text = (cpu_text + " " + _text(r.get("FREQ_CPU"))).strip()
            if not cpu_text:
                cpu_text = char_value(r.get("CPU2"))
            se_text = char_value(r.get("SE")) or char_value(r.get("SE2"))
            net_text = char_value(r.get("NET")) or char_value(r.get("NET2"))
            ram_value = character_number(r.get("RAM"))
            if ram_value is None:
                ram_value = character_number(r.get("RAM2"))
            disk_value = character_number(r.get("DISK"))
            if disk_value is None:
                disk_value = character_number(r.get("DISK2"))
            cur.execute("""INSERT INTO materiel
                (id_mat, id_str, id_typ_mat, id_model_mat, marque_mat, num_inv, num_ser,
                 dat_acq, dat_mes, etat_mat, obs_mat, dat_sortie, motif_sortie,
                 ram, disk, cpu, se, net, ordi, ip, id_uti, archiv, dat_cre, dat_mod,
                 statut_mat, etat_reforme, motif_reforme, date_reforme, annee_reforme)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r.get("ID_MAT"),
                 r.get("ID_STR") if r.get("ID_STR") in structure_ids else None,
                 r.get("ID_TYP_MAT") if r.get("ID_TYP_MAT") in type_ids else None,
                 r.get("ID_MODEL_MAT") if r.get("ID_MODEL_MAT") in model_ids else None,
                 _text((models and next((m.get("MARQUE_MAT") for m in models if m.get("ID_MODEL_MAT") == r.get("ID_MODEL_MAT")), None)) or ""),
                 item["_GPARC_NUM_INV"], item["_GPARC_NUM_SER"],
                 _date(r.get("DAT_ACQ")), _date(r.get("DAT_MES")), state, r.get("OBS_MAT"),
                 _date(r.get("DAT_SORTIE")), r.get("MOTIF_SORTIE"),
                 ram_value, disk_value, cpu_text, se_text, net_text, r.get("ORDI"), r.get("IP"),
                 r.get("ID_UTI") if r.get("ID_UTI") in user_ids else None,
                 "O" if archived else "N", _date(r.get("DAT_CRE")), _date(r.get("DAT_MOD")),
                 lifecycle, reform_state, r.get("MOTIF_SORTIE") if retired else None,
                 _date(r.get("DAT_SORTIE")) if retired else None,
                 int(_date(r.get("DAT_SORTIE"))[:4]) if retired and _date(r.get("DAT_SORTIE")) else None))

        # Refresh current assignment on equipment from Oracle's AFFECT_MAT when it has the latest DAT_AFF.
        latest_assignment = {}
        for r in assignments:
            item = _match_equipment(r, by_inventory, by_serial)
            if item is None:
                continue
            mat_id = item.get("ID_MAT")
            previous = latest_assignment.get(mat_id)
            if previous is None or _text(r.get("DAT_AFF")) > _text(previous.get("DAT_AFF")):
                latest_assignment[mat_id] = r
        for mat_id, r in latest_assignment.items():
            if r.get("ID_STR") in structure_ids:
                cur.execute("UPDATE materiel SET id_str = ? WHERE id_mat = ?", (r.get("ID_STR"), mat_id))

        for r in assignments:
            item = _match_equipment(r, by_inventory, by_serial)
            if item is None:
                continue
            mat_id = item.get("ID_MAT")
            structure_id = r.get("ID_STR") if r.get("ID_STR") in structure_ids else None
            model_id = r.get("ID_MODEL_MAT") if r.get("ID_MODEL_MAT") in model_ids else None
            type_id = r.get("ID_TYP_MAT") if r.get("ID_TYP_MAT") in type_ids else None
            current_user = cur.execute("SELECT id_uti FROM materiel WHERE id_mat = ?", (mat_id,)).fetchone()
            cur.execute("""INSERT INTO affect_mat
                (id_aff_mat, id_mat, id_str, id_model_mat, id_typ_mat, num_inv, num_ser,
                 dat_aff, obs_aff, id_uti, action_aff, archiv, dat_cre, dat_mod)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NOUVELLE_AFFECTATION', ?, ?, ?)""",
                (r.get("ID_AFF_MAT"), mat_id, structure_id, model_id, type_id,
                 item["_GPARC_NUM_INV"], item["_GPARC_NUM_SER"], _date(r.get("DAT_AFF")),
                 r.get("OBS_AFF"), current_user["id_uti"] if current_user else None,
                 "O" if _archived(r.get("ARCHIV")) else "N", _date(r.get("DAT_CRE")), _date(r.get("DAT_MOD"))))

        for r in incidents:
            item = _match_equipment(r, by_inventory, by_serial)
            if item is None:
                continue
            mat_id = item.get("ID_MAT")
            diag = _text(r.get("DIAG_PAN"), "Diagnostic non renseigné (import Oracle)")
            date_panne = _date(r.get("DAT_PAN"), _date(r.get("DAT_CRE"), date.today().isoformat()))
            place_id = r.get("ID_LIEU_REP") if r.get("ID_LIEU_REP") in place_ids else None
            code = _panne_state(r.get("ETA_PAN"))
            cur.execute("""INSERT INTO panne
                (id_pan, id_mat, id_str, id_typ_mat, id_model_mat, num_inv, num_ser,
                 dat_pan, diag_pan, dat_env_rep, dat_ret_rep, id_lieu_rep, obs_rep,
                 eta_pan, tp, technicien, pieces_remplacees, recommandations, cout_rep,
                 archiv, dat_cre)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (r.get("ID_PAN"), mat_id,
                 r.get("ID_STR") if r.get("ID_STR") in structure_ids else item.get("ID_STR"),
                 r.get("ID_TYP_MAT") if r.get("ID_TYP_MAT") in type_ids else item.get("ID_TYP_MAT"),
                 r.get("ID_MODEL_MAT") if r.get("ID_MODEL_MAT") in model_ids else item.get("ID_MODEL_MAT"),
                 item["_GPARC_NUM_INV"], item["_GPARC_NUM_SER"], date_panne, diag,
                 _date(r.get("DAT_ENV_REP")), _date(r.get("DAT_RET_REP")), place_id,
                 r.get("OBS_REP"), code, "MAT", None, None, None,
                 "O" if _archived(r.get("ARCHIV")) else "N", _date(r.get("DAT_CRE"))))
            if code in {"EP", "ER"}:
                cur.execute("UPDATE materiel SET etat_mat = 'PANNE' WHERE id_mat = ?", (mat_id,))
            elif code == "IR":
                cur.execute("UPDATE materiel SET etat_mat = 'IRREPARABLE' WHERE id_mat = ?", (mat_id,))

        # Convert the characteristic reference data into selectable values without dropping the raw rows.
        for r in chars:
            label = _text(r.get("LIB_CARA_MAT"))
            if not label:
                continue
            family = _text(r.get("FAM_CARA_MAT"), "oracle")
            normalized = family.lower()
            if any(k in normalized for k in ("processeur", "cpu", "frequence")):
                category = "cpu"
            elif any(k in normalized for k in ("ram", "memoire", "mémoire")):
                category = "ram"
            elif any(k in normalized for k in ("disk", "disque", "stockage")):
                category = "disk"
            elif any(k in normalized for k in ("systeme", "système", "os", "exploitation")):
                category = "se"
            elif any(k in normalized for k in ("reseau", "réseau", "net")):
                category = "net"
            else:
                category = "oracle_" + "".join(ch.lower() if ch.isalnum() else "_" for ch in family).strip("_")[:40]
            exists = cur.execute("SELECT 1 FROM parametres_materiel WHERE categorie = ? AND LOWER(TRIM(valeur)) = LOWER(TRIM(?)) AND archiv = 'N'", (category, label)).fetchone()
            if not exists:
                cur.execute("INSERT INTO parametres_materiel (categorie, valeur, description, ordre, archiv) VALUES (?, ?, ?, 0, ?)",
                            (category, label, "Importé de CARA_MAT Oracle (" + family + ")", "O" if _archived(r.get("ARCHIV")) else "N"))

        # Keep the parameter selectors aligned with the newly imported brands/models.
        sync_reference_data(cur)

        conn.commit()
        return {
            "success": True,
            "batchId": batch_id,
            "backupPath": backup_path,
            "counts": {table: len(rows) for table, rows in data.items()},
            "operationalCounts": {
                table: conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                for table in ("structures", "utilisateurs", "type_mat", "model_mat", "lieu_rep", "materiel", "affect_mat", "panne")
            },
            "message": "Import Oracle terminé. Les lignes sources complètes sont conservées dans oracle_source_archive."
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
