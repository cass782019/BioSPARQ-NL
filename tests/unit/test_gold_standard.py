"""Unit tests for the gold standard dataset (data/gold_standard/questions.json)."""

import json
import pathlib

import pytest

DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "gold_standard"
QUESTIONS_PATH = DATA_DIR / "questions.json"

REQUIRED_FIELDS = {
    "id",
    "question_pt",
    "question_en",
    "sparql",
    "type",
    "difficulty",
    "expected_min_results",
}


@pytest.fixture(scope="module")
def questions():
    """Load the gold standard questions once for all tests in this module."""
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_minimum_30_questions(questions):
    """The gold standard must contain at least 30 questions."""
    assert len(questions) >= 30, (
        f"Expected at least 30 questions, found {len(questions)}"
    )


def test_difficulty_distribution(questions):
    """There must be exactly 10 easy, 10 medium, and 10 hard questions."""
    counts = {"easy": 0, "medium": 0, "hard": 0}
    for q in questions:
        diff = q.get("difficulty")
        if diff in counts:
            counts[diff] += 1

    assert counts["easy"] == 10, f"Expected 10 easy, got {counts['easy']}"
    assert counts["medium"] == 10, f"Expected 10 medium, got {counts['medium']}"
    assert counts["hard"] == 10, f"Expected 10 hard, got {counts['hard']}"


def test_all_fields_present(questions):
    """Every question must have all required fields."""
    for idx, q in enumerate(questions):
        missing = REQUIRED_FIELDS - set(q.keys())
        assert not missing, (
            f"Question at index {idx} (id={q.get('id', '?')}) "
            f"is missing fields: {missing}"
        )


def test_sparql_syntax_valid(questions):
    """Every SPARQL string must be parseable by rdflib's SPARQL parser."""
    from rdflib.plugins.sparql.parser import parseQuery

    for idx, q in enumerate(questions):
        sparql = q.get("sparql", "")
        try:
            parseQuery(sparql)
        except Exception as exc:
            pytest.fail(
                f"Question at index {idx} (id={q.get('id', '?')}) "
                f"has invalid SPARQL: {exc}"
            )


def test_unique_ids(questions):
    """All question IDs must be unique."""
    ids = [q["id"] for q in questions]
    duplicates = [qid for qid in ids if ids.count(qid) > 1]
    assert not duplicates, f"Duplicate IDs found: {set(duplicates)}"
