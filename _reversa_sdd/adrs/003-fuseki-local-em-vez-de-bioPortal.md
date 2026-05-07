# ADR-003 — Apache Jena Fuseki local em vez de BioPortal SPARQL endpoint

> Data: 2026-05-04 (retroativo — inferido da estrutura do projeto)
> Status: **Aceito**
> Confiança: 🟡 INFERIDO — sem commit explícito, mas evidenciado pela presença de `tools/apache-jena-fuseki-6.0.0/` e ausência de qualquer referência a BioPortal no código atual

---

## Contexto

Para servir queries SPARQL sobre DOID, HPO e HPOA, duas opções foram consideradas:

- **BioPortal SPARQL endpoint** — serviço público gerenciado pela NCBO (National Center for Biomedical Ontology)
- **Apache Jena Fuseki local** — triplestore self-hosted com os arquivos OWL/Turtle carregados localmente

Mencionado no histórico de correções do `CLAUDE.md`: `"BioPortal SPARQL endpoint → Fuseki local"`.

## Decisão

Usar **Apache Jena Fuseki 6.0.0 local** com TDB2 persistente em `fuseki-db/`.

## Alternativas consideradas

| Alternativa | Resultado | Motivo da rejeição |
|---|---|---|
| BioPortal SPARQL endpoint | Descartado | Instabilidade, rate limits, latência variável, dependência de rede — incompatível com avaliação reprodutível de 30×N questões |
| Virtuoso OSS | Não tentado | Fuseki é mais simples de instalar e configurar para OWL |
| GraphDB Free | Não tentado | Mesmo motivo |
| Oxigraph (Rust) | Não tentado | Suporte a OWL menos maduro |

## Consequências

- Triplestore local garante latência constante e reprodutibilidade da avaliação
- `fuseki-db/` está no `.gitignore` — novos desenvolvedores precisam carregar as ontologias manualmente
- Java 21+ é uma dependência de sistema (não gerenciada pelo pip ou npm)
- Fuseki requer ~2GB de heap para as 3 ontologias (`-Xmx2G`)
- Porta 3030 deve estar disponível — conflito possível com outros serviços locais (🟡 INFERIDO)
