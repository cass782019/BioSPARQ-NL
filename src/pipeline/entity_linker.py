"""Entity Linker — adapter over pluggable NER backends.

Preserves the original public interface (extract_entities / format_for_prompt)
while delegating to whichever backend NER_BACKEND selects.
"""
from __future__ import annotations

import logging
import os

from src.pipeline.ner.base import Entity
from src.pipeline.ner.factory import get_backend

logger = logging.getLogger(__name__)

# CURIE prefix → (OBO URI prefix, Fuseki graph)
_CURIE_TO_URI: dict[str, tuple[str, str]] = {
    "DOID": ("http://purl.obolibrary.org/obo/DOID_", "urn:doid"),
    "HP":   ("http://purl.obolibrary.org/obo/HP_",   "urn:hpo"),
}


def _curie_to_uri_graph(curie: str) -> tuple[str, str] | None:
    """Expand a CURIE like 'DOID:14330' to (full URI, graph). Returns None if unknown."""
    if ":" not in curie:
        return None
    ns, local = curie.split(":", 1)
    if ns in _CURIE_TO_URI:
        uri_prefix, graph = _CURIE_TO_URI[ns]
        return uri_prefix + local, graph
    return None


def _entity_to_dict(ent: Entity) -> dict:
    """Convert an Entity to the legacy dict format expected by the pipeline."""
    entry: dict = {"text": ent.text, "start": ent.start, "end": ent.end}
    if ent.ontology_ids:
        expanded = _curie_to_uri_graph(ent.ontology_ids[0])
        if expanded:
            entry["uri"], entry["graph"] = expanded
    return entry


class EntityLinker:
    """Thin adapter: loads a NER backend and exposes the original dict-based API."""

    def __init__(self, endpoint: str = "http://localhost:3030/biomedical/sparql"):
        self.endpoint = endpoint
        backend_name = os.getenv("NER_BACKEND", "scispacy").lower()

        # For scispaCy, propagate the endpoint so Fuseki resolution works.
        if backend_name == "scispacy":
            from src.pipeline.ner.scispacy_backend import ScispaCyBackend
            self._backend = ScispaCyBackend(endpoint=endpoint)
            try:
                self._backend.warm_up()
            except Exception as e:
                logger.warning("ScispaCyBackend warm_up failed: %s", e)
                self._backend = None
        else:
            try:
                self._backend = get_backend(backend_name)
            except Exception as e:
                logger.warning("NER backend '%s' failed to load: %s", backend_name, e)
                self._backend = None

        # Expose nlp for legacy code that checks `pipe.entity_linker.nlp is not None`
        self.nlp = getattr(getattr(self._backend, "_nlp", None), "__class__", None)

    # ------------------------------------------------------------------
    # Public API (unchanged)
    # ------------------------------------------------------------------

    def extract_entities(self, text: str) -> list[dict]:
        """Extract named entities and resolve to ontology URIs.

        Returns list of dicts: {text, start, end, uri?, graph?}
        """
        backend = getattr(self, "_backend", None)
        if backend is None:
            return []
        try:
            entities: list[Entity] = backend.extract(text)
            result = [_entity_to_dict(e) for e in entities]
            logger.info("Extracted %d entities via '%s'.", len(result),
                        getattr(backend, "name", "?"))
            return result
        except Exception:
            logger.warning("Entity extraction failed.", exc_info=True)
            return []

    @staticmethod
    def format_for_prompt(entities: list[dict]) -> str:
        """Format resolved entities for inclusion in an LLM prompt."""
        if not entities:
            return ""
        lines = ["Entidades identificadas na pergunta:"]
        for ent in entities:
            if "uri" in ent:
                lines.append(
                    f'  - "{ent["text"]}" → <{ent["uri"]}> (grafo: {ent["graph"]})'
                )
            else:
                lines.append(f'  - "{ent["text"]}" (não resolvida)')
        return "\n".join(lines)
