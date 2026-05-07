# User Stories — Fluxo: Avaliação Sistemática de Modelos LLM

> Gerado pelo Redator (Writer) em 2026-05-04 | doc_level: detalhado
> Ator principal: Pesquisador executando experimentos reprodutíveis

---

## Contexto

O pesquisador avalia o desempenho do pipeline BioSPARQL-NL com diferentes modelos LLM usando um gold standard de 30 questões biomédicas (10 easy / 10 medium / 10 hard). Os resultados alimentam o paper científico. O framework suporta dois cenários padrão (com/sem validação), ablação em 6 configurações e comparação multi-modelo.

**Resultado chave já obtido:** Nemotron 4B (80%) > Qwen 9B (50%) > Gemma 3 4B (46.7%) — arquitetura importa mais que tamanho.

---

## US-01 — Avaliar um modelo LLM com as 30 questões do gold standard

**Como** pesquisador,
**quero** executar a avaliação completa de um modelo LLM nas 30 questões biomédicas,
**para** obter métricas comparáveis de sucesso, spot-check e timing entre modelos.

### Critérios de Aceitação

```gherkin
Dado que o LM Studio está rodando com o modelo "nvidia/nemotron-3-nano-4b" carregado
E o Fuseki está rodando com os três grafos carregados
Quando run_evaluation.py --model "nvidia/nemotron-3-nano-4b" --backend lmstudio é executado
Então 30 questões são avaliadas no Cenário A (com validação de schema, max_retries=2)
E 30 questões são avaliadas no Cenário B (sem validação, max_retries=0)
E os resultados são salvos em output/eval_nvidia_nemotron-3-nano-4b.json
E o arquivo contém métricas de sucesso, spot_check_pass, timing e retries por questão
```

```gherkin
Dado que o gold standard tem exatamente 30 questões
Quando a avaliação é executada
Então todas as 30 questões são processadas (nunca reduzido)
E as questões são identificadas como Q01–Q30 com dificuldades easy/medium/hard
```

**Rastreabilidade:** 🟢 `src/evaluation/run_evaluation.py`; 🟢 `data/gold_standard/questions.json`; 🟢 RN-10 (gold standard imutável)

---

## US-02 — Entender a diferença entre Cenário A (com validação) e Cenário B (sem validação)

**Como** pesquisador,
**quero** comparar o desempenho do pipeline com e sem validação de schema,
**para** quantificar a contribuição do SchemaValidator e do loop de autocorreção.

### Critérios de Aceitação

```gherkin
Dado Cenário A (configuração padrão com validação)
Quando evaluate() é chamado com use_validation=True
Então pipeline.config["max_retries"] = 2 (loop de autocorreção ativo)
E pipeline.config["disable_schema"] = False
E a taxa de sucesso reflete o benefício do loop de correção
```

```gherkin
Dado Cenário B (baseline sem validação)
Quando evaluate() é chamado com use_validation=False
Então pipeline.config["max_retries"] = 0 (sem re-prompt)
E pipeline.config["disable_schema"] = True
E a taxa de sucesso representa o desempenho zero-correction do LLM
```

```gherkin
Dado os resultados de ambos os cenários para o mesmo modelo
Quando são comparados
Então a diferença Δ = Cenário A% − Cenário B% quantifica o ganho do loop de correção
```

**Rastreabilidade:** 🟢 `src/evaluation/run_evaluation.py:evaluate()` — parâmetros `use_validation` e `max_retries`

---

## US-03 — Verificar spot-check semântico dos resultados

**Como** pesquisador,
**quero** que o framework verifique automaticamente se os resultados contêm os termos esperados,
**para** ir além da métrica binária success/failure e detectar respostas parcialmente corretas.

### Critérios de Aceitação

```gherkin
Dado uma questão com expected_contains = ["parkinson", "tremor"]
E o Fuseki retornou bindings contendo "Parkinson disease" e "Tremor"
Quando o spot_check é executado
Então todos os valores dos bindings são achatados em uma string lowercase
E cada termo de expected_contains é buscado na string resultante
E spot_check_pass = True (todos os termos encontrados)
```

