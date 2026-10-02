# Phase 0 inventory

Date: 2026-10-02. Branch: `claude/nagarvani-final-mvp-y345l5`.

## Finding: the repository is empty

The brief says this repository holds an existing prototype: Python, scikit-learn,
Flask and SQLite code, a 2,000-item template training set, a 160-item hand-written
test set, a 59-locality gazetteer and a 19-rule severity base. None of it is here.

What was checked:

| Check | Result |
|---|---|
| Local working tree (`/home/user/nagarvani_aiCP`) | Only `.git/`. No files at all. |
| Local git history | `No commits yet` on the branch. |
| `git ls-remote origin` (github.com/aarush-720/nagarvani_aiCP) | No refs. The remote has no branches. |
| GitHub API, list branches | `[]` |
| Filesystem search for `*nagarvani*` | Nothing outside this empty clone and tool caches. |

## Where this differs from section 2 of the brief

Every item in section 2 is missing: the code, the training data, the test data,
the gazetteer, the rule base, the evaluation scripts, the Flask app and any pinned
dependencies.

## Reported vs reproduced

| Quantity | Reported | Reproduced |
|---|---|---|
| All 15 rows of the section 2 table | as in brief | **Not reproducible: no code or data** |

## Why the build stopped here

This is the brief's planned stop at the end of Phase 0, reached for a stronger
reason than a number mismatch. The ground rules forbid regenerating the training
set, test set, gazetteer or rules, and forbid inventing numbers. Writing a new
prototype from the summary would produce different data and different numbers,
and the submitted report would no longer describe the code. So nothing was built.

## What is needed to continue

Push the prototype as it was when the reported numbers were produced (all source
files, `data/` with the train/test CSVs, gazetteer and rules, plus any
requirements file) to this repository, ideally on `main`. Then start a new
session with the same brief. Phase 0 will restart from step 1.
