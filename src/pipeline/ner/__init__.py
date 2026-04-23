"""Pluggable NER backends for BioSPARQL-NL."""
from .base import Entity, NERBackend, merge_overlaps
from .factory import get_backend, get_all_backends

__all__ = ["Entity", "NERBackend", "merge_overlaps", "get_backend", "get_all_backends"]
