from datetime import datetime

from domain.models.snapshot import DatasetPart, DatasetSnapshot, RawBatch


def test_dataset_snapshot_stable_batch_identity():
    batch = RawBatch(
        batch_id="batch_001",
        source_id="oepm_bopi",
        retrieval_timestamp=datetime(2026, 9, 2, 10, 0, 0),
        payload_sha256="2832dc5936b881b4045b26b415f5c5ed2c0bfdc71f6902b838d85000e6799d7b",
    )
    part = DatasetPart(
        part_name="patents/part-0000.parquet",
        row_count=16,
        file_sha256="c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e",
    )
    snap = DatasetSnapshot(
        dataset_id="patents_es_v1",
        schema_version="2.3.0",
        source_batches=[batch],
        record_count=16,
        parts=[part],
        dataset_content_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        manifest_sha256="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        created_at=datetime(2026, 9, 2),
        transformation_version="1.0.0",
    )
    assert snap.record_count == 16
    assert snap.source_batches[0].batch_id == "batch_001"
    assert snap.source_batches[0].source_id == "oepm_bopi"
    assert snap.parts[0].part_name == "patents/part-0000.parquet"
    assert snap.parts[0].row_count == 16
    assert snap.dataset_content_sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert snap.manifest_sha256 == "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"
