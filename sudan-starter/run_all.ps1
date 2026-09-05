$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    conda run --no-capture-output -n pypsa python scripts/fetch_data.py
    if ($LASTEXITCODE -ne 0) { throw 'Source retrieval or verification failed' }
    conda run --no-capture-output -n pypsa python scripts/prepare_data.py
    if ($LASTEXITCODE -ne 0) { throw 'Data preparation failed' }
    conda run --no-capture-output -n pypsa python run_model.py --scenario all
    if ($LASTEXITCODE -ne 0) { throw 'Model solve failed' }
    conda run --no-capture-output -n pypsa python scripts/make_report.py
    if ($LASTEXITCODE -ne 0) { throw 'Report generation failed' }
    conda run --no-capture-output -n pypsa python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Validation failed' }
} finally { Pop-Location }
