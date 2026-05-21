$root = Split-Path -Parent $PSScriptRoot
Get-ChildItem -Path $root -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Önbellek temizlendi: $root"
