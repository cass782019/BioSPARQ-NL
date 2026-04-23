"""GATE 1 - Validacao dos Dados Carregados no Fuseki."""
import sys
from SPARQLWrapper import SPARQLWrapper, JSON

ENDPOINT = "http://localhost:3030/biomedical/sparql"
sparql = SPARQLWrapper(ENDPOINT)
sparql.setReturnFormat(JSON)

checks = []

# 1a. Contagem de triplas por grafo
sparql.setQuery("""
SELECT ?g (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s ?p ?o } } GROUP BY ?g
""")
try:
    results = sparql.query().convert()["results"]["bindings"]
    counts = {r["g"]["value"]: int(r["c"]["value"]) for r in results}

    for graph, min_count in [("urn:doid", 150000), ("urn:hpo", 400000), ("urn:hpoa", 50000)]:
        actual = counts.get(graph, 0)
        ok = actual >= min_count
        checks.append((f"{graph} triplas", ok, f"{actual:,} (min: {min_count:,})"))
except Exception as e:
    checks.append(("Fuseki conexao", False, str(e)))

# 1b. Query Marfan (cross-graph HPOA<>HPO)
sparql.setQuery("""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id "OMIM:154700" ;
             hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
} LIMIT 20
""")
try:
    results = sparql.query().convert()["results"]["bindings"]
    n = len(results)
    checks.append(("Marfan phenotypes", n >= 5, f"{n} resultados (min: 5)"))
except Exception as e:
    checks.append(("Marfan phenotypes", False, str(e)))

# 1c. Contar doencas DOID
sparql.setQuery("""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(DISTINCT ?d) AS ?total) WHERE {
  GRAPH <urn:doid> { ?d rdfs:subClassOf+ obo:DOID_4 . }
}
""")
try:
    results = sparql.query().convert()["results"]["bindings"]
    n = int(results[0]["total"]["value"])
    checks.append(("DOID diseases", n >= 8000, f"{n:,} (min: 8,000)"))
except Exception as e:
    checks.append(("DOID diseases", False, str(e)))

# 1d. Cross-reference hasDbXref funciona
sparql.setQuery("""
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
SELECT (COUNT(*) AS ?c) WHERE {
  GRAPH <urn:doid> {
    ?d oboInOwl:hasDbXref ?xref .
    FILTER(STRSTARTS(STR(?xref), "MIM:") || STRSTARTS(STR(?xref), "OMIM:"))
  }
}
""")
try:
    results = sparql.query().convert()["results"]["bindings"]
    n = int(results[0]["c"]["value"])
    checks.append(("DOID hasDbXref MIM/OMIM", n >= 100, f"{n:,} xrefs (min: 100)"))
except Exception as e:
    checks.append(("DOID hasDbXref OMIM", False, str(e)))

# 1e. Cross-graph JOIN via xref (DOID<>HPOA)
sparql.setQuery("""
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX hpoa: <http://example.org/hpoa/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?doid_label ?disease_name WHERE {
  GRAPH <urn:doid> {
    ?doid_class oboInOwl:hasDbXref ?xref ;
                rdfs:label ?doid_label .
    FILTER(?xref = "MIM:154700" || ?xref = "OMIM:154700")
  }
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id "OMIM:154700" ;
             rdfs:label ?disease_name .
  }
} LIMIT 5
""")
try:
    results = sparql.query().convert()["results"]["bindings"]
    n = len(results)
    checks.append(("Cross-graph DOID<>HPOA", n >= 1, f"{n} resultados"))
except Exception as e:
    checks.append(("Cross-graph DOID<>HPOA", False, str(e)))

# Resultado
print("\n" + "=" * 60)
print("GATE 1 - Validacao dos Dados")
print("=" * 60)
all_pass = True
for name, ok, detail in checks:
    status = "[OK]" if ok else "[FAIL]"
    print(f"  {status} {name}: {detail}")
    if not ok:
        all_pass = False

print(f"\n{'[OK] GATE 1 PASSED' if all_pass else '[FAIL] GATE 1 FAILED'}")
sys.exit(0 if all_pass else 1)
