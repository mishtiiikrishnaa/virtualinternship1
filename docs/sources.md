# Public data source register

A register rather than a bibliography: each row states what the dataset
actually contains, how it is reached, and what stops it being used naively.
Licence notes are a reading of the publisher's terms at the time of writing
(October 2026) and should be re-checked before any redistribution.

## Freight flow and volume

| # | dataset | publisher | grain | access | licence / consideration | week 1 use |
|---|---|---|---|---|---|---|
| 1 | Freight Analysis Framework (FAF5.7.1 / FAF6) | US Bureau of Transportation Statistics | origin–destination flows by mode, commodity, 132 zones | bulk `.csv` / Access download, plus an interactive tabulation tool | US federal work, effectively public domain; cite BTS and the version number | Primary candidate: schema is documented and the grain is unambiguous |
| 2 | Commodity Flow Survey | BTS / US Census Bureau | sampled shipments, shipper-reported | bulk download, published tables | public; sampling weights must be applied or estimates are wrong | Deferred: needs survey weighting before any per-shipment claim |
| 3 | Border Crossing / Entry Data | BTS | monthly counts per port, mode and direction | bulk download, API | public domain | Useful context for lane volumes; not shipment-level |
| 4 | USA Trade Online / UN Comtrade | US Census Bureau / UN Statistics Division | country–commodity–partner trade values and quantities | web query, REST API with free tier and rate limits | free with attribution; Comtrade imposes call limits, so cache responses | Candidate for lane-level value context |
| 5 | IMF PortWatch | IMF | daily port calls, transit and chokepoint activity | ArcGIS-hosted layers and downloadable files | free, attribution expected; methodology is model-based, not a census | Strong candidate for a daily activity series |
| 6 | Eurostat freight transport statistics | European Commission | tonnes-km and tonnes lifted by mode, country, NUTS region | bulk download, SDMX API | free reuse with attribution | Good for European lane context; no shipment identifiers |

## Movement, network and reference data

| # | dataset | publisher | grain | access | licence / consideration | week 1 use |
|---|---|---|---|---|---|---|
| 7 | OpenStreetMap | OSM contributors | roads, ports, terminals, boundaries | planet file, Overpass API, Geofabrik extracts | ODbL 1.0: attribution and share-alike on derived databases | Needed for any geospatial enrichment; share-alike is the constraint to plan for |
| 8 | MarineCadastre AIS | NOAA / US Bureau of Ocean Energy Management | vessel positions from terrestrial AIS | bulk download, very large | US government data with usage terms; vessel identifiers are commercially sensitive | Later phase: heavy, but the only open route to real vessel behaviour |
| 9 | OpenSky Network | OpenSky | ADS-B flight states and trajectories | REST API, registered access | research/non-commercial terms; rate limited; not a cargo dataset | Rejected for week 1: flights are not freight |
| 10 | Port authority dashboards (Rotterdam, Los Angeles, NY/NJ) | individual port authorities | monthly throughput by cargo type | HTML dashboards and PDF releases | terms vary; scraping a dashboard may breach its terms even when the numbers are public | Reference only; a PDF has to be transcribed, which is not reproducible |
| 11 | ECB / FRED reference exchange rates | European Central Bank / Federal Reserve | daily bilateral rates | free API | public, attribution expected | Required for any currency normalisation; store the series, do not call it live mid-run |

## Convenience datasets — handled with suspicion

| # | dataset | publisher | grain | access | licence / consideration | week 1 use |
|---|---|---|---|---|---|---|
| 12 | DataCo smart supply chain | Kaggle upload | order-line records with shipping and profit fields | download | licence as stated on the dataset page; provenance and generation method are not documented | Useful for teaching patterns, weak as evidence: fields look simulated |
| 13 | Supply chain shipment pricing data | Kaggle upload | shipment lines with mode, service and freight cost | download | licence varies by upload; original source unclear | Rejected: no way to verify whether the prices are real |
| 14 | Company "open data" portals (carrier APIs) | DHL, Maersk, and similar | tracking events, rate quotes | authenticated REST APIs | contractual, rate limited, often forbids redistribution of rates | Out of scope: needs an account and a commercial agreement |

## Selection criteria applied to the register

A candidate dataset had to clear five gates before being shortlisted:

1. **Grain** — is there a defensible primary key, and is the row meaning
   stated by the publisher rather than inferred by me?
2. **Licence** — may the derived table be published in this repository?
3. **Stability** — is there a version number or a dated release, so that a
   figure quoted in the report can be tied to a specific extract?
4. **Documentation** — does a codebook exist for the categorical fields?
5. **Defect plausibility** — does it contain the mess this task is about
   (missing weights, mixed units, free-text locations)?

FAF clears all five and becomes the reference dataset for weeks 2–4.
Comtrade and PortWatch are the next two to add. The Kaggle uploads fail
gates 1 and 4, which is exactly why the development pipeline runs on a
synthetic extract with documented defects instead.
