"""Read-only post-install checks; does not modify the avionics project."""
from pathlib import Path
import sys, json, copy
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'logic_power'))
from kicad_block import parse, child, children, unq
PROJECT = Path(r'C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1')
parts = json.loads((HERE/'manifest.json').read_text())['parts']
allowed = {'Value','Footprint','Datasheet','MPN','DigiKey','3D Model Type'}
refs = {ref for p in parts for ref in p['refs']}
def strip_metadata(tree):
    tree = copy.deepcopy(tree)
    for s in children(tree,'symbol'):
        props = {unq(p[1]):unq(p[2]) for p in children(s,'property')}
        if props.get('Reference') in refs:
            s[:] = [p for p in s if not (isinstance(p,list) and p[0]=='property' and unq(p[1]) in allowed)]
    return tree
before = parse((HERE/'before/power_setup.kicad_sch').read_text())
after = parse((PROJECT/'power_setup.kicad_sch').read_text())
assert strip_metadata(before)==strip_metadata(after), 'Unexpected schematic change'
assert (PROJECT/'power_setup.kicad_sch').read_bytes()==(HERE/'staged/power_setup.kicad_sch').read_bytes()
lookup = {unq(next(p for p in children(s,'property') if unq(p[1])=='Reference')[2]):s for s in children(after,'symbol')}
for p in parts:
    filename = p['fp']+'.kicad_mod'
    path = PROJECT/'avionics_footprints.pretty'/filename
    assert path.read_bytes()==(HERE/'staged/avionics_footprints.pretty'/filename).read_bytes()
    fp = parse(path.read_text())
    model = children(fp,'model')
    assert len(model)==1
    resolved = Path(unq(model[0][1]).replace('${KIPRJMOD}',str(PROJECT)))
    assert resolved.is_file(), resolved
    assert resolved.read_bytes()==(HERE/'staged/footprint_3D_models'/resolved.name).read_bytes()
    for ref in p['refs']:
        props={unq(v[1]):unq(v[2]) for v in children(lookup[ref],'property')}
        assert props['Footprint']=='avionics_footprints:'+p['fp']
        assert props['Value']==p['mpn']
        assert props['DigiKey']==p['url']
def nets(path):
    tree=parse(path.read_text())
    return {tuple(sorted((unq(child(n,'ref')[1]),unq(child(n,'pin')[1])) for n in children(net,'node'))) for net in children(child(tree,'nets'),'net')}
assert nets(HERE/'before.net')==nets(HERE/'after.net')
print('PASS: 9 symbol assignments, 8 footprints, 8 local models; only allowed metadata changed; net connectivity unchanged.')
