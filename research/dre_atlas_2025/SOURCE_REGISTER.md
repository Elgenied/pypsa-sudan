# Provenance, methods and limits

The [World Bank Group Sudan DRE Atlas dataset](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre) is the public source for settlement CSV, GeoJSON and [data dictionary](https://energydata.info/dataset/sudan-distributed-renewable-energy-dre/resource/2f3a5000-7663-45e1-8e60-421c45ef1c2d). Its source platform is the [VIDA Sudan DRE Atlas](https://map.vida.place/public/workspace/c35ba2f6-7fc0-4a04-8c06-88c084ea9be6). Catalog release/last update: **12 June 2025**. Dataset licence: **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**. Attribute/geometry files here are transformed from that release; credit World Bank Group / VIDA and the original layer providers when publishing derivatives.

The project user supplied *DRE Atlas Planning Platform — Technical Documentation*, prepared by VIDA for World Bank Group / ESMAP / IFC. The source PDF is not redistributed in this repository. The report describes the processing steps and source dates below. A [public Atlas user guide](https://vidaplace.notion.site/dre-atlas-user-guide) provides platform instructions. `data/attribute_dictionary.csv` reproduces the source dictionary's Overview definitions. Dictionary rows cover all countries, so some documented fields are absent from Sudan's 42-column download.

| Input | Documented method and source period | Planning interpretation |
|---|---|---|
| Settlement outlines/buildings | VIDA clustering of merged Google and Microsoft building footprints; buildings ≥15 m² used for potential connections; imagery may be several years old | Spatial starting points, not verified households or current structures |
| Population | Building-based model with GHSL urban/rural classification and World Bank population calibration; documentation differs between national and subnational wording | Modeled counts, not settlement census observations |
| Demand | 1.1 large + 0.65 medium + 0.335 small building kWh/day; all eligible buildings considered potential connections | Fixed low-service estimate; no hourly profile, peak, demand growth or productive load |
| Grid distance | Direct distance to existing line geography; Sudan download has one mixed/unknown-voltage field | Does not establish route, status, capacity, transformer or grid connection cost |
| Nightlights | VIIRS/VIDA GridLight, Sep 2022–Aug 2023 | Overlap is a proxy; does not certify household access; period crosses the 2023 war onset |
| Solar | Global Solar Atlas long-run mean 1994–2015 kWh/kWp/year at optimum conditions | Annual resource screen; no hourly generation or feasible siting area |
| Roads/facilities | OpenStreetMap main roads and education/health POIs; roads within 500 m counted as access | Completeness and date uncertain; facilities may be counted near multiple settlements |
| Agriculture | MapSPAM 2017 sub-Saharan Africa, admin-2 values copied to settlements | Do **not** sum across settlements; not a site-level farm forecast |
| Conflict exposure | ACLED 2020–2022 fatalities by event type in 25/50 km circles | `high`: ≥1 within 25 km; `medium`: none within 25 but ≥1 within 50; `low`: none within 50. **Never a current safety rating**. Buffers overlap, so fatalities cannot be summed nationally |
| Relative wealth | Meta index | Only 23 of 33,891 Sudan sites have a value; omit from national financial choices |

The source dictionary describes `total_incidents_50km` as within 20 km, an apparent copy error; the column name and technical report say 50 km. Four source building-density values exceed 100%, one nightlight flag disagrees with positive overlap and seven road flags differ from the comparison with *rounded* 0.50 km distance. These records are preserved and counted in `validation_report.json`.

Original source SHA256: CSV `63c23d9920cc7faebc800fda2256ac857b2971fd10c321b66c810595853723e3`; GeoJSON `d49923f7091db61dd41f6995afa615fc87d67c848139128701dc3bfe988ffcc9`; dictionary XLSX `fd49f1e0d2ace31b7e5dda27a648f1f1f15a187da04c7539646a44064b219905`. Transformation and derived hashes are recorded in [validation_report.json](data/validation_report.json).

### Separate grid layer to assess later

The [World Bank Sudan Electricity Transmission Network](https://energydata.info/dataset/sudan-electricity-transmission-network) is a CC BY 4.0 shapefile with **30** line features and voltage/status fields. Its **release year is 2009**, even though the catalog page was updated in 2025. Some geometries lie in what is now South Sudan. It may help trace historical routes but must not be interpreted as a verified current Sudan network. The DRE settlement CSV contains a distance to grid, **not** the underlying route geometry or line ratings. The VIDA map can show lines and incident points as separate layers; this collection does not claim those layers are inside the settlement download.
