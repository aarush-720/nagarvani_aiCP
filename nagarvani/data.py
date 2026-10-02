"""Loading the frozen data files (UTF-8 everywhere)."""
import csv
import json
from functools import lru_cache

from . import config


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def taxonomy():
    return read_json(config.DATA / "taxonomy.json")


@lru_cache(maxsize=None)
def gazetteer():
    return read_json(config.DATA / "gazetteer.json")


@lru_cache(maxsize=None)
def severity_kb():
    return read_json(config.DATA / "severity_rules.json")


@lru_cache(maxsize=None)
def keywords():
    return read_json(config.DATA / "keywords.json")["keywords"]


def dept_codes():
    return [d["code"] for d in taxonomy()["departments"]]


def dept_names():
    return {d["code"]: d for d in taxonomy()["departments"]}


def ward_names():
    return {w["code"]: w for w in taxonomy()["wards"]}


def sla_hours():
    return {b["band"]: b["sla_hours"] for b in taxonomy()["severity_bands"]}


def load_train():
    return read_csv(config.TRAIN_CSV)


def load_test():
    return read_csv(config.TEST_CSV)
