"""Defects F1-F6 (docs/DECISIONS.md), fixed in v2.0. Each test reproduces the reported input."""
from nagarvani.location import WardResolver


def test_f4_alias_order_is_deterministic():
    r = WardResolver()
    assert r.aliases == sorted(r.aliases, key=lambda p: (-len(p[0]), p))
