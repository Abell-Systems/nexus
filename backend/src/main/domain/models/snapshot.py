from datetime import datetime
from pydantic import BaseModel, Field


class RawBatch(BaseModel):
    """Stable, machine-independent identity of an ingested raw batch."""

    batch_id: str
    source_id: str
    retrieval_timestamp: datetime
    payload_sha256: str


class DatasetPart(BaseModel):
    """Metadata for an individual Parquet partition chunk."""

    part_name: str
    row_count: int
    file_sha256: str


class DatasetSnapshot(BaseModel):
    """Content-addressed snapshot representing a frozen, immutable analytical corpus."""

    dataset_id: str
    schema_version: str
    source_batches: list[RawBatch] = Field(default_factory=list)
    record_count: int
    parts: list[DatasetPart] = Field(default_factory=list)
    dataset_content_sha256: str
    manifest_sha256: str
    created_at: datetime
    transformation_version: str
