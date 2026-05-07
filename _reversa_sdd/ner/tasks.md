# Tasks — ner

> Unit: `src/pipeline/ner/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## T-01 — Implementar dataclass `Entity` e `NERBackend` (ABC)

**Origem:** `src/pipeline/ner/base.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Sequence

@dataclass
class Entity:
    text: str
    start: int
    end: int
    type: str
    ontology_ids: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    backend: str = ""

class NERBackend(ABC):
    @abstractmethod
    def extract(self, text: str) -> list[Entity]:
        """Extrai entidades biomédicas do texto. Retorna lista vazia se nenhuma encontrada."""
        ...

    def warm_up(self) -> None:
        """Carrega modelos em memória. Chamado pelo factory após instanciação."""
        pass
```

**Critério de pronto:** `Entity` é instanciável com apenas `text`, `start`, `end`, `type`; campos opcionais têm defaults funcionais (listas vazias, não None).

---

## T-02 — Implementar `merge_overlaps(entities)`

**Origem:** `src/pipeline/ner/base.py:merge_overlaps()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
def merge_overlaps(entities: Sequence[Entity]) -> list[Entity]:
    """
    Remove entidades sobrepostas, mantendo a de maior score.
    Sobreposição: max(start_a, start_b) < min(end_a, end_b)
    Score para comparação: max(entity.scores) ou 0.0 se scores=[].
    """
    if not entities:
        return []
    
    # Ordenar por score decrescente
    sorted_ents = sorted(entities, key=lambda e: max(e.scores) if e.scores else 0.0, reverse=True)
    
    accepted: list[Entity] = []
    for ent in sorted_ents:
        overlaps = any(
            max(ent.start, acc.start) < min(ent.end, acc.end)
            for acc in accepted
        )
        if not overlaps:
            accepted.append(ent)
    
    return accepted
```

**Critério de pronto:**
- `merge_overlaps([e1(0,18,score=0.9), e2(5,14,score=0.8)])` → `[e1]`
- `merge_overlaps([e1(0,9), e2(10,18)])` → `[e1, e2]` (sem sobreposição)
- `merge_overlaps([])` → `[]`

---

## T-03 — Implementar `get_backend(name)` com `lru_cache`

**Origem:** `src/pipeline/ner/factory.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
from functools import lru_cache

REGISTRY = {
    "scispacy": "src.pipeline.ner.scispacy_backend.ScispaCyBackend",
    "llm":      "src.pipeline.ner.llm_backend.LLMBackend",
    "gilda":    "src.pipeline.ner.scispacy_backend.ScispaCyBackend",  # só resolução
}

@lru_cache(maxsize=None)
def get_backend(name: str | None = None) -> NERBackend:
    """
    Retorna singleton do backend NER pelo nome.
    Se name=None, usa BIOSPARQL_NER_BACKEND env var (padrão: 'scispacy').
    """
    resolved_name = name or os.environ.get("BIOSPARQL_NER_BACKEND", "scispacy")
    cls_path = REGISTRY.get(resolved_name)
    if cls_path is None:
        raise ValueError(f"Backend NER desconhecido: {resolved_name!r}")
    
    # importar dinamicamente
    module_path, cls_name = cls_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, cls_name)
    
    instance = cls()
    instance.warm_up()
    return instance
```

**Critério de pronto:**
- Duas chamadas com mesmo `name` retornam a mesma instância (identidade `is`)
- `get_backend("unknown")` lança `ValueError`
- `get_backend(None)` usa env var `BIOSPARQL_NER_BACKEND`

---

## T-04 — Implementar `ScispaCyBackend._is_noise(span_text)`

**Origem:** `src/pipeline/ner/scispacy_backend.py:_is_noise()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

```python
STOPWORDS_PT_EN = {
    "doença", "disease", "fenótipo", "phenotype", "sintoma", "symptom",
    "paciente", "patient", "associado", "associated", "causa", "cause",
    "humano", "human", "caracterizado", "characterized",
    # ... ~80 termos no total
}

def _is_noise(self, text: str) -> bool:
    text = text.strip()
    if len(text) < 4:
        return True
    alpha_ratio = sum(c.isalpha() for c in text) / len(text)
    if alpha_ratio < 0.5:
        return True
    if text.lower() in STOPWORDS_PT_EN:
        return True
    return False
```

**Critério de pronto:**
- `_is_noise("de")` → `True` (len < 4)
- `_is_noise("123a")` → `True` (ratio alfa < 0.5)
- `_is_noise("disease")` → `True` (em stoplist)
- `_is_noise("Parkinson")` → `False`
- `_is_noise("febre amarela")` → `False` (len >= 4, alfa >= 0.5, não em stoplist)

---

## T-05 — Implementar `ScispaCyBackend._sparql_lookup(entity_text)`

**Origem:** `src/pipeline/ner/scispacy_backend.py:_sparql_lookup()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must

### Comportamento esperado

Executar query SPARQL no Fuseki para encontrar o URI correspondente ao label da entidade:

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?uri ?label ?g WHERE {
  GRAPH ?g {
    ?uri rdfs:label ?label .
    FILTER(LCASE(STR(?label)) = LCASE("{entity_text}"))
    FILTER(?g IN (<urn:doid>, <urn:hpo>))
  }
}
LIMIT 1
```

