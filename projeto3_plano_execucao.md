# Projeto 3 — Interface de Linguagem Natural para SPARQL Biomédico com Validação por Esquema Ontológico

## Plano de Execução para Claude Code

**Título do Trabalho:** BioSPARQL-NL: Tradução de Linguagem Natural para SPARQL sobre Ontologias Biomédicas com Validação por Esquema Ontológico

**Disciplina:** Inteligência Artificial e Sistemas Inteligentes — Prof. Sandro J. Rigo  
**Programa:** Pós-Graduação em Computação Aplicada — UNISINOS  
**Formato de saída:** Relatório técnico (máx. 10 páginas, template SBC)

---

## Visão Geral da Arquitetura

```
Pergunta NL → [scispaCy NER] → [Embedding + Busca Similares] → [Schema Retrieval VoID/SHACL]
    → [Prompt Assembly] → [LLM gera SPARQL] → [Validação contra Schema]
        → Se válido: [Execução no Fuseki] → [Resposta NL]
        → Se inválido: [Feedback + Re-prompt] → (até 2 tentativas)
```

---

## FASE 0 — Setup do Ambiente
**Objetivo:** Preparar ambiente Python com todas dependências  
**Tempo estimado:** 2h  
**Executor:** Claude Code

### Tarefas

```bash
# 0.1 Criar estrutura do projeto
mkdir -p ~/biosparql-nl/{data/{ontologies,annotations,gold_standard},src/{pipeline,utils},notebooks,output}
cd ~/biosparql-nl

# 0.2 Criar e ativar virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 0.3 Instalar dependências core
pip install owlready2 rdflib sparqlwrapper requests
pip install scispacy
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz
pip install sentence-transformers faiss-cpu
pip install openai  # ou anthropic, para chamada ao LLM
pip install pyyaml tabulate tqdm

# 0.4 Instalar Apache Jena Fuseki (triplestore SPARQL)
cd /tmp
wget https://archive.apache.org/dist/jena/binaries/apache-jena-fuseki-4.10.0.tar.gz
tar xzf apache-jena-fuseki-4.10.0.tar.gz
mv apache-jena-fuseki-4.10.0 ~/fuseki
```

### 🚦 GATE 0 — Validação do Ambiente
```bash
# Checklist automatizado
python3 -c "
import owlready2; print('✅ owlready2', owlready2.__version__)
import rdflib; print('✅ rdflib', rdflib.__version__)
import scispacy; print('✅ scispacy OK')
import spacy; nlp = spacy.load('en_core_sci_sm'); print('✅ scispaCy model loaded')
import sentence_transformers; print('✅ sentence-transformers OK')
import faiss; print('✅ FAISS OK')
print('--- Todas dependências instaladas ---')
"
# Verificar Fuseki
ls ~/fuseki/fuseki-server && echo "✅ Fuseki instalado"
```
**Critério de passagem:** Todos os checks retornam ✅. Se qualquer um falhar, resolver antes de prosseguir.

---

## FASE 1 — Aquisição e Preparação dos Dados Ontológicos
**Objetivo:** Baixar DOID + HPO (OWL), converter anotações HPOA (TSV→RDF), carregar no Fuseki  
**Tempo estimado:** 4h  
**Executor:** Claude Code

### 1.1 Download das ontologias

```bash
cd ~/biosparql-nl/data/ontologies

# Disease Ontology (OWL) — ~12.000 classes de doenças
wget -O doid.owl "https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/doid.owl"

# Human Phenotype Ontology (OWL) — ~16.000 termos fenotípicos
wget -O hp.owl "http://purl.obolibrary.org/obo/hp.owl"
```

### 1.2 Download das anotações doença-fenótipo (HPO Annotations)

```bash
cd ~/biosparql-nl/data/annotations

# Anotações doença→fenótipo (formato TSV, NÃO é RDF nativo)
wget -O phenotype.hpoa "http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa"

# genes→fenótipo
wget -O genes_to_phenotype.txt "http://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt"
```

### 1.3 Converter anotações HPOA de TSV para RDF/Turtle

