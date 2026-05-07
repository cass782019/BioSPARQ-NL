# User Stories — Fluxo: Consulta NL→SPARQL via Interface Web

> Gerado pelo Redator (Writer) em 2026-05-04 | doc_level: detalhado
> Ator principal: Pesquisador biomédico usando a interface XAI

---

## Contexto

O pesquisador acessa a SPA React em `http://localhost:5173`, digita perguntas em português sobre doenças e fenótipos, e recebe respostas com o SPARQL gerado, as entidades detectadas, a validação e os resultados do Fuseki — tudo num painel de explicabilidade lateral (XAI).

---

## US-01 — Consulta simples com resposta bem-sucedida

**Como** pesquisador biomédico,
**quero** digitar uma pergunta em português sobre doenças ou fenótipos,
**para** obter resultados precisos do triplestore sem precisar conhecer SPARQL.

### Critérios de Aceitação

```gherkin
Dado que o frontend está carregado em localhost:5173
E o backend FastAPI está rodando na porta 8000
E o Fuseki está rodando na porta 3030 com os grafos urn:doid, urn:hpo, urn:hpoa carregados
Quando o pesquisador digita "Quais doenças estão associadas ao fenótipo febre?" e pressiona Enter
Então a pergunta aparece no histórico de chat como mensagem do usuário
E o campo de entrada e o botão Enviar ficam desabilitados durante o processamento
E POST /api/ask é chamado com body {"question": "Quais doenças estão associadas ao fenótipo febre?"}
E quando a resposta chega, uma mensagem bot é adicionada com o texto da resposta
E o campo de entrada é reabilitado
E o painel XAI lateral é atualizado com os dados da resposta
```

**Rastreabilidade:** 🟢 `frontend/src/App.jsx:handleSend()`, `frontend/src/components/InputBar.jsx`

---

## US-02 — Visualização do painel XAI após consulta

**Como** pesquisador biomédico,
**quero** ver as entidades detectadas, a query SPARQL gerada e o status de validação após cada resposta,
**para** entender como o sistema chegou ao resultado e auditar a qualidade da inferência.

### Critérios de Aceitação

```gherkin
Dado que uma consulta foi submetida e o backend retornou resposta com sucesso
Quando o painel XAI lateral é exibido
Então as entidades detectadas pelo NER são exibidas como badges coloridos com seus CURIEs (ex: DOID:14330, HP:0001945)
E a query SPARQL gerada é exibida em bloco monospace com opção de cópia
E o status de validação é exibido (válido = indicador verde, inválido = indicador vermelho com lista de erros)
E os tempos de execução de cada fase são exibidos (NER, FAISS, LLM, validação, Fuseki, total)
E os resultados brutos do Fuseki são exibidos em tabela com cabeçalhos dinâmicos
```

```gherkin
Dado que ainda não foi feita nenhuma consulta (xai = null)
Quando o painel XAI é renderizado
Então é exibida a mensagem "Envie uma pergunta para ver os detalhes de explicabilidade (XAI)."
```

**Rastreabilidade:** 🟢 `frontend/src/components/XaiPanel.jsx`, `EntityBadges.jsx`, `SparqlBlock.jsx`, `ValidationStatus.jsx`, `TimingBar.jsx`, `ResultsTable.jsx`

---

## US-03 — Consulta com autocorreção visível

**Como** pesquisador biomédico,
**quero** ver quando o pipeline precisou corrigir a query automaticamente,
**para** entender o esforço de inferência e a confiança na resposta.

### Critérios de Aceitação

```gherkin
Dado que o LLM gerou uma query inválida na primeira tentativa
Quando o pipeline executa o loop de autocorreção e obtém sucesso em tentativa posterior
Então o campo xai.retries indica o número de tentativas realizadas (> 0)
E o painel XAI exibe a seção "Autocorreção" com o número de tentativas e o log de erros intermediários
E a resposta final no chat indica o resultado com sucesso
```

```gherkin
Dado que o pipeline esgotou todas as tentativas sem query válida
Quando a resposta chega ao frontend
Então o status de validação no XAI mostra inválido (indicador vermelho)
E a resposta no chat indica que o resultado pode ser incompleto
```

**Rastreabilidade:** 🟢 `src/pipeline/nl_to_sparql.py:run()` — campo `retries` na resposta; 🟢 `frontend/src/components/XaiPanel.jsx`

---

## US-04 — Colapsamento e expansão do painel XAI

**Como** pesquisador biomédico,
**quero** colapsar o painel XAI quando precisar de mais espaço para ler o chat,
**para** controlar o layout da interface conforme minha necessidade.

### Critérios de Aceitação

```gherkin
Dado que o painel XAI está expandido
Quando o pesquisador clica no botão "Recolher"
Então o conteúdo do painel é ocultado
E o botão passa a exibir "Expandir"
E o chat ocupa o espaço disponível
```

```gherkin
Dado que o painel XAI está colapsado
Quando o pesquisador clica em "Expandir"
Então o painel volta ao estado expandido com os dados da última consulta
```

**Rastreabilidade:** 🟢 `frontend/src/components/XaiPanel.jsx` — estado `collapsed`

---

