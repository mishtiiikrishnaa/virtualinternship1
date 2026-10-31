.PHONY: data clean test figures report all

data:
	python -m src.make_sample_data

clean:
	python -m src.run_pipeline

test:
	python -m pytest -q

figures:
	python -m src.make_figures

report:
	python -m src.build_report

all: data clean test figures report