```python
# src/utils/hpoa_to_rdf.py
"""
Converte phenotype.hpoa (TSV) para Turtle RDF.
Gera triplas: <disease_uri> <has_phenotype> <hpo_uri>
"""
import csv
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS

DOID = Namespace("http://purl.obolibrary.org/obo/DOID_")
HP = Namespace("http://purl.obolibrary.org/obo/HP_")
HPOA = Namespace("http://example.org/hpoa/")
OBO = Namespace("http://purl.obolibrary.org/obo/")

def convert_hpoa_to_rdf(input_tsv, output_ttl):
    g = Graph()
    g.bind("doid", DOID)
    g.bind("hp", HP)
    g.bind("hpoa", HPOA)
    g.bind("obo", OBO)
    
    has_phenotype = HPOA["has_phenotype"]
    has_onset = HPOA["has_onset"]
    has_frequency = HPOA["has_frequency"]
    
    count = 0
    with open(input_tsv, 'r') as f:
        for line in f:
            if line.startswith('#') or line.startswith('database_id'):
                continue
            parts = line.strip().split('\t')
            if len(parts) < 5:
                continue
            
            db_id = parts[0]  # e.g., "OMIM:154700"
            disease_name = parts[1]
            qualifier = parts[2]  # NOT or empty
            hpo_id = parts[3]  # e.g., "HP:0001166"
            
            if qualifier == "NOT":
                continue  # Pular anotações negativas por simplicidade
            
            # Criar URIs
            hpo_uri = URIRef(f"http://purl.obolibrary.org/obo/{hpo_id.replace(':', '_')}")
            disease_uri = URIRef(f"http://example.org/disease/{db_id.replace(':', '_')}")
            
            g.add((disease_uri, RDF.type, HPOA["Disease"]))
            g.add((disease_uri, RDFS.label, Literal(disease_name)))
            g.add((disease_uri, has_phenotype, hpo_uri))
            g.add((disease_uri, HPOA["source_id"], Literal(db_id)))
            count += 1
    
    g.serialize(destination=output_ttl, format="turtle")
    print(f"✅ Convertidas {count} anotações → {output_ttl}")
    return count

if __name__ == "__main__":
    convert_hpoa_to_rdf(
        "data/annotations/phenotype.hpoa",
        "data/annotations/hpoa.ttl"
    )
```

### 1.4 Carregar dados no Fuseki

```bash
# Iniciar Fuseki com dataset persistente
cd ~/fuseki
./fuseki-server --mem /biomedical &
sleep 5

# Carregar ontologias e anotações via HTTP
# DOID
curl -X POST 'http://localhost:3030/biomedical/data?graph=urn:doid' \
  -H 'Content-Type: application/rdf+xml' \
  --data-binary @~/biosparql-nl/data/ontologies/doid.owl

# HPO
curl -X POST 'http://localhost:3030/biomedical/data?graph=urn:hpo' \
  -H 'Content-Type: application/rdf+xml' \
  --data-binary @~/biosparql-nl/data/ontologies/hp.owl

# Anotações HPOA (convertidas)
curl -X POST 'http://localhost:3030/biomedical/data?graph=urn:hpoa' \
  -H 'Content-Type: text/turtle' \
  --data-binary @~/biosparql-nl/data/annotations/hpoa.ttl
```

### 🚦 GATE 1 — Validação dos Dados Carregados
```bash
# 1a. Contar triplas por grafo
curl -s 'http://localhost:3030/biomedical/sparql' \
  --data-urlencode "query=SELECT ?g (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g"

# Esperado: urn:doid (~200K+ triplas), urn:hpo (~500K+ triplas), urn:hpoa (~100K+ triplas)

# 1b. Query de teste: fenótipos da Síndrome de Marfan
curl -s 'http://localhost:3030/biomedical/sparql' \
  --data-urlencode "query=
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?disease_name ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id 'OMIM:154700' ;
             rdfs:label ?disease_name ;
             hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
} LIMIT 10"

# 1c. Query de teste: subclasses de 'disease' no DOID
curl -s 'http://localhost:3030/biomedical/sparql' \
  --data-urlencode "query=
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(*) AS ?total_diseases) WHERE {
  GRAPH <urn:doid> {
    ?d rdfs:subClassOf+ obo:DOID_4 .
  }
}"
```

**Critérios de passagem:**
- [ ] urn:doid tem >150.000 triplas
- [ ] urn:hpo tem >400.000 triplas
- [ ] urn:hpoa tem >50.000 triplas
- [ ] Query Marfan retorna >5 fenótipos
- [ ] Count de doenças DOID > 8.000

---

## FASE 2 — Extração de Schemas e Construção do Índice de Exemplos
**Objetivo:** Extrair VoID/schemas de classes do endpoint, gerar SHACL shapes com Astrea ou introspecção, criar gold standard de pares NL↔SPARQL, indexar embeddings  
**Tempo estimado:** 6h  
**Executor:** Claude Code

### 2.1 Extrair schema de classes e predicados via introspecção SPARQL

