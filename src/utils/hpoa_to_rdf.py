"""Converte phenotype.hpoa (TSV) para Turtle RDF.

Gera triplas: <disease_uri> <has_phenotype> <hpo_uri>
Mantém source_id como valor textual para JOIN via oboInOwl:hasDbXref.
Trata IDs OMIM, ORPHA, DECIPHER.
"""
import logging
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS

logger = logging.getLogger(__name__)

HPOA = Namespace("http://example.org/hpoa/")


def convert_hpoa_to_rdf(input_tsv: str, output_ttl: str) -> int:
    g = Graph()
    g.bind("hpoa", HPOA)
    g.bind("rdfs", RDFS)

    has_phenotype = HPOA["has_phenotype"]

    count = 0
    skipped = 0
    total = 0

    with open(input_tsv, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("database_id"):
                continue
            total += 1
            try:
                parts = line.strip().split("\t")
                if len(parts) < 5:
                    skipped += 1
                    continue

                db_id = parts[0]  # "OMIM:154700", "ORPHA:558", "DECIPHER:1"
                disease_name = parts[1]
                qualifier = parts[2]
                hpo_id = parts[3]

                if qualifier == "NOT":
                    skipped += 1
                    continue

                # URI para fenótipo HPO (padrão OBO)
                hpo_uri = URIRef(
                    f"http://purl.obolibrary.org/obo/{hpo_id.replace(':', '_')}"
                )
                # URI para doença (namespace próprio, linkada via source_id)
                disease_uri = URIRef(
                    f"http://example.org/disease/{db_id.replace(':', '_')}"
                )

                g.add((disease_uri, RDF.type, HPOA["Disease"]))
                g.add((disease_uri, RDFS.label, Literal(disease_name)))
                g.add((disease_uri, has_phenotype, hpo_uri))
                g.add(
                    (disease_uri, HPOA["source_id"], Literal(db_id))
                )  # CHAVE: valor textual para JOIN
                count += 1
            except Exception as e:
                logger.warning(f"Linha ignorada: {e}")
                skipped += 1

    if total > 0 and skipped / total > 0.10:
        logger.warning(
            f"⚠️ {skipped}/{total} linhas ignoradas ({skipped / total:.1%})"
        )

    g.serialize(destination=output_ttl, format="turtle")
    print(f"✅ Convertidas {count} anotações → {output_ttl} ({skipped} ignoradas)")
    return count


if __name__ == "__main__":
    convert_hpoa_to_rdf("data/annotations/phenotype.hpoa", "data/annotations/hpoa.ttl")