Converter URI → CURIE:
- `http://purl.obolibrary.org/obo/DOID_14330` → `DOID:14330`
- `http://purl.obolibrary.org/obo/HP_0001250` → `HP:0001250`

Retornar `{"curie": str, "uri": str, "graph": str}` ou `None` se sem resultado.

Implementar com retry exponencial: 3 tentativas, `time.sleep(2**attempt)` entre elas.

**Critério de pronto:** Para "Parkinson disease" com Fuseki online, retorna dict com curie não-vazio. Com Fuseki offline, retorna `None` após 3 tentativas sem lançar exceção não capturada.

---

## T-06 — Implementar `ScispaCyBackend._gilda_lookup(entity_text)`

**Origem:** `src/pipeline/ner/scispacy_backend.py:_gilda_lookup()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should

### Comportamento esperado

```python
def _gilda_lookup(self, text: str) -> dict | None:
    """
    Fallback de resolução via Gilda quando SPARQL não encontra correspondência.
    Filtra por namespaces relevantes e score mínimo de 0.5.
    """
    import gilda
    ALLOWED_NAMESPACES = {"DOID", "HP", "OMIM", "MESH"}
    
    results = gilda.ground(text)
    for result in results:
        if result.score >= 0.5 and result.term.db in ALLOWED_NAMESPACES:
            curie = f"{result.term.db}:{result.term.id}"
            return {"curie": curie, "uri": None, "graph": _infer_graph(result.term.db)}
    return None
```

**Critério de pronto:** Para "epilepsy", retorna dict com curie `HP:0001250` ou equivalente DOID. Para "xyz_inexistente", retorna `None`.

---

## T-07 — Implementar `ScispaCyBackend.extract(text)`

**Origem:** `src/pipeline/ner/scispacy_backend.py:extract()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-01, T-02, T-04, T-05, T-06

### Comportamento esperado

```python
def extract(self, text: str) -> list[Entity]:
    doc = self.nlp(text)
    entities = []
    for span in doc.ents:
        if self._is_noise(span.text):
            continue
        resolved = self._sparql_lookup(span.text) or self._gilda_lookup(span.text)
        if resolved:
            ids = [resolved["curie"]]
            scores = [1.0]  # SPARQL match é exato; Gilda usa score do resultado
        else:
            ids, scores = [], []
        entities.append(Entity(
            text=span.text,
            start=span.start_char,
            end=span.end_char,
            type=span.label_,
            ontology_ids=ids,
            scores=scores,
            backend="scispacy"
        ))
    return merge_overlaps(entities)
```

**Critério de pronto:**
- Texto "Parkinson disease causes tremor" → lista com ≥1 Entity para "Parkinson disease"
- Texto "Qual é a definição?" → lista vazia (sem entidades biomédicas)
- Texto com spans sobrepostos → apenas o de maior score retornado

---

## T-08 — Implementar `LLMBackend.extract(text)`

**Origem:** `src/pipeline/ner/llm_backend.py:LLMBackend.extract()`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Should
**Depende de:** T-01, T-02, T-06

### Comportamento esperado

```python
def extract(self, text: str) -> list[Entity]:
    # 1. Chamar LLM com system prompt NER e response_format=json_object
    system = """Você é um extrator de entidades biomédicas. 
    Dado um texto, retorne JSON: {"entities": [{"text": str, "type": "DISEASE"|"PHENOTYPE", "start": int, "end": int}]}
    Retorne APENAS entidades de doenças ou fenótipos humanos.
    Não invente IDs ou CURIEs — apenas texto e posição."""
    
    response = self.client.chat.completions.create(
        model=self.model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": text}],
        response_format={"type": "json_object"}
    )
    
    # 2. Parse JSON
    data = json.loads(response.choices[0].message.content)
    spans = data.get("entities", [])
    
    # 3. Resolver via Gilda (NUNCA via LLM)
    entities = []
    for span in spans:
        resolved = self._gilda_lookup(span["text"])
        entities.append(Entity(
            text=span["text"],
            start=span.get("start", 0),
            end=span.get("end", len(span["text"])),
            type=span.get("type", "DISEASE"),
            ontology_ids=[resolved["curie"]] if resolved else [],
            scores=[resolved.get("score", 1.0)] if resolved else [],
            backend="llm"
        ))
    
    return merge_overlaps(entities)
```

**Critério de pronto:** Nenhum CURIE no resultado foi gerado pelo LLM diretamente — todos vêm do Gilda ou são listas vazias.

---

## T-09 — Implementar `EntityLinker`

