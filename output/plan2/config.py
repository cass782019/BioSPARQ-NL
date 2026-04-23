"""Config-driven factory. Reads NER_BACKEND from env and returns a backend."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from .base import NERBackend

load_dotenv()

REGISTRY = {
    "scispacy":  "biosparql_ner.backends.scispacy:ScispaCyBackend",
    "gilda":     "biosparql_ner.backends.gilda:GildaBackend",
    "llm":       "biosparql_ner.backends.llm:LLMBackend",
    "medcat":    "biosparql_ner.backends.medcat:MedCATBackend",
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
    """Instantiate every backend (used by the benchmark harness)."""
    out: dict[str, NERBackend] = {}
    for name in REGISTRY:
        try:
            out[name] = get_backend(name)
        except Exception as exc:  # a missing dependency must not kill the bench
            print(f"[config] skipping '{name}': {exc!r}")
    return out
