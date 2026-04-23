"""Gilda backend — best DOID/HP coverage without training data.

Uses scispaCy for candidate span extraction, then grounds each span with
Gilda (native support for DOID, HP, MESH, CHEBI, HGNC). No UMLS required.

Install: pip install gilda
"""
from __future__ import annotations

import logging

from .base import Entity, NERBackend, merge_overlaps

logger = logging.getLogger(__name__)

_NAMESPACE_TO_TYPE = {
    "DOID": "DISEASE",
    "MESH": "DISEASE",
    "OMIM": "DISEASE",
    "HP":   "PHENOTYPE",
    "HGNC": "GENE",
    "CHEBI": "CHEMICAL",
}

_KEEP_NS = ("DOID", "HP", "OMIM", "MESH")


class GildaBackend:
    name = "gilda"

    def __init__(self, spacy_model: str = "en_core_sci_sm", min_score: float = 0.5):
        self._spacy_model = spacy_model
        self._min_score = min_score
        self._nlp = None
        self._gilda = None

    def warm_up(self) -> None:
        try:
            import spacy
            import gilda
            self._nlp = spacy.load(self._spacy_model)
            self._gilda = gilda
            logger.info("GildaBackend ready.")
        except ImportError as e:
            raise ImportError(
                f"GildaBackend requires gilda: pip install gilda. ({e})"
            ) from e

    def extract(self, text: str) -> list[Entity]:
        assert self._nlp is not None and self._gilda is not None, "call warm_up() first"
        doc = self._nlp(text)

        # Named entities + noun chunks not already covered by NEs
        candidates = list(doc.ents) + [
            nc for nc in doc.noun_chunks
            if not any(nc.start < e.end and nc.end > e.start for e in doc.ents)
        ]

        results: list[Entity] = []
        for span in candidates:
            matches = self._gilda.ground(span.text)
            kept = [m for m in matches if m.score >= self._min_score]
            if not kept:
                continue

            kept.sort(key=lambda m: (
                _KEEP_NS.index(m.term.db) if m.term.db in _KEEP_NS else 99,
                -m.score,
            ))
            filtered = [m for m in kept if m.term.db in _KEEP_NS]
            if not filtered:
                continue

            primary = filtered[0]
            etype = _NAMESPACE_TO_TYPE.get(primary.term.db, "OTHER")
            ids = [f"{m.term.db}:{m.term.id}" for m in filtered]
            scores = [float(m.score) for m in filtered]

            results.append(Entity(
                text=span.text, start=span.start_char, end=span.end_char,
                type=etype, ontology_ids=ids, scores=scores, backend=self.name,
            ))

        return merge_overlaps(results)