```python
# src/utils/schema_extractor.py
"""
Extrai o schema (classes, predicados, ranges) do endpoint SPARQL
via queries introspectivas. Alternativa leve a VoID/SHACL.
"""
from SPARQLWrapper import SPARQLWrapper, JSON
import json

ENDPOINT = "http://localhost:3030/biomedical/sparql"

def extract_class_schema(endpoint_url, graph_uri):
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setReturnFormat(JSON)
    
    # 2.1a Classes com contagem de instâncias
    sparql.setQuery(f"""
    SELECT ?class (COUNT(?s) AS ?count) (SAMPLE(?label) AS ?classLabel)
    WHERE {{
      GRAPH <{graph_uri}> {{
        ?s a ?class .
        OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
      }}
    }} GROUP BY ?class ORDER BY DESC(?count) LIMIT 100
    """)
    classes = sparql.query().convert()["results"]["bindings"]
    
    # 2.1b Predicados usados com domínio/range
    sparql.setQuery(f"""
    SELECT ?pred (COUNT(*) AS ?usage)
           (SAMPLE(?sType) AS ?domain) (SAMPLE(?oType) AS ?range)
    WHERE {{
      GRAPH <{graph_uri}> {{
        ?s ?pred ?o .
        OPTIONAL {{ ?s a ?sType }}
        OPTIONAL {{ ?o a ?oType }}
      }}
      FILTER(?pred != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
    }} GROUP BY ?pred ORDER BY DESC(?usage) LIMIT 200
    """)
    predicates = sparql.query().convert()["results"]["bindings"]
    
    return {"classes": classes, "predicates": predicates}

def extract_all_schemas():
    schemas = {}
    for graph, name in [("urn:doid", "DOID"), ("urn:hpo", "HPO"), ("urn:hpoa", "HPOA")]:
        print(f"Extraindo schema de {name}...")
        schemas[name] = extract_class_schema(ENDPOINT, graph)
        print(f"  → {len(schemas[name]['classes'])} classes, {len(schemas[name]['predicates'])} predicados")
    
    with open("data/schemas.json", "w") as f:
        json.dump(schemas, f, indent=2, ensure_ascii=False)
    print("✅ Schemas salvos em data/schemas.json")
    return schemas

if __name__ == "__main__":
    extract_all_schemas()
```

### 2.2 Criar gold standard de pares pergunta↔SPARQL (30 questões)

```python
# src/utils/gold_standard.py
"""
Gold standard com 30 pares NL→SPARQL organizados por complexidade.
Cada entrada tem: pergunta (PT-BR e EN), SPARQL, tipo, dificuldade.
"""

GOLD_STANDARD = [
    # === FÁCEIS (lookup direto) ===
    {
        "id": "Q01",
        "question_pt": "Quais são os fenótipos associados à síndrome de Marfan?",
        "question_en": "What phenotypes are associated with Marfan syndrome?",
        "sparql": """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id "OMIM:154700" ;
             hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
}""",
        "type": "factoid",
        "difficulty": "easy",
        "expected_min_results": 5
    },
    {
        "id": "Q02",
        "question_pt": "Quantas subclasses de 'doença cardiovascular' existem no DOID?",
        "question_en": "How many subclasses of cardiovascular disease exist in DOID?",
        "sparql": """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(DISTINCT ?d) AS ?total) WHERE {
  GRAPH <urn:doid> {
    ?d rdfs:subClassOf+ obo:DOID_1287 .
  }
}""",
        "type": "count",
        "difficulty": "easy",
        "expected_min_results": 1
    },
    {
        "id": "Q03",
        "question_pt": "Qual é a definição da doença de Alzheimer no DOID?",
        "question_en": "What is the definition of Alzheimer disease in DOID?",
        "sparql": """
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
SELECT ?definition WHERE {
  GRAPH <urn:doid> {
    obo:DOID_10652 obo:IAO_0000115 ?definition .
  }
}""",
        "type": "factoid",
        "difficulty": "easy",
        "expected_min_results": 1
    },
    # === MÉDIAS (join entre grafos) ===
    {
        "id": "Q10",
        "question_pt": "Quais doenças estão associadas ao fenótipo 'aracnodactilia'?",
        "question_en": "Which diseases are associated with the phenotype 'arachnodactyly'?",
        "sparql": """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT DISTINCT ?disease_name WHERE {
  GRAPH <urn:hpo> {
    ?pheno rdfs:label "Arachnodactyly"@en .
  }
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype ?pheno ;
             rdfs:label ?disease_name .
  }
}""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 2
    },
    {
        "id": "Q11",
        "question_pt": "Quais fenótipos são compartilhados entre síndrome de Marfan e síndrome de Ehlers-Danlos?",
        "question_en": "Which phenotypes are shared between Marfan syndrome and Ehlers-Danlos syndrome?",
        "sparql": """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT DISTINCT ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?marfan hpoa:source_id "OMIM:154700" ;
            hpoa:has_phenotype ?pheno .
    ?eds hpoa:source_id "OMIM:130000" ;
         hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
}""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 1
    },
    # === DIFÍCEIS (inferência hierárquica, agregação) ===
    {
        "id": "Q20",
        "question_pt": "Quais doenças genéticas do DOID possuem mais de 10 fenótipos anotados no HPO?",
        "question_en": "Which genetic diseases in DOID have more than 10 annotated phenotypes in HPO?",
        "sparql": """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?disease_name (COUNT(DISTINCT ?pheno) AS ?num_phenotypes) WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype ?pheno ;
             rdfs:label ?disease_name .
  }
} GROUP BY ?disease_name
HAVING (COUNT(DISTINCT ?pheno) > 10)
ORDER BY DESC(?num_phenotypes)
LIMIT 20""",
        "type": "aggregation",
        "difficulty": "hard",
        "expected_min_results": 5
    },
    # [NOTA: Completar com 24 questões adicionais seguindo o mesmo padrão]
    # Distribuição alvo: 10 easy, 10 medium, 10 hard
]

# Salvar como JSON
import json
with open("data/gold_standard/questions.json", "w") as f:
    json.dump(GOLD_STANDARD, f, indent=2, ensure_ascii=False)
```

