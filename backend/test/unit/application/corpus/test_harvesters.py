"""Unit tests for Phase-2 harvesters and immutable raw storage (ADR 0032)."""

import hashlib
import importlib
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_acquire = importlib.import_module("experiments.phase2.acquire")
acquire_main = _acquire.main


_harvesters = importlib.import_module("experiments.phase2.harvesters")
BaseHarvester = _harvesters.BaseHarvester
EenPodHarvester = _harvesters.EenPodHarvester
InnogetHarvester = _harvesters.InnogetHarvester
PayloadCollisionError = _harvesters.PayloadCollisionError


# --------------------------------------------------------------------------
# Raw Storage & Immutability Tests
# --------------------------------------------------------------------------


def test_save_raw_payload_creates_file_and_valid_sidecar(tmp_path: Path):
    harvester = BaseHarvester()
    payload = b"<html><body><h1>Test Challenge</h1></body></html>"
    demand_id = "INNOGET-2446"
    source_id = "innoget"
    source_uri = "https://www.innoget.com/technology-calls/2446/test"

    saved_path = harvester.save_raw_payload(
        demand_id=demand_id,
        source_id=source_id,
        source_uri=source_uri,
        payload_bytes=payload,
        out_dir=tmp_path,
        metadata={"custom_key": "custom_val"},
    )

    expected_payload_file = tmp_path / source_id / f"{demand_id}.html"
    expected_meta_file = tmp_path / source_id / f"{demand_id}.meta.json"

    assert saved_path == expected_payload_file
    assert expected_payload_file.exists()
    assert expected_payload_file.read_bytes() == payload
    assert expected_meta_file.exists()

    meta = json.loads(expected_meta_file.read_text(encoding="utf-8"))
    assert meta["demand_id"] == demand_id
    assert meta["source_id"] == source_id
    assert meta["source_uri"] == source_uri
    assert meta["raw_payload_sha256"] == hashlib.sha256(payload).hexdigest()
    assert meta["harvester_version"] == "phase2_harvester_v1"
    assert meta["http_status"] == 200
    assert meta["custom_key"] == "custom_val"
    assert "acquisition_timestamp" in meta


def test_save_raw_payload_json_extension_detection(tmp_path: Path):
    harvester = BaseHarvester()
    payload = b'{"reference": "TRES20250806011", "title": "Solar"}'
    demand_id = "TRES20250806011"
    source_id = "een_pod"
    source_uri = "https://example.com/api/proposals/1"

    saved_path = harvester.save_raw_payload(
        demand_id=demand_id,
        source_id=source_id,
        source_uri=source_uri,
        payload_bytes=payload,
        out_dir=tmp_path,
    )

    assert saved_path.suffix == ".json"
    assert saved_path.exists()
    assert (tmp_path / source_id / f"{demand_id}.meta.json").exists()


def test_save_raw_payload_idempotent_when_hash_matches(tmp_path: Path):
    harvester = BaseHarvester()
    payload = b"<html><body>Repeatable content</body></html>"
    demand_id = "DEMAND-001"
    source_id = "innoget"
    source_uri = "https://example.com/item"

    p1 = harvester.save_raw_payload(
        demand_id=demand_id,
        source_id=source_id,
        source_uri=source_uri,
        payload_bytes=payload,
        out_dir=tmp_path,
    )

    mtime_before = p1.stat().st_mtime_ns

    # Second save with identical payload
    p2 = harvester.save_raw_payload(
        demand_id=demand_id,
        source_id=source_id,
        source_uri=source_uri,
        payload_bytes=payload,
        out_dir=tmp_path,
    )

    mtime_after = p2.stat().st_mtime_ns

    assert p1 == p2
    assert mtime_before == mtime_after  # File was not re-written


def test_save_raw_payload_collision_raises_error(tmp_path: Path):
    harvester = BaseHarvester()
    payload_original = b"<html>Original content</html>"
    payload_differing = b"<html>Mutated content</html>"
    demand_id = "DEMAND-COLLIDE"
    source_id = "innoget"
    source_uri = "https://example.com/item"

    harvester.save_raw_payload(
        demand_id=demand_id,
        source_id=source_id,
        source_uri=source_uri,
        payload_bytes=payload_original,
        out_dir=tmp_path,
    )

    with pytest.raises(PayloadCollisionError) as exc_info:
        harvester.save_raw_payload(
            demand_id=demand_id,
            source_id=source_id,
            source_uri=source_uri,
            payload_bytes=payload_differing,
            out_dir=tmp_path,
        )

    assert "Payload collision" in str(exc_info.value)
    assert demand_id in str(exc_info.value)


