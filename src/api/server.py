"""FastAPI backend for the BioSPARQL-NL chat interface."""

import os
import time
import logging
from typing import Any

os.environ["HF_HUB_DISABLE_XET"] = "1"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.pipeline.nl_to_sparql import BioSPARQLPipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


class ExampleUsed(BaseModel):
    id: str
    difficulty: str
    question_en: str


class ValidationInfo(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class TimingInfo(BaseModel):
    ner_s: float
    retrieval_s: float
    llm_s: float
    total_s: float


class ExplainabilityInfo(BaseModel):
    entities: list[str]
    examples_used: list[ExampleUsed]
    sparql: str
    validation: ValidationInfo
    attempts: int
    results_raw: list[Any]
    results_count: int
    timing: TimingInfo


class AskResponse(BaseModel):
    answer: str
    success: bool
    xai: ExplainabilityInfo


class HealthResponse(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="BioSPARQL-NL", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline: BioSPARQLPipeline | None = None


def get_pipeline() -> BioSPARQLPipeline:
    """Lazy-init the pipeline singleton."""
    global pipeline
    if pipeline is None:
        pipeline = BioSPARQLPipeline()
    return pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_answer(result: dict) -> str:
    """Build a human-readable NL answer from pipeline result."""
    execution = result.get("execution", {})

    if not result.get("success"):
        error = execution.get("error", "Pipeline execution failed")
        return f"Erro: {error}"

    bindings = execution.get("results", [])
    count = execution.get("count", 0)

    if count == 0:
        return "Nenhum resultado encontrado."

    # Flatten each binding row into a readable string
    items: list[str] = []
    for row in bindings:
        parts = []
        for var, val in row.items():
            parts.append(val.get("value", str(val)))
        items.append(" | ".join(parts))

    if count == 1:
        return f"Resultado: {items[0]}"

    formatted = "\n".join(f"- {item}" for item in items)
    return f"Encontrados {count} resultados:\n{formatted}"


def _extract_entities(pipe: BioSPARQLPipeline, question: str) -> tuple[list[str], float]:
    """Run NER and return (entity_labels, elapsed_seconds)."""
    t0 = time.perf_counter()
    entities: list[str] = []
    if pipe.entity_linker:
        try:
            raw = pipe.entity_linker.extract_entities(question)
            for ent in raw:
                label = ent.get("label") or ent.get("text", str(ent))
                entities.append(label)
        except Exception:
            logger.exception("Entity extraction failed")
    elapsed = time.perf_counter() - t0
    return entities, elapsed


def _retrieve_examples(pipe: BioSPARQLPipeline, question: str) -> tuple[list[dict], float]:
    """Retrieve similar examples and return (examples, elapsed_seconds)."""
    t0 = time.perf_counter()
    examples = pipe.retrieve_examples(question)
    elapsed = time.perf_counter() - t0
    return examples, elapsed


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty question")

    pipe = get_pipeline()

    # -- NER stage --
    entities, ner_s = _extract_entities(pipe, question)

    # -- Retrieval stage --
    examples, retrieval_s = _retrieve_examples(pipe, question)

    # -- Pipeline (LLM + validation + execution) --
    t_llm_start = time.perf_counter()
    try:
        result = pipe.run(question)
    except Exception as exc:
        logger.exception("Pipeline error")
        llm_s = time.perf_counter() - t_llm_start
        total_s = ner_s + retrieval_s + llm_s
        return AskResponse(
            answer=f"Erro: {exc}",
            success=False,
            xai=ExplainabilityInfo(
                entities=entities,
                examples_used=[],
                sparql="",
                validation=ValidationInfo(valid=False, errors=[str(exc)], warnings=[]),
                attempts=0,
                results_raw=[],
                results_count=0,
                timing=TimingInfo(ner_s=ner_s, retrieval_s=retrieval_s, llm_s=llm_s, total_s=total_s),
            ),
        )
    llm_s = time.perf_counter() - t_llm_start
    total_s = ner_s + retrieval_s + llm_s

    # -- Build response --
    answer = _format_answer(result)

    validation_raw = result.get("validation", {})
    validation = ValidationInfo(
        valid=validation_raw.get("valid", False),
        errors=validation_raw.get("errors", []),
        warnings=validation_raw.get("warnings", []),
    )

    examples_used = []
    for ex in examples:
        examples_used.append(ExampleUsed(
            id=ex.get("id", ""),
            difficulty=ex.get("difficulty", ""),
            question_en=ex.get("question_en", ""),
        ))

    execution = result.get("execution", {})
    results_raw = execution.get("results", [])
    results_count = execution.get("count", 0)

    xai = ExplainabilityInfo(
        entities=entities,
        examples_used=examples_used,
        sparql=result.get("sparql", ""),
        validation=validation,
        attempts=result.get("attempts", 0),
        results_raw=results_raw,
        results_count=results_count,
        timing=TimingInfo(
            ner_s=round(ner_s, 4),
            retrieval_s=round(retrieval_s, 4),
            llm_s=round(llm_s, 4),
            total_s=round(total_s, 4),
        ),
    )

    return AskResponse(answer=answer, success=result.get("success", False), xai=xai)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