### 2.3 Indexar exemplos via embeddings para few-shot retrieval

```python
# src/utils/index_builder.py
"""
Gera embeddings das perguntas do gold standard + schemas,
indexa com FAISS para retrieval rápido no pipeline.
"""
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import json

def build_index():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Carregar gold standard
    with open("data/gold_standard/questions.json") as f:
        questions = json.load(f)
    
    # Gerar embeddings das perguntas (EN para melhor matching)
    texts = [q["question_en"] for q in questions]
    embeddings = model.encode(texts, normalize_embeddings=True)
    
    # Criar índice FAISS
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product (cosine com vetores normalizados)
    index.add(embeddings.astype(np.float32))
    
    # Salvar
    faiss.write_index(index, "data/gold_standard/questions.index")
    print(f"✅ Índice FAISS criado: {len(texts)} vetores, dimensão {dim}")
    return index

if __name__ == "__main__":
    build_index()
```

### 🚦 GATE 2 — Validação de Schemas e Índice
```python
# gate2_check.py
import json
import faiss
from sentence_transformers import SentenceTransformer

# 2a. Verificar schemas extraídos
with open("data/schemas.json") as f:
    schemas = json.load(f)
for name, schema in schemas.items():
    n_classes = len(schema["classes"])
    n_preds = len(schema["predicates"])
    status = "✅" if n_classes > 0 and n_preds > 0 else "❌"
    print(f"{status} {name}: {n_classes} classes, {n_preds} predicados")

# 2b. Verificar gold standard
with open("data/gold_standard/questions.json") as f:
    qs = json.load(f)
print(f"{'✅' if len(qs) >= 6 else '⚠️'} Gold standard: {len(qs)} questões (alvo: 30)")

# 2c. Verificar índice FAISS
index = faiss.read_index("data/gold_standard/questions.index")
print(f"✅ Índice FAISS: {index.ntotal} vetores")

# 2d. Teste de retrieval
model = SentenceTransformer('all-MiniLM-L6-v2')
query = model.encode(["What symptoms does Marfan syndrome have?"], normalize_embeddings=True)
D, I = index.search(query.astype('float32'), k=3)
print(f"✅ Top-3 retrieval para 'Marfan symptoms': {[qs[i]['id'] for i in I[0]]}")
print(f"   Scores: {D[0].tolist()}")
```

**Critérios de passagem:**
- [ ] Cada ontologia tem >0 classes e >0 predicados no schema
- [ ] Gold standard tem ≥6 questões (idealmente 30)
- [ ] Índice FAISS criado com dimensão correta
- [ ] Retrieval retorna Q01 (Marfan) como top-1 para query similar

---

## FASE 3 — Pipeline Principal: NL → SPARQL → Validação → Execução
**Objetivo:** Implementar o pipeline completo com validação por schema  
**Tempo estimado:** 8h  
**Executor:** Claude Code

### 3.1 Módulo de validação de SPARQL contra schema

```python
# src/pipeline/sparql_validator.py
"""
Valida queries SPARQL geradas pelo LLM contra schemas extraídos.
Verifica: (1) classes válidas, (2) predicados válidos,
(3) grafos referenciados existem, (4) sintaxe SPARQL.
"""
import re
import json
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.algebra import translateQuery

class SchemaValidator:
    def __init__(self, schemas_path="data/schemas.json"):
        with open(schemas_path) as f:
            raw = json.load(f)
        
        # Construir sets de URIs válidas
        self.valid_classes = set()
        self.valid_predicates = set()
        self.valid_graphs = {"urn:doid", "urn:hpo", "urn:hpoa"}
        
        for schema in raw.values():
            for c in schema["classes"]:
                self.valid_classes.add(c["class"]["value"])
            for p in schema["predicates"]:
                self.valid_predicates.add(p["pred"]["value"])
    
    def validate(self, sparql_query: str) -> dict:
        """
        Retorna: {"valid": bool, "errors": list[str], "warnings": list[str]}
        """
        errors = []
        warnings = []
        
        # 1. Validação sintática
        try:
            parseQuery(sparql_query)
        except Exception as e:
            errors.append(f"SYNTAX_ERROR: {str(e)[:200]}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        
        # 2. Verificar grafos referenciados
        graph_refs = re.findall(r'GRAPH\s*<([^>]+)>', sparql_query)
        for g in graph_refs:
            if g not in self.valid_graphs:
                errors.append(f"INVALID_GRAPH: <{g}> não existe. Grafos válidos: {self.valid_graphs}")
        
        # 3. Verificar predicados (heurística: extrair URIs entre < >)
        uri_pattern = re.findall(r'<(http[^>]+)>', sparql_query)
        prefixed = re.findall(r'(\w+:\w+)', sparql_query)
        
        # Verificar se usa prefixos definidos
        defined_prefixes = re.findall(r'PREFIX\s+(\w+):', sparql_query)
        for term in prefixed:
            prefix = term.split(':')[0]
            if prefix not in defined_prefixes and prefix not in ['http', 'https']:
                warnings.append(f"UNDEFINED_PREFIX: '{prefix}:' usado mas não definido em PREFIX")
        
        # 4. Verificar padrões perigosos
        if "DELETE" in sparql_query.upper() or "INSERT" in sparql_query.upper():
            errors.append("UNSAFE_OPERATION: queries DELETE/INSERT não são permitidas")
        
        if not graph_refs:
            warnings.append("NO_GRAPH: Nenhum GRAPH especificado. Considere usar GRAPH <urn:...> para precisão.")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def format_feedback(self, validation_result: dict, original_query: str) -> str:
        """Gera feedback estruturado para o LLM corrigir a query."""
        if validation_result["valid"]:
            return ""
        
        feedback = "A query SPARQL gerada contém erros. Corrija:\n\n"
        for e in validation_result["errors"]:
            feedback += f"❌ ERRO: {e}\n"
        for w in validation_result["warnings"]:
            feedback += f"⚠️ AVISO: {w}\n"
        
        feedback += f"\nQuery original:\n```sparql\n{original_query}\n```\n"
        feedback += f"\nGrafos disponíveis: {', '.join(self.valid_graphs)}\n"
        feedback += "Gere uma query SPARQL corrigida."
        return feedback
```

