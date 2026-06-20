# evals — evaluation harness

The gate from [ADR-0007](../decisions/0007-quality-gate.md), built and running.
A routing change ships only through it.

| File | What it is |
|------|------------|
| [`quality_invariants.py`](quality_invariants.py) | Deterministic checks: a served request meets its quality floor and stays within budget; a blocked request is never served; a served provider is healthy |
| [`golden_cases.json`](golden_cases.json) | Representative seed cases (route + invariant). In production this set grows from real request classes and incidents |
| [`golden_runner.py`](golden_runner.py) | Runs every case against the real router and exits non-zero on any regression — a CI gate |

The invariants are deliberately deterministic, not model-judged: a cost dashboard
cannot see a quality regression, so the check that we didn't serve below the quality
floor has to be a hard rule, not a judge model's opinion.

```bash
python -m evals.golden_runner   # PASS/FAIL report, exit 1 on regression
```

This runs in CI on every push (see `.github/workflows/ci.yml`), which makes "a
routing change ships only through the eval gate" literally true in this repo.
