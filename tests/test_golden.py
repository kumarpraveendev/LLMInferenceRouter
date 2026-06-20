from evals.golden_runner import load_cases, run_all


def test_golden_suite_has_no_regressions():
    failures = [r for r in run_all(load_cases()) if not r.passed]
    assert not failures, "; ".join(f"{r.name} ({r.detail})" for r in failures)


def test_golden_suite_is_non_trivial():
    assert len(load_cases()) >= 10
