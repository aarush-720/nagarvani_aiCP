"""M6 - Duplicate detection with blocking and a two-threshold decision."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .normalise import normalise

# Tokens that describe *where* rather than *what*; removed before text similarity so that
# two different problems in the same locality do not look alike.
_LOC_STOP = None


class DuplicateDetector:
    def __init__(self, resolver, theta_high=0.45, theta_low=0.30):
        self.theta_high, self.theta_low = theta_high, theta_low
        self.resolver = resolver
        self.aliases = [a for a, _ in resolver.aliases]
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True,
                                   preprocessor=self._strip_loc)

    def _strip_loc(self, text):
        t = normalise(text)
        for a in self.aliases:
            t = t.replace(a, " ")
        return t

    def fit(self, corpus):
        self.vec.fit(corpus); return self

    def similarity(self, a, b):
        m = self.vec.transform([a, b])
        return float(cosine_similarity(m[0], m[1])[0, 0])

    def decide(self, new, new_dept, new_ward, open_tickets):
        """open_tickets: iterable of dicts with keys id, text, dept, ward.
        Blocking: only tickets with the same ward office AND same department are compared.
        Returns (decision, best_id, best_score) where decision in {'merge','review','new'}."""
        best, best_id = 0.0, None
        for t in open_tickets:
            if t["dept"] != new_dept or not new_ward or t["ward"] != new_ward:
                continue
            s = self.similarity(new, t.get("text") or t["raw_text"])
            if s > best:
                best, best_id = s, t["id"]
        if best >= self.theta_high: return "merge", best_id, best
        if best >= self.theta_low: return "review", best_id, best
        return "new", None, best
