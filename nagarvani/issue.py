"""v2.0 (F6) - Does the complaint state a problem at all?

A content-free complaint ("कोथरूडमध्ये खूप त्रास होतोय, कोणीतरी लक्ष द्या") still gets a
department from the classifier, sometimes with confidence above tau, and was auto-routed.
The gate now defers it (NO_ISSUE_STATED) when all three hold:

  1. no severity rule fired other than the escalation modifiers R30-R32;
  2. no keyword of the keyword baseline (classifier.KeywordBaseline.KW) occurs in it;
  3. nothing is left once place names (gazetteer aliases, with suffixes) and GENERIC words
     are removed.

GENERIC was written in advance: the training generator's greeting, location and urgency
frames (corpus/generate_train.py PREFIX, SUFFIX, LOC_TPL) plus common words for "trouble",
"please look", pronouns, auxiliaries and connectives. No training complaint is flagged.
"""
import re

from .classifier import KeywordBaseline
from .normalise import normalise

ESCALATION_RULES = ("R30", "R31", "R32")

GENERIC = set("""
action area bhagat hello kara karvai lavkar madhe namaskar please saheb sir urgent yethe आहे इलाके
करवाइए करा करावी करूनही करें कारवाई कार्रवाई कृपया घेतली घ्या जल्दी ठीक तक्रार दखल दुरुस्ती दें द्या
ध्यान नमस्कार नमस्ते नाही परिसरात भागात मध्ये में येथे लक्ष लवकर ला सर साहेब
खूप फार जास्त बहुत khup jast far very lot
त्रास समस्या प्रॉब्लेम अडचण परेशानी दिक्कत शिकायत problem problems issue issues complaint tras taklif
takrar samasya pareshani dikkat
आहेत होते होतं होतोय होतेय होत होतो झाले झालं झालाय झालंय आहोत है हैं था थी हो रहा रही रहे होती
aahe aahet ahe hota hote hotoy zala zale is are
कोणी कोणीतरी कोई कोईतरी koni konitari koi someone anyone तरी tari
बघा पहा बघावे दे दो करो करावे pls plz help मदत मदद jaldi asap
आमच्या आमचा आमची आमचे आम्हाला हमारे हमारी हमें हम मी मला मेरे मुझे aamchya amchya aamhala mala mi
we our my me
इथे इकडे यहाँ यहां इधर ithe here भाग इलाका परिसर bhag kade
आणि पण व और लेकिन ani aani pan and but the a of in to
काहीतरी काही कुछ kahi kuch something
""".split())

_TOKEN = re.compile(r"[^\s,.\-:]+")


def issue_stated(text, fired, aliases):
    """False only for a content-free complaint (the three conditions above).

    fired: rule ids from severity.infer; aliases: normalised gazetteer aliases."""
    if any(r not in ESCALATION_RULES for r in fired):
        return True
    t = normalise(text)
    if any(k.lower() in t for kws in KeywordBaseline.KW.values() for k in kws):
        return True
    places = [a for a in aliases if len(a) >= 3]
    return any(w not in GENERIC and not any(w.startswith(a) for a in places) for w in _TOKEN.findall(t))
