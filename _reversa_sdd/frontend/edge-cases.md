# Edge Cases — frontend

> Unit: `frontend/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## EC-01 — Duplo envio durante loading

**Origem:** `App.jsx:handleSend()` — guard `if (!text.trim() || loading) return`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O usuário clica em "Enviar" ou pressiona Enter enquanto uma requisição já está em andamento.

**Comportamento esperado:** A segunda submissão é ignorada silenciosamente. O campo e botão estão `disabled`, portanto o guard `loading=true` impede o disparo de um segundo `axios.post`.

**Risco:** Se por algum motivo o campo não estiver desabilitado (ex: CSS sobrescrito), o guard em `handleSend` ainda protege contra requisição dupla.

**Teste:**
```
Dado que loading=true
Quando handleSend('nova pergunta') é chamado diretamente
Então nenhuma chamada axios é feita
E o histórico de mensagens não muda
```

---

## EC-02 — Resposta do backend sem campo `answer`

**Origem:** `App.jsx:69` — `data.answer || data.natural_answer || 'Sem resposta.'`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O backend retorna JSON válido, mas sem o campo `answer` (ex: variação de API ou erro parcial).

**Comportamento esperado:** O frontend tenta `data.natural_answer` como fallback. Se ambos forem falsy, exibe a string literal `'Sem resposta.'` — nunca `undefined` ou crash.

**Risco:** Backend retornando `answer: null` (não `undefined`) → `null || data.natural_answer` continua funcionando. Backend retornando `answer: ""` (string vazia) → fallback para `natural_answer` ou `'Sem resposta.'` — pode suprimir resposta válida vazia.

---

## EC-03 — Backend offline ou timeout de rede

**Origem:** `App.jsx:75-79` — bloco `catch`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O Axios lança exceção de rede (ECONNREFUSED, timeout, etc.).

**Comportamento esperado:**
- `err.response` é `undefined` (não há resposta HTTP)
- O fallback `err.message` é usado: ex. `"Network Error"` ou `"timeout of 0ms exceeded"`
- Bubble bot exibe `"Erro: Network Error"` no histórico
- `loading` volta a `false`, interface fica responsiva

**Risco:** 🟡 Não há timeout explícito configurado no Axios — a requisição aguardará indefinidamente até que o navegador encerre (geralmente 2 minutos). Durante esse período, `loading=true` bloqueia novos envios.

---

## EC-04 — XaiPanel recebe campos com nomes alternativos

**Origem:** `XaiPanel.jsx:76-83` — resolução multi-chave
**Confiança:** 🟢 CONFIRMADO

**Situação:** O backend src2 (ClaudeCLI) pode retornar campos com nomes ligeiramente diferentes dos do backend src (LM Studio). Ex: `ner_entities` em vez de `entities`, `timings` em vez de `timing`.

**Comportamento esperado:** O XaiPanel usa cadeia de fallback (`||`/`??`) para cada campo. Se nenhuma variante estiver presente, o componente filho simplesmente não é renderizado (condição `entities.length > 0`).

**Risco:** 🟡 Se o backend adicionar um terceiro nome de campo não coberto pela cadeia, o dado será silenciosamente ignorado — não haverá erro, mas a seção correspondente ficará invisível.

---

## EC-05 — ResultsTable com resultado de coluna única ou resultado vazio após truncamento

**Origem:** `ResultsTable.jsx:54` — `Object.keys(results[0])`
**Confiança:** 🟢 CONFIRMADO

**Situação A:** Query SPARQL retorna `SELECT ?disease` — resultado com apenas uma coluna.
**Comportamento:** Tabela com um único cabeçalho `disease`. Funciona normalmente.

**Situação B:** `results = []` (zero resultados).
**Comportamento:** Exibe `"Sem resultados."` — `Object.keys` nunca é chamado.

**Situação C:** `results[0]` existe mas é `null` ou não é objeto.
**Comportamento:** 🔴 **LACUNA** — `Object.keys(null)` lança `TypeError`. Não há guard explícito além de `results.length === 0`. Se o Fuseki retornar uma lista com elemento nulo, o componente crashará.

---

## EC-06 — TimingBar com segmentos de tempo zero

**Origem:** `TimingBar.jsx:52` — `if (total === 0) return null`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O backend retorna `timing = { ner: 0, retrieval: 0, llm: 0 }` (ex: erro antes de qualquer fase executar).

**Comportamento esperado:** `total === 0` → componente retorna `null`. Nenhuma barra é exibida.

**Situação secundária:** Um segmento com < 1% do total (`pct < 1`) é omitido da barra visual, mas aparece na legenda com seu valor em segundos. Isso pode causar barra visual aparentemente incompleta (soma visual < 100%) enquanto a legenda mostra todos os valores.

---

## EC-07 — SparqlBlock com query muito longa

**Origem:** `SparqlBlock.jsx` — `wrapLongLines=true`
**Confiança:** 🟢 CONFIRMADO

**Situação:** Query SPARQL gerada tem cláusulas muito longas (ex: FILTER com muitas alternativas de OMIM IDs).

**Comportamento esperado:** `wrapLongLines=true` quebra linhas longas dentro do bloco. Sem scroll horizontal.

**Risco:** 🟡 Queries muito longas (> 50 linhas) podem estender o painel XAI verticalmente, empurrando outros componentes para baixo. O painel tem `overflowY: auto` — o scroll funciona, mas a experiência visual pode degradar.

---

## EC-08 — EntityBadges com entidade como string simples (não objeto)

**Origem:** `EntityBadges.jsx:43-44`
**Confiança:** 🟢 CONFIRMADO

**Situação:** O pipeline retorna `entities = ["DOID:14330", "HP:0001945"]` como lista de strings, não de objetos.

**Comportamento esperado:**
- `ent.uri` → `undefined` → `hasUri = false` → badge amarelo (unresolved)
- `ent.label` → `undefined` → `String(ent)` → `"DOID:14330"` exibido

**Observação:** 🟡 CURIEs como `DOID:14330` são entidades resolvidas semanticamente, mas aparecem como badge amarelo (unresolved) porque não possuem campo `uri`. O visual pode ser enganoso — o badge verde requer objeto com campo URI explícito.

---

## EC-09 — Botão de exemplo clicado com loading=true

**Origem:** `InputBar.jsx:87` — `disabled={loading}` nos botões de exemplo
**Confiança:** 🟢 CONFIRMADO

**Situação:** O usuário clica em um botão de exemplo enquanto `loading=true`.

**Comportamento esperado:** O botão está `disabled`, então o evento `onClick` não é disparado. A dupla proteção (`disabled` + guard em `handleSend`) garante que nenhum envio ocorra.

**Risco menor:** O handler do botão de exemplo chama `onSend(ex.text)` diretamente (sem passar pelo campo), pulando o guard de texto vazio. Se por algum motivo `ex.text` for vazio string, o guard `!text.trim()` em `handleSend` bloquearia. Mas `EXAMPLES` são constantes não-vazias — situação hipotética.

---

## EC-10 — Colapso do XaiPanel com nova pergunta enviada

**Origem:** `XaiPanel.jsx` — `collapsed` é estado local, `data` é prop
**Confiança:** 🟢 CONFIRMADO

**Situação:** O usuário recolhe o XaiPanel (`collapsed=true`) e então faz uma nova pergunta.

**Comportamento esperado:** O estado `collapsed` persiste entre atualizações de `data` — o painel continua colapsado mesmo com novos dados. O usuário precisa clicar em "Expandir" para ver as novas explicações.

**Risco:** 🟡 Comportamento pode ser inesperado — o usuário faz uma pergunta e não percebe que os novos dados XAI chegaram porque o painel está colapsado. Não há reset automático de `collapsed` ao receber novos dados.