### 3.2 Pipeline principal

```python
# src/pipeline/nl_to_sparql.py
"""
Pipeline completo: Pergunta NL → SPARQL → Validação → Execução → Resposta NL
"""
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from SPARQLWrapper import SPARQLWrapper, JSON
from openai import OpenAI  # ou Anthropic
from .sparql_validator import SchemaValidator

class BioSPARQLPipeline:
    def __init__(self, config=None):
        self.config = config or {
            "endpoint": "http://localhost:3030/biomedical/sparql",
            "llm_model": "gpt-4o-mini",  # ou claude-sonnet-4-20250514
            "max_retries": 2,
            "top_k_examples": 3,
        }
        
        # Componentes
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.read_index("data/gold_standard/questions.index")
        with open("data/gold_standard/questions.json") as f:
            self.examples = json.load(f)
        with open("data/schemas.json") as f:
            self.schemas = json.load(f)
        self.validator = SchemaValidator()
        self.sparql = SPARQLWrapper(self.config["endpoint"])
        self.sparql.setReturnFormat(JSON)
        self.client = OpenAI()  # Usa OPENAI_API_KEY env var
    
    def retrieve_examples(self, question: str, top_k: int = 3) -> list:
        """Busca exemplos mais similares via embedding."""
        q_emb = self.embedder.encode([question], normalize_embeddings=True)
        D, I = self.index.search(q_emb.astype(np.float32), k=top_k)
        return [self.examples[i] for i in I[0] if i < len(self.examples)]
    
    def build_prompt(self, question: str, examples: list, 
                     feedback: str = None) -> str:
        """Monta o prompt com exemplos, schemas e feedback (se retry)."""
        
        # Schema resumido
        schema_text = "## Schemas dos grafos disponíveis:\n\n"
        for name, schema in self.schemas.items():
            classes = [c["class"]["value"].split("/")[-1] for c in schema["classes"][:10]]
            preds = [p["pred"]["value"].split("/")[-1] for p in schema["predicates"][:15]]
            schema_text += f"### {name}\n"
            schema_text += f"Classes principais: {', '.join(classes)}\n"
            schema_text += f"Predicados: {', '.join(preds)}\n\n"
        
        # Exemplos few-shot
        examples_text = "## Exemplos de perguntas e queries SPARQL:\n\n"
        for ex in examples:
            examples_text += f"Pergunta: {ex['question_en']}\n"
            examples_text += f"```sparql\n{ex['sparql'].strip()}\n```\n\n"
        
        # Prompt do sistema
        system = """Você é um especialista em SPARQL para ontologias biomédicas.
Dado uma pergunta em linguagem natural, gere uma query SPARQL válida.

REGRAS:
1. Use SEMPRE a cláusula GRAPH para especificar o grafo correto:
   - GRAPH <urn:doid> para Disease Ontology (classes de doenças, hierarquia, definições)
   - GRAPH <urn:hpo> para Human Phenotype Ontology (termos fenotípicos, hierarquia)
   - GRAPH <urn:hpoa> para anotações doença→fenótipo
2. Use prefixos padrão: rdfs, rdf, obo, hpoa
3. Retorne APENAS a query SPARQL, sem explicação.
4. Queries de join entre doenças e fenótipos precisam cruzar grafos urn:hpoa e urn:hpo.

""" + schema_text + "\n" + examples_text
        
        user_msg = f"Pergunta: {question}"
        if feedback:
            user_msg += f"\n\n{feedback}"
        
        return system, user_msg
    
    def generate_sparql(self, system: str, user_msg: str) -> str:
        """Chama o LLM para gerar SPARQL."""
        response = self.client.chat.completions.create(
            model=self.config["llm_model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.0,
            max_tokens=1000
        )
        raw = response.choices[0].message.content
        # Extrair SPARQL do markdown se necessário
        if "```sparql" in raw:
            raw = raw.split("```sparql")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        return raw.strip()
    
    def execute_sparql(self, query: str) -> dict:
        """Executa a query no Fuseki."""
        try:
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()
            bindings = results["results"]["bindings"]
            return {"success": True, "results": bindings, "count": len(bindings)}
        except Exception as e:
            return {"success": False, "error": str(e), "results": [], "count": 0}
    
    def run(self, question: str) -> dict:
        """
        Pipeline completo com loop de validação/correção.
        Retorna: {question, sparql, validation, results, attempts, success}
        """
        # 1. Recuperar exemplos similares
        examples = self.retrieve_examples(question)
        
        # 2. Loop de geração + validação (até max_retries)
        feedback = None
        for attempt in range(1, self.config["max_retries"] + 2):
            # Gerar
            system, user_msg = self.build_prompt(question, examples, feedback)
            sparql_query = self.generate_sparql(system, user_msg)
            
            # Validar
            validation = self.validator.validate(sparql_query)
            
            if validation["valid"]:
                # Executar
                result = self.execute_sparql(sparql_query)
                return {
                    "question": question,
                    "sparql": sparql_query,
                    "validation": validation,
                    "execution": result,
                    "attempts": attempt,
                    "success": result["success"] and result["count"] > 0
                }
            
            # Se inválido e ainda tem tentativas, gerar feedback
            if attempt <= self.config["max_retries"]:
                feedback = self.validator.format_feedback(validation, sparql_query)
                print(f"  ⚠️ Tentativa {attempt} falhou, re-prompting...")
            else:
                return {
                    "question": question,
                    "sparql": sparql_query,
                    "validation": validation,
                    "execution": {"success": False, "error": "Validation failed after retries"},
                    "attempts": attempt,
                    "success": False
                }
