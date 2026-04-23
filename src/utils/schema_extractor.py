"""
schema_extractor.py

Extracts schema information (classes, predicates, domains/ranges) from a
SPARQL endpoint via introspective queries. Queries 3 named graphs:
urn:doid, urn:hpo, urn:hpoa.
"""

import json
import logging
import os
import time
from pathlib import Path

from SPARQLWrapper import SPARQLWrapper, JSON

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

DEFAULT_ENDPOINT = "http://localhost:3030/biomedical/sparql"
GRAPHS = ["urn:doid", "urn:hpo", "urn:hpoa"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_PATH = PROJECT_ROOT / "data" / "schemas.json"

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


def _query_with_retry(sparql: SPARQLWrapper, retries: int = MAX_RETRIES):
    """Execute a SPARQL query with exponential-backoff retry on connection errors."""
    for attempt in range(1, retries + 1):
        try:
            return sparql.query().convert()
        except Exception as exc:
            wait = BACKOFF_BASE ** attempt
            logger.warning(
                "SPARQL query failed (attempt %d/%d): %s — retrying in %ds",
                attempt,
                retries,
                exc,
                wait,
            )
            if attempt == retries:
                raise
            time.sleep(wait)


def extract_class_schema(endpoint_url: str, graph_uri: str) -> dict:
    """
    Extract classes and predicates from a single named graph.

    Returns:
        {
            'classes': [{'uri': ..., 'label': ..., 'count': ...}, ...],
            'predicates': [{'uri': ..., 'domains': [...], 'ranges': [...], 'count': ...}, ...]
        }
    """
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setTimeout(30)
    sparql.setReturnFormat(JSON)

    # --- Extract classes ---------------------------------------------------
    class_query = f"""
    SELECT ?class (COUNT(?s) AS ?count) (SAMPLE(?label) AS ?classLabel)
    WHERE {{
        GRAPH <{graph_uri}> {{
            ?s a ?class .
            OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
        }}
    }}
    GROUP BY ?class
    ORDER BY DESC(?count)
    LIMIT 100
    """
    sparql.setQuery(class_query)
    logger.info("Querying classes for graph <%s> ...", graph_uri)
    results = _query_with_retry(sparql)

    classes = []
    for row in results["results"]["bindings"]:
        classes.append(
            {
                "uri": row["class"]["value"],
                "label": row.get("classLabel", {}).get("value", ""),
                "count": int(row["count"]["value"]),
            }
        )

    # --- Extract predicates ------------------------------------------------
    predicate_query = f"""
    SELECT ?predicate
           (COUNT(*) AS ?count)
           (GROUP_CONCAT(DISTINCT ?sType; separator=',') AS ?domains)
           (GROUP_CONCAT(DISTINCT ?oType; separator=',') AS ?ranges)
    WHERE {{
        GRAPH <{graph_uri}> {{
            ?s ?predicate ?o .
            OPTIONAL {{ ?s a ?sType }}
            OPTIONAL {{ ?o a ?oType }}
            FILTER(?predicate != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
        }}
    }}
    GROUP BY ?predicate
    ORDER BY DESC(?count)
    LIMIT 100
    """
    sparql.setQuery(predicate_query)
    logger.info("Querying predicates for graph <%s> ...", graph_uri)
    results = _query_with_retry(sparql)

    predicates = []
    for row in results["results"]["bindings"]:
        domains_raw = row.get("domains", {}).get("value", "")
        ranges_raw = row.get("ranges", {}).get("value", "")
        predicates.append(
            {
                "uri": row["predicate"]["value"],
                "count": int(row["count"]["value"]),
                "domains": [d for d in domains_raw.split(",") if d],
                "ranges": [r for r in ranges_raw.split(",") if r],
            }
        )

    logger.info(
        "Graph <%s>: %d classes, %d predicates extracted.",
        graph_uri,
        len(classes),
        len(predicates),
    )
    return {"classes": classes, "predicates": predicates}


def extract_all_schemas(
    endpoint_url: str = DEFAULT_ENDPOINT,
    graphs: list = None,
    output_path: Path = SCHEMAS_PATH,
) -> dict:
    """
    Iterate over the configured named graphs, extract schemas, and save to
    data/schemas.json.  If the Fuseki endpoint is offline, try to return
    cached data from the existing schemas.json file.

    Returns:
        dict mapping graph URIs to their schema dicts.
    """
    if graphs is None:
        graphs = GRAPHS

    all_schemas: dict = {}

    try:
        for graph_uri in graphs:
            schema = extract_class_schema(endpoint_url, graph_uri)
            all_schemas[graph_uri] = schema
    except Exception as exc:
        logger.error("Failed to extract schemas from endpoint: %s", exc)
        if output_path.exists():
            logger.warning(
                "Fuseki appears offline. Loading cached schemas from %s",
                output_path,
            )
            with open(output_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        else:
            logger.error("No cached schemas.json found. Cannot proceed.")
            raise

    # Persist to disk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(all_schemas, fh, indent=2, ensure_ascii=False)
    logger.info("Schemas saved to %s", output_path)

    return all_schemas


if __name__ == "__main__":
    schemas = extract_all_schemas()
    for graph, info in schemas.items():
        print(
            f"  {graph}: {len(info['classes'])} classes, "
            f"{len(info['predicates'])} predicates"
        )
