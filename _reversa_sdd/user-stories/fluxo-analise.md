# User Stories — Fluxo: Consolidação e Análise Comparativa de Resultados

> Gerado pelo Redator (Writer) em 2026-05-04 | doc_level: detalhado
> Ator principal: Pesquisador analisando resultados e preparando o paper científico

---

## Contexto

Após a avaliação dos modelos, o pesquisador consolida os resultados, compara cenários e modelos, analisa regressões introduzidas por correções no pipeline, gera tabelas LaTeX para o paper e usa o `ClaudeCLIBackend` para incluir o Claude Sonnet nos benchmarks sem precisar de API key. Este fluxo é o fechamento do ciclo científico: dados → análise → evidências publicáveis.

---

## US-01 — Comparar desempenho de múltiplos modelos em um único dashboard

**Como** pesquisador,
**quero** consolidar os resultados de todos os modelos avaliados em um único arquivo comparativo,
**para** ter uma visão ordenada por desempenho que sirva de base para as conclusões do paper.

### Critérios de Aceitação

```gherkin
Dado que output/eval_google_gemma-3-4b.json, output/eval_nvidia_nemotron-3-nano-4b.json e output/eval_qwen_qwen3.5-9b.json existem
Quando consolidate.py é executado
Então output/evaluation_multi_model.json é gerado
E contém entrada por modelo com métricas: success_rate_A, success_rate_B, spot_check_A, spot_check_B, avg_retries, avg_timing_ms
E a ordenação reflete desempenho decrescente no Cenário A
E o resultado confirma: Nemotron (80%) > Qwen (50%) > Gemma (46.7%)
```

**Rastreabilidade:** 🟢 `src/evaluation/consolidate.py`; 🟢 `output/evaluation_multi_model.json` (existente)

---

## US-02 — Gerar tabelas LaTeX prontas para inserção no paper

**Como** pesquisador,
**quero** gerar automaticamente os fragmentos `.tex` com os resultados de avaliação e ablação,
**para** incorporá-los diretamente no paper SBC sem redigitar dados manualmente e sem risco de inconsistência.

### Critérios de Aceitação

```gherkin
Dado output/evaluation_multi_model.json consolidado
E output/ablation_nvidia_nemotron-3-nano-4b.json (modelo de referência)
Quando latex_tables.py é executado
Então output/tables/table_evaluation.tex é gerado com:
  colunas: Modelo | Params | Cenário A (%) | Cenário B (%) | Δ
  linhas: nemotron (80%, X%, +Δ) | qwen (50%, X%, +Δ) | gemma (46.7%, X%, +Δ)
E output/tables/table_ablation.tex é gerado com:
  colunas: Configuração | NER | Few-shot | Schema | Validação | Acurácia (%)
  linhas: full | no_ner | no_fewshot | no_schema | no_validation | zero_shot
E todos os valores conferem com os JSONs de origem (sem invenção de dados)
```

```gherkin
Dado que evaluation_multi_model.json contém um modelo com timeout registrado
Quando latex_tables.py processa esse modelo
Então a linha na tabela indica "Timeout" ou "N/A" em vez de percentual
```

**Rastreabilidade:** 🟢 `src/evaluation/latex_tables.py`; 🟢 `output/tables/` (existente); 🟢 CLAUDE.md — "todos os números conferem com dados reais"

---

## US-03 — Medir impacto das correções do pipeline (análise de regressões)

**Como** pesquisador,
**quero** comparar os resultados antes e depois de aplicar correções ao pipeline,
**para** demonstrar no paper a evolução entre versões e garantir que não houve regressão.

### Critérios de Aceitação

```gherkin
Dado output2/playwright_log_baseline.jsonl (snapshot antes das correções)
E output2/playwright_log.jsonl (resultados após as correções)
Quando corrections_report.py é executado
Então output2/corrections_report.json é gerado com:
  - baseline: total de questões com sucesso + taxa por dificuldade
  - corrected: total após correções + taxa por dificuldade
  - delta: absoluto (N questões) e em pontos percentuais
  - recovered: IDs de questões que passaram a funcionar
  - regressed: IDs de questões que deixaram de funcionar
  - still_failing: IDs que continuam falhas
E output2/corrections_report.md com tabelas Markdown legíveis
```

