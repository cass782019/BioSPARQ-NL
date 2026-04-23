"""LLM-as-NER backend — uses Nemotron (or any LM Studio model) to extract
span + type, then grounds via Gilda to avoid ID hallucination.

This is the cheapest ablation: removes one pipeline dependency (scispaCy
for NER) and reuses the LLM already loaded in LM Studio for SPARQL
generation. Grounding is still deterministic (Gilda), so IDs are never
hallucinated.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

from ..base import Entity, NERBackend, merge_overlaps

SYSTEM_PROMPT = """You are a biomedical NER module. Extract disease and \
phenotype mentions from the user question. Output ONLY valid JSON matching \
this schema:

{"entities": [{"text": str, "type": "DISEASE"|"PHENOTYPE", "start": int, "end": int}]}

Rules:
- "text" must be the EXACT substring as it appears in the question.
- "start"/"end" are 0-indexed character offsets.
- Do not invent entities. Do not guess ontology IDs.
- If nothing is found, return {"entities": []}.
"""


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
        self._base_url = base_url or os.getenv(
            "LLM_BASE_URL", "http://localhost:1234/v1"
        )
        self._model = model or os.getenv("LLM_NER_MODEL", "nemotron-nano-4b")
        self._temperature = temperature
        self._timeout = timeout
        self._gilda_min = gilda_min_score
        self._gilda = None
        self._client: httpx.Client | None = None

    def warm_up(self) -> None:
        import gilda
        self._gilda = gilda
        self._client = httpx.Client(timeout=self._timeout)

    def extract(self, text: str) -> list[Entity]:
        assert self._client is not None and self._gilda is not None

        resp = self._client.post(
            f"{self._base_url}/chat/completions",
            json={
                "model": self._model,
                "temperature": self._temperature,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"]["content"]

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

            # Ground the LLM's span with Gilda for safe IDs
            matches = self._gilda.ground(span_text)
            kept = [m for m in matches if m.score >= self._gilda_min]
            ids: list[str] = []
            scores: list[float] = []
            for m in kept:
                if m.term.db in ("DOID", "HP", "OMIM", "MESH"):
                    ids.append(f"{m.term.db}:{m.term.id}")
                    scores.append(float(m.score))

            results.append(Entity(
                text=span_text, start=start, end=end, type=etype,
                ontology_ids=ids, scores=scores, backend=self.name,
            ))

        return merge_overlaps(results)
