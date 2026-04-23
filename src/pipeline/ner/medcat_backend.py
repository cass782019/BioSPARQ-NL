"""MedCAT backend — end-to-end NER + linking against a custom CDB.

The CDB is built from DOID + HPO OWL files (one-time build):
  python -m src.pipeline.ner.medcat_backend build

Install: pip install medcat rdflib pandas
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from .base import Entity, NERBackend, merge_overlaps

logger = logging.getLogger(__name__)

_DEFAULT_CDB = os.getenv("MEDCAT_CDB", "data/medcat_cdb.dat")
_DEFAULT_VOCAB = os.getenv("MEDCAT_VOCAB", "data/medcat_vocab.dat")
_DOID_OWL = os.getenv("DOID_OWL", "data/ontologies/doid.owl")
_HPO_OWL = os.getenv("HPO_OWL", "data/ontologies/hp.owl")


class MedCATBackend:
    name = "medcat"

    def __init__(self, cdb_path: str | None = None, vocab_path: str | None = None):
        self._cdb_path = cdb_path or _DEFAULT_CDB
        self._vocab_path = vocab_path or _DEFAULT_VOCAB
        self._cat = None

    def warm_up(self) -> None:
        try:
            from medcat.cat import CAT
            from medcat.cdb import CDB
            from medcat.vocab import Vocab
        except ImportError as e:
            raise ImportError(
                f"MedCATBackend requires medcat: pip install medcat. ({e})"
            ) from e

        if not Path(self._cdb_path).exists():
            raise FileNotFoundError(
                f"MedCAT CDB not found at '{self._cdb_path}'. "
                "Build it first: python -m src.pipeline.ner.medcat_backend build"
            )
        cdb = CDB.load(self._cdb_path)
        vocab = Vocab.load(self._vocab_path) if Path(self._vocab_path).exists() else None
        self._cat = CAT(cdb=cdb, vocab=vocab)
        logger.info("MedCATBackend ready (CDB: %s).", self._cdb_path)

    def extract(self, text: str) -> list[Entity]:
        assert self._cat is not None, "call warm_up() first"
        doc = self._cat(text)
        out: list[Entity] = []
        for _, ent in doc.get("entities", {}).items():
            cui: str = ent["cui"]
            src_val = ent["source_value"]
            start, end = ent["start"], ent["end"]
            acc = float(ent.get("context_similarity", 1.0))
            etype = ("DISEASE" if cui.startswith("DOID") else
                     "PHENOTYPE" if cui.startswith("HP") else "OTHER")
            out.append(Entity(
                text=src_val, start=start, end=end, type=etype,
                ontology_ids=[cui], scores=[acc], backend=self.name,
            ))
        return merge_overlaps(out)


def _build_cdb(
    doid_owl: str = _DOID_OWL,
    hpo_owl: str = _HPO_OWL,
    out_path: str = _DEFAULT_CDB,
) -> None:
    """Parse OWL files and emit a MedCAT CDB. Run once."""
    import rdflib
    import pandas as pd
    from medcat.cdb_maker import CDBMaker
    from medcat.config import Config

    OBO_INFOWL = rdflib.Namespace("http://www.geneontology.org/formats/oboInOwl#")

    rows: list[dict] = []
    for path, prefix in [(doid_owl, "DOID"), (hpo_owl, "HP")]:
        print(f"[cdb] parsing {path} ...")
        g = rdflib.Graph()
        g.parse(path)
        for s in set(g.subjects()):
            s_str = str(s)
            if f"/{prefix}_" not in s_str:
                continue
            local = s_str.rsplit("/", 1)[-1].replace("_", ":")
            if not local.startswith(prefix):
                continue

            labels = [str(o) for o in g.objects(s, rdflib.RDFS.label)]
            synonyms = [str(o) for o in g.objects(s, OBO_INFOWL.hasExactSynonym)]
            synonyms += [str(o) for o in g.objects(s, OBO_INFOWL.hasRelatedSynonym)]
            names = [n for n in (labels + synonyms) if n]
            if not names:
                continue

            rows.append({
                "cui": local,
                "name": "|".join(names),
                "ontologies": prefix,
                "name_status": "P",
                "tui": "T047" if prefix == "DOID" else "T184",
            })

    df = pd.DataFrame(rows)
    csv_path = Path(out_path).with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    print(f"[cdb] {len(df)} concepts -> {csv_path}")

    cfg = Config()
    cfg.general["spacy_model"] = "en_core_sci_sm"
    maker = CDBMaker(cfg)
    cdb = maker.prepare_csvs([str(csv_path)], full_build=True)
    cdb.save(out_path)
    print(f"[cdb] saved MedCAT CDB -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        _build_cdb()
    else:
        print("Usage: python -m src.pipeline.ner.medcat_backend build")
