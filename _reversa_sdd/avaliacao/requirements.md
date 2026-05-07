# Requisitos — avaliacao

> Unit: `src/evaluation/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `avaliacao` |
| Caminho legado | `src/evaluation/run_evaluation.py`, `run_all_models.py`, `ablation_configs.py`, `run_ablation.py`, `consolidate.py`, `latex_tables.py`, `inter_annotator.py`, `bench_ner.py` |
| Responsabilidade | Framework de avaliação reprodutível: 30 questões, 2 cenários padrão, ablação em 6 configs, consolidação multi-modelo e geração de tabelas LaTeX para o paper |
| Complexidade | 🟡 Média |

---

## Requisitos Funcionais

### RF-01 — Avaliação single-model em 30 questões
🟢 **CONFIRMADO** — `run_evaluation.py`

**Must**

Dado um modelo LLM configurado, executar o pipeline nas 30 questões do gold standard em dois cenários e salvar os resultados.

**Critérios de Aceitação:**

```gherkin
Dado o modelo "nvidia/nemotron-3-nano-4b" e backend "lmstudio"
Quando run_evaluation.py --model "nvidia/nemotron-3-nano-4b" --backend lmstudio é executado
Então 30 questões são avaliadas no Cenário A (com validação, max_retries=2)
E 30 questões são avaliadas no Cenário B (sem validação, max_retries=0)
E resultados são salvos em output/eval_nvidia_nemotron-3-nano-4b.json
```

```gherkin
Dado que uma questão não tem "expected_contains" definido
Quando spot_check é calculado
Então spot_check_pass = None (não avaliado)
```

---

### RF-02 — Dois cenários padrão de avaliação (A e B)
🟢 **CONFIRMADO** — `run_evaluation.py:evaluate()` — RN-10

**Must**

- **Cenário A:** pipeline com validação de schema e max_retries=2 (configuração padrão)
- **Cenário B:** pipeline sem validação e max_retries=0 (baseline sem correção)

**Critérios de Aceitação:**

```gherkin
Dado Cenário A (com validação)
Quando evaluate(pipeline, questions, use_validation=True) é chamado
Então pipeline.config["max_retries"] = 2
E pipeline.config["disable_schema"] = False
```

```gherkin
Dado Cenário B (sem validação)
Quando evaluate(pipeline, questions, use_validation=False) é chamado
Então pipeline.config["max_retries"] = 0
E pipeline.config["disable_schema"] = True
```

---

### RF-03 — Spot-check semântico dos resultados
🟢 **CONFIRMADO** — `run_evaluation.py` — lógica de spot-check

**Should**

Para questões com `expected_contains` definido no gold standard, verificar se os termos esperados aparecem nos bindings retornados pelo Fuseki.

**Critérios de Aceitação:**

```gherkin
Dado questão com expected_contains=["parkinson", "tremor"]
E resultado com bindings contendo "Parkinson disease" e "Tremor"
Quando spot_check é executado
Então flatten todos valores dos bindings em string lowercase
E verificar se todos os termos de expected_contains estão presentes
Então spot_check_pass = True
```

---

### RF-04 — Ablação em 6 configurações
🟢 **CONFIRMADO** — `ablation_configs.py`, `run_ablation.py`

**Should**

Executar a avaliação em 6 configurações que removem componentes individualmente para medir sua contribuição:

| Config | NER | Few-shot | Schema | Validação |
|---|---|---|---|---|
| `full` | ✅ | ✅ | ✅ | ✅ |
| `no_ner` | ❌ | ✅ | ✅ | ✅ |
| `no_fewshot` | ✅ | ❌ | ✅ | ✅ |
| `no_schema` | ✅ | ✅ | ❌ | ✅ |
| `no_validation` | ✅ | ✅ | ✅ | ❌ |
| `zero_shot` | ❌ | ❌ | ❌ | ❌ |

**Critério de Aceitação:**

```gherkin
Dado o modelo "nvidia/nemotron-3-nano-4b"
Quando run_ablation.py é executado
Então 6 avaliações são executadas, uma por config
E resultados salvos em output/ablation_nvidia_nemotron-3-nano-4b.json
```

---

### RF-05 — Consolidação multi-modelo
🟢 **CONFIRMADO** — `consolidate.py`

**Should**

Agregar resultados de múltiplos modelos (`output/eval_*.json`) em um único arquivo comparativo.

**Critério de Aceitação:**

```gherkin
Dado arquivos output/eval_*.json de 3 modelos avaliados
Quando consolidate.py é executado
Então output/evaluation_multi_model.json é gerado
E contém métricas agregadas por modelo e cenário
```

---

### RF-06 — Geração de tabelas LaTeX para o paper
🟢 **CONFIRMADO** — `latex_tables.py`

**Should**

A partir dos resultados consolidados, gerar fragmentos `.tex` prontos para importação no paper SBC.

**Critério de Aceitação:**

```gherkin
Dado output/evaluation_multi_model.json e output/ablation_*.json
Quando latex_tables.py é executado
Então arquivos .tex são gerados em output/tables/
E tabelas contêm colunas: Modelo, Cenário A (%), Cenário B (%), Δ
```

---

### RF-07 — Nome de arquivo seguro para saída (`safe_name`)
🟢 **CONFIRMADO** — convenção documentada em `CLAUDE.md`

**Must**

O nome do arquivo de saída usa `model.replace("/", "_")` para evitar barras no path:
- `"nvidia/nemotron-3-nano-4b"` → `output/eval_nvidia_nemotron-3-nano-4b.json`

---

### RF-08 — Gold standard imutável (30 questões)
🟢 **CONFIRMADO** — RN-10

**Must**

O conjunto de avaliação deve ter exatamente 30 questões (10 easy / 10 medium / 10 hard). Não deve ser reduzido para garantir comparabilidade histórica entre modelos.

---

## Requisitos Não Funcionais

### RNF-01 — Não rodar modelos >20B sem verificar memória
🟡 **INFERIDO** — RN-09 documentado em `CLAUDE.md`, não enforçado em código

Antes de avaliar modelos com >20B parâmetros, verificar memória disponível (8GB VRAM + 16GB RAM).

### RNF-02 — Saída em `output/` (src) ou `output2/` (src2)
🟢 **CONFIRMADO** — convenção de paths

`src/evaluation/` salva em `output/`. `src2/evaluation/` salva em `output2/`. Nunca misturar.

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 Avaliação single-model | **Must** | Base de todo o framework |
| RF-02 Dois cenários A/B | **Must** | Comparação padrão do paper |
| RF-03 Spot-check semântico | **Should** | Métrica adicional de qualidade |
| RF-04 Ablação 6 configs | **Should** | Necessária para a seção de ablação do paper |
| RF-05 Consolidação multi-modelo | **Should** | Necessária para tabelas comparativas |
| RF-06 Tabelas LaTeX | **Should** | Necessária para compilar o paper |
| RF-07 Safe name | **Must** | Evita erros de path no Windows/Linux |
| RF-08 Gold standard imutável | **Must** | Comparabilidade histórica |

---

## Dependências

| Dependência | Tipo | Obrigatória |
|---|---|---|
| `BioSPARQLPipeline` | Módulo interno | Sim |
| `data/gold_standard/questions.json` | Arquivo | Sim |
| Apache Jena Fuseki em `:3030` | Serviço externo | Sim |
| LM Studio em `:1234` | Serviço externo | Sim (para modelos locais) |
| `output/eval_*.json` existentes | Arquivo | Apenas para consolidação |