```gherkin
Dado que playwright_log_baseline.jsonl não existe (primeira execução)
Quando corrections_report.py é executado
Então baseline é tratado como {} (vazio, 0/0)
E o relatório é gerado sem erro, mostrando apenas os resultados atuais
```

**Rastreabilidade:** 🟢 `src2/evaluation/corrections_report.py`; 🟢 `output2/corrections_report.json` e `corrections_report.md` (existentes)

---

## US-04 — Incluir Claude Sonnet no benchmark via CLI OAuth (sem API key)

**Como** pesquisador,
**quero** avaliar o Claude Sonnet no mesmo framework das 30 questões sem precisar de ANTHROPIC_API_KEY,
**para** ter o modelo comercial como upper bound de comparação usando a sessão OAuth já ativa.

### Critérios de Aceitação

```gherkin
Dado que o claude CLI está no PATH e autenticado via OAuth do Claude Code
Quando run_evaluation.py --model "claude-sonnet-4-20250514" --backend claude_cli é executado
Então ClaudeCLIBackend.generate() invoca `claude --print --disable-slash-commands`
E o workdir usado é ~/.biosparql-bench-workdir (fora do proj1/ para não contaminar com CLAUDE.md)
E user_msg é passado via stdin
E o resultado é salvo em output2/eval_claude-sonnet-4-20250514.json
```

```gherkin
Dado que o subprocess `claude` excede 180s (timeout padrão)
Quando ClaudeCLIBackend.generate() detecta TimeoutExpired
Então RuntimeError("claude CLI timeout after 180s") é lançado
E a questão é registrada como falha com tipo "timeout"
```

```gherkin
Dado que o claude CLI não está instalado
Quando ClaudeCLIBackend.__init__() é chamado
Então RuntimeError("claude CLI not found in PATH") é lançado imediatamente
E a mensagem instrui o usuário a instalar ou adicionar ao PATH
```

**Rastreabilidade:** 🟢 `src2/pipeline/llm_backends.py:ClaudeCLIBackend`; 🟢 ADR-005 (claude CLI subprocess sem API key); 🟢 RF-02 — isolamento workdir

---

## US-05 — Executar análise comparativa de quatro modelos (four-way comparison)

**Como** pesquisador,
**quero** visualizar um relatório comparativo entre os quatro modelos avaliados (gemma, nemotron, qwen, claude),
**para** compor a seção de resultados do paper com evidências de todos os modelos testados.

### Critérios de Aceitação

```gherkin
Dado output2/playwright_log.jsonl de múltiplas execuções de modelos
Quando o four-way comparison é gerado (via corrections_report ou script dedicado)
Então output2/four_way_comparison.json e four_way_comparison.md são gerados
E contêm métricas por modelo, por dificuldade (easy/medium/hard) e por cenário
E a comparação inclui: taxa de sucesso, avg_retries, avg_timing_ms
```

**Rastreabilidade:** 🟢 `output2/four_way_comparison.json` e `four_way_comparison.md` (existentes)

---

## US-06 — Rastrear regressões no conjunto de regression suite

**Como** pesquisador,
**quero** manter um subconjunto estável de questões para detectar regressões rapidamente,
**para** não precisar rodar as 30 questões completas após cada mudança no pipeline.

### Critérios de Aceitação

```gherkin
Dado data/gold_standard/regression_suite.json com subconjunto de questões críticas
Quando playwright_runner.py --regression-suite é executado
Então apenas as questões de regression_suite.json são processadas
E os resultados são salvos em output2/regression_log.jsonl
E output2/regression_summary.json contém métricas do subconjunto
```

```gherkin
Dado output2/regression_log.jsonl de uma execução anterior
Quando uma nova execução é comparada com a anterior
Então qualquer questão que passou a falhar é marcada como "regredida"
E um alerta é gerado para o pesquisador
```

**Rastreabilidade:** 🟢 `src2/evaluation/playwright_runner.py` — flag `--regression-suite`; 🟢 `output2/regression_log.jsonl` (existente)

---

## US-07 — Verificar validade das referências bibliográficas antes de submeter o paper

**Como** pesquisador,
**quero** verificar automaticamente todos os DOIs e metadados do BibTeX via CrossRef/Semantic Scholar,
**para** garantir que nenhuma referência inventada ou incorreta chegue ao paper final.

