PYTHON ?= python3

.PHONY: all pipeline test report figures

all: pipeline test

pipeline:
	$(PYTHON) -m src.run_pipeline
	$(PYTHON) -m src.build_report

test:
	$(PYTHON) -m pytest -q

figures:
	$(PYTHON) -m src.make_figures

report:
	$(PYTHON) -m src.build_report
