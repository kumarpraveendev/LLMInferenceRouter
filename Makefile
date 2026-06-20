.PHONY: test eval all

test:
	pytest

eval:
	python -m evals.golden_runner

all: test eval
