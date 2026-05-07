# Questions — pipeline

> Unit: `src/pipeline/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado
> Lacunas que requerem validação humana antes de reimplementação segura.

---

## Como usar este arquivo

Cada questão abaixo representa uma **lacuna de conhecimento** identificada durante a análise. Antes de reimplementar o módulo `pipeline`, o responsável deve responder cada questão ou documentar explicitamente a decisão de aceitar o risco.

Marque cada questão com:
- ✅ **Respondido** — resposta documentada abaixo
- ⏭️ **Aceito como risco** — decisão consciente de não investigar
- 🔄 **Em investigação** — alguém está verificando

---

## Q-01 — Interações entre as 9 transformações de pós-processamento em queries complexas

**Confiança:** 🔴 LACUNA
**Origem:** Detetive + ADR-P02 + EC-02
**Risco:** 🔴 Alto

### Contexto

O método `_fix_common_errors()` aplica 9 transformações regex sequencialmente. Cada transformação foi projetada para um padrão específico de erro, mas não há testes que verifiquem o comportamento quando **múltiplos padrões coexistem** na mesma query.

Caso específico identificado: transform ⑦ (FILTER após `}`) usa regex baseada no último `}` da query. Em queries com **subconsultas aninhadas** (`{ SELECT ... WHERE { FILTER ... } }`), o "último `}`" pode ser o fechamento de uma subconsulta, não do WHERE principal.

### Questão

> Qual é o comportamento correto de `_fix_common_errors()` quando a query contém FILTERs após subconsultas aninhadas? A transform ⑦ move o FILTER para o lugar correto nesses casos?

### Dados para investigar

- Arquivo: `src/pipeline/nl_to_sparql.py:_fix_common_errors()`
- Testes relevantes: `tests/unit/` (verificar cobertura de subconsultas)
- Questões do gold standard: Q20–Q30 (dificuldade "hard") — mais propensas a subconsultas

### Status: ⏭️ Aceito como risco — transforms ⑦ e ⑧ operam em regiões distintas da query (FILTER solto vs. BIND auto-ref). Sobreposição simultânea é rara. Testes de combinação devem ser escritos antes de reimplementar.

---

## Q-02 — Impacto do modo permissivo do SchemaValidator em queries com termos inválidos

**Confiança:** 🔴 LACUNA
**Origem:** Detetive + RN-06 + EC-04
**Risco:** 🟡 Médio

### Contexto

Quando `data/schemas.json` está ausente, o `SchemaValidator` opera em modo permissivo: valida apenas sintaxe, operações unsafe e grafos nomeados. Predicados e classes inexistentes passam sem erro.

Não está documentado **qual é a proporção de falsos positivos** que isso introduz: quantas queries que passariam em modo STRICT (com schemas) mas falhariam no Fuseki chegam ao triplestore quando em modo permissivo.

### Questão

> Quantas das 30 questões do gold standard geram queries que passam em modo PERMISSIVE mas falham no Fuseki por usar predicados/classes inválidos? Esse número justifica tratar a ausência de `schemas.json` como erro fatal em vez de fallback silencioso?

### Dados para investigar

- Executar avaliação com `disable_schema=True` (ablação `no_schema`) e comparar com resultado com schema
- Arquivo de ablação: `output/ablation_*.json` (se disponível para o modelo)
- Regra relacionada: RN-06 em `domain.md`

### Resultado (medido em 2026-05-06, 30 questões, com fix de data leak no few-shot e remoção do placeholder copiável)

**Comparação Full Pipeline vs no_schema por modelo:**

| Modelo | Full Pipeline (correct) | no_schema (correct) | Delta |
|--------|-------------------------|---------------------|-------|
| Claude Sonnet 4.5 (CLI) | **90.0%** | 90.0% | 0.0pp |
| Nemotron 4B (LM Studio) | 53.3% | 66.7% | **+13.3pp** |
| Gemma 3 4B (LM Studio) | 50.0% | 46.7% | −3.3pp |

**Tabela completa de ablação (correctness rate):**

| Config | Claude | Nemotron | Gemma |
|--------|--------|----------|-------|
| Full Pipeline | **90.0%** | 53.3% | 50.0% |
| − NER | 90.0% | 63.3% | 63.3% |
| − Few-shot | 56.7% | **70.0%** | 46.7% |
| − Schema | 90.0% | 66.7% | 46.7% |
| − Validation | 83.3% | 53.3% | 50.0% |
| Zero-shot | 43.3% | 66.7% | 66.7% |

**Interpretações:**

- **Claude:** schema é neutro (90% → 90% sem). Few-shot é crítico — sem ele cai para 56.7%. Modelo grande tira proveito de exemplos.
- **Nemotron:** schema atrapalha (+13.3pp sem schema). Few-shot atrapalha (+16.7pp sem). Modelo pequeno se confunde com mais contexto. Zero-shot iguala Full Pipeline.
- **Gemma:** schema ajuda marginalmente (−3.3pp sem). Few-shot atrapalha (−3.3pp sem). Padrão similar ao Nemotron mas menos pronunciado.

**Achados importantes:**

1. **O resultado histórico de 80% do Nemotron era data leak.** O FAISS index incluía as 30 questões do gold standard, e durante a avaliação o pipeline retornava a própria questão como Top-1 exemplo few-shot, injetando o gold SPARQL no prompt. Após corrigir (parâmetro `exclude_id` em `retrieve_examples()`), Nemotron cai para 53.3% real.

2. **Schema validation tem efeito modelo-dependente.** Não há resposta única para o impacto do modo permissivo — depende do modelo gerador. Claude é insensível, Nemotron sofre, Gemma se beneficia minimamente.

3. **Few-shot é benéfico apenas para modelos com bom in-context learning.** Para modelos pequenos (≤4B params), exemplos confundem mais do que ajudam.

**Recomendação:** tratar `schemas.json` ausente como warning, não erro fatal. Decisões de pipeline (manter/remover NER, schema, few-shot) devem ser por modelo.

### Status: 🟢 Respondido

---

## Q-03 — Validação de `LLM_MODEL` e `LLM_TIMEOUT` via variável de ambiente

**Confiança:** 🔴 LACUNA
**Origem:** Detetive
**Risco:** 🟢 Baixo

### Contexto

O pipeline aceita `LLM_MODEL` e `LLM_TIMEOUT` via variáveis de ambiente:

```python
llm_model = os.environ.get("LLM_MODEL", "auto")
llm_timeout = float(os.environ.get("LLM_TIMEOUT", 300))
```

Não está claro se há validação dessas variáveis:
- `LLM_TIMEOUT` com valor não-numérico (`float("abc")`) lança `ValueError` não capturado
- `LLM_MODEL` inválido pode resultar em `"auto"` sendo passado ao LM Studio, que pode ou não resolver corretamente o modelo padrão

### Questão

> Existe tratamento de erro para `LLM_TIMEOUT` não-numérico? Se `LLM_MODEL` for um nome inválido, o LM Studio retorna erro imediato ou silenciosamente usa outro modelo?

### Dados para investigar

- Arquivo: `src/pipeline/nl_to_sparql.py:__init__()`
- Testar: `LLM_TIMEOUT=abc python -c "from src.pipeline.nl_to_sparql import BioSPARQLPipeline; BioSPARQLPipeline()"`

### Status: ✅ Respondido — `try/except ValueError` adicionado em `nl_to_sparql.py:__init__()`. Em caso de valor inválido, fallback para 300s com `logger.warning`. `LLM_MODEL` inválido é passado ao LM Studio que retorna erro na primeira chamada ao backend (comportamento aceitável).

---

## Q-04 — Comportamento do FILTER-mover com subconsultas aninhadas (detalhe de implementação)

**Confiança:** 🟡 INFERIDO [atualizado pelo Reviewer em 2026-05-04]
**Origem:** Detetive + EC-02 + inspeção direta do código
**Risco:** 🟡 Médio (reduzido de Alto após inspeção)

### Contexto

A transform ⑦ em `_fix_common_errors()` usa **bracket counting** via variável `brace_depth` (linha 269 de `nl_to_sparql.py`):

```python
brace_depth += stripped.count("{") - stripped.count("}")
if brace_depth == 0 and stripped == "}":
    last_close_idx = i
