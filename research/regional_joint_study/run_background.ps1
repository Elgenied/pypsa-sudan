param(
    [string]$Python = (Join-Path $env:USERPROFILE 'miniconda3\envs\pypsa\python.exe'),
    [string]$Mirror,
    [int]$WaitPid = 0,
    [switch]$Publish
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python)) { throw "Python environment not found: $Python. Supply -Python with its executable path." }
$studyRoot = $PSScriptRoot
$repositoryRoot = Split-Path (Split-Path $studyRoot -Parent) -Parent
$studyRunner = Join-Path $studyRoot 'run_study.py'
$stdout = Join-Path $studyRoot 'batch_stdout.log'
$stderr = Join-Path $studyRoot 'batch_stderr.log'
$arguments = ('"{0}"' -f $studyRunner)
if ($Mirror) { $arguments += (' --mirror "{0}"' -f $Mirror) }
if ($WaitPid -gt 0) { $arguments += (' --wait-pid {0}' -f $WaitPid) }
if ($Publish) { $arguments += ' --publish' }
$process = Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $repositoryRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Write-Output "Started study driver PID $($process.Id). Open $(Join-Path $studyRoot 'RUN_STATUS.html') for progress."
