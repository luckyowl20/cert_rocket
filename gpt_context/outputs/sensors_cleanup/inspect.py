from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'logic_power'))
from kicad_block import *
P=Path('C:/Users/mdsch/Desktop/rocketry/avionics/avionics_rev1')
for name in ['QFN_22DFTR_STM','LGA_CC-14-1_ADI','LGA-14L_2p5X3p0X0p86_STM']:
 d=parse((P/'avionics_footprints.pretty'/f'{name}.kicad_mod').read_text())
 print(name)
 for p in children(d,'pad'): print(unq(p[1]),child(p,'at')[1:],child(p,'size')[1:])
 print('models',children(d,'model'))
d=parse(Path('outputs/sensors_cleanup/qa/before.net').read_text())
for n in children(child(d,'nets'),'net'):
 print(unq(child(n,'name')[1]),[(unq(child(p,'ref')[1]),unq(child(p,'pin')[1]),unq(child(p,'pinfunction')[1]) if children(p,'pinfunction') else '') for p in children(n,'node')])
K=Path('C:/Program Files/KiCad/10.0/share/kicad')
for f in ['Capacitor_Tantalum_SMD.pretty/CP_EIA-3216-18_Kemet-A.kicad_mod','Capacitor_SMD.pretty/C_0201_0603Metric.kicad_mod','Resistor_SMD.pretty/R_0201_0603Metric.kicad_mod']:
 d=parse((K/'footprints'/f).read_text());print(f,children(d,'model'))
for p in (P.parent/'downloads').glob('**/*.step'):
 if any(n in p.name for n in ['LGA_CC','LGA-14','QFN_22']):
  print('STEP',p,p.stat().st_size);print('\n'.join(p.read_text().splitlines()[:20]))
