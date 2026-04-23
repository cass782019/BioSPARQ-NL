"""Common interface for all NER backends in BioSPARQL-NL."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Sequence


# Canonical entity types the downstream pipeline cares about.
# Every backend must emit one of these (or "OTHER" for anything else).
ENTITY_TYPES = {"DISEASE", "PHENOTYPE", "GENE", "CHEMICAL", "OTHER"}


@dataclass
class Entity:
    """Normalized NER output. All backends produce this shape."""
    text: str                     # surface form as it appeared in input
    start: int                    # char offset in source text
    end: int                      # char offset (exclusive)
    type: str                     # one of ENTITY_TYPES
    ontology_ids: list[str] = field(default_factory=list)
    # e.g. ["DOID:14330", "HP:0001250"] — most-confident first.
    scores: list[float] = field(default_factory=list)
    # Parallel to ontology_ids. Empty if backend does not provide scores.
    backend: str = ""             # which backend produced this (for logs)

    @property
    def primary_id(self) -> str | None:
        return self.ontology_ids[0] if self.ontology_ids else None


@runtime_checkable
class NERBackend(Protocol):
    """Every backend implements this. Keep it narrow on purpose."""

    name: str  # short id used in metrics, e.g. "gilda", "llm+gilda", "medcat"

    def extract(self, text: str) -> list[Entity]: ...

    def warm_up(self) -> None:
        """Optional: load models, caches, etc. Called once before a run."""
        ...


def merge_overlaps(entities: Sequence[Entity]) -> list[Entity]:
    """Prefer the entity with the highest score when spans overlap."""
    if not entities:
        return []
    sorted_ents = sorted(entities, key=lambda e: (e.start, -(e.end - e.start)))
    kept: list[Entity] = []
    for e in sorted_ents:
        if kept and e.start < kept[-1].end:
            prev = kept[-1]
            prev_score = prev.scores[0] if prev.scores else 0.0
            cur_score = e.scores[0] if e.scores else 0.0
            if cur_score > prev_score:
                kept[-1] = e
        else:
            kept.append(e)
    return kept
