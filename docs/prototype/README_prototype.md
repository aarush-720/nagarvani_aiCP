# NagarVani — prototype

Marathi / Hindi / romanised / code-mixed civic-complaint triage for PMC: department classification,
ward-office resolution, rule-based severity, duplicate detection, abstention, SQLite + per-ward CSV queues.
A triage layer that could sit in front of PMC CARE — **not** an integration (PMC CARE has no public API).

```
pip install scikit-learn numpy matplotlib flask            # playwright only for demo screenshots
python corpus/generate_train.py 200                        # 2,000-row template training corpus
python experiments/run_eval.py                             # all metrics -> results/results.json, figures
python experiments/make_architecture.py
python app/app.py                                          # console on http://127.0.0.1:5000
python experiments/demo_scenario.py                        # scripted demo + screenshots
```

| Path | Contents |
|---|---|
| `nagarvani/normalise.py` | M3 text normalisation |
| `nagarvani/classifier.py` | M4a department classifier + 4 baselines |
| `nagarvani/location.py` | M4b gazetteer ward resolver (exact + fuzzy) |
| `nagarvani/severity.py` | M5 rule-based expert system (19 rules, forward chaining, explanations) |
| `nagarvani/dedup.py` | M6 duplicate detection (blocking + two thresholds) |
| `nagarvani/asr.py` | M2 ASR interface + transcription-noise simulator |
| `nagarvani/store.py`, `pipeline.py` | M7 routing, SQLite store, CSV export |
| `corpus/test_handwritten.tsv` | 160 hand-written, hand-labelled test complaints |
| `corpus/dup_pairs.tsv` | 30 labelled duplicate / non-duplicate pairs |
| `data/gazetteer.json` | 59 localities -> 15 ward offices (approximate) |
| `docs/annotation_guideline.md` | severity labelling guideline |

Limitations: all data is team-constructed (no real PMC complaints); no ASR model was run; the gazetteer is approximate.
