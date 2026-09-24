"""Stage targeted sensors changes; never writes the live avionics project."""
from pathlib import Path
import sys,copy,re,json,shutil,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'logic_power'))
from kicad_block import parse,child,children,unq,q,dump
B=Path(__file__).resolve().parent
P=Path('C:/Users/mdsch/Desktop/rocketry/avionics/avionics_rev1')
K=Path('C:/Program Files/KiCad/10.0/share/kicad')
S=B/'staged'; F=S/'avionics_footprints.pretty'; M=S/'footprint_3D_models'
F.mkdir(exist_ok=True);M.mkdir(exist_ok=True)
src=(B/'before/sensors.kicad_sch').read_text();d=parse(src);old=copy.deepcopy(d)
def props(s):return {unq(p[1]):unq(p[2]) for p in children(s,'property')}
parts={props(s)['Reference']:s for s in children(d,'symbol')}
def prop(s,n):return next(p for p in children(s,'property') if unq(p[1])==n)
def field(s,n,v):
 if n in props(s):p=prop(s,n);p[2]=q(v);return p
 x,y=child(s,'at')[1:3];p=parse(f'(property {q(n)} {q(v)} (at {x} {y} 0) (hide yes) (effects (font (size 1 1))))');s.append(p);return p
for r in ['C22','C23','C24','C25','C26']:
 s=parts[r];field(s,'Value','1u 10%' if r=='C24' else '100n 10%');field(s,'Tolerance','10%')
 field(s,'Dielectric','Tantalum' if r=='C24' else 'X7R')
 v=field(s,'Voltage','16V' if r=='C24' else '10V')
 for h in children(v,'hide'):v.remove(h)
 vp=prop(s,'Value');child(v,'at')[1:]=child(vp,'at')[1:];child(v,'at')[2]=str(float(child(vp,'at')[2])+2)
 child(v,'effects')[:]=copy.deepcopy(child(vp,'effects'))
 # Angle-180 originals have right justification although fields sit right of body.
 for n in ['Reference','Value','Voltage']:
  p=prop(s,n);e=child(p,'effects');child(child(e,'font'),'size')[1:]=['1','1']
  for j in children(e,'justify'):e.remove(j)
  e.append(['justify','left' if r=='C24' else 'right'])
  child(p,'at')[1]=str(float(child(s,'at')[1])+(-2.54 if r=='C22' else 2.54))
for r in ['R9','R10','R11']:
 s=parts[r];field(s,'Value','10k 1%');field(s,'Tolerance','1%');field(s,'Power','0.05W');field(s,'Voltage','25V')
 child(child(child(prop(s,'Value'),'effects'),'font'),'size')[1:]=['1','1']
 # All resistor text is left of body, so right justification is retained.
for r,name in [('U8','QFN_22DFTR_STM'),('U9','LGA_CC-14-1_ADI'),('U10','LGA-14L_2p5X3p0X0p86_STM')]:
 field(parts[r],'Footprint','avionics_footprints:'+name)
 field(parts[r],'MPN',props(parts[r])['Value'])
 field(parts[r],'3D Model Type','Supplier nominal package; visualization only')
field(parts['U9'],'Datasheet','https://www.analog.com/media/en/technical-documentation/data-sheets/ADXL375.pdf')
types={
 'ADXL375BCCZ-RL7':{1:'power_in',2:'power_in',3:'passive',4:'power_in',5:'power_in',6:'power_in',7:'input',8:'output',9:'output',10:'no_connect',11:'passive',12:'bidirectional',13:'bidirectional',14:'input'},
 'LPS22DFTR':{1:'power_in',2:'input',3:'passive',4:'bidirectional',5:'bidirectional',6:'input',7:'output',8:'power_in',9:'power_in',10:'power_in'},
 'LSM6DSV32XTR':{1:'bidirectional',2:'bidirectional',3:'bidirectional',4:'output',5:'power_in',6:'power_in',7:'power_in',8:'power_in',9:'output',10:'input',11:'tri_state',12:'input',13:'input',14:'bidirectional'}}
