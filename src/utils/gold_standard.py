"""Gold standard com 30 pares NL→SPARQL organizados por complexidade.

Distribuição: 10 easy, 10 medium, 10 hard.
Cada entrada: id, question_pt, question_en, sparql, type, difficulty,
              expected_min_results, expected_contains (opcional).
"""
import json

GOLD_STANDARD = [
    # ===================== EASY (Q01-Q10): Lookup direto =====================
    {
        "id": "Q01",
        "question_pt": "Quais são os fenótipos associados à síndrome de Marfan?",
        "question_en": "What phenotypes are associated with Marfan syndrome?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id "OMIM:154700" ;
             hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
}""",
        "type": "factoid",
        "difficulty": "easy",
        "expected_min_results": 5,
        "expected_contains": ["Arachnodactyly", "Scoliosis"],
    },
    {
        "id": "Q02",
        "question_pt": "Quantas subclasses de 'doença cardiovascular' existem no DOID?",
        "question_en": "How many subclasses of cardiovascular disease exist in DOID?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT (COUNT(DISTINCT ?d) AS ?total) WHERE {
  GRAPH <urn:doid> {
    ?d rdfs:subClassOf+ obo:DOID_1287 .
  }
}""",
        "type": "count",
        "difficulty": "easy",
        "expected_min_results": 1,
    },
    {
        "id": "Q03",
        "question_pt": "Qual é a definição da doença de Alzheimer no DOID?",
        "question_en": "What is the definition of Alzheimer disease in DOID?",
        "sparql": """PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?definition WHERE {
  GRAPH <urn:doid> {
    obo:DOID_10652 obo:IAO_0000115 ?definition .
  }
}""",
        "type": "factoid",
        "difficulty": "easy",
        "expected_min_results": 1,
    },
    {
        "id": "Q04",
        "question_pt": "Qual é o label da classe raiz 'disease' no DOID?",
        "question_en": "What is the label of the root class 'disease' in DOID?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?label WHERE {
  GRAPH <urn:doid> {
    obo:DOID_4 rdfs:label ?label .
  }
}""",
        "type": "factoid",
        "difficulty": "easy",
        "expected_min_results": 1,
        "expected_contains": ["disease"],
    },
    {
        "id": "Q05",
        "question_pt": "Quais são os sinônimos de 'diabetes mellitus' no DOID?",
        "question_en": "What are the synonyms of diabetes mellitus in DOID?",
        "sparql": """PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
