$ErrorActionPreference = 'Stop'
$cleanupSource = 'C:\Users\mdsch\Desktop\rocketry\gpt_context\outputs\power_setup_cleanup\after\power_setup.kicad_sch'
$cleanupTarget = 'C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1\power_setup.kicad_sch'
$cleanupExpectedHash = '19AC1945F7407F391218DDAA0B63D543A16060B8916B22368B32BD1215BC1D82'
if ((Get-FileHash -LiteralPath $cleanupTarget).Hash -ne $cleanupExpectedHash) {
    throw 'The project sheet changed after the snapshot. Refusing to overwrite new user edits.'
}
Copy-Item -LiteralPath $cleanupSource -Destination $cleanupTarget
if ((Get-FileHash -LiteralPath $cleanupTarget).Hash -ne (Get-FileHash -LiteralPath $cleanupSource).Hash) {
    throw 'Post-copy verification failed.'
}
Write-Output 'Updated only the existing power_setup.kicad_sch; backup remains under gpt_context.'
