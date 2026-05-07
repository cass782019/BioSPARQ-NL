# Requisitos — frontend

> Unit: `frontend/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## Identificação

| Campo | Valor |
|---|---|
| Módulo | `frontend` |
| Caminho legado | `frontend/src/` |
| Responsabilidade | Interface XAI (Explainability AI) — React SPA para consulta em linguagem natural e visualização de evidências do pipeline NL→SPARQL |
| Complexidade | 🟢 Baixa–Média |

---

## Requisitos Funcionais

### RF-01 — Campo de entrada e envio de perguntas
🟢 **CONFIRMADO** — `App.jsx:handleSend()`, `InputBar.jsx`

**Must**

O usuário deve poder digitar uma pergunta em linguagem natural e enviá-la ao backend via `POST /api/ask`. O envio é acionado pelo botão "Enviar" ou pela tecla Enter. Durante o processamento, o campo e o botão devem ficar desabilitados.

**Critérios de Aceitação:**

```gherkin
Dado que a aplicação está carregada e não há requisição em andamento
Quando o usuário digita "Quais doenças causam febre?" e pressiona Enter
Então a mensagem aparece no histórico como mensagem do usuário
E o campo de entrada e botão ficam desabilitados (loading=true)
E POST /api/ask é enviado com body {"question": "Quais doenças causam febre?"}
```

```gherkin
Dado que loading=true (requisição em andamento)
Quando o usuário tenta submeter outra pergunta
Então a submissão é ignorada silenciosamente (guard: if loading return)
```

```gherkin
Dado que o campo de entrada está vazio ou contém apenas espaços
Quando o usuário pressiona Enter ou clica em Enviar
Então a submissão é ignorada (guard: if !text.trim() return)
```

---

### RF-02 — Exibição do histórico de mensagens (ChatPanel)
🟢 **CONFIRMADO** — `ChatPanel.jsx`, `App.jsx:messages[]`

**Must**

O histórico de mensagens deve exibir alternadamente mensagens do usuário e do bot. A resposta do bot é o campo `answer` (ou `natural_answer` como fallback) da `AskResponse`. Em caso de erro de rede ou HTTP, uma mensagem de erro é adicionada ao histórico.

**Critérios de Aceitação:**

```gherkin
Dado que o backend retornou AskResponse com answer="Encontrados 3 resultado(s):"
Quando a resposta chega ao frontend
Então uma mensagem bot é adicionada ao histórico com o texto da answer
E loading é definido como false
```

```gherkin
Dado que a chamada POST /api/ask falhou com erro HTTP 500
Quando o erro é capturado no catch
Então uma mensagem bot é adicionada com texto "Erro: <detail ou mensagem>"
E loading é definido como false
```

---

### RF-03 — Painel de explicabilidade XAI (XaiPanel)
🟢 **CONFIRMADO** — `XaiPanel.jsx`, `App.jsx:xai state`

**Must**

Após cada resposta do backend, o painel lateral direito deve exibir os dados de explicabilidade da `AskResponse`: entidades detectadas, exemplos few-shot, SPARQL gerado, status de validação, log de autocorreção, resultados brutos e tempos de execução. O painel deve ser colapsável via botão "Recolher/Expandir".

**Critérios de Aceitação:**

```gherkin
Dado que nenhuma pergunta foi feita ainda (xai=null)
Quando o XaiPanel é renderizado
Então é exibida a mensagem "Envie uma pergunta para ver os detalhes de explicabilidade (XAI)."
```

```gherkin
Dado que xai contém dados válidos da última resposta
Quando o XaiPanel é renderizado
Então EntityBadges exibe as entidades se entities.length > 0
E SparqlBlock exibe a query SPARQL se sparql não for vazio
E ValidationStatus exibe o resultado de validação
E TimingBar exibe os tempos de execução
E ResultsTable exibe os resultados brutos se results.length > 0
```

```gherkin
Dado que xai.retries > 0
Quando o XaiPanel é renderizado
Então a seção "Autocorreção" exibe o número de tentativas e o log de erros
```

```gherkin
Dado que o painel está expandido
Quando o usuário clica em "Recolher"
Então o conteúdo do painel é ocultado (collapsed=true)
E o botão passa a exibir "Expandir"
```

---

### RF-04 — Exibição de entidades NER (EntityBadges)
🟢 **CONFIRMADO** — `EntityBadges.jsx`

**Should**

Cada entidade detectada pelo NER deve ser exibida como um badge colorido com o CURIE (ex.: `DOID:14330`) ou texto da entidade.

**Critérios de Aceitação:**

```gherkin
Dado que entities = ["DOID:14330", "HP:0001945"]
Quando EntityBadges é renderizado
Então dois badges são exibidos com os respectivos CURIEs
```

---

### RF-05 — Exibição de SPARQL com syntax highlighting (SparqlBlock)
🟢 **CONFIRMADO** — `SparqlBlock.jsx`

**Should**

A query SPARQL gerada deve ser exibida em bloco de código com formatação monospace. O usuário deve poder copiar a query.

**Critérios de Aceitação:**

```gherkin
Dado que sparql contém uma query válida
Quando SparqlBlock é renderizado
Então a query é exibida em fonte monospace
E um mecanismo de cópia está disponível (botão ou seleção de texto)
```

---

### RF-06 — Exibição de status de validação (ValidationStatus)
🟢 **CONFIRMADO** — `ValidationStatus.jsx`

**Should**

O resultado da validação SPARQL (válido/inválido, erros, avisos) deve ser exibido de forma visual (ícone + texto).

**Critérios de Aceitação:**

```gherkin
Dado que validation.valid = true e warnings = []
Quando ValidationStatus é renderizado
Então um indicador verde de "Válido" é exibido
```

```gherkin
Dado que validation.valid = false com errors = ["FILTER fora de WHERE"]
Quando ValidationStatus é renderizado
Então um indicador vermelho é exibido com a lista de erros
```

---

### RF-07 — Exibição de tempos de execução (TimingBar)
🟢 **CONFIRMADO** — `TimingBar.jsx`

**Could**

Os tempos de execução das fases do pipeline (NER, FAISS, LLM, validação, Fuseki, total) devem ser exibidos em formato legível (ms).

---

### RF-08 — Exibição de resultados em tabela (ResultsTable)
🟢 **CONFIRMADO** — `ResultsTable.jsx`

**Should**

Os resultados brutos retornados pelo Fuseki devem ser exibidos em formato tabular, com cabeçalhos dinâmicos derivados das variáveis SPARQL.

---

## Requisitos Não Funcionais

### RNF-01 — Proxy Vite para `/api/*`
🟢 **CONFIRMADO** — `frontend/vite.config.js`

Todas as requisições `/api/*` do frontend devem ser proxiadas para `http://localhost:8000` pelo servidor de desenvolvimento Vite. Não há chamadas CORS diretas em desenvolvimento.

### RNF-02 — Layout responsivo de duas colunas
🟢 **CONFIRMADO** — `App.jsx:styles`

O layout deve dividir a tela em área de chat (flex:1) e painel XAI (largura fixa 420px, mínimo 320px). Não há suporte explícito a mobile (uso acadêmico/desktop).

### RNF-03 — Estado gerenciado exclusivamente no App root
🟢 **CONFIRMADO** — `App.jsx`

Os estados `messages`, `xai` e `loading` vivem exclusivamente em `App`. Componentes filhos recebem dados via props e emitem eventos via callbacks — sem estado local crítico exceto o `collapsed` do `XaiPanel`.

### RNF-04 — Sem autenticação
🟢 **CONFIRMADO** — ausência de qualquer middleware auth no código

O frontend não implementa autenticação. Destina-se a uso local em ambiente controlado.

---

## MoSCoW

| Requisito | Prioridade | Justificativa |
|---|---|---|
| RF-01 Entrada de perguntas | **Must** | Ponto de entrada principal do sistema |
| RF-02 Histórico de mensagens | **Must** | Feedback imediato ao usuário |
| RF-03 Painel XAI | **Must** | Razão de ser do frontend — demonstra explicabilidade |
| RF-04 EntityBadges | **Should** | Importante para XAI, mas não bloqueia uso |
| RF-05 SparqlBlock | **Should** | Visibilidade da query gerada |
| RF-06 ValidationStatus | **Should** | Transparência sobre qualidade da query |
| RF-07 TimingBar | **Could** | Útil para benchmarking, não crítico |
| RF-08 ResultsTable | **Should** | Exibe resultados sem necessidade de acesso ao Fuseki |

---

## Dependências

| Dependência | Tipo | Obrigatória |
|---|---|---|
| React 18.3.1 | Framework UI | Sim |
| Vite 5.4.0 | Build tool / dev server | Sim |
| axios | Cliente HTTP | Sim |
| `POST /api/ask` (módulo api) | Serviço externo local | Sim |
| FastAPI backend na porta 8000 | Serviço externo local | Sim |