```gherkin
Dado uma questão com expected_contains = ["epilepsy"]
E o Fuseki retornou 0 resultados
Quando o spot_check é executado
Então spot_check_pass = False
```

```gherkin
Dado uma questão sem campo expected_contains definido
Quando o spot_check é executado
Então spot_check_pass = None (não avaliado — sem penalidade)
```

**Rastreabilidade:** 🟢 `src/evaluation/run_evaluation.py` — lógica de spot-check

---

## US-04 — Executar estudo de ablação para medir contribuição de cada componente

**Como** pesquisador,
**quero** rodar o pipeline em 6 configurações de ablação (removendo componentes individualmente),
**para** publicar evidências quantitativas da contribuição de NER, few-shot, schema e validação.

### Critérios de Aceitação

```gherkin
Dado o modelo "nvidia/nemotron-3-nano-4b"
Quando run_ablation.py é executado
Então 6 avaliações são executadas com as seguintes configurações:
  | Config         | NER | Few-shot | Schema | Validação |
  | full           |  ✅  |    ✅     |   ✅    |    ✅      |
  | no_ner         |  ❌  |    ✅     |   ✅    |    ✅      |
  | no_fewshot     |  ✅  |    ❌     |   ✅    |    ✅      |
  | no_schema      |  ✅  |    ✅     |   ❌    |    ✅      |
  | no_validation  |  ✅  |    ✅     |   ✅    |    ❌      |
  | zero_shot      |  ❌  |    ❌     |   ❌    |    ❌      |
E os resultados são salvos em output/ablation_nvidia_nemotron-3-nano-4b.json
E cada config tem métricas de sucesso separadas para comparação
```

**Rastreabilidade:** 🟢 `src/evaluation/ablation_configs.py`, `src/evaluation/run_ablation.py`

---

## US-05 — Avaliar todos os modelos em sequência (orquestração multi-modelo)

**Como** pesquisador,
**quero** executar a avaliação de todos os modelos disponíveis em um único comando,
**para** obter resultados comparáveis sem precisar disparar cada modelo manualmente.

### Critérios de Aceitação

```gherkin
Dado a lista de modelos configurados (gemma-3-4b, nemotron-3-nano-4b, qwen3.5-9b)
Quando run_all_models.py é executado (src versão)
Então cada modelo é avaliado sequencialmente com os dois cenários A e B
E os resultados individuais são salvos em output/eval_{safe_name}.json
E nenhum modelo >20B é iniciado sem verificação manual de memória (RN-09)
```

```gherkin
Dado que um modelo está em execução e esgota o timeout de 30 minutos
Quando run_all_models.py detecta o timeout
Então o modelo é marcado como "Timeout" no log
E a execução continua para o próximo modelo (sem abortar toda a avaliação)
```

**Rastreabilidade:** 🟢 `src/evaluation/run_all_models.py`; 🟡 RN-09 (guard de memória documentado, não enforçado em código)

---

## US-06 — Consolidar resultados multi-modelo em arquivo comparativo

**Como** pesquisador,
**quero** agregar os resultados de todos os modelos avaliados em um único arquivo JSON,
**para** ter uma visão comparativa consolidada como base para as tabelas do paper.

### Critérios de Aceitação

```gherkin
Dado arquivos output/eval_*.json de 3 modelos avaliados (gemma, nemotron, qwen)
Quando consolidate.py é executado
Então output/evaluation_multi_model.json é gerado
E contém métricas por modelo: success_rate_A, success_rate_B, spot_check_A, spot_check_B, avg_timing
E a ordenação reflete desempenho decrescente no Cenário A
```

**Rastreabilidade:** 🟢 `src/evaluation/consolidate.py`

---

## US-07 — Gerar tabelas LaTeX prontas para o paper

**Como** pesquisador,
**quero** gerar automaticamente fragmentos `.tex` com os resultados de avaliação,
**para** importar diretamente no paper SBC sem redigitar números manualmente.

### Critérios de Aceitação

