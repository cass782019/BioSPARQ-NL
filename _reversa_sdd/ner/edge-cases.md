# Edge Cases — ner

> Unit: `src/pipeline/ner/` | Gerado pelo Redator em 2026-05-04 | doc_level: detalhado

---

## EC-01 — Entidade biomédica presente na stoplist (falso negativo)

**Confiança:** 🟡 INFERIDO
**Risco:** 🟡 Médio

### Descrição

A stoplist de ~80 termos pode inadvertidamente incluir termos que também são nomes de entidades biomédicas válidas. Exemplo hipotético: se "fever" estiver na stoplist (como termo genérico), a entidade "Yellow Fever" seria descartada mesmo sendo uma doença específica.

### Tratamento atual

Não há tratamento — a stoplist é verificada apenas contra `text.lower()` (match exato no span completo). "Yellow Fever" ≠ "fever", então o exemplo acima não ocorre. O risco real é com spans de uma palavra que coincidam com termos da stoplist.

### Mitigação

Revisar a stoplist periodicamente e garantir que nomes de doenças monossilábicas ou curtas não estejam incluídos. Usar match exato (não substring) — já é o comportamento atual.

---

## EC-02 — Dois modelos spaCy identificam spans diferentes para o mesmo texto

**Confiança:** 🟡 INFERIDO
**Risco:** 🟢 Baixo

### Descrição

O modelo `en_ner_bc5cdr_md` é treinado no corpus BC5CDR (chemicals e diseases). Fenótipos (HP terms) são frequentemente subidentificados porque o modelo não foi treinado nessa categoria explicitamente. Exemplo: "episodic ataxia" pode não ser detectado como entidade.

### Tratamento atual

`_gilda_lookup()` como fallback de resolução não ajuda aqui — o problema está na **detecção** de spans, não na resolução. Se spaCy não detecta o span, ele nunca chega ao Gilda.

### Impacto medido

Afeta principalmente questões sobre fenótipos raros (HP terms específicos). Questões de dificuldade "hard" no gold standard são mais afetadas.

### Mitigação possível (não implementada)

Usar `LLMBackend` como fallback quando `ScispaCyBackend` retorna lista vazia. 🔴 **Não implementado.**

---

## EC-03 — Resolução SPARQL retorna múltiplos URIs para o mesmo label

**Confiança:** 🟡 INFERIDO
**Risco:** 🟡 Médio

### Descrição

Alguns labels são ambíguos entre DOID e HPO. Exemplo: "Epilepsy" pode existir como `DOID:*` (doença) e `HP:*` (fenótipo). A query usa `LIMIT 1` — o resultado depende da ordem de retorno do Fuseki (não determinística).

### Tratamento atual

`LIMIT 1` retorna arbitrariamente um dos dois. O `build_prompt()` inclui o CURIE no contexto, mas o LLM decide qual grafo usar na query.

### Impacto

🟡 Médio — em queries que precisam de doença (`urn:doid`) mas recebem fenótipo (`urn:hpo`) ou vice-versa, o LLM pode usar o grafo errado. O semantic retry pode corrigir em alguns casos.

### Mitigação

Priorizar resultado de `urn:doid` para entidades classificadas como `DISEASE` e `urn:hpo` para `PHENOTYPE` na query SPARQL de resolução. 🟡 **Inferido como possível melhoria.**

---

## EC-04 — Gilda não disponível (import error)

**Confiança:** 🟡 INFERIDO
**Risco:** 🟢 Baixo

### Descrição

Se o pacote `gilda` não estiver instalado, `import gilda` em `_gilda_lookup()` lança `ModuleNotFoundError`. Isso ocorre dentro do fallback — o código principal já passou pela tentativa SPARQL.

### Tratamento atual

Não há tratamento explícito de `ImportError` em torno do import Gilda. Se Gilda não estiver instalado, `_gilda_lookup()` lança exceção não capturada, que pode propagar até `extract()` e interromper o NER.

### Mitigação recomendada

```python
def _gilda_lookup(self, text: str) -> dict | None:
    try:
        import gilda
    except ImportError:
        return None   # Gilda não instalado, fallback silencioso
    ...
```

---

## EC-05 — Fuseki offline durante resolução NER (não durante execução da query principal)

**Confiança:** 🟢 CONFIRMADO
**Risco:** 🟢 Baixo

### Descrição

O `_sparql_lookup()` usa o Fuseki para resolver entidades. Se o Fuseki cair **durante** uma requisição ativa (após inicialização do pipeline), a resolução falha após 3 retries e retorna `None`. O Gilda é acionado como fallback.

### Tratamento atual

Retry exponencial (3 tentativas) + fallback para Gilda. Se ambos falham, `ontology_ids=[]` para a entidade — o pipeline continua sem IDs de ancoragem.

### Impacto

O LLM recebe o prompt sem CURIEs de ancoragem. Pode gerar query mais genérica mas ainda funcional.

---

## EC-06 — LLMBackend retorna JSON inválido

**Confiança:** 🟡 INFERIDO
**Risco:** 🟡 Médio

### Descrição

Mesmo com `response_format={"type": "json_object"}`, modelos menores (Gemma 4B) podem retornar JSON malformado ou com estrutura diferente da esperada (ex: `{"result": [...]}` em vez de `{"entities": [...]}`).

### Tratamento atual

`json.loads()` lança `JSONDecodeError` se o JSON for inválido. `data.get("entities", [])` retorna `[]` se a chave `entities` estiver ausente.

### Comportamento resultante

`LLMBackend.extract()` retorna `[]` — pipeline continua sem entidades. Não lança exceção.

### Mitigação recomendada

Adicionar `try/except JSONDecodeError` em torno do `json.loads()` para capturar JSON totalmente inválido e retornar `[]` em vez de propagar a exceção.
