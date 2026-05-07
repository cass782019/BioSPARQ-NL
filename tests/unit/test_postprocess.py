"""Unit tests for SPARQL post-processing transforms in BioSPARQLPipeline."""

from src.pipeline.nl_to_sparql import BioSPARQLPipeline


def _fix(q: str) -> str:
    return BioSPARQLPipeline._fix_common_errors(q)


def test_transform7_only():
    """FILTER orfão após o } de fechamento do WHERE deve ser movido para dentro.
    Requer } em linha própria — padrão gerado pelo Nemotron."""
    q = "SELECT ?x WHERE {\n  ?x a obo:DOID_4 .\n}\nFILTER(?x != <bad>)"
    out = _fix(q)
    assert "FILTER" in out
    assert out.index("FILTER") < out.rindex("}")


def test_transform8_only():
    """BIND com auto-referência deve renomear ?x para ?x_mim antes do BIND."""
    q = (
        "SELECT ?x WHERE {\n"
        "  ?x <p> ?val .\n"
        "  BIND(REPLACE(STR(?x), 'MIM:', 'OMIM:') AS ?x)\n"
        "}"
    )
    out = _fix(q)
    assert "?x_mim" in out
    assert "BIND(REPLACE(STR(?x_mim)" in out


def test_transforms_7_and_8_combined():
    """Query com FILTER orfão + BIND circular — ambas as transforms devem aplicar corretamente."""
    q = (
        "SELECT ?x WHERE {\n"
        "  ?x <p> ?val .\n"
        "  BIND(REPLACE(STR(?x), 'MIM:', 'OMIM:') AS ?x)\n"
        "}\n"
        "FILTER(?x != <bad>)"
    )
    out = _fix(q)
    # transform ⑦: FILTER deve estar dentro do WHERE
    assert out.index("FILTER") < out.rindex("}")
    # transform ⑧: auto-referência deve ter sido corrigida
    assert "?x_mim" in out