### Critérios de Aceitação

```gherkin
Dado output/relatorio/biosparql-nl.bib com 22 referências
Quando verify-bib é executado
Então cada entrada é verificada via CrossRef API (https://api.crossref.org/works/<DOI>)
E entradas sem DOI são verificadas via Semantic Scholar (ARXIV:<id> ou ACL:<id>)
E o relatório lista: OK (DOI confirmado), WARNING (metadados divergentes), FAIL (DOI inválido ou não encontrado)
E nenhuma entrada com FAIL permanece no BibTeX sem correção
```

**Nota:** Histórico de correções já aplicadas: auer2007dbpedia→harris2013sparql, dejean→emonet, prenosil com 9 autores reais, xu→lu, manda vol 12(11), toro pages=19.

**Rastreabilidade:** 🟢 CLAUDE.md — seção "Histórico de Correções (auditoria de alucinações)"; 🟢 skill `verify-bib`

---

## US-08 — Compilar o paper LaTeX em PDF (máximo 10 páginas)

**Como** pesquisador,
**quero** compilar o paper `biosparql-nl.tex` para PDF com todas as tabelas e referências corretas,
**para** obter o documento final no formato SBC pronto para submissão.

### Critérios de Aceitação

```gherkin
Dado output/relatorio/biosparql-nl.tex e biosparql-nl.bib com conteúdo final
Quando a sequência de compilação é executada:
  cd output/relatorio
  pdflatex biosparql-nl
  bibtex biosparql-nl
  pdflatex biosparql-nl
  pdflatex biosparql-nl
Então biosparql-nl.pdf é gerado sem erros fatais
E o PDF tem <= 10 páginas (limite template SBC)
E todas as referências aparecem resolvidas (sem "[?]" ou "UNDEFINED")
E todas as tabelas de avaliação e ablação estão presentes
E o autor aparece como "Cassiano Ricardo Neubauer Moralles" (nunca "[Seu Nome]")
```

```gherkin
Dado que o PDF gerado tem 11 páginas
Quando o pesquisador verifica o limite
Então conteúdo deve ser reduzido (resumir seções, cortar figura opcional)
E recompilação deve resultar em <= 10 páginas
```

**Rastreabilidade:** 🟢 CLAUDE.md — "Máximo 10 páginas (template SBC)"; 🟢 `output/relatorio/biosparql-nl.tex` e `biosparql-nl.pdf` (existentes)

---

## Ciclo completo de análise e publicação

```
Fase 1 — Coletar resultados
  run_evaluation.py (por modelo) → output/eval_*.json
  run_ablation.py (modelo ref)   → output/ablation_*.json
  playwright_runner.py           → output2/playwright_log.jsonl

Fase 2 — Comparar e analisar
  consolidate.py                 → output/evaluation_multi_model.json
  corrections_report.py          → output2/corrections_report.json/.md
  four_way_comparison             → output2/four_way_comparison.json/.md

Fase 3 — Gerar evidências publicáveis
  latex_tables.py                → output/tables/*.tex
  verify-bib                     → validação BibTeX via CrossRef/S2
  pdflatex × 3 + bibtex          → output/relatorio/biosparql-nl.pdf

Fase 4 — Controle de qualidade
  Conferir: todos os números do PDF batem com output/eval_*.json
  Conferir: PDF <= 10 páginas
  Conferir: autor correto, sem "[Seu Nome]", sem "and others"
```

---

## Invariantes da análise

| Invariante | Confiança |
|---|---|
| Resultados em `output/` vêm exclusivamente de `src/` | 🟢 CONFIRMADO |
| Resultados em `output2/` vêm exclusivamente de `src2/` — nunca misturar | 🟢 CONFIRMADO |
| Nenhum número no paper sem rastreabilidade a um JSON em `output/` | 🟢 CONFIRMADO — regra CLAUDE.md |
| ClaudeCLIBackend nunca usa ANTHROPIC_API_KEY | 🟢 CONFIRMADO — ADR-005 |
| verify-bib executado antes de cada versão submetida | 🟡 INFERIDO — convenção documentada, não automatizada |
| Paper nunca excede 10 páginas após compilação final | 🟢 CONFIRMADO — limite template SBC |
