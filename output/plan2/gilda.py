"""Gilda backend — best coverage for DOID + HP without training.

Gilda grounds terms across MESH, DOID, HP, CHEBI, HGNC, etc. out of the box.
Strategy: chunk text into candidate noun phrases (spaCy lookup), ground each
with gilda.ground(), keep only hits in namespaces we care about.
"""
from __future__ import annotations

from ..base import Entity, NERBackend, merge_overlaps

_NAMESPACE_TO_TYPE = {
    "DOID": "DISEASE",
    "MESH": "DISEASE",
    "OMIM": "DISEASE",
    "HP":   "PHENOTYPE",
    "HGNC": "GENE",
    "CHEBI":"CHEMICAL",
}

# Namespaces we keep in ontology_ids, in preference order
_KEEP_NS = ("DOID", "HP", "OMIM", "MESH")


class GildaBackend:
    name = "gilda"

    def __init__(self, spacy_model: str = "en_core_sci_sm", min_score: float = 0.5):
        self._spacy_model = spacy_model
        self._min_score = min_score
        self._nlp = None
        self._gilda = None

    def warm_up(self) -> None:
        import spacy
        import gilda

        self._nlp = spacy.load(self._spacy_model)
        self._gilda = gilda

    def extract(self, text: str) -> list[Entity]:
        assert self._nlp is not None and self._gilda is not None
        doc = self._nlp(text)

        # Candidate spans: named entities from scispaCy + noun chunks as fallback.
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

            # Order: prefer DOID > HP > OMIM > MESH, then by score
            kept.sort(key=lambda m: (_KEEP_NS.index(m.term.db) if m.term.db in _KEEP_NS else 99,
                                     -m.score))
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
