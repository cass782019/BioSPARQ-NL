"""Shared pytest fixtures for BioSPARQL-NL test suite."""

import json
import urllib.request
import urllib.error

import pytest


@pytest.fixture
def fuseki_endpoint():
    """Return the local Fuseki SPARQL endpoint URL, skipping if offline."""
    url = "http://localhost:3030/$/ping"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3):
            pass
    except (urllib.error.URLError, OSError):
        pytest.skip("Fuseki is not running at localhost:3030")
    return "http://localhost:3030/biomedical/sparql"


@pytest.fixture
def lm_studio_client():
    """Return an OpenAI client pointing at LM Studio, skipping if offline."""
    try:
        from openai import OpenAI
    except ImportError:
        pytest.skip("openai package is not installed")

    url = "http://localhost:1234/v1/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3):
            pass
    except (urllib.error.URLError, OSError):
        pytest.skip("LM Studio is not running at localhost:1234")

    return OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")


@pytest.fixture
def sample_hpoa_lines():
    """Return a list of sample HPOA TSV lines for testing the converter.

    Lines included:
      - OMIM entry (valid)
      - ORPHA entry (valid)
      - NOT qualifier (should be skipped)
      - Malformed line with fewer than 5 fields
      - Comment line starting with '#'
    """
    return [
        "# Comment line -- should be ignored\n",
        "database_id\tdisease_name\tqualifier\thpo_id\treference\n",
        "OMIM:154700\tMarfan syndrome\t\tHP:0001166\tOMIM:154700\n",
        "ORPHA:558\tMarfan syndrome\t\tHP:0001519\tORPHA:558\n",
        "OMIM:154700\tMarfan syndrome\tNOT\tHP:0000001\tOMIM:154700\n",
        "BADLINE\tonly_two_fields\n",
    ]


@pytest.fixture
def validator():
    """Return a SchemaValidator with a minimal fake schema (non-permissive)."""
    from src.pipeline.sparql_validator import SchemaValidator

    v = SchemaValidator.__new__(SchemaValidator)
    v.valid_classes = {"http://purl.obolibrary.org/obo/DOID_4"}
    v.valid_predicates = {"http://www.w3.org/2000/01/rdf-schema#label"}
    v.valid_graphs = {"urn:doid", "urn:hpo", "urn:hpoa"}
    v.permissive = False
    return v


@pytest.fixture
def mini_gold_standard():
    """Load the first 3 questions from the gold standard, skipping if absent."""
    from pathlib import Path

    gs_path = Path("data/gold_standard/questions.json")
    if not gs_path.exists():
        pytest.skip("Gold standard file not found at data/gold_standard/questions.json")
    with open(gs_path, encoding="utf-8") as f:
        questions = json.load(f)
    return questions[:3]
