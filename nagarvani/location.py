"""M4b - Gazetteer-based locality extraction and ward-office resolution."""
import json, os, re
from .normalise import normalise

_GAZ_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gazetteer.json")


from difflib import SequenceMatcher


class WardResolver:
    def __init__(self, path=_GAZ_PATH, fuzzy=True, fuzzy_threshold=0.80):
        self.fuzzy, self.fuzzy_threshold = fuzzy, fuzzy_threshold
        g = json.load(open(path, encoding="utf-8"))
        self.wards = g["ward_offices"]
        self.loc2ward = {k: v["ward"] for k, v in g["localities"].items()}
        # alias -> locality key, longest aliases first so "वडगाव शेरी" beats "वडगाव"
        pairs = []
        for key, v in g["localities"].items():
            for a in v["aliases"]:
                pairs.append((normalise(a), key))
        self.aliases = sorted(set(pairs), key=lambda p: -len(p[0]))
        self.ambiguous = {normalise(a): ks for a, ks in g["ambiguous"].items()}

    @staticmethod
    def _find(alias, text):
        if alias.isascii():                      # Latin: whole-word match
            return re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", text) is not None
        return alias in text                     # Devanagari: substring, tolerates suffixes (कोथरूडमध्ये)

    def resolve(self, text):
        """Return dict(locality, ward, ward_name, status, candidates).

        status: 'resolved' | 'ambiguous' | 'unresolved'
        """
        t = normalise(text)
        hits = []
        masked = t
        for alias, key in self.aliases:
            if self._find(alias, masked):
                hits.append(key)
                masked = masked.replace(alias, " ")   # stop "वडगाव" re-matching inside "वडगाव शेरी"
        wards = sorted({self.loc2ward[k] for k in hits})
        if len(wards) == 1:
            k = hits[0]
            return dict(locality=k, ward=wards[0], ward_name=self.wards[wards[0]],
                        status="resolved", candidates=hits)
        if len(wards) > 1:
            return dict(locality=None, ward=None, ward_name=None, status="ambiguous", candidates=hits)
        for a, ks in self.ambiguous.items():
            if self._find(a, masked):
                return dict(locality=None, ward=None, ward_name=None, status="ambiguous", candidates=ks)
        if self.fuzzy:
            fz = self._fuzzy(t)
            if fz:
                k = fz
                return dict(locality=k, ward=self.loc2ward[k], ward_name=self.wards[self.loc2ward[k]],
                            status="resolved", candidates=[k], fuzzy=True)
        return dict(locality=None, ward=None, ward_name=None, status="unresolved", candidates=[])

    def _fuzzy(self, t):
        """Fallback for transcription errors: best alias whose similarity to some token window
        (same number of tokens, compared on the window prefix so Marathi suffixes are tolerated)
        is >= fuzzy_threshold. Only aliases of 4+ characters are considered."""
        toks = t.split()
        best, best_key = 0.0, None
        for alias, key in self.aliases:
            if len(alias) < 4: continue
            n = len(alias.split())
            for i in range(len(toks) - n + 1):
                win = " ".join(toks[i:i + n])[:len(alias) + 1]
                r = SequenceMatcher(None, alias, win).ratio()
                if r > best:
                    best, best_key = r, key
        return best_key if best >= self.fuzzy_threshold else None
