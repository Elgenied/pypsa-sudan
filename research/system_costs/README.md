# Sudan system-cost and electrification-pilot notebook

**Role: supporting and previous-stage analysis.** The active settlement study is [OnSSET–PyPSA recovery](../onsset_pypsa_recovery/README.md). This notebook retains the cost ledger, pilots, regional diagnostics and provenance; its older "latest experiment" wording below refers to the sequence inside this notebook, not the current project direction.

Open [Sudan_System_Costs.ipynb](Sudan_System_Costs.ipynb) or the [HTML reading copy](Sudan_System_Costs.html). All cost analysis is in this single notebook, supported by editable [data/system_costs](../../data/system_costs/README.md).

**Latest experiment: section 13 diagnoses regional technology switches with a cumulative grid-design library.** Read its before/after maps and numerical checks alongside the original six-state results in section 12. It preserves every original option, permits earlier battery-backed grid designs under improved recovery, and tests a grid-service requirement for Gezira. Supporting scripts are `regional_candidate_diagnostic.py`, `check_regional_candidates.py` and `regional_candidate_analysis.py`; the experiment remains a conditional finite-library study.

The continuation is in a **separate [section-14 notebook](../gezira_joint_planning/Sudan_Gezira_Joint_Planning.ipynb)**: Gezira joint grid/PV/battery sizing and hourly national dispatch, with the surrounding section-13 plan held fixed. See its [reproduction guide](../gezira_joint_planning/README.md).

Sections 1–6 cost four fixed illustrative designs. **Section 7 now optimizes supply for three real DRE clusters**, using 8,760 hourly NASA POWER weather observations per site, matched assumed demand and the complete lifecycle costs. Eighteen solves compare base options, grid interruption, no diesel and higher demand. Prices, routes and demand remain provisional. Conditional local rankings are reported; there is no field-validated recommendation or national total.

Run from the repository root:

```shell
python research/system_costs/check_costs.py
python research/system_costs/run_notebook.py --kernel pypsa
python research/system_costs/check_pilot.py
```

`build_notebook.py` regenerates the notebook structure if its presentation changes. Inputs are edited in CSVs; `cost_model.py` is the reusable accounting engine. Outputs are generated under `results/`. Neither the 2022 dispatch notebook nor source evidence is modified by running this module.

`pilot_model.py` performs hourly PyPSA optimization. Its [input guide](../../data/electrification_pilot/README.md) explains selection, assumptions, source metadata and limitations. The notebook reuses cached, fingerprint-checked pilot results unless inputs change; use `python research/system_costs/pilot_model.py --force` for an explicit fresh solve. `check_pilot.py` independently reconstructs feasibility and costs from the hourly outputs. All study steps remain in this one notebook.
