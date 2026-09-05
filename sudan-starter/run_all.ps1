$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    conda run --no-capture-output -n pypsa python run_model.py
    if ($LASTEXITCODE -ne 0) { throw '2022 model solve failed' }
    conda run --no-capture-output -n pypsa python scripts/make_reference_report.py
    if ($LASTEXITCODE -ne 0) { throw 'Report generation failed' }
    conda run --no-capture-output -n pypsa python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Validation failed' }
} finally { Pop-Location }
