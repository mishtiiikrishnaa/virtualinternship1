PYTHON ?= python3

.PHONY: all pipeline test report figures clean audit

all: pipeline report audit

pipeline:
	$(PYTHON) -m src.run_pipeline
	$(PYTHON) -m src.build_report

report:
	$(PYTHON) -m src.build_report

audit:
	$(PYTHON) -m src.audit_report_numbers

test:
	$(PYTHON) -m pytest -q

figures:
	$(PYTHON) -m src.make_figures

clean:
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache
