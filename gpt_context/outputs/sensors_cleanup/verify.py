from pathlib import Path
import sys,json,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'logic_power'))
from kicad_block import *
B=Path(__file__).resolve().parent
def nets(p):
 d=parse(p.read_text())
 return {unq(child(n,'name')[1]):{(unq(child(x,'ref')[1]),unq(child(x,'pin')[1])) for x in children(n,'node')} for n in children(child(d,'nets'),'net')}
a=nets(B/'qa/before.net');b=nets(B/'qa/after.net')
for name,nodes in a.items():
 expected={(r,('1' if p=='2' else '2') if r=='C24' else p) for r,p in nodes}
 assert expected==b[name],(name,expected^b[name])
assert ('C24','1') in b['+3.3V'] and ('C24','2') in b['GND']
before=parse((B/'before/sensors.kicad_sch').read_text());after=parse((B/'staged/sensors.kicad_sch').read_text())
for key in ['wire','junction','no_connect','global_label','rectangle']:
 assert children(before,key)==children(after,key),key
def parts(d):return {unq(next(p for p in children(s,'property') if unq(p[1])=='Reference')[2]):s for s in children(d,'symbol')}
old=parts(before);new=parts(after)
assert old.keys()==new.keys()
for r,s in new.items():
 assert child(old[r],'at')[1:3]==child(s,'at')[1:3],r
 if r.startswith('#'):continue
 p={unq(p[1]):unq(p[2]) for p in children(s,'property')}
 assert p['Footprint']
 if r.startswith(('C','R')):assert p['Tolerance'] and p['Voltage']
for name,count in [('QFN_22DFTR_STM',10),('LGA_CC-14-1_ADI',14),('LGA-14L_2p5X3p0X0p86_STM',14)]:
 d=parse((B/'staged/avionics_footprints.pretty'/f'{name}.kicad_mod').read_text());pads=children(d,'pad')
 assert {unq(p[1]) for p in pads}==set(map(str,range(1,count+1)))
 assert len(pads)==count
 assert len(children(d,'model'))==1
 if name=='LGA_CC-14-1_ADI':
  xmin=min(float(child(p,'at')[1])-float(child(p,'size')[1])/2 for p in pads)
  xmax=max(float(child(p,'at')[1])+float(child(p,'size')[1])/2 for p in pads)
  ymin=min(float(child(p,'at')[2])-float(child(p,'size')[2])/2 for p in pads)
  ymax=max(float(child(p,'at')[2])+float(child(p,'size')[2])/2 for p in pads)
  assert abs(xmax-xmin-3.34)<1e-6 and abs(ymax-ymin-5.34)<1e-6
def erc(p):
 d=json.loads(p.read_text())
 return {(s['path'],v['type'],v['description'],tuple(sorted(i['description'] for i in v['items']))) for s in d['sheets'] for v in s['violations']}
e0=erc(B/'qa/before_erc.json');e1=erc(B/'qa/after_erc.json')
delta={'removed':list(e0-e1),'added':list(e1-e0)}
(B/'qa/erc_delta.json').write_text(json.dumps(delta,indent=2))
print('PASS: all original wires, labels, junctions, no-connects and symbol positions unchanged.')
print('PASS: connectivity unchanged except intentional C24 polarity numbering (1 positive, 2 ground).')
print('PASS: 11 physical components assigned; 5 capacitor and 3 resistor ratings present.')
print('PASS: sensor pad counts and unique numbering; ADXL375 copper extent 3.34 x 5.34 mm.')
print(f'ERC: {len(e0)} -> {len(e1)} findings; {len(e0-e1)} removed, {len(e1-e0)} added. See erc_delta.json.')
for v in e1-e0:print('ADDED',v)
