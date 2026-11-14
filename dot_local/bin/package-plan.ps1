#Requires -Version 5.1
& python (Join-Path $PSScriptRoot 'package_layers.py') @args
exit $LASTEXITCODE