## US-05 — Submissão múltipla (histórico de conversa)

**Como** pesquisador biomédico,
**quero** fazer múltiplas perguntas em sequência,
**para** explorar diferentes aspectos das ontologias numa sessão contínua.

### Critérios de Aceitação

```gherkin
Dado que uma consulta anterior já foi respondida
Quando o pesquisador digita uma nova pergunta e pressiona Enter
Então a nova pergunta é adicionada ao histórico abaixo das anteriores
E o painel XAI é atualizado com os dados da nova consulta (substituindo os dados anteriores)
E o pipeline processa cada pergunta de forma independente (stateless)
```

**Rastreabilidade:** 🟢 `frontend/src/App.jsx:messages[]` — array acumulativo; 🟢 `src/pipeline/nl_to_sparql.py:run()` — sem estado entre chamadas (RNF-04)

---

## US-06 — Tratamento de erro de rede ou backend indisponível

**Como** pesquisador biomédico,
**quero** receber uma mensagem clara quando o backend estiver indisponível,
**para** saber que devo verificar os serviços antes de tentar novamente.

### Critérios de Aceitação

```gherkin
Dado que o backend FastAPI não está rodando na porta 8000
Quando o pesquisador submete uma pergunta
Então uma mensagem de erro é adicionada ao histórico de chat (ex: "Erro: Network Error" ou "Erro: <detalhe HTTP>")
E loading é definido como false
E o campo de entrada é reabilitado para nova tentativa
```

**Rastreabilidade:** 🟢 `frontend/src/App.jsx:handleSend()` — bloco catch com setMessages + setLoading(false)

---

## US-07 — Consulta com query válida retornando 0 resultados (semantic retry transparente)

**Como** pesquisador biomédico,
**quero** que o sistema tente reformular a query automaticamente quando não encontrar resultados,
**para** maximizar as chances de obter resposta sem intervenção manual.

### Critérios de Aceitação

```gherkin
Dado que o LLM gerou uma query SPARQL sintáticamente válida
E o Fuseki retornou 0 resultados na primeira execução
E semantic_retry_used = False
Quando o pipeline detecta count == 0
Então o pipeline re-prompta o LLM com SEMANTIC_RETRY_FEEDBACK (sugestões de labels em inglês, conversão MIM→OMIM)
E semantic_retry_used é marcado como True (não repete)
E o resultado final na interface reflete a segunda tentativa
```

```gherkin
Dado que mesmo após o semantic retry o Fuseki retorna 0 resultados
Quando a resposta chega ao frontend
Então a mensagem no chat indica "0 resultados encontrados"
E o painel XAI mostra a query final e o status de validação
```

**Rastreabilidade:** 🟢 `src/pipeline/nl_to_sparql.py:run()` — flag `semantic_retry_used`, constante `SEMANTIC_RETRY_FEEDBACK`

---

## US-08 — Submissão de pergunta vazia ou inválida (guard)

**Como** pesquisador biomédico,
**quero** que a interface ignore cliques acidentais no botão Enviar sem texto,
**para** evitar requisições desnecessárias ao backend.

### Critérios de Aceitação

```gherkin
Dado que o campo de entrada está vazio ou contém apenas espaços
Quando o pesquisador pressiona Enter ou clica em Enviar
Então nenhuma requisição é enviada ao backend
E nenhuma mensagem é adicionada ao histórico
E o campo de entrada permanece focado e vazio
```

```gherkin
Dado que uma requisição já está em andamento (loading = true)
Quando o pesquisador tenta submeter outra pergunta
Então a submissão é ignorada silenciosamente
E a requisição em andamento continua sem interferência
```

**Rastreabilidade:** 🟢 `frontend/src/App.jsx:handleSend()` — guards `if (!text.trim()) return` e `if (loading) return`

---

## Fluxo de sucesso (cenário feliz completo)

```
Pesquisador → digita pergunta → pressiona Enter
  → loading=true (UI desabilitada)
  → POST /api/ask → FastAPI → BioSPARQLPipeline
    → NER detecta entidades (ex: "febre" → HP:0001945)
    → FAISS recupera 3 exemplos similares
    → LLM gera SPARQL
    → pós-processamento corrige prefixos
    → SchemaValidator valida
    → Fuseki executa query
    → retorna results_count ≥ 1
  → resposta JSON → frontend
  → mensagem bot adicionada ao chat
  → XaiPanel atualizado (entidades, SPARQL, validação, timing, resultados)
  → loading=false (UI reabilitada)
```

---

## Notas de confiança

| Afirmação | Confiança |
|---|---|
| Guard de submissão vazia e loading | 🟢 CONFIRMADO — código lido |
| Painel XAI com seções EntityBadges, SparqlBlock, ValidationStatus, TimingBar, ResultsTable | 🟢 CONFIRMADO — componentes existentes |
| Semantic retry transparente ao usuário (interno ao pipeline) | 🟢 CONFIRMADO — não exposto como evento separado no frontend |
| Layout duas colunas chat + XAI | 🟢 CONFIRMADO — `App.jsx:styles` |
| Sem autenticação | 🟢 CONFIRMADO — ausência de middleware auth |
