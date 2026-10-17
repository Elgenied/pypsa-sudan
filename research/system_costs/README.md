# Sudan system-cost notebook

Open [Sudan_System_Costs.ipynb](Sudan_System_Costs.ipynb) or the [HTML reading copy](Sudan_System_Costs.html). All cost analysis is in this single notebook, supported by editable [data/system_costs](../../data/system_costs/README.md).

Four fixed illustrative designs: 100 standalone homes, a 100-home mini-grid, grid extension and grid extension with synthetic repairs. Three cost/finance scenarios, component budgets, cash-flow ledger and one-at-a-time sensitivities are calculated. Numerical tests check accounting and units. Prices and feasibility are **not independently validated**. No least-cost winner or national total is reported.

Run from the repository root:

```shell
python research/system_costs/check_costs.py
python research/system_costs/run_notebook.py --kernel pypsa
```

`build_notebook.py` regenerates the notebook structure if its presentation changes. Inputs are edited in CSVs; `cost_model.py` is the reusable accounting engine. Outputs are generated under `results/`. Neither the 2022 dispatch notebook nor source evidence is modified by running this module.