```

Isso é mais robusto do que uma simples busca pelo último `}`. O `last_close_idx` é atualizado apenas quando `brace_depth` atinge 0 E a linha é exatamente `}`, garantindo que seja o fechamento externo do WHERE.

### Risco residual (🟡)

A condição `stripped == "}"` exige que o `}` de fechamento esteja **sozinho em sua linha**. Se o LLM gerar `} }` em uma única linha, a depth decrementaria corretamente mas o `last_close_idx` não seria atualizado. Além disso, queries com subconsultas do tipo `{ SELECT ... WHERE { FILTER ... } }` não foram testadas explicitamente.

### Status: 🟡 Parcialmente respondido — implementação usa depth counting (🟢), edge cases com multi-brace na mesma linha não testados (🟡)

---

## Resumo de Lacunas

| ID | Questão resumida | Risco | Status |
|---|---|---|---|
| Q-01 | Interações entre 9 transforms em queries com subconsultas | 🔴 Alto | Não respondido |
| Q-02 | Falsos positivos em modo permissivo (schemas.json ausente) | 🟡 Médio | Não respondido |
| Q-03 | Validação de env vars LLM_MODEL e LLM_TIMEOUT | 🟢 Baixo | Não respondido |
| Q-04 | Implementação exata do bracket counting na transform ⑦ | 🟡 Médio | Parcialmente respondido — usa brace_depth counting ✅ |

---

## Ação recomendada antes de reimplementar

1. **Q-01 e Q-04** (alto risco, mesmo tema): Ler `_fix_common_errors()` linha a linha e escrever ao menos 3 testes unitários com subconsultas aninhadas. Se a regex não usa bracket counting, reimplementar com um parser de profundidade simples.

2. **Q-02** (médio risco): Verificar `output/ablation_*.json` com configuração `no_schema`. Se disponível, comparar taxa de sucesso com e sem schema para determinar impacto real.

3. **Q-03** (baixo risco): Adicionar `try/except ValueError` ao redor do `float(os.environ.get("LLM_TIMEOUT", 300))` e testar `LLM_MODEL` inválido no LM Studio.
