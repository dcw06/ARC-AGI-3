# Run the project's Linux Python from PowerShell.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$linuxPath = & wsl.exe -d Ubuntu -- wslpath -a $projectRoot.Replace('\', '/')
if ($LASTEXITCODE -ne 0) { throw 'Unable to resolve the project path in Ubuntu WSL.' }
$linuxRoot = $linuxPath.Trim()
& wsl.exe -d Ubuntu --cd $linuxRoot -- env MPLCONFIGDIR="$linuxRoot/.cache/matplotlib" XDG_CACHE_HOME="$linuxRoot/.cache" KAGGLE_CONFIG_DIR="$linuxRoot/.kaggle" .venv/bin/python @args
exit $LASTEXITCODE