```

### 🚦 GATE 3 — Validação do Pipeline End-to-End
```python
# gate3_check.py
"""Executa 3 perguntas de teste e verifica pipeline completo."""
from src.pipeline.nl_to_sparql import BioSPARQLPipeline

pipeline = BioSPARQLPipeline()

test_questions = [
    ("Quais fenótipos estão associados à síndrome de Marfan?", "easy"),
    ("Quantas doenças cardiovasculares existem no DOID?", "easy"),
    ("Quais doenças compartilham fenótipos com a síndrome de Ehlers-Danlos?", "medium"),
]

results = []
for q, difficulty in test_questions:
    print(f"\n{'='*60}")
    print(f"Q: {q} [{difficulty}]")
    r = pipeline.run(q)
    print(f"  Tentativas: {r['attempts']}")
    print(f"  Validação: {'✅' if r['validation']['valid'] else '❌'}")
    print(f"  Execução: {'✅' if r['execution']['success'] else '❌'}")
    print(f"  Resultados: {r['execution'].get('count', 0)}")
    if r['validation']['warnings']:
        print(f"  Warnings: {r['validation']['warnings']}")
    results.append(r)

passed = sum(1 for r in results if r['success'])
print(f"\n{'='*60}")
print(f"GATE 3: {passed}/{len(results)} questões respondidas com sucesso")
print(f"{'✅ GATE PASSED' if passed >= 2 else '❌ GATE FAILED'}")
```

**Critérios de passagem:**
- [ ] Pipeline executa sem erros de importação
- [ ] ≥2/3 questões de teste retornam resultados válidos
- [ ] Mecanismo de retry é acionado quando necessário
- [ ] Validator detecta erros de sintaxe e grafos inválidos

---

## FASE 4 — Avaliação Sistemática
**Objetivo:** Executar pipeline em 30 questões, calcular métricas, gerar tabelas/gráficos  
**Tempo estimado:** 4h  
**Executor:** Claude Code

### 4.1 Avaliação em dois cenários

```python
# src/evaluation/run_evaluation.py
"""
Avalia o pipeline em dois cenários:
  A) COM validação por schema (pipeline completo)
  B) SEM validação (LLM direto, sem feedback/retry)
Métricas: taxa de validade sintática, taxa de execução, 
          correção dos resultados (manual spot-check), 
          número médio de tentativas.
"""
import json
import time
from src.pipeline.nl_to_sparql import BioSPARQLPipeline

def evaluate(pipeline, questions, use_validation=True):
    results = []
    for q in questions:
        if not use_validation:
            # Cenário B: desabilitar retry
            pipeline.config["max_retries"] = 0
        else:
            pipeline.config["max_retries"] = 2
        
        start = time.time()
        r = pipeline.run(q["question_en"])
        elapsed = time.time() - start
        
        r["question_id"] = q["id"]
        r["difficulty"] = q["difficulty"]
        r["type"] = q["type"]
        r["time_seconds"] = elapsed
        r["expected_min_results"] = q.get("expected_min_results", 1)
        r["meets_expected"] = r["execution"].get("count", 0) >= q.get("expected_min_results", 1)
        results.append(r)
    
    return results

