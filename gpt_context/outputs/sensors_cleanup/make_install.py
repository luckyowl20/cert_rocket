from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent;P=Path('C:/Users/mdsch/Desktop/rocketry/avionics/avionics_rev1')
files=['sensors.kicad_sch','symbol_library/rocketry_library.kicad_sym']
for a in json.loads((B/'assets.json').read_text()):files.extend(['avionics_footprints.pretty/'+a['footprint']+'.kicad_mod','footprint_3D_models/'+a['model']])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
entries=[]
for rel in files:
 target=P/rel;baseline=B/'before'/target.name
 old=sha(baseline) if baseline.exists() else None
 if target.exists():
  assert old==sha(target),('Target changed or no baseline',rel)
 entries.append({'relative':rel,'before':old,'after':sha(B/'staged'/rel)})
(B/'install_manifest.json').write_text(json.dumps(entries,indent=2))
ps=f'''$ErrorActionPreference = 'Stop'
$sensorBase = '{B}'
$sensorProject = '{P}'
$sensorFiles = Get-Content -Raw -LiteralPath (Join-Path $sensorBase 'install_manifest.json') | ConvertFrom-Json
foreach ($sensorFile in $sensorFiles) {{
    $sensorTarget = Join-Path $sensorProject $sensorFile.relative
    $sensorSource = Join-Path (Join-Path $sensorBase 'staged') $sensorFile.relative
    if ((Get-FileHash -LiteralPath $sensorSource).Hash -ne $sensorFile.after) {{ throw 'Staged content changed after verification.' }}
    if ($sensorFile.before) {{
        if ((Get-FileHash -LiteralPath $sensorTarget).Hash -ne $sensorFile.before) {{ throw "User file changed: $sensorTarget" }}
    }} elseif (Test-Path -LiteralPath $sensorTarget) {{ throw "New target already exists: $sensorTarget" }}
}}
foreach ($sensorFile in $sensorFiles) {{
    $sensorTarget = Join-Path $sensorProject $sensorFile.relative
    $sensorSource = Join-Path (Join-Path $sensorBase 'staged') $sensorFile.relative
    Copy-Item -LiteralPath $sensorSource -Destination $sensorTarget
    if ((Get-FileHash -LiteralPath $sensorTarget).Hash -ne $sensorFile.after) {{ throw "Copy verification failed: $sensorTarget" }}
}}
Write-Output 'Installed and hash-verified 10 sensor files. Originals are backed up in outputs/sensors_cleanup/before.'
'''
(B/'install.ps1').write_text(ps)
print('Prepared hash-guarded install for',len(entries),'files.')
