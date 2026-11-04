<a id="readme-top"></a>

<!-- project shields -->
[![contributors][contributors-shield]][contributors-url]
[![forks][forks-shield]][forks-url]
[![stargazers][stars-shield]][stars-url]
[![issues][issues-shield]][issues-url]

<!-- project logo -->
<br />
<div align="center">

<h3 align="center">virtualinternship1</h3>

  <p align="center">
    a four-week virtual logistics data analysis internship: public logistics data, python pipelines, and the written report that goes with each week.
    <br />
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks"><strong>explore the weeks »</strong></a>
    <br />
    <br />
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks/week1">week 1</a>
    &middot;
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks/week2">week 2</a>
    &middot;
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks/week3">week 3</a>
    &middot;
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/issues/new?labels=bug">report bug</a>
    &middot;
    <a href="https://github.com/mishtiiikrishnaa/virtualinternship1/issues/new?labels=enhancement">request feature</a>
  </p>
</div>

<!-- table of contents -->
<details>
  <summary>table of contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">about the project</a>
      <ul>
        <li><a href="#the-four-weeks">the four weeks</a></li>
        <li><a href="#built-with">built with</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">getting started</a>
      <ul>
        <li><a href="#prerequisites">prerequisites</a></li>
        <li><a href="#installation">installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">usage</a></li>
    <li><a href="#repository-layout">repository layout</a></li>
    <li><a href="#roadmap">roadmap</a></li>
    <li><a href="#contributing">contributing</a></li>
    <li><a href="#license">license</a></li>
    <li><a href="#contact">contact</a></li>
    <li><a href="#acknowledgments">acknowledgments</a></li>
  </ol>
</details>

<!-- about the project -->
## about the project

