# Data sources and acquisition log

Sources checked 5 September 2026. Download timestamps, exact URLs, byte sizes and SHA-256 values are in `data/raw/download_manifest.json`. `scripts/fetch_data.py` validates the archived inputs or fetches missing copies. Source update dates must not be confused with the dates of the assets they describe.

| ID | Primary source | Used for | Important limitation |
|---|---|---|---|
| WB_STATUS_2024 | [World Bank: Updates of Electricity and Petroleum Report in Sudan](https://documents1.worldbank.org/curated/en/099080625100525928/pdf/P171810-aceaafc9-7439-4838-974c-81284effd33a.pdf) | Downloaded; manually transcribed plant facts and dated status; grid split and import context | Status refers to August 2024; published/disclosed later. PDF pages 11–13 contain Annexes 1–2; page 7 contains grid context. Not a 2026 operating dataset. |
| WB_AICD | [Sudan transmission catalog](https://datacatalog.worldbank.org/search/dataset/0067111/sudan-electricity-transmission-network) and [ENERGYDATA record](https://energydata.info/dataset/sudan-electricity-transmission-network) | Downloaded ZIP and XML; historical geometry and original endpoints | Release year 2009; many source maps 2004–2008. Catalog metadata refreshed in 2025/2026 does not make the network contemporary. No usable MW ratings. |
| WRI_GPPD | [WRI Global Power Plant Database repository](https://github.com/wri/global-power-plant-database) | Downloaded global CSV and README; 19 historical SDN-labelled candidates; selected coordinate matches | WRI README says maintenance stopped in early 2022. Downloaded master bytes are hashed, not claimed to be a fresh 2026 census or a formally tagged release. |
| WB_DIAGNOSTIC | [From Subsidy to Sustainability: Diagnostic Review](https://documents.worldbank.org/curated/en/486961588608080192/pdf/From-Subsidy-to-Sustainability-Diagnostic-Review-of-Sudan-Electricity-Sector.pdf) | Downloaded historical report; useful pre-conflict calibration reference | Historical statistics/plans must be separated from commissioned assets and actual subsequent generation. Not used to scale this model's synthetic demand. |
| NATURAL_EARTH | [Natural Earth vector data](https://github.com/nvkelso/natural-earth-vector) | Downloaded 1:110m countries; approximate Sudan outline and coarse spatial screening | Coastal points and disputed boundaries need finer review. Never treat a coarse clip as authoritative border adjudication. |
| UNDP_2026 | [Solar Energy Value Chain Study, 18 May 2026](https://www.undp.org/sudan/publications/solar-energy-value-chain-study) | Read publication-page summary; identifies current distributed-solar research needs | The PDF download returned HTTP 403; not archived or used to assert plant capacities. It is not a verified plant-by-plant 2026 status list. |
| OSM_HISTORIC | [openAFRICA Sudan network record](https://open.africa/dataset/sudan-electricity-transmission-network-2013) | Research lead for alternative historic lines/substations | Page describes a 2013 collection despite its 2017 title. Old API resource was unavailable. This ODbL dataset was not downloaded or integrated. |
| OSM_CURRENT | [OpenStreetMap Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) | Attempted national power-line and substation query | Endpoint returned HTTP 406. No current OSM geometry was obtained; this model does not claim a current OSM-derived topology. Query retained in raw folder. |
| ASSUMPTION | Project modelling choices | Demand, marginal costs, transfer limits, hydro energy, partial diesel operation | Editable and uncalibrated. Never cite these values as observed facts. |

## Where to start next

1. **Utility and ministry records:** Sudan Electricity Company and the responsible generation/transmission/dispatch teams. Request monthly generation, unit availability, substation single-line diagrams, transformer and line ratings, regional energy and scheduled/unplanned outages. The prepared data-request template lists exact fields.
2. **Transmission geometry:** use a dated OSM extract through the PyPSA-Earth workflow and compare to the utility diagram, World Bank map and historical GIS. Open mapping is a starting point; missing tags, substations and connectivity require repair. Use ODbL-compatible publication arrangements if deriving a database from OSM.
3. **Plant cross-checks:** [Global Energy Monitor's Global Integrated Power Tracker](https://globalenergymonitor.org/projects/global-integrated-power-tracker/) and manufacturer/utility commissioning records. Check project status and technology-specific coverage; do not infer operation from a project listing. This starter has not downloaded GEM tables.
4. **Demand:** obtain observed hourly data if possible. Otherwise anchor public synthetic demand profiles to separately verified monthly/national energy and spatial population/industry estimates. Distinguish served electricity, suppressed demand and unmet demand. Sudan's population displacement makes static pre-war allocations questionable.
5. **Renewables/hydro:** PyPSA-Earth/atlite workflows can build weather-based wind and solar profiles; use river inflows and reservoir records for hydro. These datasets and a full-year weather cutout have not been fetched for this starter.
6. **Access and distributed energy:** the UNDP 2026 solar study and World Bank [ASCENT-Sudan project announcement](https://www.worldbank.org/en/news/press-release/2025/06/02/advancing-energy-and-digital-connectivity-in-afe-sudan-new-project-to-support-private-sector) are leads for decentralized supply. Project targets are not commissioned-capacity observations.

## Audit files

- `data/processed/wri_sudan_candidates_audit.csv`: original candidates, location screening and review decisions.
- `data/processed/transmission_feature_audit.csv`: all 30 historical features, including excluded study/planned projects.
- `data/processed/plants_geolocated.csv`: plant records with coordinate confidence and historical WRI IDs.
- `data/processed/plants.geojson`: GIS points; inspect `coordinate_quality` before using locations.
- `data/processed/historical_transmission_clipped.geojson`: historical context only, not the solved electrical topology.
- `data/curated/corridors.csv`: actual model topology, with explicit capacity assumptions.

The model never automatically appends every WRI candidate, converts every GIS feature to an active branch, or equates voltage with transmission capacity.
