$ErrorActionPreference = 'Stop'
$sensorBase = 'C:\Users\mdsch\Desktop\rocketry\gpt_context\outputs\sensors_cleanup'
$sensorProject = 'C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1'
$sensorFiles = Get-Content -Raw -LiteralPath (Join-Path $sensorBase 'install_manifest.json') | ConvertFrom-Json
foreach ($sensorFile in $sensorFiles) {
    $sensorTarget = Join-Path $sensorProject $sensorFile.relative
    $sensorSource = Join-Path (Join-Path $sensorBase 'staged') $sensorFile.relative
    if ((Get-FileHash -LiteralPath $sensorSource).Hash -ne $sensorFile.after) { throw 'Staged content changed after verification.' }
    if ($sensorFile.before) {
        if ((Get-FileHash -LiteralPath $sensorTarget).Hash -ne $sensorFile.before) { throw "User file changed: $sensorTarget" }
    } elseif (Test-Path -LiteralPath $sensorTarget) { throw "New target already exists: $sensorTarget" }
}
foreach ($sensorFile in $sensorFiles) {
    $sensorTarget = Join-Path $sensorProject $sensorFile.relative
    $sensorSource = Join-Path (Join-Path $sensorBase 'staged') $sensorFile.relative
    Copy-Item -LiteralPath $sensorSource -Destination $sensorTarget
    if ((Get-FileHash -LiteralPath $sensorTarget).Hash -ne $sensorFile.after) { throw "Copy verification failed: $sensorTarget" }
}
Write-Output 'Installed and hash-verified 10 sensor files. Originals are backed up in outputs/sensors_cleanup/before.'