<!-- add a screenshot of a generated figure or report page here, e.g.
[![product name screen shot][product-screenshot]](https://example.com) -->

this repository holds the work for a four-week virtual internship in logistics data analysis. it covers collecting and cleaning public logistics data with python, exploring it, and modelling it, with a written report for every week.

here's why it is set up this way:

* each week lives in its own directory with its own report, code, data contract and generated artefacts
* nothing from a later week overwrites an earlier one, so a reviewer can read week 1 without wading through week 4, and the commit history for each week stays legible
* weeks 2 onward build on the schema contract and entry point introduced in week 1, so the structure stays deliberately shallow: one folder per week, no shared package to break, and a root `Makefile` that delegates
* the internship asks for a single project url, and splitting four weeks across four repositories would hide the progression. one repository keeps the diff readable, including what the week 1 contract had to learn when the week 2 dataset arrived

week 1 in particular ships a python pipeline with a schema contract, 13 validation checks, 19 tests and generated reports.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### the four weeks

| week | focus                                                 | status      | folder                                                                                        |
|------|-------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------|
| 1    | strategic data collection and preprocessing blueprint | submitted   | [`weeks/week1`](https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks/week1) |
| 2    | exploratory data analysis and visualization           | submitted   | [`weeks/week2`](https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks/week2) |
| 3    | predictive modelling and forecasting                  | submitted   | [`weeks/week3`](https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks/week3) |
| 4    | not started                                           | not started | [`weeks/week4`](https://github.com/mishtiiikrishnaa/virtualinternship1/tree/main/weeks/week4) |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### built with

* [![python][python-shield]][python-url]
* [![pandas][pandas-shield]][pandas-url]
* [![plotly][plotly-shield]][plotly-url]
* [![pytest][pytest-shield]][pytest-url]
* [![gnu make][make-shield]][make-url]

report tooling: [pandoc](https://pandoc.org/) and [libreoffice](https://www.libreoffice.org/) for building the `.docx` / pdf reports, and [ghostscript](https://www.ghostscript.com/) for compressing the week 2 pdf.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- getting started -->
## getting started

to get a local copy up and running, follow these steps.

### prerequisites

* python 3 (the `Makefile` calls `python3`) and `pip`
* `make` (optional, for the root-level shortcuts)
* only needed for rebuilding reports:
  * **week 1**: `pandoc` and `libreoffice` to rebuild the `.docx`
  * **week 2**: a chrome build for plotly's static image export (one-time), `libreoffice` to render the pdf, and `ghostscript` to compress it
  * **week 3**: `libreoffice`, and only for the optional pdf proof (no pandoc needed)

### installation

each week has its own dependencies, so set up a virtual environment inside the week you want to run.

1. clone the repo
   ```sh
   git clone https://github.com/mishtiiikrishnaa/virtualinternship1.git
   cd virtualinternship1
   ```
2. create a virtual environment and install the requirements for a week (week 1 shown)
   ```sh
   cd weeks/week1
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. for week 2 only, download chrome once so plotly can export static images
   ```sh
   plotly_get_chrome -y
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- usage -->
## usage

### week 1: data collection and preprocessing

```sh
cd weeks/week1
python -m src.run_pipeline    # clean, validate, publish, regenerate the report
python -m pytest -q           # 19 tests
python -m src.build_report    # rebuild the .docx (needs pandoc + libreoffice)
```

### week 2: exploratory data analysis and visualization

from the repository root, `make week2` runs the whole chain in order:

```sh
python3 -m src.fetch_real_data
python3 -m src.generate_data
python3 -m src.clean
python3 -m src.analyze
python3 -m src.make_figures
python3 -m src.build_report
sh src/render_pdf.sh
python3 -m src.build_notebook
python3 -m src.audit
```

### week 3: predictive modelling and forecasting

```sh
cd weeks/week3
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.run_pipeline    # build features, models, figures, results, report
python -m pytest -q           # 13 tests
python -m src.build_report    # rebuild the .docx (no pandoc; libreoffice only for the optional pdf proof)
```

### from the repository root

```sh
make week1    # run the week 1 pipeline
make week2    # run the week 2 chain
make week3    # run the week 3 pipeline
make week4    # placeholder: week 4 has not started yet
make test     # run the week 1 and week 3 test suites
```

see each week's own folder for its report, data contract and generated artefacts.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- repository layout -->
## repository layout

```
virtualinternship1/
├── Makefile                 # delegates: make week1 / week2 / week3 ...
├── README.md                # this file
└── weeks/
    ├── week1/               # strategy, pipeline, diagrams, submitted .docx
    │   ├── config/          # schema contract
    │   ├── data/            # raw (seeded, committed) and processed (generated)
    │   ├── docs/            # report source, source register, dictionary, decisions
    │   ├── reports/         # generated quality report, submitted docx + pdf
    │   ├── src/             # ingest, clean, validate, run, figures, docx build
    │   └── tests/
    ├── week2/               # eda and visualization
    ├── week3/               # predictive modelling and forecasting
    └── week4/               # not started
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- roadmap -->
## roadmap

- [x] week 1: strategic data collection and preprocessing blueprint
- [x] week 2: exploratory data analysis and visualization
- [x] week 3: predictive modelling and forecasting
- [ ] week 4

see the [open issues](https://github.com/mishtiiikrishnaa/virtualinternship1/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- contributing -->
## contributing

this is a personal internship project, but suggestions and fixes are welcome. if you have a suggestion that would make this better, please fork the repo and create a pull request. you can also simply open an issue with the tag "enhancement".

1. fork the project
2. create your feature branch (`git checkout -b feature/amazingfeature`)
3. commit your changes (`git commit -m 'add some amazingfeature'`)
4. push to the branch (`git push origin feature/amazingfeature`)
5. open a pull request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- license -->
## license

<!-- add a LICENSE file to the repo (e.g. via https://choosealicense.com), then name it here -->
no license file has been added yet. once one is added, this section should read: distributed under the [license name] license. see `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- acknowledgments -->
## acknowledgments

* [best-readme-template](https://github.com/othneildrew/Best-README-Template) by othneildrew, which this readme is based on
* [choose an open source license](https://choosealicense.com)
* [img shields](https://shields.io)
* [plotly static image export](https://plotly.com/python/static-image-export/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- markdown links & images -->
[contributors-shield]: https://img.shields.io/github/contributors/mishtiiikrishnaa/virtualinternship1.svg?style=for-the-badge
[contributors-url]: https://github.com/mishtiiikrishnaa/virtualinternship1/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/mishtiiikrishnaa/virtualinternship1.svg?style=for-the-badge
[forks-url]: https://github.com/mishtiiikrishnaa/virtualinternship1/network/members
[stars-shield]: https://img.shields.io/github/stars/mishtiiikrishnaa/virtualinternship1.svg?style=for-the-badge
[stars-url]: https://github.com/mishtiiikrishnaa/virtualinternship1/stargazers
[issues-shield]: https://img.shields.io/github/issues/mishtiiikrishnaa/virtualinternship1.svg?style=for-the-badge
[issues-url]: https://github.com/mishtiiikrishnaa/virtualinternship1/issues
[linkedin-shield]: https://img.shields.io/badge/-linkedin-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/your_linkedin_username
[python-shield]: https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/
[pandas-shield]: https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white
[pandas-url]: https://pandas.pydata.org/
[plotly-shield]: https://img.shields.io/badge/plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white
[plotly-url]: https://plotly.com/python/
[pytest-shield]: https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white
[pytest-url]: https://docs.pytest.org/
[make-shield]: https://img.shields.io/badge/gnu%20make-A42E2B?style=for-the-badge&logo=gnu&logoColor=white
[make-url]: https://www.gnu.org/software/make/
