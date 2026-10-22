import json

import pytest
from harness.guard import NotAuthorised, protocol_sha256, require_authorisation
from harness.contract import EXIT_REFUSED
import run_benchmark


def auth(path, protocol, **o):
    data = {"protocol_sha256": protocol_sha256(protocol), "authorised_by": "someone", "protocol_pr_merged_commit": "abc", **o}
    path.write_text(json.dumps(data))


def test_shouldRefuseWhenThereIsNoAuthorisationFile(tmp_path):
    p = tmp_path / "P.md"; p.write_text("protocol")
    with pytest.raises(NotAuthorised):
        require_authorisation(p, tmp_path / "AUTHORISATION.json")


def test_shouldRefuseWhenProtocolChangedAfterAuthorisation(tmp_path):
    p, a = tmp_path / "P.md", tmp_path / "A.json"
    p.write_text("v1"); auth(a, p); p.write_text("v2")
    with pytest.raises(NotAuthorised):
        require_authorisation(p, a)


@pytest.mark.parametrize("missing", ["authorised_by", "protocol_pr_merged_commit"])
def test_shouldRefuseWhenAuthorisationDoesNotNameWhoAndWhichMerge(tmp_path, missing):
    p, a = tmp_path / "P.md", tmp_path / "A.json"
    p.write_text("v1"); auth(a, p, **{missing: ""})
    with pytest.raises(NotAuthorised):
        require_authorisation(p, a)


def test_shouldAcceptWhenAuthorisationMatchesTheProtocol(tmp_path):
    p, a = tmp_path / "P.md", tmp_path / "A.json"
    p.write_text("v1"); auth(a, p)
    assert require_authorisation(p, a)["authorised_by"] == "someone"


def test_shouldExitRefusedWhenEntryPointRunsWithoutAuthorisation():
    assert run_benchmark.main(["--work-dir", "x", "--pg-dsn", "x", "--container", "x"]) == EXIT_REFUSED  # no AUTHORISATION.json exists in the repository
