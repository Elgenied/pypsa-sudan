# Reference year: 2022

Decision made 5 September 2026. **Use calendar year 2022 for the historical research baseline.** This is the latest year in the current UNSD Electricity Profiles edition in which Sudan's total, hydro and combustible generation are all unflagged. It is not a claim that every required 2022 network input is available or verified. The model is a national annual calibration benchmark; a defensible regional reconstruction remains unfinished.

## Why this year

The [UNSD current-edition catalog](https://unstats.un.org/unsd/energystats/pubs/eprofiles/) lists Electricity Profiles 2023, covering 2018–2023. Its [Sudan table, printed p.196 / PDF p.30](https://unstats.un.org/unsd/energystats/pubs/eprofiles/2023/prt.pdf#page=30) marks 2023 headline generation, hydro and combustible generation with asterisks. The [symbol definitions](https://unstats.un.org/unsd/energystats/pubs/eprofiles/2023/04.pdf) identify these as UNSD estimates. Their 2022 counterparts are not starred. Unflagged does not establish independent measurement or complete coverage.

Later statistics exist, but do not provide a better consistent operating-system reconstruction in the sources reviewed. The [IRENA Sudan profile](https://www.irena.org/-/media/Files/IRENA/Agency/Statistics/Statistical_Profiles/Africa/Sudan_Africa_RE_SP.pdf) gives a materially different 2023 generation total; these series must not be spliced silently. The [CBOS 2025 review](https://cbos.gov.sd/sites/default/files/Econ_stat_rview_2025.pdf) examined here is mainly macroeconomic and trade statistics, not a full plant/network operating inventory. This source review is not proof that no later utility dataset exists.

2022 also avoids mixing the existing 2024 wartime availability ledger with pre-conflict demand. The 2021 CCG starter kit remains useful for historical parameters and methodology, but its 2018 assets and future projections do not become 2022 observations.

## Source values and flags

The transcription is in `data/reference/unsd_2022/statistics.csv`; source URLs, page, retrieval date and PDF SHA-256 are in `source_manifest.json`. Original PDFs are not republished. Figures include main activity producers and autoproducers.

| 2022 statistic | Value | UNSD status |
|---|---:|---|
| Net installed capacity | 4,209 MW | Not flagged |
| Combustible / hydro / Other capacity | 2,134 / 1,885 / 190 MW | Other estimated |
| Gross generation | 16,771 GWh | Not flagged |
| Hydro / combustible / Other gross output | 11,804 / 4,842 / 126 GWh | Not flagged |
| Plant own use / net generation | 740 / 16,031 GWh | Not flagged |
| Imports / system losses | 882 / 3,652 GWh | Not flagged |
| Consumption | 13,261 GWh | Estimated |
| Exports | Missing/not applicable | Not an observed zero |

The source's main-activity-only capacity is 3,950 MW, so the implied autoproducer difference is 259 MW. Neither total is interchangeable with the legacy 3,647.4 MW selected plant list, which has a different date, coverage and nameplate basis. No invented residual plant has been added to close that gap.

## Accounting and dispatch

The [UNSD definitions](https://unstats.un.org/unsd/energystats/pubs/eprofiles/2023/03.pdf) distinguish gross generation, station own use, net generation and net capacity. The new benchmark therefore models **net supply** against consumption plus transmission/distribution losses:

`16,031 + 882 = 13,261 + 3,652 GWh`.

Exports are assumed zero to close this published balance; the missing source cell remains missing. Station own use is already deducted from generation and must not be added to this model's load a second time. System losses include nontechnical losses, not only physical line losses.

Technology gross outputs sum to 16,772 GWh, one GWh above the rounded headline total. The model preserves both source figures and allocates net generation by `technology gross / 16,772 * 16,031`. This assumes proportional station own use and rounding adjustment across technologies; derived net technology targets are **not observed data**.

The one-bus PyPSA model uses all 8,760 hours of 2022, fixed installed net capacity, synthetic hourly consumption and loss profiles, an annual net hydro energy ceiling, flat imports and flat Other output. Other remains aggregated and is not assigned a solar profile. The import generator's MW value represents fixed annual-average energy accounting, **not interconnector capacity**. Hydro can shift energy freely within the year; there are no reservoirs, monthly inflows, outages, ramping or internal network constraints. Illustrative marginal costs establish a dispatch order, not a calibrated economic result. Combustible generation is the residual after lower-cost hydro, fixed Other and imports.

Matching annual input totals is calibration and accounting verification, not independent validation. The model's demand represents historically supplied consumption plus losses; suppressed or latent demand is unknown. Zero model shortage cannot be interpreted as zero historical outages. Monthly dispatch should not be cited as actual monthly generation.

## Files and next work

- Default command: `python run_model.py`; results in `results/reference_2022/`.
- Code: `src/pypsa_sudan/reference.py`; configuration: `config/reference_2022.json`.
- `python scripts/make_reference_report.py` builds the default `START_HERE.html` viewer.
- The earlier regional module, curated plant/corridor tables, six scenarios and notebook remain **legacy 2024 illustrations**. Run them explicitly with `python run_model.py --scenario all`; `python scripts/make_report.py` writes `LEGACY_2024.html`.
- Reconstruct a dated **2022 plant/unit ledger**, reconcile net/gross capacity and autoproducer coverage, then assign plants to verified substations. Do not copy 2024 available MW or outages into 2022.
- Obtain **2022 line and transformer connectivity/ratings**, commissioning dates and a dated network diagram before interpreting regional congestion.
- Obtain **monthly demand, hydro output and import flows**, ideally hourly demand, hydrology/reservoir constraints, fuel costs and outages. Use separate observations for validation and sensitivity ranges where unavailable.
- Define a research question and contribution (for example, an open and validated historical network with uncertainty quantified). Archive a versioned release, check data redistribution rights, and follow the publication roadmap before making policy claims.
