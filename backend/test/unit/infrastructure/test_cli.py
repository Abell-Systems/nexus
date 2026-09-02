"""Unit tests for nexus ingest CLI parsing and execution."""

from pathlib import Path

from infrastructure.cli import main


def test_cli_help_exits_zero(monkeypatch):
    monkeypatch.setattr("sys.argv", ["nexus", "ingest", "--help"])
    try:
        main()
    except SystemExit as exc:
        assert exc.code == 0


def test_cli_missing_file_exits_nonzero(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "nexus",
            "ingest",
            "--source-type",
            "oepm",
            "--source-file",
            "/nonexistent/file.jsonl",
            "--dataset-id",
            "test_ds",
        ],
    )
    try:
        code = main()
        assert code != 0
    except SystemExit as exc:
        assert exc.code != 0


def test_cli_successful_ingest(tmp_path: Path, monkeypatch):
    sample_file = tmp_path / "sample.json"
    sample_file.write_text('{"items": [{"id": "ES-1234567-A1", "title": "Solid battery", "publication_date": "2021-01-01"}]}')
    output_dir = tmp_path / "output"

    monkeypatch.setattr(
        "sys.argv",
        [
            "nexus",
            "ingest",
            "--source-type",
            "oepm",
            "--source-file",
            str(sample_file),
            "--dataset-id",
            "test_ds",
            "--output-dir",
            str(output_dir),
        ],
    )
    code = main()
    assert code == 0
    assert (output_dir / "canonical").exists()
