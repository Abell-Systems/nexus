"""The biblio_v1 tables (ADR 0037 §3.2): the single definition both alternatives are built from.

Types are abstract ("int", "text", "date", "bigint") and mapped by each store, so A and B cannot drift apart in schema.
"""
from collections.abc import Iterable
from dataclasses import dataclass

from domain.models.whitespace import PatentPublication, RejectedRecord


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[tuple[str, str], ...]
    key: tuple[str, ...]
    references: tuple[tuple[str, str], ...] = ()  # (column, referenced table); enforced by A only, see HARNESS_DESIGN.md


TABLES: tuple[Table, ...] = (
    Table("source_file", (("file_id", "int"), ("name", "text"), ("sha256", "text"), ("bytes", "bigint")), ("file_id",)),
    Table("source_record", (("record_id", "int"), ("file_id", "int"), ("archive_path", "text")), ("record_id",),
          (("file_id", "source_file"),)),
    Table("publication", (("record_id", "int"), ("country", "text"), ("doc_number", "text"), ("kind", "text"),
                          ("publication_date", "date"), ("application_country", "text"), ("application_number", "text"),
                          ("application_kind", "text"), ("application_date", "date"), ("title", "text")), ("record_id",),
          (("record_id", "source_record"),)),
    Table("priority_date", (("record_id", "int"), ("ordinal", "int"), ("priority_date", "date")), ("record_id", "ordinal"),
          (("record_id", "publication"),)),
    Table("party", (("record_id", "int"), ("role", "text"), ("ordinal", "int"), ("name", "text")), ("record_id", "role", "ordinal"),
          (("record_id", "publication"),)),
    Table("ipc_subclass", (("symbol", "text"), ("section", "text"), ("class_number", "text"), ("subclass", "text")), ("symbol",)),
    Table("ipc_entry", (("record_id", "int"), ("ordinal", "int"), ("subclass_symbol", "text"), ("main_group", "text"),
                        ("subgroup", "text"), ("version", "text"), ("level", "text"), ("value", "text")), ("record_id", "ordinal"),
          (("record_id", "publication"), ("subclass_symbol", "ipc_subclass"))),
    Table("anomaly", (("record_id", "int"), ("ordinal", "int"), ("field", "text"), ("raw_value", "text"), ("reason", "text")),
          ("record_id", "ordinal"), (("record_id", "publication"),)),
    Table("rejected_record", (("file_id", "int"), ("archive_path", "text"), ("reason", "text")), ("file_id", "archive_path"),
          (("file_id", "source_file"),)),
)
BY_NAME = {t.name: t for t in TABLES}


def rows_from_outcomes(
    outcomes: Iterable[PatentPublication | RejectedRecord], files: dict[str, dict]
) -> dict[str, list[tuple]]:
    """The same rows for A and B, from the adapter's output. `files` maps file name to {sha256, bytes}."""
    file_id = {name: i for i, name in enumerate(sorted(files))}
    rows: dict[str, list[tuple]] = {t.name: [] for t in TABLES}
    rows["source_file"] = [(i, n, files[n]["sha256"], files[n]["bytes"]) for n, i in file_id.items()]
    symbols: dict[str, tuple[str, str, str]] = {}
    rid = 0
    for o in outcomes:
        pv = o.provenance
        if isinstance(o, RejectedRecord):
            rows["rejected_record"].append((file_id[pv.source_file], pv.archive_path, o.reason))
            continue
        rid += 1
        a = o.application_reference
        rows["source_record"].append((rid, file_id[pv.source_file], pv.archive_path))
        rows["publication"].append((rid, o.country, o.doc_number, o.kind, o.publication_date, a.country if a else None,
                                    a.number if a else None, a.kind if a else None, o.application_date, o.title))
        rows["priority_date"] += [(rid, k, d) for k, d in enumerate(o.priority_dates)]
        rows["party"] += [(rid, "applicant", k, n) for k, n in enumerate(o.applicants)]
        rows["party"] += [(rid, "inventor", k, n) for k, n in enumerate(o.inventors)]
        for k, e in enumerate(o.ipc_entries):
            symbols[e.subclass_symbol] = (e.section, e.class_number, e.subclass)
            rows["ipc_entry"].append((rid, k, e.subclass_symbol, e.main_group, e.subgroup, e.version, e.level, e.value))
        rows["anomaly"] += [(rid, k, x.field, x.raw_value, x.reason) for k, x in enumerate(o.anomalies)]
    rows["ipc_subclass"] = [(s, *v) for s, v in sorted(symbols.items())]
    return rows


class ReferentialError(Exception):
    """A row refers to a row that does not exist. Raised by both stores at prepare time, so they enforce the same semantics."""


def check_references(rows: dict[str, list[tuple]]) -> None:
    """The foreign keys of `tables.py`, checked on the shared rows. A also enforces them in the database; B calls this."""
    for t in TABLES:
        names = [c for c, _ in t.columns]
        for column, referenced in t.references:
            target = BY_NAME[referenced]
            tnames = [c for c, _ in target.columns]
            # a reference points at the referenced table's key column of the same name, or at its single key column
            tcol = column if column in tnames else target.key[0]
            valid = {r[tnames.index(tcol)] for r in rows[referenced]}
            i = names.index(column)
            for r in rows[t.name]:
                if r[i] not in valid:
                    raise ReferentialError(f"{t.name}.{column}={r[i]!r} has no row in {referenced}.{tcol}")


def canonical_rows_digest(rows: dict[str, list[tuple]]) -> str:
    """Logical content digest, common to both stores: rows sorted in Python by primary key (independent of any collation or
    physical order), serialised as canonical JSON. Equal logical content gives an equal digest whatever the storage."""
    import hashlib
    import json

    parts = []
    for t in TABLES:
        names = [c for c, _ in t.columns]
        idx = [names.index(k) for k in t.key]
        ordered = sorted(rows[t.name], key=lambda r: tuple(r[i] for i in idx))
        blob = json.dumps([list(r) for r in ordered], separators=(",", ":"), ensure_ascii=False, default=str)
        parts.append(f"{t.name}:{hashlib.sha256(blob.encode()).hexdigest()}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()
