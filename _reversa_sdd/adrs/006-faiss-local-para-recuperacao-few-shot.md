# ADR-006 — FAISS local para recuperação few-shot em vez de serviço externo

> Data: 2026-05-04 (retroativo — inferido da estrutura do projeto)
> Status: **Aceito**
> Confiança: 🟡 INFERIDO — sem commit explícito, mas evidenciado pela escolha de `faiss.IndexFlatIP` + `SentenceTransformer("all-MiniLM-L6-v2")` com índice persistido em `data/gold_standard/questions.index`

---

## Contexto

O pipeline usa recuperação de exemplos similares (few-shot RAG) para incluir no prompt do LLM queries SPARQL análogas à pergunta do usuário. As opções consideradas para a camada de recuperação foram:

- **FAISS local** — biblioteca de busca por similaridade em CPU/GPU (Meta)
- **ChromaDB** — banco de vetores com servidor embutido
- **Pinecone / Weaviate** — serviços cloud de vetores

## Decisão

Usar **FAISS com IndexFlatIP** (Inner Product, equivalente a cosine com vetores normalizados) e embeddings gerados por `SentenceTransformer("all-MiniLM-L6-v2")` (384 dimensões). Índice persistido em `data/gold_standard/questions.index`.

## Alternativas consideradas

| Alternativa | Resultado | Motivo da rejeição |
|---|---|---|
| ChromaDB | Não tentado | Overhead de servidor, mais complexo para 30 exemplos |
| Pinecone / Weaviate cloud | Não tentado | Dependência de rede, custo, incompatível com avaliação offline |
| BM25 (busca lexical) | Não tentado | Pior para similaridade semântica entre perguntas biomédicas |
| **FAISS local** | ✅ Adotado | Zero dependência de rede, CPU-only, rápido para 30 exemplos, graceful fallback se ausente |

## Consequências

- `data/gold_standard/questions.index` deve ser gerado antes do primeiro uso via `index_builder.py`
- Embedder `SentenceTransformer` é lazy-loaded — primeiro acesso tem latência de ~2-5s de carregamento de modelo
- Se o índice estiver ausente, pipeline cai em zero-shot automaticamente (graceful fallback — RN confirmada)
- Corpus fixo de 30 exemplos — não cresce dinamicamente com novas perguntas
- `IndexFlatIP` é busca exata (não aproximada) — adequado para corpus pequeno; para >100K exemplos, seria necessário `IndexIVFFlat` (🟡 INFERIDO — melhoria futura documentada implicitamente)
- Modelo `all-MiniLM-L6-v2` é genérico — não especializado em texto biomédico (🟡 INFERIDO — possível melhoria com `BioLinkBERT` ou similar)