**Origem:** `src/pipeline/entity_linker.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Must
**Depende de:** T-03

### Comportamento esperado

```python
class EntityLinker:
    def __init__(self, endpoint: str, ner_backend: str = "scispacy"):
        self.endpoint = endpoint
        try:
            self._backend = get_backend(ner_backend)
        except Exception:
            self._backend = None   # graceful fallback

    def extract_entities(self, text: str) -> list[dict]:
        """Extrai entidades e retorna como lista de dicts para o pipeline."""
        if self._backend is None:
            return []
        entities = self._backend.extract(text)
        return [self._entity_to_dict(e) for e in entities]

    def format_for_prompt(self, entities: list[dict]) -> str:
        """Formata entidades para inclusão no system prompt do LLM."""
        if not entities:
            return "Nenhuma entidade biomédica detectada."
        lines = []
        for e in entities:
            ids = ", ".join(e.get("ontology_ids", [])) or "ID não resolvido"
            lines.append(f"- {e['text']} ({e['type']}): {ids}")
        return "\n".join(lines)

    def _entity_to_dict(self, entity: Entity) -> dict:
        return {
            "text": entity.text,
            "type": entity.type,
            "ontology_ids": entity.ontology_ids,
            "scores": entity.scores,
            "backend": entity.backend,
        }
```

**Critério de pronto:**
- `extract_entities("Parkinson disease")` retorna lista de dicts com `ontology_ids`
- Com `_backend=None`, retorna `[]` sem exceção
- `format_for_prompt([])` retorna string não-vazia (mensagem de fallback)

---

## T-10 — `GildaBackend` (backend experimental)

**Origem:** `src/pipeline/ner/gilda_backend.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Could (experimental — não usado no pipeline de produção)
**Dependência:** `pip install gilda`

### Comportamento esperado

`GildaBackend` é um backend standalone que usa `gilda.ground()` para resolução de entidades sem depender de spaCy NER biomédico. Usa spaCy apenas para extração de spans de superfície, delegando toda a identificação ontológica ao Gilda.

Namespaces aceitos (`_KEEP_NS`): `DOID`, `HP`, `OMIM`, `MESH`. Score mínimo: `0.5`.

```python
_KEEP_NS = ("DOID", "HP", "OMIM", "MESH")

class GildaBackend:   # não herda NERBackend ABC
    def extract(self, text: str) -> list[Entity]:
        doc = self._nlp(text)
        entities = []
        for span in doc.ents:
            results = gilda.ground(span.text)
            for r in results:
                if r.score >= 0.5 and r.term.db in _KEEP_NS:
                    curie = f"{r.term.db}:{r.term.id}"
                    entities.append(Entity(
                        text=span.text,
                        start=span.start_char,
                        end=span.end_char,
                        type=span.label_,
                        ontology_ids=[curie],
                        scores=[r.score],
                        backend="gilda"
                    ))
                    break  # primeiro resultado válido por span
        return merge_overlaps(entities)
```

**Critério de pronto:**
- `GildaBackend().extract("Parkinson disease")` retorna ≥1 Entity com `ontology_ids` não vazio
- Apenas namespaces `_KEEP_NS` são aceitos
- Score < 0.5 ou namespace fora da lista → span ignorado
- Sem resultados Gilda → retorna `[]` sem exceção

---

## T-11 — `MedCATBackend` (backend experimental)

**Origem:** `src/pipeline/ner/medcat_backend.py`
**Confiança:** 🟢 CONFIRMADO
**Prioridade:** Could (experimental — requer build prévio de CDB)
**Dependência:** `pip install medcat` + one-time build step

### Setup obrigatório (one-time)

```bash
python -m src.pipeline.ner.medcat_backend build
```

Lê `DOID_OWL` e `HPO_OWL` (env vars) e gera `MEDCAT_CDB` e `MEDCAT_VOCAB`.

### Variáveis de ambiente

| Env var | Default | Descrição |
|---|---|---|
| `MEDCAT_CDB` | `data/medcat/cdb.dat` | CDB compilado |
| `MEDCAT_VOCAB` | `data/medcat/vocab.dat` | Vocabulário |
| `DOID_OWL` | `data/ontologies/doid.owl` | Fonte DOID para build |
| `HPO_OWL` | `data/ontologies/hp.owl` | Fonte HPO para build |

### Comportamento esperado

```python
class MedCATBackend:
    def __init__(self):
        cdb_path = os.environ.get("MEDCAT_CDB", "data/medcat/cdb.dat")
        vocab_path = os.environ.get("MEDCAT_VOCAB", "data/medcat/vocab.dat")
        self.cat = CAT.load_model_pack(cdb_path, vocab_path)

    def extract(self, text: str) -> list[Entity]:
        entities_data = self.cat.get_entities(text)
        result = []
        for eid, edata in entities_data["entities"].items():
            result.append(Entity(
                text=edata["detected_name"],
                start=edata["start"],
                end=edata["end"],
                type=edata.get("type", "DISEASE"),
                ontology_ids=[edata["cui"]],
                scores=[edata.get("acc", 1.0)],
                backend="medcat"
            ))
        return merge_overlaps(result)
```

**Critério de pronto:**
- Com CDB pré-compilado: `MedCATBackend().extract("Parkinson disease")` retorna ≥1 Entity
- Sem CDB: lança exceção informativa (não silencia)
- Modo `build`: gera os arquivos `MEDCAT_CDB` e `MEDCAT_VOCAB` a partir dos OWLs