SELECT ?synonym WHERE {
  GRAPH <urn:doid> {
    obo:DOID_9351 oboInOwl:hasExactSynonym ?synonym .
  }
}""",
        "type": "list",
        "difficulty": "easy",
        "expected_min_results": 1,
    },
    {
        "id": "Q06",
        "question_pt": "Quais são as subclasses diretas de 'neoplasm' no DOID?",
        "question_en": "What are the direct subclasses of neoplasm in DOID?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?subclass ?label WHERE {
  GRAPH <urn:doid> {
    ?subclass rdfs:subClassOf obo:DOID_14566 .
    ?subclass rdfs:label ?label .
  }
}""",
        "type": "list",
        "difficulty": "easy",
        "expected_min_results": 2,
    },
    {
        "id": "Q07",
        "question_pt": "Qual é a definição de 'Arachnodactyly' no HPO?",
        "question_en": "What is the definition of Arachnodactyly in HPO?",
        "sparql": """PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?definition WHERE {
  GRAPH <urn:hpo> {
    obo:HP_0001166 obo:IAO_0000115 ?definition .
  }
}""",
        "type": "factoid",
        "difficulty": "easy",
        "expected_min_results": 1,
    },
    {
        "id": "Q08",
        "question_pt": "Quantos termos fenotípicos existem no HPO?",
        "question_en": "How many phenotype terms exist in HPO?",
        "sparql": """PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT (COUNT(DISTINCT ?term) AS ?total) WHERE {
  GRAPH <urn:hpo> {
    ?term a owl:Class .
  }
}""",
        "type": "count",
        "difficulty": "easy",
        "expected_min_results": 1,
    },
    {
        "id": "Q09",
        "question_pt": "Quais são os xrefs OMIM da doença de Huntington no DOID?",
        "question_en": "What are the OMIM cross-references for Huntington disease in DOID?",
        "sparql": """PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
SELECT ?xref WHERE {
  GRAPH <urn:doid> {
    obo:DOID_12858 oboInOwl:hasDbXref ?xref .
    FILTER(STRSTARTS(STR(?xref), "OMIM:"))
  }
}""",
        "type": "factoid",
        "difficulty": "easy",
        "expected_min_results": 1,
    },
    {
        "id": "Q10",
        "question_pt": "Quais doenças estão anotadas com o fenótipo 'Seizure'?",
        "question_en": "Which diseases are annotated with the phenotype Seizure?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?disease_name WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype obo:HP_0001250 ;
             rdfs:label ?disease_name .
  }
} LIMIT 20""",
        "type": "list",
        "difficulty": "easy",
        "expected_min_results": 5,
    },
    # =================== MEDIUM (Q11-Q20): JOIN entre grafos ===================
    {
        "id": "Q11",
        "question_pt": "Quais doenças estão associadas ao fenótipo 'aracnodactilia'?",
        "question_en": "Which diseases are associated with the phenotype arachnodactyly?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?disease_name WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype obo:HP_0001166 ;
             rdfs:label ?disease_name .
  }
}""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 2,
    },
    {
        "id": "Q12",
        "question_pt": "Quais fenótipos são compartilhados entre síndrome de Marfan e síndrome de Ehlers-Danlos?",
        "question_en": "Which phenotypes are shared between Marfan syndrome and Ehlers-Danlos syndrome?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT DISTINCT ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?marfan hpoa:source_id "OMIM:154700" ;
            hpoa:has_phenotype ?pheno .
    ?eds hpoa:source_id "OMIM:130000" ;
         hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
}""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 1,
    },
    {
        "id": "Q13",
        "question_pt": "Quais doenças OMIM estão associadas ao fenótipo 'Intellectual disability'?",
        "question_en": "Which OMIM diseases are associated with the phenotype Intellectual disability?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?disease_name ?source_id WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype obo:HP_0001249 ;
             rdfs:label ?disease_name ;
             hpoa:source_id ?source_id .
    FILTER(STRSTARTS(?source_id, "OMIM:"))
  }
} LIMIT 20""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 5,
    },
    {
        "id": "Q14",
        "question_pt": "Quais fenótipos estão associados à doença com xref OMIM:154700 no DOID?",
        "question_en": "What phenotypes are associated with the disease having xref OMIM:154700 in DOID?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?doid_label ?phenotype_label WHERE {
  GRAPH <urn:doid> {
    ?doid_class oboInOwl:hasDbXref "MIM:154700" ;
                rdfs:label ?doid_label .
  }
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id "OMIM:154700" ;
             hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
}""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 3,
    },
    {
        "id": "Q15",
        "question_pt": "Quais subclasses de 'doença infecciosa' no DOID possuem definição?",
        "question_en": "Which subclasses of infectious disease in DOID have a definition?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?disease ?label ?definition WHERE {
  GRAPH <urn:doid> {
    ?disease rdfs:subClassOf obo:DOID_0050117 ;
             rdfs:label ?label ;
             obo:IAO_0000115 ?definition .
  }
} LIMIT 10""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 2,
    },
    {
        "id": "Q16",
        "question_pt": "Quais doenças no DOID possuem xref tanto OMIM quanto ORPHA?",
        "question_en": "Which diseases in DOID have both OMIM and ORPHA cross-references?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
SELECT DISTINCT ?label WHERE {
  GRAPH <urn:doid> {
    ?disease oboInOwl:hasDbXref ?omim_xref ;
             oboInOwl:hasDbXref ?orpha_xref ;
             rdfs:label ?label .
    FILTER(STRSTARTS(STR(?omim_xref), "MIM:"))
    FILTER(CONTAINS(STR(?orpha_xref), "orpha.net"))
  }
} LIMIT 20""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 2,
    },
    {
        "id": "Q17",
        "question_pt": "Quais são os fenótipos da fibrose cística via source_id OMIM?",
        "question_en": "What are the phenotypes of cystic fibrosis via OMIM source_id?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id "OMIM:219700" ;
             hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
}""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 5,
    },
    {
        "id": "Q18",
        "question_pt": "Quais doenças no HPOA têm nome contendo 'syndrome'?",
        "question_en": "Which diseases in HPOA have a name containing 'syndrome'?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT DISTINCT ?disease_name WHERE {
  GRAPH <urn:hpoa> {
    ?disease rdfs:label ?disease_name .
    FILTER(CONTAINS(LCASE(?disease_name), "syndrome"))
  }
} LIMIT 20""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 5,
    },
    {
        "id": "Q19",
        "question_pt": "Quais são as subclasses de 'doença ocular' no DOID com label?",
        "question_en": "What are the subclasses of eye disease in DOID with their labels?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?subclass ?label WHERE {
  GRAPH <urn:doid> {
    ?subclass rdfs:subClassOf obo:DOID_5614 ;
              rdfs:label ?label .
  }
} LIMIT 20""",
        "type": "list",
        "difficulty": "medium",
        "expected_min_results": 2,
    },
    {
        "id": "Q20",
        "question_pt": "Qual doença no DOID possui o maior número de xrefs externos?",
        "question_en": "Which disease in DOID has the most external cross-references?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
SELECT ?label (COUNT(DISTINCT ?xref) AS ?num_xrefs) WHERE {
  GRAPH <urn:doid> {
    ?disease oboInOwl:hasDbXref ?xref ;
             rdfs:label ?label .
  }
} GROUP BY ?disease ?label
ORDER BY DESC(?num_xrefs)
LIMIT 10""",
        "type": "aggregation",
        "difficulty": "medium",
        "expected_min_results": 1,
    },
    # ================= HARD (Q21-Q30): Hierarquia, agregação, 3 grafos =================
    {
        "id": "Q21",
        "question_pt": "Quais doenças genéticas do DOID possuem mais de 10 fenótipos anotados no HPO?",
        "question_en": "Which genetic diseases in DOID have more than 10 annotated phenotypes in HPO?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?disease_name (COUNT(DISTINCT ?pheno) AS ?num_phenotypes) WHERE {
  GRAPH <urn:doid> {
    ?doid_class rdfs:subClassOf+ obo:DOID_630 .
    ?doid_class oboInOwl:hasDbXref ?xref .
    FILTER(STRSTARTS(STR(?xref), "MIM:"))
  }
  BIND(REPLACE(STR(?xref), "^MIM:", "OMIM:") AS ?omim_id)
  GRAPH <urn:hpoa> {
    ?disease hpoa:source_id ?omim_id ;
             hpoa:has_phenotype ?pheno ;
             rdfs:label ?disease_name .
  }
} GROUP BY ?disease ?disease_name
HAVING (COUNT(DISTINCT ?pheno) > 10)
ORDER BY DESC(?num_phenotypes)
LIMIT 20""",
        "type": "aggregation",
        "difficulty": "hard",
        "expected_min_results": 1,
    },
    {
        "id": "Q22",
        "question_pt": "Quais são os 10 fenótipos mais frequentes no HPOA?",
        "question_en": "What are the top 10 most frequent phenotypes in HPOA?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?phenotype_label (COUNT(DISTINCT ?disease) AS ?frequency) WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
} GROUP BY ?pheno ?phenotype_label
ORDER BY DESC(?frequency)
LIMIT 10""",
        "type": "aggregation",
        "difficulty": "hard",
        "expected_min_results": 10,
    },
    {
        "id": "Q23",
        "question_pt": "Quais doenças compartilham 3 ou mais fenótipos com a síndrome de Marfan?",
        "question_en": "Which diseases share 3 or more phenotypes with Marfan syndrome?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?other_name (COUNT(DISTINCT ?pheno) AS ?shared) WHERE {
  GRAPH <urn:hpoa> {
    ?marfan hpoa:source_id "OMIM:154700" ;
            hpoa:has_phenotype ?pheno .
    ?other hpoa:has_phenotype ?pheno ;
           rdfs:label ?other_name .
    FILTER(?other != ?marfan)
  }
} GROUP BY ?other ?other_name
HAVING (COUNT(DISTINCT ?pheno) >= 3)
ORDER BY DESC(?shared)
LIMIT 20""",
        "type": "aggregation",
        "difficulty": "hard",
        "expected_min_results": 1,
    },
    {
        "id": "Q24",
        "question_pt": "Qual é a hierarquia completa de 'cardiomyopathy' no DOID (3 níveis)?",
        "question_en": "What is the full hierarchy of cardiomyopathy in DOID (3 levels)?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT ?child ?child_label ?parent ?parent_label WHERE {
  GRAPH <urn:doid> {
    ?child rdfs:subClassOf+ obo:DOID_0050700 ;
           rdfs:label ?child_label .
    ?child rdfs:subClassOf ?parent .
    ?parent rdfs:label ?parent_label .
  }
} LIMIT 30""",
        "type": "hierarchy",
        "difficulty": "hard",
        "expected_min_results": 3,
    },
    {
        "id": "Q25",
        "question_pt": "Quais fenótipos são exclusivos da síndrome de Marfan (não aparecem em Ehlers-Danlos)?",
        "question_en": "Which phenotypes are exclusive to Marfan syndrome (not in Ehlers-Danlos)?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT DISTINCT ?phenotype_label WHERE {
  GRAPH <urn:hpoa> {
    ?marfan hpoa:source_id "OMIM:154700" ;
            hpoa:has_phenotype ?pheno .
    MINUS {
      ?eds hpoa:source_id "OMIM:130000" ;
           hpoa:has_phenotype ?pheno .
    }
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
  }
}""",
        "type": "set_operation",
        "difficulty": "hard",
        "expected_min_results": 1,
    },
    {
        "id": "Q26",
        "question_pt": "Quais doenças do DOID não possuem nenhum fenótipo anotado no HPOA?",
        "question_en": "Which DOID diseases have no annotated phenotypes in HPOA?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?doid_label WHERE {
  GRAPH <urn:doid> {
    ?disease rdfs:subClassOf obo:DOID_4 ;
             rdfs:label ?doid_label ;
             oboInOwl:hasDbXref ?xref .
    FILTER(STRSTARTS(STR(?xref), "OMIM:"))
  }
  OPTIONAL {
    GRAPH <urn:hpoa> {
      ?hpoa_disease hpoa:source_id ?xref .
    }
  }
  FILTER(!BOUND(?hpoa_disease))
} LIMIT 20""",
        "type": "set_operation",
        "difficulty": "hard",
        "expected_min_results": 1,
    },
    {
        "id": "Q27",
        "question_pt": "Quais fenótipos com label contendo 'cardiac' estão associados a quais doenças?",
        "question_en": "Which phenotypes with label containing 'cardiac' are associated with which diseases?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?phenotype_label ?disease_name WHERE {
  GRAPH <urn:hpo> {
    ?pheno rdfs:label ?phenotype_label .
    FILTER(CONTAINS(LCASE(?phenotype_label), "cardiac"))
  }
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype ?pheno ;
             rdfs:label ?disease_name .
  }
} LIMIT 20""",
        "type": "complex_join",
        "difficulty": "hard",
        "expected_min_results": 2,
    },
    {
        "id": "Q28",
        "question_pt": "Quais são os ancestrais comuns de 'asma' e 'DPOC' na hierarquia DOID?",
        "question_en": "What are the common ancestors of asthma and COPD in the DOID hierarchy?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
SELECT DISTINCT ?ancestor_label WHERE {
  GRAPH <urn:doid> {
    obo:DOID_2841 rdfs:subClassOf+ ?ancestor .
    obo:DOID_3083 rdfs:subClassOf+ ?ancestor .
    ?ancestor rdfs:label ?ancestor_label .
  }
}""",
        "type": "hierarchy",
        "difficulty": "hard",
        "expected_min_results": 1,
        "expected_contains": ["disease"],
    },
    {
        "id": "Q29",
        "question_pt": "Qual é a distribuição de fenótipos por categoria raiz do HPO?",
        "question_en": "What is the distribution of phenotypes by HPO root category?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT ?category_label (COUNT(DISTINCT ?pheno) AS ?count) WHERE {
  GRAPH <urn:hpoa> {
    ?disease hpoa:has_phenotype ?pheno .
  }
  GRAPH <urn:hpo> {
    ?pheno rdfs:subClassOf+ ?category .
    ?category rdfs:subClassOf obo:HP_0000118 .
    ?category rdfs:label ?category_label .
  }
} GROUP BY ?category ?category_label
ORDER BY DESC(?count)""",
        "type": "aggregation",
        "difficulty": "hard",
        "expected_min_results": 3,
    },
    {
        "id": "Q30",
        "question_pt": "Quais doenças raras (ORPHA) são subclasse de 'doença metabólica' no DOID?",
        "question_en": "Which rare diseases (ORPHA) are subclasses of metabolic disease in DOID?",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>
PREFIX hpoa: <http://example.org/hpoa/>
SELECT DISTINCT ?doid_label ?orpha_id WHERE {
  GRAPH <urn:doid> {
    ?disease rdfs:subClassOf+ obo:DOID_0014667 ;
             rdfs:label ?doid_label ;
             oboInOwl:hasDbXref ?orpha_id .
    FILTER(CONTAINS(STR(?orpha_id), "orpha.net"))
  }
} LIMIT 20""",
        "type": "complex_join",
        "difficulty": "hard",
        "expected_min_results": 1,
    },
]


def save_gold_standard(output_path: str = "data/gold_standard/questions.json"):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(GOLD_STANDARD, f, indent=2, ensure_ascii=False)
    print(f"[OK] Gold standard salvo: {len(GOLD_STANDARD)} questoes em {output_path}")

    # Verificar distribuição
    for diff in ["easy", "medium", "hard"]:
        count = sum(1 for q in GOLD_STANDARD if q["difficulty"] == diff)
        print(f"   {diff}: {count} questoes")


if __name__ == "__main__":
    save_gold_standard()
