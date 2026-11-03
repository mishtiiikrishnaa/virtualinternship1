.PHONY: week1 week2 week3 week4 test clean

PYTHON ?= python3

week1:
	$(MAKE) -C weeks/week1 all

week2:
	cd weeks/week2 && $(PYTHON) -m src.fetch_real_data
	cd weeks/week2 && $(PYTHON) -m src.generate_data
	cd weeks/week2 && $(PYTHON) -m src.clean
	cd weeks/week2 && $(PYTHON) -m src.analyze
	cd weeks/week2 && $(PYTHON) -m src.make_figures
	cd weeks/week2 && $(PYTHON) -m src.build_report
	cd weeks/week2 && $(PYTHON) -m src.build_notebook
	cd weeks/week2 && $(PYTHON) -m src.audit

week3:
	@echo "week 3 has not started yet — see weeks/week3/README.md"

week4:
	@echo "week 4 has not started yet — see weeks/week4/README.md"

test:
	cd weeks/week1 && $(PYTHON) -m pytest -q