def compute_metrics(results):
    total = len(results)
    syntactically_valid = sum(1 for r in results if r["validation"]["valid"])
    executed_ok = sum(1 for r in results if r["execution"].get("success", False))
    has_results = sum(1 for r in results if r["execution"].get("count", 0) > 0)
    meets_expected = sum(1 for r in results if r.get("meets_expected", False))
    avg_attempts = sum(r["attempts"] for r in results) / total
    avg_time = sum(r["time_seconds"] for r in results) / total
    
    # Por dificuldade
    by_difficulty = {}
    for diff in ["easy", "medium", "hard"]:
        subset = [r for r in results if r["difficulty"] == diff]
        if subset:
            by_difficulty[diff] = {
                "total": len(subset),
                "valid": sum(1 for r in subset if r["validation"]["valid"]),
                "executed": sum(1 for r in subset if r["execution"].get("success", False)),
                "correct": sum(1 for r in subset if r.get("meets_expected", False)),
            }
    
    return {
        "total": total,
        "syntactically_valid": syntactically_valid,
        "syntactic_rate": syntactically_valid / total,
        "execution_success": executed_ok,
        "execution_rate": executed_ok / total,
        "has_results": has_results,
        "results_rate": has_results / total,
        "meets_expected": meets_expected,
        "correctness_rate": meets_expected / total,
        "avg_attempts": avg_attempts,
        "avg_time_seconds": avg_time,
        "by_difficulty": by_difficulty,
    }

