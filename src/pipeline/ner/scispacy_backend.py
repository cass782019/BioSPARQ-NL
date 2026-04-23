"""scispaCy backend — preserves the current BioSPARQL-NL behavior.

Extracts NEs via en_core_sci_sm then resolves to DOID/HP CURIEs by querying
Fuseki for exact rdfs:label matches. No UMLS dependency.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import requests

from .base import Entity, NERBackend

logger = logging.getLogger(__name__)

_NER_STOPWORDS = {
    "quais", "qual", "quantos", "quantas", "como", "quando", "onde", "por que",
    "o que", "que", "quem", "cujo", "cuja",
    "estao", "estão", "associadas", "associados", "associada", "associado",
    "relacionado", "relacionada", "relacionados", "relacionadas",
    "existem", "possuem", "possuam", "tem", "têm", "ha", "há",
    "foram", "sao", "são", "e", "ou", "nao", "não", "mais", "menos",
    "todas", "todos", "toda", "todo", "cada", "alguns", "algumas",
    "doencas", "doenças", "doenca", "doença", "sintomas", "sintoma",
    "fenotipos", "fenótipos", "fenotipo", "fenótipo", "termos", "termo",
    "classes", "classe", "subclasses", "subclasse", "hierarquia",
    "definicao", "definição", "definicoes", "definições",
    "sinonimos", "sinônimos", "sinonimo", "sinônimo",
    "anotacao", "anotação", "anotacoes", "anotações",
    "label", "labels", "nome", "nomes",
    "de", "do", "da", "dos", "das", "no", "na", "nos", "nas",
    "em", "para", "pelo", "pela", "pelos", "pelas", "com", "sem",
    "por", "a", "o", "as", "os", "um", "uma", "uns", "umas",
    "which", "what", "how", "when", "where", "who",
    "are", "is", "were", "was", "have", "has", "had", "do", "does", "did",
    "diseases", "disease", "phenotypes", "phenotype", "symptoms", "terms",
    "classes", "subclasses", "definition", "synonyms", "annotations",
    "the", "an", "of", "in", "for", "with", "from", "to", "by",
    "doid", "hpo", "hpoa", "omim", "orpha", "mesh", "icd", "snomed",
    "ontology", "ontologia", "database", "banco",
}

# Mapping from OBO IRI prefix to CURIE namespace + graph
_URI_TO_CURIE = {
    "http://purl.obolibrary.org/obo/DOID_": ("DOID", "urn:doid"),
    "http://purl.obolibrary.org/obo/HP_":   ("HP",   "urn:hpo"),
}


def _is_noise(text: str) -> bool:
    if not text:
        return True
    normalized = text.lower().strip(" .,;:'\"!?()[]")
    if len(normalized) < 4:
        return True
    if normalized in _NER_STOPWORDS:
        return True
    if not any(c.isalnum() for c in normalized):
        return True
    alpha_ratio = sum(c.isalpha() for c in normalized) / max(len(normalized), 1)
    return alpha_ratio < 0.5


def _uri_to_curie(uri: str) -> str | None:
    for prefix, (ns, _) in _URI_TO_CURIE.items():
        if uri.startswith(prefix):
            local = uri[len(prefix):]
            return f"{ns}:{local}"
    return None


class ScispaCyBackend:
    name = "scispacy"

    def __init__(self, endpoint: str | None = None):
        self._endpoint = endpoint or os.getenv(
            "FUSEKI_ENDPOINT", "http://localhost:3030/biomedical/sparql"
        )
        self._nlp = None

    def warm_up(self) -> None:
        try:
            import spacy
            self._nlp = spacy.load("en_core_sci_sm")
            logger.info("scispaCy model loaded.")
        except OSError:
            self._nlp = None
            logger.warning(
                "Could not load 'en_core_sci_sm'. Entity extraction disabled. "
                "Install: pip install scispacy && "
                "pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/"
                "releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz"
            )

    def extract(self, text: str) -> list[Entity]:
        if self._nlp is None:
            return []

        doc = self._nlp(text)
        out: list[Entity] = []
        for ent in doc.ents:
            if _is_noise(ent.text):
                continue
            resolved = self._resolve(ent.text)
            ids = [resolved["curie"]] if resolved else []
            scores = [1.0] if resolved else []
            etype = "DISEASE" if (resolved and "DOID" in resolved["curie"]) else (
                    "PHENOTYPE" if (resolved and resolved["curie"].startswith("HP:")) else "OTHER")
            out.append(Entity(
                text=ent.text, start=ent.start_char, end=ent.end_char,
                type=etype, ontology_ids=ids, scores=scores, backend=self.name,
            ))
        return out

    def _resolve(self, entity_text: str) -> Optional[dict]:
        """Query Fuseki for an exact rdfs:label match. Returns {curie, uri, graph}."""
        try:
            safe_text = entity_text.replace("\\", "\\\\").replace("'", "\\'")
            query = (
                "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
                "SELECT ?entity ?g WHERE {\n"
                "  GRAPH ?g {\n"
                "    ?entity rdfs:label ?label .\n"
                f"    FILTER(LCASE(STR(?label)) = LCASE('{safe_text}'))\n"
                "  }\n"
                "} LIMIT 1"
            )
            response = requests.get(
                self._endpoint,
                params={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=10,
            )
            response.raise_for_status()
            bindings = response.json().get("results", {}).get("bindings", [])
            if bindings:
                uri = bindings[0]["entity"]["value"]
                graph = bindings[0]["g"]["value"]
                curie = _uri_to_curie(uri) or uri
                return {"curie": curie, "uri": uri, "graph": graph}
        except Exception:
            logger.debug("Failed to resolve '%s'.", entity_text, exc_info=True)
        return None