def fix_types(symbol):
 name=unq(symbol[1]).split(':')[-1]
 if name not in types:return
 for sub in children(symbol,'symbol'):
  for pin in children(sub,'pin'):pin[1]=types[name][int(unq(child(pin,'number')[1]))]
for libsym in children(child(d,'lib_symbols'),'symbol'):fix_types(libsym)
# Polarized replacement has identical pin spacing; pin 1 (anode) must be at +3.3V.
lib=parse((K/'symbols/Device.kicad_sym').read_text())
c=copy.deepcopy(next(s for s in children(lib,'symbol') if unq(s[1])=='C_Polarized_Small'));c[1]=q('Device:C_Polarized_Small');child(d,'lib_symbols').append(c)
s=parts['C24'];child(s,'lib_id')[1]=q('Device:C_Polarized_Small');child(s,'at')[3]='0'
field(s,'Footprint','avionics_footprints:TAJA105K016RNJ_3216_18')
field(s,'Datasheet','https://datasheets.kyocera-avx.com/TAJ.pdf');field(s,'MPN','TAJA105K016RNJ');field(s,'Manufacturer','KYOCERA AVX')
field(s,'DigiKey','https://www.digikey.com/en/products/detail/kyocera-avx/TAJA105K016RNJ/563757')
field(s,'Description','1uF 10% 16V tantalum, A case; positive pin 1 to +3.3V')
field(s,'3D Model Type','KiCad generic 3216-18 package')
for t in children(d,'text'):
 text=unq(t[1])
 if text.startswith('The datasheet calls'):
  t[1]=q('C24: 1uF tantalum per ADXL375 p.26.\nTAJA105K016RNJ, 16V, 10%, A case.\nPositive pin 1 to +3.3V; place at VS.');child(child(child(t,'effects'),'font'),'size')[1:]=['1','1']
 if text.startswith('TODO:'):
  t[1]=q('SENSOR DESIGN NOTES\n3.3V, 4-wire SPI; keep all CS high at startup.\nR9-R11: 10k 1% (0.33mA when selected).\nPlace bypass capacitors at each supply pin.\nU10: mode 1, Qvar/analog hub disabled.\nC24 follows ADI tantalum recommendation.\nDigiKey: TAJA105K016RNJ (478-1649-1-ND)\nhttps://www.digikey.com/en/products/detail/kyocera-avx/TAJA105K016RNJ/563757')
  child(child(child(t,'effects'),'font'),'size')[1:]=['1.27','1.27']
  child(t,'at')[1:3]=['177.038','105.41']
  for n in children(child(child(t,'effects'),'font'),'bold'):child(child(t,'effects'),'font').remove(n)
