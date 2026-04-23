"""Download ontologias e anotações para o projeto BioSPARQL-NL."""
import urllib.request
import os
import logging

logger = logging.getLogger(__name__)

DOWNLOADS = [
    (
        "https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/doid.owl",
        "data/ontologies/doid.owl",
    ),
    (
        "http://purl.obolibrary.org/obo/hp.owl",
        "data/ontologies/hp.owl",
    ),
    (
        "http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa",
        "data/annotations/phenotype.hpoa",
    ),
]


def download_all():
    for url, dest in DOWNLOADS:
        if os.path.exists(dest):
            size_mb = os.path.getsize(dest) / 1024 / 1024
            print(f"  ⏭️  {dest} já existe ({size_mb:.1f} MB)")
            continue
        print(f"  Baixando {url}")
        print(f"    → {dest} ...")
        try:
            urllib.request.urlretrieve(url, dest)
            size_mb = os.path.getsize(dest) / 1024 / 1024
            print(f"    ✅ {size_mb:.1f} MB")
        except Exception as e:
            logger.error(f"Falha ao baixar {url}: {e}")
            print(f"    ❌ Erro: {e}")


if __name__ == "__main__":
    download_all()
