"""scispaCy baseline — mirrors the current BioSPARQL-NL behavior."""
from __future__ import annotations

import os

from ..base import Entity, NERBackend


# scispaCy EntityLinker returns UMLS CUIs. We convert to DOID/HP via xrefs
# that are already present in the triplestore (MedDRA / OMIM bridges).
_UMLS_TO_DOID_FALLBACK = os.getenv("SCISPACY_UMLS_BRIDGE", "")


class ScispaCyBackend:
    name = "scispacy"

    def __init__(self, model: str = "en_core_sci_sm", linker: str = "umls"):
        self._model_name = model
        self._linker_name = linker
        self._nlp = None

    def warm_up(self) -> None:
        import spacy  # local import keeps the dependency optional
        from scispacy.linking import EntityLinker  # noqa: F401  (side-effect)

        self._nlp = spacy.load(self._model_name)
        self._nlp.add_pipe(
            "scispacy_linker",
            config={"resolve_abbreviations": True, "linker_name": self._linker_name},
        )

    def extract(self, text: str) -> list[Entity]:
        assert self._nlp is not None, "call warm_up() first"
        doc = self._nlp(text)
        out: list[Entity] = []
        for ent in doc.ents:
            etype = _map_scispacy_label(ent.label_)
            ids, scores = [], []
            for cui, score in getattr(ent._, "kb_ents", []):
                ids.append(f"UMLS:{cui}")
                scores.append(float(score))
            out.append(Entity(
                text=ent.text, start=ent.start_char, end=ent.end_char,
                type=etype, ontology_ids=ids, scores=scores, backend=self.name,
            ))
        return out


def _map_scispacy_label(label: str) -> str:
    # en_core_sci_sm emits generic "ENTITY"; the linker does the heavy lifting.
    # Heuristic mapping left to downstream if richer labels are needed.
    return "OTHER"
