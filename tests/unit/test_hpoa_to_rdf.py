"""Unit tests for src.utils.hpoa_to_rdf -- HPOA TSV to RDF converter."""

import os
import textwrap

import pytest
from rdflib import Graph, Literal

from src.utils.hpoa_to_rdf import convert_hpoa_to_rdf


# ------------------------------------------------------------------ helpers

def _write_lines(tmp_path, lines):
    """Write lines to a temp TSV file and return (input_path, output_path)."""
    input_file = os.path.join(str(tmp_path), "test_input.hpoa")
    output_file = os.path.join(str(tmp_path), "test_output.ttl")
    with open(input_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return input_file, output_file


def _count_source_ids(ttl_path, value):
    """Count triples whose object is Literal(value) for the source_id predicate."""
    g = Graph()
    g.parse(ttl_path, format="turtle")
    source_id_pred = "http://example.org/hpoa/source_id"
    return sum(
        1
        for _s, _p, o in g.triples((None, None, None))
        if str(_p) == source_id_pred and str(o) == value
    )


# ------------------------------------------------------------------ tests

class TestConvertOMIMEntry:
    def test_convert_omim_entry(self, tmp_path):
        """An OMIM line produces a triple with source_id='OMIM:154700'."""
        lines = ["OMIM:154700\tMarfan syndrome\t\tHP:0001166\tOMIM:154700\n"]
        inp, out = _write_lines(tmp_path, lines)
        count = convert_hpoa_to_rdf(inp, out)
        assert count == 1
        assert _count_source_ids(out, "OMIM:154700") == 1


class TestConvertORPHAEntry:
    def test_convert_orpha_entry(self, tmp_path):
        """An ORPHA line produces a triple with source_id='ORPHA:558'."""
        lines = ["ORPHA:558\tMarfan syndrome\t\tHP:0001519\tORPHA:558\n"]
        inp, out = _write_lines(tmp_path, lines)
        count = convert_hpoa_to_rdf(inp, out)
        assert count == 1
        assert _count_source_ids(out, "ORPHA:558") == 1


class TestSkipNOTQualifier:
    def test_skip_not_qualifier(self, tmp_path):
        """Lines with qualifier 'NOT' must be skipped entirely."""
        lines = ["OMIM:154700\tMarfan syndrome\tNOT\tHP:0000001\tOMIM:154700\n"]
        inp, out = _write_lines(tmp_path, lines)
        count = convert_hpoa_to_rdf(inp, out)
        assert count == 0


class TestSkipMalformedLines:
    def test_skip_malformed_lines(self, tmp_path):
        """Lines with fewer than 5 tab-separated fields must not crash and yield 0."""
        lines = ["BADLINE\tonly_two_fields\n"]
        inp, out = _write_lines(tmp_path, lines)
        count = convert_hpoa_to_rdf(inp, out)
        assert count == 0


class TestEmptyFile:
    def test_empty_file(self, tmp_path):
        """An empty input file produces zero annotations."""
        inp, out = _write_lines(tmp_path, [])
        count = convert_hpoa_to_rdf(inp, out)
        assert count == 0


class TestHeaderLinesIgnored:
    def test_header_lines_ignored(self, tmp_path):
        """Comment lines starting with '#' and the header row must be ignored."""
        lines = [
            "# This is a comment\n",
            "database_id\tdisease_name\tqualifier\thpo_id\treference\n",
        ]
        inp, out = _write_lines(tmp_path, lines)
        count = convert_hpoa_to_rdf(inp, out)
        assert count == 0
