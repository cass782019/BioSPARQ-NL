"""Pipeline completo: Pergunta NL -> SPARQL -> Validacao -> Execucao -> Resposta."""
import json
import logging
import os
import time

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from SPARQLWrapper import SPARQLWrapper, JSON

from src.exceptions import LLMConnectionError, FusekiConnectionError
from src.pipeline.entity_linker import EntityLinker
from src.pipeline.llm_backends import create_backend
from src.pipeline.sparql_validator import SchemaValidator

logger = logging.getLogger(__name__)


class BioSPARQLPipeline:
    def __init__(self, config=None):
        # Permite sobrescrever via env var (util para trocar sem editar codigo)
        default_model = os.getenv("LLM_MODEL", "auto")
        default_llm_timeout = float(os.getenv("LLM_TIMEOUT", "300"))
        self.config = config or {
            "endpoint": "http://localhost:3030/biomedical/sparql",
            "lm_studio_url": "http://localhost:1234/v1",
            "llm_model": default_model,
            "max_retries": 2,
            "top_k_examples": 3,
            "llm_timeout": default_llm_timeout,
            "fuseki_timeout": 30,
        }
        logger.info(
            f"Pipeline: modelo={self.config['llm_model']} "
            f"timeout={self.config['llm_timeout']}s"
        )

        # LLM backend (LM Studio ou Anthropic)
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
        if self.index is None or not self.examples:
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
                # Support both formats: {uri:...} or {class:{value:...}}
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
        examples_text = "## Exemplos de perguntas e queries SPARQL:\n\n"
        for ex in examples:
            examples_text += f"Pergunta: {ex['question_en']}\n"
            examples_text += f"```sparql\n{ex['sparql'].strip()}\n```\n\n"

        system = f"""Especialista SPARQL em ontologias biomedicas. Gere UMA query SPARQL valida.

GRAFOS: <urn:doid>=Disease Ontology | <urn:hpo>=HPO fenotipos | <urn:hpoa>=anotacoes doenca->fenotipo
PREFIXOS: PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#> PREFIX obo:<http://purl.obolibrary.org/obo/> PREFIX oboInOwl:<http://www.geneontology.org/formats/oboInOwl#> PREFIX hpoa:<http://example.org/hpoa/>
IDIOMA: Labels em INGLES. Traduza termos PT->EN nos FILTER (febre->fever, dor->pain, hipertensao->hypertension).

REGRAS:
1. Use GRAPH <urn:...> em todo triple pattern.
2. Filtre por nome: rdfs:label ?l . FILTER(CONTAINS(LCASE(?l),"termo_ingles"))
3. DOID<->HPOA join: GRAPH <urn:doid> {{ ?d oboInOwl:hasDbXref ?mim . FILTER(STRSTARTS(STR(?mim),"MIM:")) BIND(REPLACE(STR(?mim),"^MIM:","OMIM:") AS ?oid) }} GRAPH <urn:hpoa> {{ ?a hpoa:source_id ?oid }}
4. has_phenotype/source_id/rdfs:label de doencas so em <urn:hpoa>; rdfs:label de fenotipos em <urn:hpo>.
5. GROUP BY inclui todas variaveis nao-agregadas.
6. Retorne APENAS a query SPARQL.

{entity_context}

{schema_text}

{examples_text}"""

        user_msg = f"Pergunta: {question}"
        if feedback:
            user_msg += f"\n\n{feedback}"
        return system, user_msg

    # Prefixos conhecidos injetados automaticamente se usados mas nao declarados.
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
    def _fix_common_errors(cls, query: str) -> str:
        """Canonicaliza declaracoes PREFIX e remove pseudo-keywords alucinadas.

        Seguro e reversivel:
        1. Remove blocos DECLARE { ... } (mantendo linhas PREFIX de dentro)
        2. Remove linhas soltas com pseudo-keywords (DECLARE, IMPORT, USE, NAMESPACE)
        3. Substitui qualquer URI declarada para prefixo conhecido pela canonical
        """
        import re

        # 1. Remover blocos "DECLARE { ... }" mas preservar as linhas PREFIX internas.
        #    Padrao: "DECLARE" [opcional { ou (] ... ate' o } ou ) de fechamento.
        pseudo_block_re = re.compile(
            r"DECLARE\s*[\{\(]([^\}\)]*)[\}\)]",
            flags=re.IGNORECASE | re.DOTALL,
        )
        def _block_replacer(m):
            inner = m.group(1)
            # Extrair linhas PREFIX do interior, limpar ; finais
            prefixes = []
            for line in inner.splitlines():
                line = line.strip().rstrip(";").strip()
                if line.upper().startswith("PREFIX "):
                    prefixes.append(line)
            return "\n".join(prefixes)
        query = pseudo_block_re.sub(_block_replacer, query)

        # 2. Remover linhas soltas com pseudo-keywords (nao em blocos)
        pseudo_keywords = ["DECLARE", "IMPORT", "USE ", "NAMESPACE"]
        cleaned_lines = []
        for line in query.splitlines():
            stripped = line.strip()
            if any(stripped.upper().startswith(kw) for kw in pseudo_keywords):
                continue
            cleaned_lines.append(line)
        query = "\n".join(cleaned_lines)

        # 3. Canonicalizar URIs de prefixos conhecidos
        for alias, canonical in cls.KNOWN_PREFIXES.items():
            pattern = rf"PREFIX\s+{re.escape(alias)}\s*:\s*<[^>]+>"
            replacement = f"PREFIX {alias}: <{canonical}>"
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

        # 4a. Corrigir "oboInOwl#localname" -> "oboInOwl:localname" no corpo da query
        #    (NAO aplica dentro de URIs <...>, pois oboInOwl# e' parte valida da URI base)
        query = re.sub(r"oboInOwl#([A-Za-z]\w*)", r"oboInOwl:\1", query)

        # 4b. Corrigir "pred = ?var" -> "pred ?var" (= nao e operador de tripla em SPARQL)
        query = re.sub(r"(hpoa:\w+|oboInOwl:\w+|rdfs:\w+)\s*=\s*(\?\w+)", r"\1 \2", query)

        # 4. Remover declaracoes PREFIX erroneas usando URNs de grafo como namespace
        #    ex: "PREFIX doid: <urn:doid>" ou "PREFIX hpoa: <urn:hpoa>"
        query = re.sub(
            r"PREFIX\s+(?:doid|hpo|hpoa)\s*:\s*<urn:[^>]+>\s*\n?",
            "",
            query,
            flags=re.IGNORECASE,
        )

        # 5. Corrigir URIs de grafo abreviadas geradas pelo modelo
        #    GRAPH <doid> -> GRAPH <urn:doid>  etc.
        graph_fixes = {
            r"GRAPH\s+<doid>":  "GRAPH <urn:doid>",
            r"GRAPH\s+<hpo>":   "GRAPH <urn:hpo>",
            r"GRAPH\s+<hpoa>":  "GRAPH <urn:hpoa>",
            # prefixo com alias: GRAPH doid: -> GRAPH <urn:doid>
            r"GRAPH\s+doid:":   "GRAPH <urn:doid>",
            r"GRAPH\s+hpo:":    "GRAPH <urn:hpo>",
            r"GRAPH\s+hpoa:":   "GRAPH <urn:hpoa>",
        }
        for pattern, replacement in graph_fixes.items():
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

        # 6. Remover asserções de tipo hallucinated: "?x a doid:Disease" / "?x a hpo:*"
        #    No triplestore desse projeto, doid: e hpo: nao sao prefixos validos.
        #    Remove a linha inteira que usa esses prefixos como tipo rdf:type.
        query = re.sub(
            r"[ \t]*\?[\w]+ a (?:doid|hpo):[A-Za-z]+\s*[;.]\s*\n?",
            "",
            query,
        )
        # Substitui referencias restantes a doid:Disease pelo URI raiz correto
        query = re.sub(r"\bdoid:Disease\b", "obo:DOID_4", query)
        # Substitui hpo:HumanPhenotype pelo URI raiz de fenotipos
        query = re.sub(r"\bhpo:HumanPhenotype\b", "obo:HP_0000118", query)

        # 7. Corrigir BIND com auto-referencia: BIND(REPLACE(STR(?x),...) AS ?x)
        #    Jena rejeita: "Variable used when already in-scope in BIND"
        #    Fix: renomeia ocorrencias de ?x somente ANTES do BIND para ?x_mim
        bind_self_re = re.compile(
            r"BIND\s*\(\s*REPLACE\s*\(\s*STR\s*\(\s*\?(\w+)\s*\)(.*?)\)\s+AS\s+\?(\w+)\s*\)",
            flags=re.IGNORECASE | re.DOTALL,
        )
        m = bind_self_re.search(query)
        if m:
            src, tgt = m.group(1), m.group(3)
            if src == tgt:
                new_src = src + "_mim"
                bind_start = m.start()
                # Rename ?src -> ?new_src only in the portion BEFORE the BIND
                before = re.sub(rf"\?{src}\b", f"?{new_src}", query[:bind_start])
                # Update the BIND itself: src inside REPLACE becomes new_src
                bind_fixed = m.group(0).replace(f"?{src}", f"?{new_src}", 1)
                # After BIND: keep ?src as-is (it now refers to the BIND output)
                after = query[m.end():]
                query = before + bind_fixed + after

        return query

    @classmethod
    def _inject_missing_prefixes(cls, query: str) -> str:
        """Auto-declara prefixos conhecidos usados mas nao declarados na query."""
        import re

        # Prefixos ja declarados na query
        declared = set(re.findall(r"PREFIX\s+(\w+)\s*:", query, flags=re.IGNORECASE))

        # Prefixos usados no corpo (forma: alias:name)
        used = set(re.findall(r"(?<![:/\w])(\w+):\w+", query))
        # Tambem detecta literais tipados como "..."^^xsd:string
        used |= set(re.findall(r"\^\^(\w+):", query))

        missing = [p for p in used if p in cls.KNOWN_PREFIXES and p not in declared]
        if not missing:
            return query

        header = "\n".join(
            f"PREFIX {p}: <{cls.KNOWN_PREFIXES[p]}>" for p in missing
        )
        return header + "\n" + query

    def generate_sparql(self, system: str, user_msg: str) -> str:
        """Chama o backend LLM, extrai SPARQL, canonicaliza prefixos e injeta faltantes."""
        try:
            raw = self.backend.generate(system, user_msg)
            query = self._extract_sparql(raw)
            query = self._fix_common_errors(query)      # canonicaliza URIs alucinadas
            query = self._inject_missing_prefixes(query) # declara faltantes
            return query
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

    SEMANTIC_RETRY_FEEDBACK = (
        "Query anterior retornou 0 resultados. Reescreva:\n"
        "(1) Labels em INGLES nos FILTER (febre->fever, hipertensao->hypertension, etc)\n"
        "(2) Para fenotipo: GRAPH <urn:hpo> {?ph rdfs:label ?pl . FILTER(CONTAINS(LCASE(?pl),\"termo\"))} "
        "GRAPH <urn:hpoa> {?d hpoa:has_phenotype ?ph ; rdfs:label ?dn .}\n"
        "(3) DOID<->HPOA: GRAPH <urn:doid> {?d oboInOwl:hasDbXref ?mim . "
        "FILTER(STRSTARTS(STR(?mim),\"MIM:\")) BIND(REPLACE(STR(?mim),\"^MIM:\",\"OMIM:\") AS ?oid)} "
        "GRAPH <urn:hpoa> {?a hpoa:source_id ?oid ; hpoa:has_phenotype ?ph}\n"
        "(4) NAO use doid:, hpo: como prefixos."
    )

    def run(self, question: str) -> dict:
        """Pipeline completo com loop de validacao/correcao + semantic retry.

        Retorna: {question, sparql, validation, execution, attempts, success}
        """
        examples = self.retrieve_examples(question)

        feedback = None
        semantic_retry_used = False
        max_attempts = self.config["max_retries"] + 2  # total incluindo inicial
        attempt = 0
        last_result = None
        last_query = None
        last_validation = None

        while attempt < max_attempts:
            attempt += 1
            # Gerar SPARQL via LLM
            try:
                system, user_msg = self.build_prompt(question, examples, feedback)
                sparql_query = self.generate_sparql(system, user_msg)
            except LLMConnectionError as e:
                return {
                    "question": question,
                    "sparql": "",
                    "validation": {
                        "valid": False,
                        "errors": [str(e)],
                        "warnings": [],
                    },
                    "execution": {
                        "success": False,
                        "error": str(e),
                        "results": [],
                        "count": 0,
                    },
                    "attempts": attempt,
                    "success": False,
                }

            # Validar
            validation = self.validator.validate(sparql_query)

            if validation["valid"]:
                # Executar no Fuseki
                result = self.execute_sparql(sparql_query)

                # Semantic retry: query valida + execucao OK + 0 resultados + primeira vez
                if (
                    self.config.get("semantic_retry", True)
                    and not semantic_retry_used
                    and result["success"]
                    and result["count"] == 0
                    and attempt < max_attempts
                ):
                    logger.info(
                        f"Tentativa {attempt}: query valida mas 0 resultados, semantic retry..."
                    )
                    semantic_retry_used = True
                    feedback = self.SEMANTIC_RETRY_FEEDBACK
                    last_result = result
                    last_query = sparql_query
                    last_validation = validation
                    continue  # re-prompt com feedback semantico

                return {
                    "question": question,
                    "sparql": sparql_query,
                    "validation": validation,
                    "execution": result,
                    "attempts": attempt,
                    "success": result["success"] and result["count"] > 0,
                }

            # Se invalido e ainda tem tentativas -> gerar feedback para re-prompt
            if attempt < max_attempts:
                feedback = self.validator.format_feedback(validation, sparql_query)
                logger.info(f"Tentativa {attempt} falhou, re-prompting...")
            else:
                # Ultima tentativa falhou -> tentar executar mesmo assim
                result = self.execute_sparql(sparql_query)
                return {
                    "question": question,
                    "sparql": sparql_query,
                    "validation": validation,
                    "execution": result,
                    "attempts": attempt,
                    "success": result["success"] and result["count"] > 0,
                }

        # Fallback: se saiu do loop sem return (ex: semantic retry esgotou sem resultado melhor)
        return {
            "question": question,
            "sparql": last_query or "",
            "validation": last_validation or {"valid": False, "errors": ["no result"], "warnings": []},
            "execution": last_result or {"success": False, "error": "no result", "results": [], "count": 0},
            "attempts": attempt,
            "success": False,
        }