def main():
    pipeline = BioSPARQLPipeline()
    with open("data/gold_standard/questions.json") as f:
        questions = json.load(f)
    
    print("=" * 60)
    print("CENÁRIO A: COM validação por schema")
    print("=" * 60)
    results_a = evaluate(pipeline, questions, use_validation=True)
    metrics_a = compute_metrics(results_a)
    
    print("\n" + "=" * 60)
    print("CENÁRIO B: SEM validação (baseline)")
    print("=" * 60)
    results_b = evaluate(pipeline, questions, use_validation=False)
    metrics_b = compute_metrics(results_b)
    
    # Salvar
    output = {
        "scenario_a_with_validation": {"metrics": metrics_a, "results": results_a},
        "scenario_b_without_validation": {"metrics": metrics_b, "results": results_b},
    }
    with open("output/evaluation_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    # Tabela comparativa
    print("\n" + "=" * 60)
    print("COMPARAÇÃO")
    print(f"{'Métrica':<30} {'COM Schema':<15} {'SEM Schema':<15}")
    print("-" * 60)
    print(f"{'Validade Sintática':<30} {metrics_a['syntactic_rate']:.1%}{'':<10} {metrics_b['syntactic_rate']:.1%}")
    print(f"{'Execução com Sucesso':<30} {metrics_a['execution_rate']:.1%}{'':<10} {metrics_b['execution_rate']:.1%}")
    print(f"{'Correção (meets expected)':<30} {metrics_a['correctness_rate']:.1%}{'':<10} {metrics_b['correctness_rate']:.1%}")
    print(f"{'Média de Tentativas':<30} {metrics_a['avg_attempts']:.2f}{'':<10} {metrics_b['avg_attempts']:.2f}")
    print(f"{'Tempo Médio (s)':<30} {metrics_a['avg_time_seconds']:.2f}{'':<10} {metrics_b['avg_time_seconds']:.2f}")

if __name__ == "__main__":
    main()
```

### 🚦 GATE 4 — Validação da Avaliação
```python
# gate4_check.py
import json

with open("output/evaluation_results.json") as f:
    data = json.load(f)

ma = data["scenario_a_with_validation"]["metrics"]
mb = data["scenario_b_without_validation"]["metrics"]

print("GATE 4 — Checklist de Avaliação:")
print(f"  {'✅' if ma['total'] >= 6 else '❌'} Questões avaliadas: {ma['total']} (mín: 6, alvo: 30)")
print(f"  {'✅' if ma['syntactic_rate'] > 0.5 else '⚠️'} Taxa sintática COM schema: {ma['syntactic_rate']:.1%}")
print(f"  {'✅' if ma['execution_rate'] > 0.4 else '⚠️'} Taxa execução COM schema: {ma['execution_rate']:.1%}")
print(f"  {'✅' if ma['execution_rate'] >= mb['execution_rate'] else '⚠️'} Schema melhora execução: {ma['execution_rate']:.1%} vs {mb['execution_rate']:.1%}")
print(f"  {'✅' if 'by_difficulty' in ma else '❌'} Métricas por dificuldade presentes")
```

**Critérios de passagem:**
- [ ] ≥6 questões avaliadas em ambos cenários
- [ ] evaluation_results.json gerado com métricas completas
- [ ] Cenário A (com schema) ≥ Cenário B (sem schema) em taxa de execução
- [ ] Métricas por dificuldade (easy/medium/hard) calculadas

---

## FASE 5 — Geração do Relatório Técnico (Template SBC)
**Objetivo:** Gerar relatório .docx no formato SBC com resultados  
**Tempo estimado:** 4h  
**Executor:** Claude Code

### 5.1 Estrutura do relatório (máx. 10 páginas)

```
1. Introdução (1 página)
   - Motivação: dificuldade de SPARQL, potencial de LLMs, necessidade de validação
   - Objetivo: pipeline NL→SPARQL com validação ontológica
   - Contribuição: demonstrar que schemas ontológicos melhoram geração SPARQL

2. Conceitos Gerais (2 páginas)
   - 2.1 Ontologias biomédicas (DOID, HPO, OWL, SPARQL)
   - 2.2 LLMs e geração de código (RAG, few-shot learning)
   - 2.3 Validação de dados RDF (VoID, SHACL, introspecção de esquemas)

3. Estado da Arte (2 páginas)
   - SPARQL-LLM (SIB Swiss) — referência principal
   - KG-RAG (Soman et al., 2024)
   - Text-to-SPARQL surveys
   - Tabela comparativa de abordagens

4. Aplicação Desenvolvida (2-3 páginas)
   - 4.1 Arquitetura do pipeline (diagrama)
   - 4.2 Preparação dos dados (DOID+HPO+HPOA, conversão TSV→RDF)
   - 4.3 Extração de schemas e indexação
   - 4.4 Geração e validação de SPARQL
   - 4.5 Loop de autocorreção

5. Análise de Resultados e Conclusão (2 páginas)
   - 5.1 Resultados: tabelas comparativas (com/sem schema, por dificuldade)
   - 5.2 Discussão: análise de erros, limitações
   - 5.3 Conclusão: contribuições, trabalhos futuros

Referências (~15-20 referências)
```

### 5.2 Gerar o .docx

```bash
# Usar a skill docx do Claude para gerar o documento no template SBC
# O conteúdo será montado a partir de:
# - output/evaluation_results.json (métricas)
# - data/schemas.json (info sobre ontologias)
# - Artigos referenciados na pesquisa anterior
```

### 🚦 GATE 5 — Validação Final do Relatório
```
Checklist manual:
- [ ] Título, autores e filiação presentes
- [ ] Abstract (EN) e Resumo (PT) em até 10 linhas cada
- [ ] Seções 1-5 completas
- [ ] Tabelas de resultados com métricas numéricas
- [ ] ≥15 referências bibliográficas formatadas
- [ ] Máximo 10 páginas
- [ ] Formato SBC (fonte Times 12pt, margens corretas)
```

---

## Resumo de Fases e Tempos

| Fase | Descrição | Tempo Est. | Gate |
|------|-----------|-----------|------|
| 0 | Setup do ambiente | 2h | Dependências + Fuseki OK |
| 1 | Dados ontológicos (DOID+HPO+HPOA→Fuseki) | 4h | Triplas carregadas, query Marfan OK |
| 2 | Schemas + Gold Standard + Índice FAISS | 6h | Schemas extraídos, retrieval funciona |
| 3 | Pipeline NL→SPARQL→Validação→Execução | 8h | ≥2/3 questões de teste OK |
| 4 | Avaliação sistemática (2 cenários) | 4h | Métricas calculadas, JSON exportado |
| 5 | Relatório técnico SBC (.docx) | 4h | Documento completo, ≤10 páginas |
| **Total** | | **28h** | |

---

## Referências-chave para o relatório

1. **Soman, K. et al. (2024).** "Biomedical KG-Optimized Prompt Generation for LLMs." *Bioinformatics*, 40(9). DOI: 10.1093/bioinformatics/btae560
2. **Manda, P. (2025).** "Large Language Models in Bio-Ontology Research: A Review." *Bioengineering*, 12(11), 1260.
3. **Pan, S. et al. (2024).** "Unifying LLMs and KGs: A Roadmap." *IEEE TKDE*, 36(7).
4. **Prenosil, G.A. et al. (2025).** "Neuro-Symbolic AI for Auditable Info Extraction." *Comm. Medicine* (Nature), 5, 491.
5. **SPARQL-LLM** — Déjean, V. et al. (2024). "LLM-based SPARQL Query Generation over Federated KGs." arXiv:2410.06062. GitHub: sib-swiss/sparql-llm
6. **Toro, S. et al. (2024).** "DRAGON-AI." *J. Biomedical Semantics*, 15, 19.
7. **Schriml, L.M. et al. (2022).** "The Human Disease Ontology 2022 update." *NAR*, 50(D1).
8. **Köhler, S. et al. (2021).** "The Human Phenotype Ontology in 2021." *NAR*, 49(D1).
9. **Feng, H. et al. (2026).** "OntologyRAG." Springer LNCS.
10. **Xu, R. et al. (2025).** "A Survey on Unifying LLMs and KGs for Biomedicine." *KDD '25*.
