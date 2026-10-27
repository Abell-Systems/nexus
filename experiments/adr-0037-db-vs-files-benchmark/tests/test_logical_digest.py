"""canonical_rows_digest must not hide duplicates, cardinality changes or value ambiguities."""
from datetime import date

from harness.tables import TABLES, canonical_rows_digest


def base():
    rows = {t.name: [] for t in TABLES}
    rows["ipc_subclass"] = [("A61K", "A", "61", "K"), ("A61k", "A", "61", "k")]
    rows["party"] = [(1, "applicant", 0, "Ana"), (1, "applicant", 1, "None")]
    rows["priority_date"] = [(1, 0, date(1999, 3, 1))]
    return rows


def test_shouldChangeWhenARowIsDuplicated():
    a, b = base(), base()
    b["party"].append(b["party"][0])
    assert canonical_rows_digest(a) != canonical_rows_digest(b)


def test_shouldChangeWhenARowIsRemoved():
    a, b = base(), base()
    b["ipc_subclass"].pop()
    assert canonical_rows_digest(a) != canonical_rows_digest(b)


def test_shouldNotDependOnRowOrderInput():
    a, b = base(), base()
    b["ipc_subclass"].reverse()
    assert canonical_rows_digest(a) == canonical_rows_digest(b)


def test_shouldDistinguishNullFromTheTextNone():
    a, b = base(), base()
    b["party"][1] = (1, "applicant", 1, None)
    assert canonical_rows_digest(a) != canonical_rows_digest(b)


def test_shouldDistinguishCaseOfSymbols():
    a, b = base(), base()
    b["ipc_subclass"][1] = ("A61K ", "A", "61", "k")
    assert canonical_rows_digest(a) != canonical_rows_digest(b)


def test_shouldChangeWhenAValueMovesBetweenTables():
    a, b = base(), base()
    b["priority_date"] = []
    b["party"].append((1, "inventor", 0, "1999-03-01"))
    assert canonical_rows_digest(a) != canonical_rows_digest(b)
