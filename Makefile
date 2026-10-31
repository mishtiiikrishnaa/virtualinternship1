.PHONY: week1 week2 week3 week4 test clean

week1:
	$(MAKE) -C weeks/week1 all

week2:
	@echo "week 2 has not started yet — see weeks/week2/README.md"

week3:
	@echo "week 3 has not started yet — see weeks/week3/README.md"

week4:
	@echo "week 4 has not started yet — see weeks/week4/README.md"

test:
	cd weeks/week1 && python -m pytest -q
