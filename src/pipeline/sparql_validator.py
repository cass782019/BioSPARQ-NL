"""
sparql_validator.py — Validates SPARQL queries against extracted ontology schemas.

Checks syntax (via rdflib), graph references, unsafe operations,
prefix declarations, and class/predicate usage against the schema
extracted by schema_extractor.py.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validate SPARQL queries against an ontology schema file."""

    def __init__(self, schemas_path: str = "data/schemas.json"):
        self.permissive: bool = False
        self.valid_classes: set[str] = set()
        self.valid_predicates: set[str] = set()
        self.valid_graphs: set[str] = {"urn:doid", "urn:hpo", "urn:hpoa"}

        try:
            path = Path(schemas_path)
            with open(path, encoding="utf-8") as f:
                schemas = json.load(f)

            # Build lookup sets from the schema file.
            # Expected structure: {"classes": [...], "predicates": [...]}
            self.valid_classes = set(schemas.get("classes", []))
            self.valid_predicates = set(schemas.get("predicates", []))

            # If the file supplies graph names, use them; otherwise keep defaults.
            if "graphs" in schemas:
                self.valid_graphs = set(schemas["graphs"])

            logger.info(
                "Schema loaded: %d classes, %d predicates, %d graphs",
                len(self.valid_classes),
                len(self.valid_predicates),
                len(self.valid_graphs),
            )

        except FileNotFoundError:
            logger.warning(
                "Schema file not found at %s — running in permissive mode.",
                schemas_path,
            )
            self.permissive = True

        except json.JSONDecodeError as exc:
            logger.warning(
                "Invalid JSON in %s (%s) — running in permissive mode.",
                schemas_path,
                exc,
            )
            self.permissive = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, sparql_query: str) -> dict:
        """Validate *sparql_query* and return a result dict.

        Returns
        -------
        dict with keys:
            valid    : bool        — True when no errors were found.
            errors   : list[str]   — Hard errors that must be fixed.
            warnings : list[str]   — Soft issues worth mentioning.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Syntax check via rdflib -----------------------------------
        try:
            from rdflib.plugins.sparql.parser import parseQuery

            parseQuery(sparql_query)
        except ImportError:
            warnings.append(
                "rdflib is not installed; syntax check skipped."
            )
        except Exception as exc:
            errors.append(f"SYNTAX_ERROR: {exc}")

        # 3. Unsafe operations (check before graph/prefix analysis) ----
        unsafe_pattern = re.compile(
            r"\b(DELETE|INSERT)\b", re.IGNORECASE
        )
        if unsafe_pattern.search(sparql_query):
            errors.append(
                "UNSAFE_OPERATION: DELETE/INSERT operations are not allowed."
            )

        # 2. GRAPH references -----------------------------------------
        graph_refs = re.findall(r"GRAPH\s*<([^>]+)>", sparql_query, re.IGNORECASE)
        if graph_refs:
            for g in graph_refs:
                if g not in self.valid_graphs:
                    errors.append(
                        f"INVALID_GRAPH: <{g}> is not a recognised graph. "
                        f"Valid graphs: {sorted(self.valid_graphs)}"
                    )
        else:
            warnings.append(
                "NO_GRAPH: Query does not specify a GRAPH clause. "
                "Consider targeting a specific named graph."
            )

        # 4. Undefined prefixes ----------------------------------------
        declared = {
            m[0]
            for m in re.findall(
                r"PREFIX\s+(\w+):\s*<([^>]+)>", sparql_query, re.IGNORECASE
            )
        }
        used = {
            m.split(":")[0]
            for m in re.findall(r"(?:^|\s)(\w+:\w+)", sparql_query)
        }
        # Exclude common built-in / well-known prefixes that rdflib
        # resolves implicitly (e.g. rdf, rdfs, xsd, owl).
        builtins = {"rdf", "rdfs", "xsd", "owl", "fn", "afn"}
        undefined = used - declared - builtins
        for p in sorted(undefined):
            warnings.append(
                f"UNDEFINED_PREFIX: prefix '{p}:' is used but not declared."
            )

        # 5. Class / predicate validation (skip when permissive) -------
        if not self.permissive:
            expanded = self._expand_prefixes(sparql_query)
            for uri in expanded:
                if self.valid_classes and uri in self.valid_classes:
                    continue
                if self.valid_predicates and uri in self.valid_predicates:
                    continue
                # Only flag URIs that look like ontology terms (contain # or end
                # with a local-name segment) to avoid false positives on graph
                # URIs, literal datatypes, etc.
                if "#" in uri or re.search(r"/[A-Z][A-Za-z]+$", uri):
                    if self.valid_classes or self.valid_predicates:
                        warnings.append(
                            f"UNKNOWN_TERM: <{uri}> not found in schema classes or predicates."
                        )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _expand_prefixes(self, query: str) -> set[str]:
        """Extract PREFIX declarations and expand prefixed terms to full URIs.

        Returns a set of expanded URI strings found in the query.
        """
        # Build prefix map from declared PREFIX lines.
        prefix_map: dict[str, str] = {}
        for alias, iri in re.findall(
            r"PREFIX\s+(\w+):\s*<([^>]+)>", query, re.IGNORECASE
        ):
            prefix_map[alias] = iri

        # Find all prefixed terms (e.g.  doid:Disease , rdf:type ).
        prefixed_terms = re.findall(r"(?:^|\s)(\w+:\w+)", query)

        expanded: set[str] = set()
        for term in prefixed_terms:
            prefix, local = term.split(":", 1)
            if prefix in prefix_map:
                expanded.add(prefix_map[prefix] + local)

        return expanded

    def format_feedback(
        self, validation_result: dict, original_query: str
    ) -> str:
        """Format validation errors/warnings into an LLM-friendly feedback string.

        Returns an empty string when the query is valid.
        """
        if validation_result["valid"] and not validation_result["warnings"]:
            return ""

        if validation_result["valid"]:
            # Only warnings — still return them so the LLM can improve.
            pass

        parts: list[str] = []

        if validation_result["errors"]:
            parts.append("## Validation Errors")
            for err in validation_result["errors"]:
                parts.append(f"- {err}")

        if validation_result["warnings"]:
            parts.append("## Validation Warnings")
            for warn in validation_result["warnings"]:
                parts.append(f"- {warn}")

        parts.append("")
        parts.append("## Available Named Graphs")
        for g in sorted(self.valid_graphs):
            parts.append(f"- <{g}>")

        parts.append("")
        parts.append("## Original Query")
        parts.append("```sparql")
        parts.append(original_query.strip())
        parts.append("```")

        parts.append("")
        parts.append(
            "Please regenerate the SPARQL query fixing the issues listed above."
        )

        return "\n".join(parts)
