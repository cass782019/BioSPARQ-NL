"""Common interface for all NER backends in BioSPARQL-NL."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Sequence

ENTITY_TYPES = {"DISEASE", "PHENOTYPE", "GENE", "CHEMICAL", "OTHER"}


@dataclass
class Entity:
    """Normalized NER output. All backends produce this shape."""
    text: str
    start: int
    end: int
    type: str                          # one of ENTITY_TYPES
    ontology_ids: list[str] = field(default_factory=list)
    # CURIEs, e.g. ["DOID:14330", "HP:0001250"] — most-confident first
    scores: list[float] = field(default_factory=list)
    backend: str = ""

    @property
    def primary_id(self) -> str | None:
        return self.ontology_ids[0] if self.ontology_ids else None


@runtime_checkable
class NERBackend(Protocol):
    name: str

    def extract(self, text: str) -> list[Entity]: ...

    def warm_up(self) -> None:
        """Load models/caches. Called once before a run."""
        ...


def merge_overlaps(entities: Sequence[Entity]) -> list[Entity]:
    """Keep highest-score entity when spans overlap."""
    if not entities:
        return []
    sorted_ents = sorted(entities, key=lambda e: (e.start, -(e.end - e.start)))
    kept: list[Entity] = []
    for e in sorted_ents:
        if kept and e.start < kept[-1].end:
            prev_score = kept[-1].scores[0] if kept[-1].scores else 0.0
            cur_score = e.scores[0] if e.scores else 0.0
            if cur_score > prev_score:
                kept[-1] = e
        else:
            kept.append(e)
    return kept
