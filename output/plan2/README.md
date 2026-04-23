# biosparql_ner — NER backends plugáveis para BioSPARQL-NL

Todos os backends implementam o mesmo `Protocol` (`base.NERBackend`) e
retornam `list[Entity]`. Escolha via `.env` sem mudar o pipeline.

## Instalação

```bash
pip install -r requirements.txt
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.5/en_core_sci_sm-0.5.5.tar.gz
cp .env.example .env
```

## Uso no pipeline

Substitua o bloco scispaCy atual por:

```python
from biosparql_ner.config import get_backend

ner = get_backend()               # lê NER_BACKEND do .env
entities = ner.extract(question)  # list[Entity]

# cada Entity expõe: .text .start .end .type .ontology_ids .primary_id .scores
```

Troca de backend em runtime: só mudar `NER_BACKEND` no `.env` e reiniciar.
Nenhuma outra parte do pipeline (FAISS, prompt builder, Fuseki) muda.

## Construção da CDB do MedCAT (uma vez)

```bash
export DOID_OWL=./data/doid.owl
export HPO_OWL=./data/hp.owl
python -m biosparql_ner.backends.medcat build
```

Gera `medcat_cdb_doid_hpo.dat` (concept database com labels + synonyms de
DOID e HPO parseados direto do OWL).

## Comparação (harness)

```bash
python -m biosparql_ner.bench --gold gold_standard.json --out bench_results/
```

Formato esperado de `gold_standard.json`:

```json
[
  {
    "id": "Q01",
    "question": "Which phenotypes are associated with Parkinson disease?",
    "expected_entities": [
      {"text": "Parkinson disease", "type": "DISEASE", "ontology_id": "DOID:14330"}
    ]
  }
]
```

Saída: tabela no stdout (P / R / F1 / coverage / latência / erros) +
`bench_results/full.json` com predições por questão e por backend. Isso
alimenta diretamente uma nova seção de ablação no artigo (Tabela: impacto
da escolha do NER).

## Paralelismo

Backends carregam modelos diferentes. Rodar em paralelo só é seguro se
eles não competirem por GPU. Para o caso típico (scispaCy + Gilda na CPU,
LLM na GPU, MedCAT na CPU), use `--parallel`:

```bash
python -m biosparql_ner.bench --gold gold_standard.json --parallel
```

## Adicionar um novo backend

1. Cria `backends/meu_backend.py` com uma classe que satisfaça
   `NERBackend` (`name`, `warm_up()`, `extract()`).
2. Registra em `config.REGISTRY`.
3. Pronto — aparece automaticamente no bench.

## Gancho com o paper

O `bench.py` produz exatamente as métricas que faltam na Tabela 6 do
BioSPARQL-NL para uma nova coluna "NER backend". Sugestão de novas
linhas no estudo de ablação:

| Configuração | Sint. | Correção | Δ vs Full |
| --- | --- | --- | --- |
| Full (scispaCy NER) | ... | ... | — |
| Full (Gilda NER) | ... | ... | ... |
| Full (LLM NER + Gilda link) | ... | ... | ... |
| Full (MedCAT NER) | ... | ... | ... |
