"""Hierarquia de exceções do BioSPARQL-NL."""


class BioSPARQLError(Exception):
    """Base exception para o projeto."""
    pass


class FusekiConnectionError(BioSPARQLError):
    """Fuseki offline ou timeout."""
    pass


class LLMConnectionError(BioSPARQLError):
    """Ollama/LLM offline ou timeout."""
    pass


class ValidationError(BioSPARQLError):
    """Query SPARQL inválida após validação."""
    pass


class SchemaLoadError(BioSPARQLError):
    """schemas.json ausente ou corrompido."""
    pass


class EntityLinkingError(BioSPARQLError):
    """Falha no módulo scispaCy/entity linking."""
    pass
