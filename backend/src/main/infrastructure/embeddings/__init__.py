"""Offline embedding artifacts shared by the generation scripts and the runtime retriever.

Must not import duckdb, pyarrow, torch, or anything from infrastructure.matching: the isolated
generation environment (requirements/evaluation-generation.txt) has none of them.
"""
