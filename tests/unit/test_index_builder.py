"""Unit tests for the index builder artifacts."""

import pathlib

import faiss
import pytest

DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "gold_standard"


def test_gold_standard_json_exists():
    """data/gold_standard/questions.json must exist on disk."""
    path = DATA_DIR / "questions.json"
    assert path.exists(), f"File not found: {path}"


def test_faiss_index_exists_and_has_vectors():
    """data/gold_standard/questions.index must exist and contain >= 30 vectors."""
    path = DATA_DIR / "questions.index"
    assert path.exists(), f"FAISS index not found: {path}"

    index = faiss.read_index(str(path))
    assert index.ntotal >= 30, (
        f"Expected at least 30 vectors in FAISS index, found {index.ntotal}"
    )
