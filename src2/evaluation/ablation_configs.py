"""Configuracoes nomeadas para estudo de ablacao formal (revisao 2)."""

ABLATION_CONFIGS = {
    "full_pipeline": {},
    "no_ner": {"disable_ner": True},
    "no_fewshot": {"top_k_examples": 0},
    "no_schema": {"disable_schema": True},
    "no_validation": {"max_retries": 0},
    "zero_shot": {
        "disable_ner": True,
        "top_k_examples": 0,
        "disable_schema": True,
        "max_retries": 0,
    },
}

ABLATION_LABELS = {
    "full_pipeline": "Full Pipeline",
    "no_ner": "- NER",
    "no_fewshot": "- Few-shot",
    "no_schema": "- Schema",
    "no_validation": "- Validation",
    "zero_shot": "Zero-shot",
}
