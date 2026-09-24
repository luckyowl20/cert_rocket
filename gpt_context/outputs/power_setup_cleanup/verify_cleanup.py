"""Verify cleanup metadata and compare actual KiCad-exported net partitions."""
from pathlib import Path
import sys, re, json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'logic_power'))
from kicad_block import parse, child, children, unq
BASE=Path(__file__).resolve().parent
def netmap(path):
    d=parse(path.read_text(encoding='utf-8'))
    return {unq(child(n,'name')[1]):{(unq(child(p,'ref')[1]),unq(child(p,'pin')[1])) for p in children(n,'node')} for n in children(child(d,'nets'),'net')}
before=netmap(BASE.parent/'logic_power/review_before.net')
after=netmap(BASE/'after.net')
def partition(nets):
    return {frozenset(p for p in nodes if p[0] not in {'D2','D3','C37'}) for nodes in nets.values()}-{frozenset()}
assert partition(before)==partition(after), 'Unintended change in existing electrical connectivity'
for pin,name in [('1','USB_D+'),('3','USB_D-'),('4','/power_setup/USB_CC1'),('6','/power_setup/USB_CC2'),('2','GND'),('5','VIN_USB')]:
    assert ('D2',pin) in after[name], (pin,name)
assert ('C37','1') in after['VIN_USB'] and ('C37','2') in after['GND']
assert not any(r=='D3' for nodes in after.values() for r,p in nodes)
d=parse((BASE/'after/power_setup.kicad_sch').read_text(encoding='utf-8'))
parts={unq(next(p for p in children(s,'property') if unq(p[1])=='Reference')[2]):s for s in children(d,'symbol')}
def props(s): return {unq(p[1]):unq(p[2]) for p in children(s,'property')}
caps={r:props(s) for r,s in parts.items() if re.fullmatch(r'C\d+',r)}
res={r:props(s) for r,s in parts.items() if re.fullmatch(r'R\d+',r)}
assert len(caps)==17 and all(p.get('Voltage') for p in caps.values())
assert all(p.get('Tolerance') in ['1%','0.1%'] for p in res.values())
assert props(parts['R1'])['Value']=='15.2k 1%'
assert props(parts['D2'])['MPN']=='USBLC6-4SC6'
def erc(path):
    data=json.loads(path.read_text())
    return {(s['path'],v['type'],tuple(sorted(i['description'] for i in v['items']))) for s in data['sheets'] for v in s['violations']}
old_erc=erc(BASE/'before_erc.json');new_erc=erc(BASE/'after_erc.json')
assert not new_erc-old_erc, new_erc-old_erc
print(f'PASS: {len(caps)} capacitor voltage fields; {len(res)} resistor tolerance fields.')
print('PASS: D2 pin map, C37 bypass, and unchanged pre-existing net partitions.')
print('PASS: no new ERC findings; existing findings remain (not an ERC-clean project).')
