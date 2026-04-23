"""Unit tests for src.pipeline.sparql_validator -- SPARQL query validation."""

import pytest

from src.pipeline.sparql_validator import SchemaValidator


# All tests in this module use the ``validator`` fixture from conftest.py,
# which provides a SchemaValidator with a small fake schema and permissive=False.


class TestValidQueryPasses:
    def test_valid_query_passes(self, validator):
        """A syntactically correct query referencing a valid GRAPH passes."""
        query = (
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "SELECT ?label WHERE {\n"
            "  GRAPH <urn:doid> {\n"
            "    ?x rdfs:label ?label .\n"
            "  }\n"
            "}"
        )
        result = validator.validate(query)
        assert result["valid"] is True


class TestSyntaxErrorDetected:
    def test_syntax_error_detected(self, validator):
        """A query with invalid syntax must produce a SYNTAX_ERROR."""
        query = "SELCT ?x WHERE { ?x ?y ?z }"
        result = validator.validate(query)
        assert any("SYNTAX_ERROR" in e for e in result["errors"])


class TestInvalidGraphDetected:
    def test_invalid_graph_detected(self, validator):
        """Referencing an unrecognised GRAPH URI must produce INVALID_GRAPH."""
        query = (
            "SELECT ?x WHERE {\n"
            "  GRAPH <urn:fake> {\n"
            "    ?x ?y ?z .\n"
            "  }\n"
            "}"
        )
        result = validator.validate(query)
        assert any("INVALID_GRAPH" in e for e in result["errors"])


class TestUndefinedPrefixWarning:
    def test_undefined_prefix_warning(self, validator):
        """Using an undeclared prefix must produce an UNDEFINED_PREFIX warning."""
        query = (
            "SELECT ?x WHERE {\n"
            "  GRAPH <urn:doid> {\n"
            "    ?x foo:bar ?z .\n"
            "  }\n"
            "}"
        )
        result = validator.validate(query)
        assert any("UNDEFINED_PREFIX" in w for w in result["warnings"])


class TestDeleteBlocked:
    def test_delete_blocked(self, validator):
        """A DELETE query must be flagged as UNSAFE_OPERATION."""
        query = "DELETE WHERE { ?s ?p ?o }"
        result = validator.validate(query)
        assert any("UNSAFE_OPERATION" in e for e in result["errors"])


class TestInsertBlocked:
    def test_insert_blocked(self, validator):
        """An INSERT query must be flagged as UNSAFE_OPERATION."""
        query = "INSERT DATA { <urn:a> <urn:b> <urn:c> }"
        result = validator.validate(query)
        assert any("UNSAFE_OPERATION" in e for e in result["errors"])


class TestNoGraphWarning:
    def test_no_graph_warning(self, validator):
        """A query without any GRAPH clause must produce a NO_GRAPH warning."""
        query = (
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "SELECT ?x WHERE { ?x rdfs:label ?z }"
        )
        result = validator.validate(query)
        assert any("NO_GRAPH" in w for w in result["warnings"])


class TestFormatFeedbackOnErrors:
    def test_format_feedback_on_errors(self, validator):
        """When errors are present, format_feedback must return a non-empty string."""
        query = "SELCT ?x WHERE { ?x ?y ?z }"
        result = validator.validate(query)
        feedback = validator.format_feedback(result, query)
        assert isinstance(feedback, str)
        assert len(feedback) > 0


class TestFormatFeedbackOnValid:
    def test_format_feedback_on_valid(self, validator):
        """When the query is fully valid, format_feedback must return an empty string."""
        query = (
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "SELECT ?label WHERE {\n"
            "  GRAPH <urn:doid> {\n"
            "    ?x rdfs:label ?label .\n"
            "  }\n"
            "}"
        )
        result = validator.validate(query)
        feedback = validator.format_feedback(result, query)
        assert feedback == ""
