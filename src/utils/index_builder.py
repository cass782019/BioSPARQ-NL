"""Gera embeddings das perguntas do gold standard e indexa com FAISS."""
import json
import logging
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def build_index(
    questions_path: str = "data/gold_standard/questions.json",
    index_path: str = "data/gold_standard/questions.index",
    model_name: str = "all-MiniLM-L6-v2",
) -> faiss.Index:
    with open(questions_path, encoding="utf-8") as f:
        questions = json.load(f)

    if not questions:
        raise ValueError(
            "Gold standard vazio. Execute gold_standard.py primeiro."
        )

    model = SentenceTransformer(model_name)

    # Gerar embeddings das perguntas (EN para melhor matching)
    texts = [q["question_en"] for q in questions]
    embeddings = model.encode(texts, normalize_embeddings=True)

    # Criar índice FAISS (Inner Product = cosine com vetores normalizados)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))

    faiss.write_index(index, index_path)
    print(f"✅ Índice FAISS criado: {len(texts)} vetores, dimensão {dim}")
    print(f"   Salvo em {index_path}")
    return index


if __name__ == "__main__":
    build_index()
