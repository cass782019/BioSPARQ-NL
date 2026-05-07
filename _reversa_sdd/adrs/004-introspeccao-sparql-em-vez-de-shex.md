# ADR-004 — Introspecção SPARQL para extração de schema em vez de ShEx shapes

> Data: 2026-05-04 (retroativo — inferido do histórico de correções no CLAUDE.md)
> Status: **Aceito**
> Confiança: 🟡 INFERIDO — mencionado em `CLAUDE.md`: "ShEx shapes → Introspecção SPARQL com GROUP_CONCAT"

---

## Contexto

Para o `SchemaValidator` poder verificar se classes e predicados usados numa query existem nas ontologias, é necessário extrair o schema do triplestore. Duas abordagens foram consideradas:

- **ShEx (Shape Expressions)** — linguagem formal de shapes para grafos RDF
- **Introspecção SPARQL com GROUP_CONCAT** — queries que extraem classes e predicados diretamente via SPARQL

## Decisão

Usar **introspecção SPARQL** via `src/utils/schema_extractor.py`, que emite queries `GROUP_CONCAT` sobre cada grafo nomeado e persiste o resultado em `data/schemas.json`.

## Alternativas consideradas

| Alternativa | Resultado | Motivo da rejeição |
|---|---|---|
| ShEx shapes | Descartado | As ontologias DOID/HPO não distribuem shapes ShEx prontos; criar shapes manualmente seria trabalho significativo e frágil a atualizações |
| SHACL shapes | Não tentado | Mesmo problema que ShEx |
| Schema hardcoded | Descartado | Seria desatualizado a cada versão das ontologias |
| Introspecção SPARQL | ✅ Adotado | Automático, genérico, aproveita o Fuseki já disponível |

## Consequências

- `data/schemas.json` é gerado uma vez e reusado (pode ficar desatualizado se as ontologias forem atualizadas)
- Se o arquivo estiver ausente, `SchemaValidator` entra em modo permissivo — validação de termos é pulada (RN-06)
- Introspecção com `GROUP_CONCAT` em grafos grandes pode ser lenta — implementado com retry exponencial (3 tentativas, backoff 2^n)
- O schema extraído inclui apenas classes e predicados presentes nos dados — não inclui classes declaradas mas sem instâncias (🟡 INFERIDO — impacto em validação: false negatives possíveis)