assets=[]
for name,source in [('QFN_22DFTR_STM','ul_LPS22DFTR'),('LGA_CC-14-1_ADI','ADXL375BCCZ_RL7'),('LGA-14L_2p5X3p0X0p86_STM','ul_LSM6DSV32XTR')]:
 fp=P/'avionics_footprints.pretty'/f'{name}.kicad_mod';out=parse(fp.read_text())
 shutil.copy2(fp,B/'before'/fp.name)
 if name=='LGA_CC-14-1_ADI':
  # ADXL375 Rev B Figure 38: outer copper 3.34 x 5.34;
  # side pads 1.145 x .55, .25 gap; end pads .55 x 1.145.
  out=parse(f'(footprint "{name}" (version 20260206) (generator "pcbnew") (layer "F.Cu") (attr smd) (descr "ADXL375 CC-14-1; ADI Rev B Figure 38 recommended land pattern; 3x5mm body, 0.8mm pitch") (tags "ADXL375BCCZ-RL7 ADI recommended"))')
  for n,v,y,layer in [('Reference','REF**',-3.5,'F.SilkS'),('Value',name,3.5,'F.Fab')]:
   out.append(parse(f'(property "{n}" "{v}" (at 0 {y}) (layer "{layer}") (effects (font (size 1 1) (thickness 0.15))))'))
  for num in range(1,15):
   if num<=6:x,y,w,h=-1.0975,-2+(num-1)*.8,1.145,.55
   elif num==7:x,y,w,h=0,2.0975,.55,1.145
   elif num<=13:x,y,w,h=1.0975,2-(num-8)*.8,1.145,.55
   else:x,y,w,h=0,-2.0975,.55,1.145
   out.append(parse(f'(pad "{num}" smd rect (at {x:.6f} {y:.6f}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask"))'))
  for x1,y1,x2,y2,layer,width in [(-1.5,-2.5,1.5,2.5,'F.Fab',.1),(-1.95,-2.95,1.95,2.95,'F.CrtYd',.05),(-1.85,-2.85,1.85,2.85,'F.SilkS',.12)]:
   out.append(parse(f'(fp_rect (start {x1} {y1}) (end {x2} {y2}) (stroke (width {width}) (type default)) (fill none) (layer "{layer}"))'))
  out.append(parse('(fp_circle (center -2.15 -2) (end -2.05 -2) (stroke (width 0.12) (type default)) (fill solid) (layer "F.SilkS"))'))
  out.append(parse('(fp_line (start -1.5 -2) (end -1 -2.5) (stroke (width 0.1) (type default)) (layer "F.Fab"))'))
 model=P.parent/'downloads'/source/f'{name}.step';shutil.copy2(model,M/model.name)
 for n in children(out,'model'):out.remove(n)
 out.append(parse(f'(model "${{KIPRJMOD}}/footprint_3D_models/{model.name}" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))'))
 for n in children(out,'property'):
  if unq(n[1])=='Reference':child(n,'at')[1:3]=['0','-3.4' if name=='LGA_CC-14-1_ADI' else '-2']
  if unq(n[1])=='Value':child(n,'at')[1:3]=['0','3.4' if name=='LGA_CC-14-1_ADI' else '2']
 (F/fp.name).write_text(dump(out)+'\n')
 assets.append({'footprint':name,'model':model.name,'source':str(model)})
# A-case generic STEP is a package envelope, not a vendor-specific model.
name='TAJA105K016RNJ_3216_18';out=parse((K/'footprints/Capacitor_Tantalum_SMD.pretty/CP_EIA-3216-18_Kemet-A.kicad_mod').read_text());out[1]=q(name)
child(out,'descr')[1]=q('KYOCERA AVX TAJA105K016RNJ; A case 3216-18; generic KiCad IPC nominal land pattern; pin 1 positive')
model='CP_EIA-3216-18_Kemet-A.step';shutil.copy2(K/'3dmodels/Capacitor_Tantalum_SMD.3dshapes'/model,M/model)
child(out,'model')[1]=q('${KIPRJMOD}/footprint_3D_models/'+model)
(F/(name+'.kicad_mod')).write_text(dump(out)+'\n')
assets.append({'footprint':name,'model':model,'source':'KiCad generic 3216-18 package'})
# Preserve untouched top-level text verbatim.
def spans(text):
 depth=0;start=None;quote=False;escape=False
 for i,c in enumerate(text):
  if quote:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quote=False
  elif c=='"':quote=True
  elif c=='(':
   depth+=1
   if depth==2:start=i
  elif c==')':
   if depth==2:yield start,i+1
   depth-=1
raw={dump(n):src[a:b] for n,(a,b) in zip(old[1:],spans(src))}
(S/'sensors.kicad_sch').write_text('(kicad_sch\n\t'+'\n\t'.join(raw.get(dump(n),dump(n)) for n in d[1:])+'\n)\n',encoding='utf-8')
# Update the same three definitions in the project symbol library only.
libpath=P/'symbol_library/rocketry_library.kicad_sym'
backup=B/'before/rocketry_library.kicad_sym'
if not backup.exists():shutil.copy2(libpath,backup)
text=backup.read_text();edits=[]
for a,b in spans(text):
 n=parse(text[a:b])
 if n[0]=='symbol' and unq(n[1]) in types:
  fix_types(n);edits.append((a,b,dump(n)))
for a,b,new in reversed(edits):text=text[:a]+new+text[b:]
(S/'symbol_library').mkdir(exist_ok=True)
(S/'symbol_library/rocketry_library.kicad_sym').write_text(text)
(B/'assets.json').write_text(json.dumps(assets,indent=2))
print('Staged sensors schematic, four footprints, and four models.')
