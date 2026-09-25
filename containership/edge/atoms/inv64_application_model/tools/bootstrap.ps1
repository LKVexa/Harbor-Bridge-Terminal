# Day-0 bootstrap for Windows hosts (MC-02 / MC-33). Mirrors tools/bootstrap.sh.
#   usage: powershell -File tools\bootstrap.ps1 [-Certification] [-Wheelhouse DIR]
param([switch]$Certification, [string]$Wheelhouse = "")
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Parent = Split-Path -Parent $Here
$Venv = if ($env:INV64_VENV) { $env:INV64_VENV } else { Join-Path $Parent ".inv64-venv" }
py -3 -c "import sys; assert (3,10) <= sys.version_info[:2] <= (3,13), sys.version"
if ($LASTEXITCODE -ne 0) { Write-Error "unsupported Python (need 3.10-3.13; see compatibility.json)"; exit 2 }
py -3 -m venv $Venv
$Py = Join-Path $Venv "Scripts\python.exe"
if ($Wheelhouse) { & $Py -m pip install --no-index --find-links $Wheelhouse "inv64-application-model[crypto]" }
else { & $Py -m pip install -c (Join-Path $Here "constraints-certification.txt") "$Here[crypto]"; if ($LASTEXITCODE -ne 0) { & $Py -m pip install --no-deps $Here } }
& $Py -m pip check
Set-Location $Parent
$args = @("-m", "inv64_application_model.tools.preflight", "--out", (Join-Path $Here "evidence\PREFLIGHT.json"))
if ($Certification) { $args += "--certification" }
& $Py @args
exit $LASTEXITCODE
