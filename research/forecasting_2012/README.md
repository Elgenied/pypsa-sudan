# Sudan forecasting report: extracted data and partial replication

Open **[Sudan_Forecasting_Replication.html](Sudan_Forecasting_Replication.html)** to read the executed analysis, charts and findings. Open **[Sudan_Forecasting_Replication.ipynb](Sudan_Forecasting_Replication.ipynb)** to inspect or rerun the code.

The source is Lahmeyer International / Sudan Ministry of Water Resources and Electricity, *Long and Medium Term Power System Plans: Demand Forecast Report*, report 260690, final revision 18 October 2012. The source PDF has 139 pages. Its checksum and provenance are in `source_metadata.json`.

## Delivered

- One executed notebook and an HTML reading copy.
- Structured CSVs covering 19 plant/configuration records, 131 localities, historical state-sector consumption, population, GDP, hydro profiles, heat rates, transmission plans and all three forecast scenarios.
- 60 national scenario-years with 59 metrics each; 720 monthly scenario records.
- Nine figures, each saved as PNG and SVG under `results/figures/`.
- A [source register](SOURCE_REGISTER.md), [data dictionary](DATA_DICTIONARY.md), numerical validation and an explicit source-conflict register.
- The extraction script can recover 98 raw table blocks from a user-supplied PDF for local checking. Raw page exports are not distributed in this repository.

## Main findings

The report's sequential loss formula reproduces all 60 annual sent-out energy values within **0.872 GWh**, consistent with the precision of the printed data. Ten arithmetic checks pass their stated rounding tolerances.

The source itself contains unresolved differences: annual versus summed monthly energy differs by up to **1,022 GWh**, state versus national peak by up to **237 MW**, and monthly reserve calculations use a different basis from the annual 15% margin. The notebook exposes these differences rather than adjusting the extracted values to conceal them.

This is a **2012 forecast**, not observed 2022 demand or current capacity. The historical geography contains 15 states. “Committed” does not mean subsequently built; Roseires and Sennar replacement configurations must not be counted as extra independent plants. Costs have an unverified price base and do not represent post-war repair costs.

## Reproduce

From this directory, using the existing environment:

```powershell
conda activate pypsa
python run_notebook.py
```

Alternatively, open the notebook with Jupyter and select the `pypsa` Python environment, then Run All. The analysis reads the included CSVs and needs no network or original PDF. Runtime package versions are recorded in `results/runtime_versions.json`.

To regenerate the notebook layout after editing its builder:

```powershell
python build_notebook.py
python run_notebook.py
```

To redo extraction from the supplied original document (requires pandas, pypdf and pdfplumber):

```powershell
python extract_data.py --pdf "C:\path\to\Sudan_electricity_forecasting.pdf"
python build_notebook.py
python run_notebook.py
```

`extract_data.py` preserves printed numbers, with explicit parsing rules and page references. It does not digitize curves into fictitious hourly data. Its optional cache is tied to this exact report; use a new cache for any different document or revision.

## Research use

The notebook separates extracted values, recalculated quantities and unresolved source issues. It reconstructs visible loss and adequacy arithmetic; it does **not** regenerate the original locality forecasting workbook or solve an investment optimization.

Use plant parameters, historical consumption shares and seasonal hydro characteristics as evidence-backed priors after matching to the 2022 baseline. For a post-war least-cost electrification paper, add repair/availability scenarios, updated settlement demand, connection and distribution costs, renewable profiles, and explicit access and reliability constraints. The notebook's final section gives a concrete integration plan.

This package is maintained in the public PyPSA-Sudan repository under `research/forecasting_2012/`. The root `data/catalog.json` indexes its structured datasets and checksums. The supplied PDF, its full text and raw page exports are excluded. The 2022 baseline is a separate model. Original code is covered by the repository MIT licence; underlying third-party data retain their source attribution and qualifications. No licence to the original report or its presentation is granted here. See `DATA_SOURCES_AND_RIGHTS.md`.
