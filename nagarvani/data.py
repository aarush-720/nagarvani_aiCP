"""Loading the frozen data (UTF-8 everywhere) and the display names used by the web app."""
import csv
import json
from functools import lru_cache

from . import config
from .classifier import DEPARTMENTS
from .pipeline import load_tsv          # the original loader (maps lang 'rom' -> 'mr-rom')


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_csv(path, delimiter=","):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


@lru_cache(maxsize=None)
def gazetteer():
    return read_json(config.GAZETTEER)


@lru_cache(maxsize=None)
def taxonomy():
    """Display metadata only (Marathi names, SLA labels). Not used by any frozen logic."""
    return read_json(config.DATA / "taxonomy.json")


def dept_codes():
    return sorted(DEPARTMENTS)


def dept_names():
    mr = taxonomy()["departments_mr"]
    return {c: {"code": c, "en": DEPARTMENTS[c], "mr": mr.get(c, DEPARTMENTS[c])} for c in dept_codes()}


def ward_names():
    mr = taxonomy()["wards_mr"]
    return {c: {"code": c, "en": n, "mr": mr.get(c, n)} for c, n in gazetteer()["ward_offices"].items()}


def sla_hours():
    from .severity import SLA_HOURS
    return dict(SLA_HOURS)


def load_train():
    return load_tsv(str(config.TRAIN_TSV))


def load_test():
    return load_tsv(str(config.TEST_TSV))


def load_pairs():
    return read_csv(config.PAIRS_TSV, delimiter="\t")
