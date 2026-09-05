# Joining the PyPSA community

You can develop an independent project called PyPSA-Sudan and participate by sharing useful data, asking technical questions, and contributing code/documentation. Official hosting, naming within an organization, or endorsement requires agreement with maintainers; this local project does not claim it.

The most direct upstream partner is [PyPSA meets Earth](https://pypsa-meets-earth.github.io/). Read the [contribution guide](https://pypsa-earth.readthedocs.io/en/latest/community/contributing/) and use its current meeting/Discord links. The guide welcomes country-specific data and documents its code checks. Meeting times can change, so use the live page.

## A practical first contribution

1. Present this small dated Sudan model, including its limitations and data audit.
2. Ask whether a Sudan data/configuration effort already exists, to avoid duplication.
3. Propose one concrete contribution: a vetted plant-status ledger, corrected Sudan/South Sudan matching, or a verified transmission/substation subset with license and source dates.
4. Agree an upstream schema and tests. Publish only verified records and preserve uncertain observations separately.
5. Use a public issue or pull request for review when the data and rights are ready.

Suggested introduction, **draft only, not sent**:

> I am developing PyPSA-Sudan, initially as a regional dispatch model with an August 2024 World Bank plant-status reference. I have preserved source provenance and separated assumptions from observations. I would like to collaborate on Sudan-specific plant data and network validation, and contribute reusable corrections to PyPSA-Earth. Is there an existing Sudan effort I should coordinate with, and which data schema would be most useful?

## Moving to PyPSA-Earth

The [country baseline tutorial](https://pypsa-earth.readthedocs.io/en/latest/tutorials/use-cases/1-baseline-model/) describes the upstream config and Snakemake workflow. Its country code for Sudan is `SD`; South Sudan is `SS`. Our plant country screening uses the three-letter `SDN` code only when reading WRI.

`config/pypsa-earth.SD.reference.yaml` is a minimal reference based on the documented workflow. **It is not consumed by this starter and has not been executed.** Use a separate PyPSA-Earth checkout and environment, follow its installation instructions, pin a revision and inspect a dry run before downloading the larger data/weather bundles. Do not expect the small existing `pypsa` environment to contain the complete upstream stack.

After copying the reference config into a compatible PyPSA-Earth checkout:

```powershell
snakemake --cores 1 solve_all_networks --configfile config.SD.yaml --dryrun
```

Validate the upstream output against the curated Sudan ledger. Add a proper schema adapter rather than assuming `data/curated/plants.csv` can be dropped directly into PyPSA-Earth. Reconcile its automated population/demand and capacity estimates with dated Sudan observations; do not interpret automatically filled capacities as measured installations.

PyPSA-ZA is a useful country-study precedent; PyPSA-Earth is a useful reusable data/network workflow. You need not maintain a separate copy of every upstream algorithm to make a valuable Sudan contribution.