```gherkin
Dado output/evaluation_multi_model.json consolidado
E output/ablation_*.json de pelo menos um modelo
Quando latex_tables.py é executado
Então arquivos .tex são gerados em output/tables/
E a tabela de avaliação principal contém colunas: Modelo, Params, Cenário A (%), Cenário B (%), Δ
E a tabela de ablação contém colunas: Config, NER, Few-shot, Schema, Validação, Acurácia (%)
E todos os números conferem com os dados em output/eval_*.json (sem invenção)
```

**Rastreabilidade:** 🟢 `src/evaluation/latex_tables.py`; 🟢 CLAUDE.md — regra "todos os números conferem com dados reais"

---

## US-08 — Avaliar via Playwright runner (teste end-to-end pelo frontend)

**Como** pesquisador,
**quero** avaliar as 30 questões passando pelo frontend real (não direto no pipeline),
**para** capturar comportamentos de integração que só aparecem no fluxo completo browser → API → pipeline.

### Critérios de Aceitação

```gherkin
Dado que o frontend está rodando em localhost:3000 (ou 5173)
E o backend FastAPI está rodando em localhost:8000
Quando playwright_runner.py é executado (sem --headed, sem --limit)
Então as 30 questões são submetidas via interface web
E as respostas de /api/ask são interceptadas e salvas em output2/playwright_log.jsonl
E cada linha do JSONL contém: question_id, question, success, entities, sparql, results_count, timing
```

```gherkin
Dado playwright_runner.py --limit 5 --ids Q01 Q05 --headed
Quando executado
Então apenas as questões Q01 e Q05 são processadas (--ids prevalece sobre --limit)
E o browser fica visível durante a execução (--headed)
```

**Rastreabilidade:** 🟢 `src2/evaluation/playwright_runner.py`; 🟢 CLAUDE.md — flags --limit, --ids, --headed, --screenshots

---

## US-09 — Comparar resultados antes e após correções (relatório de regressão)

**Como** pesquisador,
**quero** gerar um relatório comparando os resultados pré e pós correções do pipeline,
**para** demonstrar a evolução entre revisões e detectar regressões.

### Critérios de Aceitação

```gherkin
Dado output2/playwright_log_baseline.jsonl (snapshot pré-correções)
E output2/playwright_log.jsonl (resultados atuais)
Quando corrections_report.py é executado
Então output2/corrections_report.json e corrections_report.md são gerados
E o relatório indica por questão: melhorou / piorou / sem alteração
E métricas agregadas mostram Δ global em success_rate
```

**Rastreabilidade:** 🟢 `src2/evaluation/corrections_report.py`; 🟢 `output2/corrections_report.md` (existente)

---

## Fluxo completo de avaliação (ciclo de pesquisa)

```
1. Garantir serviços rodando:
   Fuseki :3030 → LM Studio :1234 → FastAPI :8000

2. Avaliar modelo individual:
   run_evaluation.py --model "<modelo>" --backend lmstudio
   → output/eval_{safe_name}.json

3. (Opcional) Ablação:
   run_ablation.py --model "<modelo>"
   → output/ablation_{safe_name}.json

4. Repetir para todos os modelos:
   run_all_models.py
   → output/eval_*.json (múltiplos)

5. Consolidar:
   consolidate.py
   → output/evaluation_multi_model.json

6. Gerar tabelas:
   latex_tables.py
   → output/tables/*.tex

7. (Opcional) Avaliação via frontend:
   playwright_runner.py
   → output2/playwright_log.jsonl
```

---

## Restrições de hardware conhecidas

| Modelo | Parâmetros | Status | Observação |
|---|---|---|---|
| google/gemma-3-4b | 4B | Avaliado (30 q) | 46.7% Cenário A |
| nvidia/nemotron-3-nano-4b | 4B | Avaliado (30 q) | 80% Cenário A |
| qwen/qwen3.5-9b | 9B | Avaliado (30 q) | 50% Cenário A |
| google/gemma-4-26b-a4b | 26B (4B ativo) | Timeout 30min | Não concluído |
| openai/gpt-oss-20b | 20B | Não avaliado | Restrição de memória |
| claude-sonnet-4-20250514 | — | Via API / CLI OAuth | Requer ANTHROPIC_API_KEY ou ClaudeCLIBackend |

🟡 **INFERIDO** — guard de >20B documentado em CLAUDE.md, não enforçado em código (RN-09)
