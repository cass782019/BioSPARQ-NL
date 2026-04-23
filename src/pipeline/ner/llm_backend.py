"""LLM-as-NER backend — LM Studio extracts spans, Gilda grounds them.

No ID hallucination: the LLM only provides span text and type; Gilda
resolves the canonical DOID/HP IDs deterministically.

Install: pip install gilda httpx
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from .base import Entity, NERBackend, merge_overlaps

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a biomedical NER module. Extract disease and phenotype mentions "
    "from the user question. Output ONLY valid JSON matching this schema:\n\n"
    '{"entities": [{"text": str, "type": "DISEASE"|"PHENOTYPE", '
    '"start": int, "end": int}]}\n\n'
    "Rules:\n"
    '- "text" must be the EXACT substring as it appears in the question.\n'
    '- "start"/"end" are 0-indexed character offsets.\n'
    "- Do not invent entities. Do not guess ontology IDs.\n"
    '- If nothing is found, return {"entities": []}.'
)

_KEEP_NS = ("DOID", "HP", "OMIM", "MESH")


class LLMBackend:
    name = "llm+gilda"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        timeout: float = 60.0,
        gilda_min_score: float = 0.5,
    ):
        self._base_url = (base_url or os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")).rstrip("/")
        self._model = model or os.getenv("LLM_MODEL", "nemotron-nano-4b")
        self._temperature = temperature
        self._timeout = timeout
        self._gilda_min = gilda_min_score
        self._gilda = None
        self._client = None

    def warm_up(self) -> None:
        try:
            import gilda
            import httpx
            self._gilda = gilda
            self._client = httpx.Client(timeout=self._timeout)
            logger.info("LLMBackend (llm+gilda) ready.")
        except ImportError as e:
            raise ImportError(
                f"LLMBackend requires gilda and httpx: pip install gilda httpx. ({e})"
            ) from e

    def extract(self, text: str) -> list[Entity]:
        assert self._client is not None and self._gilda is not None, "call warm_up() first"

        try:
            resp = self._client.post(
                f"{self._base_url}/chat/completions",
                json={
                    "model": self._model,
                    "temperature": self._temperature,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("LLMBackend request failed: %s", e)
            return []

        try:
            parsed: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            return []

        results: list[Entity] = []
        for item in parsed.get("entities", []):
            span_text = (item.get("text") or "").strip()
            if not span_text:
                continue
            start = int(item.get("start", text.find(span_text)))
            end = int(item.get("end", start + len(span_text)))
            etype = item.get("type", "OTHER").upper()

            matches = self._gilda.ground(span_text)
            ids, scores = [], []
            for m in matches:
                if m.score >= self._gilda_min and m.term.db in _KEEP_NS:
                    ids.append(f"{m.term.db}:{m.term.id}")
                    scores.append(float(m.score))

            results.append(Entity(
                text=span_text, start=start, end=end, type=etype,
                ontology_ids=ids, scores=scores, backend=self.name,
            ))

        return merge_overlaps(results)
