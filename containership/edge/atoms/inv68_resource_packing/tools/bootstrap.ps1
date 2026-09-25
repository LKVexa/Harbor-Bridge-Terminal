# INV-68 clean-environment bootstrap for Windows (MC-12). Mirrors tools/bootstrap.sh.
param([switch]$Online, [switch]$Certification, [string]$StateDir = "")
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $PSScriptRoot
$Parent = Split-Path -Parent $Here
$Py = if ($env:PYTHON) { $env:PYTHON } else { "python" }
& $Py -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; if ($LASTEXITCODE -ne 0) { Write-Error "Python >= 3.10 required"; exit 2 }
if (Test-Path "$Here\SHA256SUMS") {
  Get-Content "$Here\SHA256SUMS" | ForEach-Object {
    $d, $f = $_ -split "\s+", 2; $f = $f.TrimStart("*")
    if ((Get-FileHash -Algorithm SHA256 (Join-Path $Here $f)).Hash.ToLower() -ne $d) { Write-Error "digest mismatch: $f"; exit 3 }
  }
}
if ($Online) { if (-not (Select-String -Path "$Here\requirements-dev.lock" -Pattern "--hash=" -SimpleMatch -Quiet)) { Write-Warning "dev lock has no hashes (MC-09 open)" }; & $Py -m pip install -r "$Here\requirements-dev.lock"; if ($LASTEXITCODE -ne 0) { exit 3 } }
Push-Location $Parent
$args = @(); if ($Certification) { $args += "--certification" }; if ($StateDir) { $args += @("--state-dir", $StateDir) }
& $Py -m inv68_resource_packing.tools.preflight @args; if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
& $Py -m unittest discover -s inv68_resource_packing/tests -q; if ($LASTEXITCODE -ne 0) { Pop-Location; exit 1 }
Pop-Location
Write-Output "INV-68 bootstrap: ready"
