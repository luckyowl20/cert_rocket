$ErrorActionPreference = 'Stop'
$projectDir = 'C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1'
$auditDir = $PSScriptRoot
$manifest = Get-Content -LiteralPath (Join-Path $auditDir 'manifest.json') -Raw | ConvertFrom-Json
$sheetPath = Join-Path $projectDir 'power_setup.kicad_sch'
$actualHash = (Get-FileHash -LiteralPath $sheetPath -Algorithm SHA256).Hash
if ($actualHash -ne $manifest.source_sha256) { throw 'Schematic changed since inspection; stop rather than overwrite user edits.' }
$stagedDir = Join-Path $auditDir 'staged'
foreach ($subdir in @('avionics_footprints.pretty','footprint_3D_models')) {
    $destinationDir = Join-Path $projectDir $subdir
    if (-not (Test-Path -LiteralPath $destinationDir)) { New-Item -ItemType Directory -Path $destinationDir | Out-Null }
    foreach ($asset in Get-ChildItem -LiteralPath (Join-Path $stagedDir $subdir) -File) {
        $destination = Join-Path $destinationDir $asset.Name
        if (Test-Path -LiteralPath $destination) {
            if ((Get-FileHash -LiteralPath $destination).Hash -ne (Get-FileHash -LiteralPath $asset.FullName).Hash) {
                throw "Existing different asset: $destination"
            }
        }
    }
}
foreach ($subdir in @('avionics_footprints.pretty','footprint_3D_models')) {
    foreach ($asset in Get-ChildItem -LiteralPath (Join-Path $stagedDir $subdir) -File) {
        $destination = Join-Path (Join-Path $projectDir $subdir) $asset.Name
        if (-not (Test-Path -LiteralPath $destination)) { Copy-Item -LiteralPath $asset.FullName -Destination $destination }
    }
}
Copy-Item -LiteralPath (Join-Path $stagedDir 'power_setup.kicad_sch') -Destination $sheetPath
Write-Output 'Installed eight footprints and eight model references; updated power_setup only. Original sheet preserved in audit/before.'
