"""MedCAT backend — end-to-end NER + linking against a custom CDB built
from DOID + HPO OWL files.

Two-step usage:
  1) Build the CDB once:      python -m biosparql_ner.backends.medcat build
  2) Run inference via the pipeline with NER_BACKEND=medcat.

The builder parses rdfs:label and oboInOwl:hasExactSynonym / hasRelatedSynonym
from each OWL file and emits a MedCAT CDB with type assignments.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..base import Entity, NERBackend, merge_overlaps


class MedCATBackend:
    name = "medcat"

    def __init__(
        self,
        cdb_path: str | None = None,
        vocab_path: str | None = None,
    ):
        self._cdb_path = cdb_path or os.getenv(
            "MEDCAT_CDB", "./medcat_cdb_doid_hpo.dat"
        )
        self._vocab_path = vocab_path or os.getenv(
            "MEDCAT_VOCAB", "./medcat_vocab.dat"
        )
        self._cat = None

    def warm_up(self) -> None:
        from medcat.cat import CAT
        from medcat.cdb import CDB
        from medcat.vocab import Vocab

        if not Path(self._cdb_path).exists():
            raise FileNotFoundError(
                f"MedCAT CDB not found at {self._cdb_path}. "
                "Build it first: python -m biosparql_ner.backends.medcat build"
            )
        cdb = CDB.load(self._cdb_path)
        vocab = Vocab.load(self._vocab_path) if Path(self._vocab_path).exists() else None
        self._cat = CAT(cdb=cdb, vocab=vocab)

    def extract(self, text: str) -> list[Entity]:
        assert self._cat is not None
        doc = self._cat(text)
        out: list[Entity] = []
        for _, ent in doc.get("entities", {}).items():
            cui: str = ent["cui"]                 # e.g. "DOID:14330"
            src_val = ent["source_value"]
            start, end = ent["start"], ent["end"]
            acc = float(ent.get("context_similarity", 1.0))

            etype = "DISEASE" if cui.startswith("DOID") else (
                    "PHENOTYPE" if cui.startswith("HP") else "OTHER")
            out.append(Entity(
                text=src_val, start=start, end=end, type=etype,
                ontology_ids=[cui], scores=[acc], backend=self.name,
            ))
        return merge_overlaps(out)


# --------------------------- CDB BUILDER ---------------------------
# Run once: python -m biosparql_ner.backends.medcat build

def _build_cdb(
    doid_owl: str = os.getenv("DOID_OWL", "./data/doid.owl"),
    hpo_owl: str = os.getenv("HPO_OWL", "./data/hp.owl"),
    out_path: str = os.getenv("MEDCAT_CDB", "./medcat_cdb_doid_hpo.dat"),
):
    """Parse OWL files and emit a MedCAT CDB."""
    import rdflib
    from medcat.cdb_maker import CDBMaker
    from medcat.config import Config
    import pandas as pd

    RDFS_LABEL = rdflib.RDFS.label
    OBO = rdflib.Namespace("http://www.geneontology.org/formats/oboInOwl#")

    rows: list[dict] = []
    for path, prefix in [(doid_owl, "DOID"), (hpo_owl, "HP")]:
        print(f"[cdb] parsing {path} ...")
        g = rdflib.Graph()
        g.parse(path)
        for s in set(g.subjects()):
            s_str = str(s)
            # IRIs look like http://purl.obolibrary.org/obo/DOID_14330
            if f"/{prefix}_" not in s_str:
                continue
            local = s_str.rsplit("/", 1)[-1].replace("_", ":")
            if not local.startswith(prefix):
                continue

            labels = [str(o) for o in g.objects(s, RDFS_LABEL)]
            synonyms = [str(o) for o in g.objects(s, OBO.hasExactSynonym)]
            synonyms += [str(o) for o in g.objects(s, OBO.hasRelatedSynonym)]

            names = [n for n in (labels + synonyms) if n]
            if not names:
                continue

            rows.append({
                "cui": local,
                "name": "|".join(names),
                "ontologies": prefix,
                "name_status": "P",
                "tui": "T047" if prefix == "DOID" else "T184",  # disease / s-s-f
            })

    df = pd.DataFrame(rows)
    csv_path = Path(out_path).with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    print(f"[cdb] wrote {len(df)} concepts to {csv_path}")

    cfg = Config()
    cfg.general["spacy_model"] = "en_core_sci_sm"
    maker = CDBMaker(cfg)
    cdb = maker.prepare_csvs([str(csv_path)], full_build=True)
    cdb.save(out_path)
    print(f"[cdb] saved MedCAT CDB to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        _build_cdb()
    else:
        print("Usage: python -m biosparql_ner.backends.medcat build")
