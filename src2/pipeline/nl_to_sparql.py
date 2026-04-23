"""Pipeline BioSPARQL-NL (revisao 2): usa src2.pipeline.llm_backends (ClaudeCLIBackend).

Reutiliza EntityLinker e SchemaValidator de src/ (nao mudaram).
"""
import json
import logging
import time

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from SPARQLWrapper import SPARQLWrapper, JSON

from src.exceptions import LLMConnectionError
from src.pipeline.entity_linker import EntityLinker
from src.pipeline.sparql_validator import SchemaValidator
from src2.pipeline.llm_backends import create_backend

logger = logging.getLogger(__name__)


class BioSPARQLPipeline:
    def __init__(self, config=None):
        self.config = config or {
            "endpoint": "http://localhost:3030/biomedical/sparql",
            "lm_studio_url": "http://localhost:1234/v1",
            "llm_model": "google/gemma-3-4b",
            "backend": "lm_studio",
            "max_retries": 2,
            "top_k_examples": 3,
            "llm_timeout": 120.0,
            "fuseki_timeout": 30,
        }

        # LLM backend (LM Studio ou Claude CLI)
        self.backend = create_backend(self.config)

        # Entity linker (graceful fallback se scispaCy falhar)
        try:
            self.entity_linker = EntityLinker(self.config["endpoint"])
        except Exception as e:
            logger.warning(f"Entity linker disabled: {e}")
            self.entity_linker = None

        # FAISS index (graceful fallback se corrompido)
        try:
            self.index = faiss.read_index("data/gold_standard/questions.index")
            with open("data/gold_standard/questions.json", encoding="utf-8") as f:
                self.examples = json.load(f)
        except Exception as e:
            logger.warning(f"FAISS index unavailable, using zero-shot: {e}")
            self.index = None
            self.examples = []

        # Schema (graceful fallback se ausente)
        try:
            with open("data/schemas.json", encoding="utf-8") as f:
                self.schemas = json.load(f)
        except Exception as e:
            logger.warning(f"Schemas unavailable: {e}")
            self.schemas = {}

        # Validator
        self.validator = SchemaValidator()

        # Embedder (carregado lazy)
        self._embedder = None

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder

    def retrieve_examples(self, question: str, top_k: int = 3) -> list:
        """Busca exemplos similares via FAISS. Fallback: lista vazia."""
        if self.index is None or not self.examples or top_k <= 0:
            return []
        q_emb = self.embedder.encode([question], normalize_embeddings=True)
        D, I = self.index.search(q_emb.astype(np.float32), k=top_k)
        return [self.examples[i] for i in I[0] if i < len(self.examples)]

    def build_prompt(self, question: str, examples: list, feedback: str = None):
        """Monta prompt com entidades resolvidas + exemplos + schema."""
        # Entity linking (desabilitavel via ablacao)
        entity_context = ""
        if self.entity_linker and not self.config.get("disable_ner"):
            entities = self.entity_linker.extract_entities(question)
            entity_context = self.entity_linker.format_for_prompt(entities)

        # Schema resumido (desabilitavel via ablacao)
        schema_text = ""
        if not self.config.get("disable_schema"):
            schema_text = "## Schemas dos grafos disponiveis:\n\n"
            for name, schema in self.schemas.items():
                raw_classes = schema.get("classes", [])[:10]
                classes = []
                for c in raw_classes:
                    if "uri" in c:
                        classes.append(c["uri"].split("/")[-1])
                    elif "class" in c:
                        classes.append(c["class"]["value"].split("/")[-1])
                raw_preds = schema.get("predicates", [])[:15]
                preds = []
                for p in raw_preds:
                    if "uri" in p:
                        preds.append(p["uri"].split("/")[-1])
                    elif "pred" in p:
                        preds.append(p["pred"]["value"].split("/")[-1])
                schema_text += f"### {name}\n"
                schema_text += f"Classes principais: {', '.join(classes)}\n"
                schema_text += f"Predicados: {', '.join(preds)}\n\n"

        # Exemplos few-shot
        examples_text = ""
        if examples:
            examples_text = "## Exemplos de perguntas e queries SPARQL:\n\n"
            for ex in examples:
                examples_text += f"Pergunta: {ex['question_en']}\n"
                examples_text += f"```sparql\n{ex['sparql'].strip()}\n```\n\n"

        system = f"""Voce e um especialista em SPARQL para ontologias biomedicas.
Dado uma pergunta em linguagem natural, gere uma query SPARQL valida.

REGRAS:
1. Use SEMPRE a clausula GRAPH para especificar o grafo correto:
   - GRAPH <urn:doid> para Disease Ontology (classes de doencas, hierarquia, definicoes)
   - GRAPH <urn:hpo> para Human Phenotype Ontology (termos fenotipicos, hierarquia)
   - GRAPH <urn:hpoa> para anotacoes doenca->fenotipo
2. DECLARE TODOS os prefixos usados no topo da query. Prefixos comuns:
   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
   PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
   PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
   PREFIX obo: <http://purl.obolibrary.org/obo/>
   PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
   PREFIX hpoa: <http://example.org/hpoa/>
3. Para cruzar doencas DOID com anotacoes HPOA, use:
   GRAPH <urn:doid> {{ ?d oboInOwl:hasDbXref ?xref }}
   GRAPH <urn:hpoa> {{ ?disease hpoa:source_id ?xref }}
4. Retorne APENAS a query SPARQL, sem explicacao.

{entity_context}

{schema_text}

{examples_text}"""

        user_msg = f"Pergunta: {question}"
        if feedback:
            user_msg += f"\n\n{feedback}"
        return system, user_msg

    KNOWN_PREFIXES = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "obo": "http://purl.obolibrary.org/obo/",
        "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
        "hpoa": "http://example.org/hpoa/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    @staticmethod
    def _extract_sparql(raw: str) -> str:
        """Extrai SPARQL de resposta markdown ou texto puro."""
        if "```sparql" in raw:
            return raw.split("```sparql")[1].split("```")[0].strip()
        elif "```" in raw:
            return raw.split("```")[1].split("```")[0].strip()
        return raw.strip()

    @classmethod
    def _inject_missing_prefixes(cls, query: str) -> str:
        """Auto-declara prefixos conhecidos usados mas nao declarados na query."""
        import re
        declared = set(re.findall(r"PREFIX\s+(\w+)\s*:", query, flags=re.IGNORECASE))
        used = set(re.findall(r"(?<![:/\w])(\w+):\w+", query))
        used |= set(re.findall(r"\^\^(\w+):", query))
        missing = [p for p in used if p in cls.KNOWN_PREFIXES and p not in declared]
        if not missing:
            return query
        header = "\n".join(
            f"PREFIX {p}: <{cls.KNOWN_PREFIXES[p]}>" for p in missing
        )
        return header + "\n" + query

    def generate_sparql(self, system: str, user_msg: str) -> str:
        """Chama o backend LLM, extrai SPARQL e injeta prefixos faltantes."""
        try:
            raw = self.backend.generate(system, user_msg)
            query = self._extract_sparql(raw)
            return self._inject_missing_prefixes(query)
        except Exception as e:
            raise LLMConnectionError(f"LLM backend error: {e}")

    def execute_sparql(self, query: str) -> dict:
        """Executa query no Fuseki com timeout e retry."""
        sparql = SPARQLWrapper(self.config["endpoint"])
        sparql.setReturnFormat(JSON)
        sparql.setTimeout(self.config["fuseki_timeout"])

        for attempt in range(2):
            try:
                sparql.setQuery(query)
                results = sparql.query().convert()
                bindings = results["results"]["bindings"]
                return {"success": True, "results": bindings, "count": len(bindings)}
            except Exception as e:
                if attempt == 0 and "connection" in str(e).lower():
                    time.sleep(2)
                    continue
                return {
                    "success": False,
                    "error": str(e),
                    "results": [],
                    "count": 0,
                }

    def run(self, question: str) -> dict:
        """Pipeline completo com loop de validacao/correcao."""
        examples = self.retrieve_examples(question, top_k=self.config.get("top_k_examples", 3))

        feedback = None
        for attempt in range(1, self.config["max_retries"] + 2):
            try:
                system, user_msg = self.build_prompt(question, examples, feedback)
                sparql_query = self.generate_sparql(system, user_msg)
            except LLMConnectionError as e:
                return {
                    "question": question,
                    "sparql": "",
                    "validation": {"valid": False, "errors": [str(e)], "warnings": []},
                    "execution": {"success": False, "error": str(e), "results": [], "count": 0},
                    "attempts": attempt,
                    "success": False,
                }

            validation = self.validator.validate(sparql_query)

            if validation["valid"]:
                result = self.execute_sparql(sparql_query)
                return {
                    "question": question,
                    "sparql": sparql_query,
                    "validation": validation,
                    "execution": result,
                    "attempts": attempt,
                    "success": result["success"] and result["count"] > 0,
                }

            if attempt <= self.config["max_retries"]:
                feedback = self.validator.format_feedback(validation, sparql_query)
                logger.info(f"Tentativa {attempt} falhou, re-prompting...")
            else:
                result = self.execute_sparql(sparql_query)
                return {
                    "question": question,
                    "sparql": sparql_query,
                    "validation": validation,
                    "execution": result,
                    "attempts": attempt,
                    "success": result["success"] and result["count"] > 0,
                }