# --------------------------------------------------------------------------
# Mocked Harvester & Operational Error Handling Tests
# --------------------------------------------------------------------------


def test_harvester_records_network_errors(tmp_path: Path):
    harvester = InnogetHarvester(delay_seconds=0.0)

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        results = harvester.harvest(out_dir=tmp_path, max_pages=1)

    assert len(results) == 0
    assert len(harvester.acquisition_errors) > 0
    err = harvester.acquisition_errors[0]
    assert err["source_id"] == "innoget"
    assert "Connection refused" in err["message"]

    # Test error log dumping
    error_file = tmp_path / "errors.json"
    harvester.dump_errors(error_file)
    assert error_file.exists()
    logged = json.loads(error_file.read_text(encoding="utf-8"))
    assert len(logged) == 1
    assert logged[0]["source_id"] == "innoget"


def test_innoget_harvester_discovers_and_saves_payloads(tmp_path: Path):
    listing_html = b"""
    <html>
    <body>
        <div class="call-card">
            <a href="/technology-calls/101/seeking-polymer-solutions">Polymer Challenge</a>
        </div>
        <div class="call-card">
            <a href="https://www.innoget.com/technology-calls/102/novel-coating">Coating Challenge</a>
        </div>
    </body>
    </html>
    """

    detail_101 = b"<html><head><title>Polymer</title></head><body><h1>Polymer Challenge</h1></body></html>"
    detail_102 = b"<html><head><title>Coating</title></head><body><h1>Coating Challenge</h1></body></html>"

    def mock_urlopen(req, timeout=30):
        url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.getcode.return_value = 200
        mock_resp.status = 200

        if "/technology-calls?page=" in url:
            mock_resp.read.return_value = listing_html
        elif "/technology-calls/101" in url:
            mock_resp.read.return_value = detail_101
        elif "/technology-calls/102" in url:
            mock_resp.read.return_value = detail_102
        else:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore
        return mock_resp

    harvester = InnogetHarvester(delay_seconds=0.0)
    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        saved = harvester.harvest(out_dir=tmp_path, max_pages=1)

    assert len(saved) == 2
    assert (tmp_path / "innoget" / "INNOGET-101.html").exists()
    assert (tmp_path / "innoget" / "INNOGET-102.html").exists()
    assert (tmp_path / "innoget" / "INNOGET-101.meta.json").exists()


def test_een_pod_harvester_discovers_and_saves_payloads(tmp_path: Path):
    listing_html = b"""
    <html>
    <body>
        <div class="listing">
            <a href="/en/collaborations/collaboration-proposals/860/manutenzione-giunti-di-ponti">Bridge Maintenance</a>
        </div>
    </body>
    </html>
    """

    detail_html = b"""
    <html>
    <head><title>Bridge Maintenance</title></head>
    <body>
        <h1>Bridge Maintenance</h1>
        <div class="reference">
            <span>POD Reference:</span>
            <span>TRES20250806011</span>
        </div>
    </body>
    </html>
    """

    def mock_urlopen(req, timeout=30):
        url = req.get_full_url() if hasattr(req, "get_full_url") else str(req)
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.getcode.return_value = 200
        mock_resp.status = 200

        if "collaboration-proposals" in url and "/860/" not in url:
            mock_resp.read.return_value = listing_html
        elif "/860/" in url:
            mock_resp.read.return_value = detail_html
        else:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)  # type: ignore
        return mock_resp

    harvester = EenPodHarvester(delay_seconds=0.0)
    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        saved = harvester.harvest(out_dir=tmp_path, max_pages=1)

    assert len(saved) == 1
    assert (tmp_path / "een_pod" / "TRES20250806011.html").exists()
    assert (tmp_path / "een_pod" / "TRES20250806011.meta.json").exists()


# --------------------------------------------------------------------------
# CLI Runner Test
# --------------------------------------------------------------------------


def test_acquire_cli_runner(tmp_path: Path):
    out_dir = tmp_path / "raw"
    errors_file = tmp_path / "errors.json"

    with patch.object(InnogetHarvester, "harvest") as mock_inno_harvest, patch.object(
        EenPodHarvester, "harvest"
    ) as mock_een_harvest:
        mock_inno_harvest.return_value = [out_dir / "innoget" / "INNOGET-1.html"]
        mock_een_harvest.return_value = [out_dir / "een_pod" / "TRIT1.html"]

        exit_code = acquire_main(
            [
                "--out-dir",
                str(out_dir),
                "--sources",
                "innoget,een_pod",
                "--limit",
                "5",
                "--delay",
                "0.0",
                "--errors-file",
                str(errors_file),
            ]
        )

        assert exit_code == 0
        assert mock_inno_harvest.called
        assert mock_een_harvest.called
