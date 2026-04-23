"""Factory: reads NER_BACKEND from env and returns a cached backend instance."""
from __future__ import annotations

import os
from functools import lru_cache

from .base import NERBackend

REGISTRY: dict[str, str] = {
    "scispacy": "src.pipeline.ner.scispacy_backend:ScispaCyBackend",
    "gilda":    "src.pipeline.ner.gilda_backend:GildaBackend",
    "llm":      "src.pipeline.ner.llm_backend:LLMBackend",
    "medcat":   "src.pipeline.ner.medcat_backend:MedCATBackend",
}


def _import_class(path: str):
    module_path, cls_name = path.split(":")
    module = __import__(module_path, fromlist=[cls_name])
    return getattr(module, cls_name)


@lru_cache(maxsize=None)
def get_backend(name: str | None = None) -> NERBackend:
    """Return a cached instance of the requested backend.

    Selection order: explicit arg > NER_BACKEND env > 'scispacy'.
    """
    name = (name or os.getenv("NER_BACKEND", "scispacy")).lower()
    if name not in REGISTRY:
        raise ValueError(
            f"Unknown NER_BACKEND='{name}'. Valid: {list(REGISTRY)}"
        )
    cls = _import_class(REGISTRY[name])
    inst = cls()
    inst.warm_up()
    return inst


def get_all_backends() -> dict[str, NERBackend]:
    """Instantiate every registered backend (used by the benchmark harness).
    Backends that fail to import (missing optional dep) are silently skipped.
    """
    out: dict[str, NERBackend] = {}
    for name in REGISTRY:
        try:
            out[name] = get_backend(name)
        except Exception as exc:
            print(f"[ner.factory] skipping '{name}': {exc!r}")
    return out
