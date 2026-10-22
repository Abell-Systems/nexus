"""Barrier: the benchmark does not run until the protocol is authorised (reviewer's condition, 2026-10-22).

AUTHORISATION.json must exist next to the pre-registration and record the sha256 of PREREGISTRATION.md as it stands.
It is created by a person after the protocol PR is merged; this code never creates it.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROTOCOL = HERE / "PREREGISTRATION.md"
AUTHORISATION = HERE / "AUTHORISATION.json"


class NotAuthorised(Exception):
    pass


def protocol_sha256(path: Path = PROTOCOL) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_authorisation(protocol: Path = PROTOCOL, authorisation: Path = AUTHORISATION) -> dict:
    if not authorisation.is_file():
        raise NotAuthorised(f"{authorisation.name} is missing: the protocol has not been authorised for execution")
    data = json.loads(authorisation.read_text())
    if data.get("protocol_sha256") != protocol_sha256(protocol):
        raise NotAuthorised("the protocol changed after it was authorised: amend it and authorise the new version")
    if not data.get("authorised_by") or not data.get("protocol_pr_merged_commit"):
        raise NotAuthorised("authorisation must name who authorised it and the merge commit of the protocol")
    return data
