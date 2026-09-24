from pathlib import Path
import re,json
P=Path('C:/Users/mdsch/Desktop/rocketry/avionics/downloads')
for f in [P/'ADXL375BCCZ_RL7/LGA_CC-14-1_ADI.step',P/'ul_LPS22DFTR/QFN_22DFTR_STM.step',P/'ul_LSM6DSV32XTR/LGA-14L_2p5X3p0X0p86_STM.step']:
 t=f.read_text();entities=dict(re.findall(r'#(\d+)=(.*?);',t,re.S));print(f.name)
 for n,e in entities.items():
  if not e.startswith('MANIFOLD_SOLID_BREP'):continue
  seen=set();pts=[]
  def visit(n):
   if n in seen:return
   seen.add(n);e=entities[n]
   if e.startswith('CARTESIAN_POINT'):
    m=re.search(r',\(([^)]+)\)',e)
    if m:pts.append(tuple(map(float,m[1].split(','))))
   for x in re.findall(r'#(\d+)',e):visit(x)
  visit(n)
  bounds=[(round(min(a),5),round(max(a),5)) for a in zip(*pts)]
  print(n,bounds)
