"""Unit tests for the EntityLinker class (src.pipeline.entity_linker)."""

from src.pipeline.entity_linker import EntityLinker


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_linker_stub() -> EntityLinker:
    """Create an EntityLinker instance without triggering __init__."""
    obj = EntityLinker.__new__(EntityLinker)
    obj.nlp = None
    obj.endpoint = ""
    return obj


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_model_not_loaded_returns_empty():
    """When nlp is None, extract_entities must return an empty list."""
    linker = _make_linker_stub()
    result = linker.extract_entities("What diseases are associated with fever?")
    assert result == []


def test_format_for_prompt_empty():
    """format_for_prompt with an empty list must return an empty string."""
    linker = _make_linker_stub()
    result = linker.format_for_prompt([])
    assert result == ""


def test_format_for_prompt_with_entities():
    """format_for_prompt must produce the expected multi-line output."""
    entities = [
        {
            "text": "Asthma",
            "start": 0,
            "end": 6,
            "uri": "http://purl.obolibrary.org/obo/DOID_2841",
            "graph": "urn:doid",
        },
        {
            "text": "fever",
            "start": 10,
            "end": 15,
        },
    ]

    linker = _make_linker_stub()
    result = linker.format_for_prompt(entities)

    assert "Entidades identificadas na pergunta:" in result
    assert '"Asthma"' in result
    assert "<http://purl.obolibrary.org/obo/DOID_2841>" in result
    assert "(grafo: urn:doid)" in result
    assert '"fever"' in result
    assert "(n\u00e3o resolvida)" in result
