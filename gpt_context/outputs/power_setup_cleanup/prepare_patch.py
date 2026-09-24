"""Print an apply_patch patch for the staged sheet; never write the project."""
import copy, difflib, re, sys, uuid
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'logic_power'))
from kicad_block import parse, child, children, unq, q, dump

BASE = Path(__file__).resolve().parent
TARGET = BASE / 'after/power_setup.kicad_sch'
src = (BASE / 'before/power_setup.kicad_sch').read_text(encoding='utf-8')
doc = parse(src)
original = copy.deepcopy(doc)
def uid(): return str(uuid.uuid4())
def prop(s, name): return next(p for p in children(s,'property') if unq(p[1]) == name)
def ref(s): return unq(prop(s,'Reference')[2])
parts = {ref(s):s for s in children(doc,'symbol')}
def field(s, name, value, visible=False):
    ps = [p for p in children(s,'property') if unq(p[1]) == name]
    if ps:
        ps[0][2] = q(value)
        return ps[0]
    x,y = child(s,'at')[1:3]
    p = parse(f'(property {q(name)} {q(value)} (at {x} {y} 0) {"" if visible else "(hide yes)"} (effects (font (size 1 1))))')
    s.insert(12,p)
    return p

# Actual rail ratings; existing capacitance values are preserved.
cap_specs = {
 'C1':('4.7u',50,'0805_2012'), 'C2':('100n',50,'0402_1005'),
 'C3':('100n',10,'0201_0603'), 'C4':('4.7u',16,'0603_1608'),
 'C5':('10u',16,'0805_2012'), 'C12':('100n',10,'0402_1005'),
 'C16':('10u',35,'0805_2012'), 'C17':('10u',35,'0805_2012'),
 'C18':('100n',50,'0402_1005'), 'C19':('10n',10,'0402_1005'),
 'C31':('1u',10,'0402_1005'), 'C32':('10u',35,'0805_2012'),
 'C33':('10u',35,'0805_2012'), 'C34':('100n',10,'0402_1005'),
 'C35':('10n',10,'0402_1005'), 'C36':('100n',10,'0402_1005')}
assert {r for r in parts if re.fullmatch(r'C\d+',r)} == set(cap_specs)
for r,(value,volts,package) in cap_specs.items():
    s=parts[r]
    field(s,'Value',value)
    voltage=field(s,'Voltage',f'{volts}V')
    for h in children(voltage,'hide')[:]: voltage.remove(h)
    vp=prop(s,'Value')
    child(voltage,'at')[1:]=child(vp,'at')[1:]
    child(voltage,'at')[2]=str(float(child(vp,'at')[2])+2.0)
    child(voltage,'effects')[:]=copy.deepcopy(child(vp,'effects'))
    child(child(child(voltage,'effects'),'font'),'size')[1:]=['1','1']
    field(s,'Dielectric','X7R')
    field(s,'Footprint',f'Capacitor_SMD:C_{package}Metric')

# Precision on sense/threshold ratios; general control resistors need only 1%.
precise = {'R3','R4','R19','R22','R23','R24','R30','R31','R32','R33','R42','R43'}
for r,s in parts.items():
    if not re.fullmatch(r'R\d+',r): continue
    val = unq(prop(s,'Value')[2]).split()[0]
    if r=='R1': val='15.2k'  # explicitly approved correction
    tol='0.1%' if r in precise else '1%'
    field(s,'Value',f'{val} {tol}')
    field(s,'Tolerance',tol)

for r,s in parts.items():
    if re.fullmatch(r'[RC]\d+',r):
        child(child(child(prop(s,'Value'),'effects'),'font'),'size')[1:]=['1','1']
for name,y in [('Reference',140.97),('Value',143.51),('Voltage',145.51)]:
    child(prop(parts['C36'],name),'at')[1:3]=['289.21',str(y)]

# Replace D2/D3 placeholders with the standard, verified six-pin array symbol.
libfile=Path('C:/Program Files/KiCad/10.0/share/kicad/symbols/Power_Protection.kicad_sym')
library=parse(libfile.read_text(encoding='utf-8'))
lib=copy.deepcopy(next(s for s in children(library,'symbol') if unq(s[1])=='USBLC6-4SC6'))
lib[1]=q('Power_Protection:USBLC6-4SC6')
child(doc,'lib_symbols').append(lib)
old_d2=parts['D2']
new=parse(f'''(symbol (lib_id "Power_Protection:USBLC6-4SC6")
 (at 218.44 231.14 0) (unit 1) (in_bom yes) (on_board yes) (dnp no)
 (uuid {child(old_d2,'uuid')[1]}))''')
for name,value,x,y,hide in [
 ('Reference','D2',218.44,216.535,False),
 ('Value','USBLC6-4SC6',218.44,219.075,False),
 ('Footprint','Package_TO_SOT_SMD:SOT-23-6',218.44,231.14,True),
 ('Datasheet','https://www.st.com/resource/en/datasheet/usblc6-4.pdf',218.44,231.14,True),
 ('Manufacturer','STMicroelectronics',218.44,231.14,True),
 ('MPN','USBLC6-4SC6',218.44,231.14,True),
 ('Product URL','https://www.digikey.com/en/products/detail/stmicroelectronics/USBLC6-4SC6/725216',218.44,231.14,True),
 ('Description','USB ESD array: D+, D-, CC1, CC2 and VBUS; fixed 5 V only',218.44,231.14,True)]:
    new.append(parse(f'(property {q(name)} {q(value)} (at {x} {y} 0) {"(hide yes)" if hide else ""} (effects (font (size 1 1))))'))
new.append(copy.deepcopy(child(old_d2,'instances')))
doc[doc.index(old_d2)]=new
doc.remove(parts['D3'])

# Remove only the four obsolete diode branch wires, preserving USB data routes.
obsolete={'39ac7b6d-9d8c-4205-8ca3-8f94edbf0829','a92d6e61-c703-4999-af64-2d1d52514fae',
          'c0c5b3d9-bae5-4849-bd75-28ca2e9b0a24','f442e48b-cbba-4428-9e82-ed916c3fa6c2'}
for w in children(doc,'wire')[:]:
    if unq(child(w,'uuid')[1]) in obsolete: doc.remove(w)
for j in children(doc,'junction')[:]:
    if tuple(map(float,child(j,'at')[1:3])) in {(130.81,236.22),(146.05,241.3),(130.81,262.89),(146.05,262.89)}:
        doc.remove(j)

def wire(x1,y1,x2,y2):
    doc.append(parse(f'(wire (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0) (type default)) (uuid "{uid()}"))'))
def label(name,x,y,angle=0):
    doc.append(parse(f'(label {q(name)} (at {x} {y} {angle}) (effects (font (size 1 1)) (justify left bottom)) (uuid "{uid()}"))'))
def global_label(name,x,y):
    doc.append(parse(f'(global_label {q(name)} (shape input) (at {x} {y} 180) (effects (font (size 1 1)) (justify right)) (uuid "{uid()}"))'))

# Local CC names preserve the two independent 5.1k sink terminations.
label('USB_CC1',153.67,227.33)
label('USB_CC2',144.78,229.87)
for name,y in [('USB_D+',228.6),('USB_D-',231.14),('USB_CC1',233.68),('USB_CC2',236.22)]:
    wire(203.2,y,210.82,y)
    if name in ['USB_D+','USB_D-']: global_label(name,203.2,y)
    else: label(name,203.2,y)
wire(218.44,223.52,232.41,223.52)
global_label('VIN_USB',218.44,223.52)
wire(218.44,241.3,232.41,241.3)
global_label('GND',218.44,241.3)

# Local bypass per ST's layout guidance; not a second protection IC.
c37=copy.deepcopy(parts['C36'])
for key in ['pin','instances','fields_autoplaced','mirror']:
    for v in children(c37,key)[:]: c37.remove(v)
child(c37,'uuid')[1]=q(uid())
child(c37,'at')[1:]=['232.41','231.14','0']
for p in children(c37,'property'):
    child(p,'at')[1:]=['236.22','231.14','0']
field(c37,'Reference','C37');field(c37,'Value','100n');field(c37,'Voltage','10V')
child(prop(c37,'Reference'),'at')[2]='228.6'
child(prop(c37,'Voltage'),'at')[2]='233.14'
for p in [prop(c37,'Reference'),prop(c37,'Value'),prop(c37,'Voltage')]:
    eff=child(p,'effects')
    for j in children(eff,'justify')[:]: eff.remove(j)
    eff.append(['justify','left'])
ins=copy.deepcopy(child(old_d2,'instances'))
for prj in children(ins,'project'):
    for path in children(prj,'path'): child(path,'reference')[1]=q('C37')
c37.append(ins);doc.append(c37)
wire(232.41,223.52,232.41,228.6)
wire(232.41,233.68,232.41,241.3)

# A slightly wider USB box accommodates the array without moving other sections.
box=next(x for x in children(doc,'rectangle') if unq(child(x,'uuid')[1])=='98094d5b-595f-461c-bd7e-1f6711f0250d')
child(box,'end')[1]='255.27'
doc.append(parse(f'(text "D2: one SOT-23-6 package; 4 I/O + VBUS ESD.\\nPlace D2/C37 at J4; short, wide ground return.\\nFixed 5 V only; not sustained-overvoltage protection.\\nhttps://www.st.com/en/protections-and-emi-filters/usblc6-4.html" (at 107.95 269.24 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid()}"))'))

# Correct a contradictory arithmetic note, not the divider itself.
for t in children(doc,'text'):
    if unq(child(t,'uuid')[1])=='882da429-6e42-4c76-8ad7-a729656cf08e':
        t[1]=q('VIN_LOGIC sense; not raw battery\nR3/R4: 220k/47k (ratio 0.1760)\n16.8 V -> 2.957 V at SENS_BATT')

# Preserve original text for unchanged top-level objects, minimizing the patch.
def spans(text):
    depth=0; start=None; string=False; esc=False
    for i,c in enumerate(text):
        if string:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': string=False
            continue
        if c=='"': string=True
        elif c=='(':
            depth+=1
            if depth==2: start=i
        elif c==')':
            if depth==2: yield start,i+1
            depth-=1
raws=list(spans(src))
oldobjs=[x for x in original[1:] if isinstance(x,list)]
assert len(raws)==len(oldobjs)
rawmap={dump(x):src[a:b] for x,(a,b) in zip(oldobjs,raws)}
def keyed(nodes):
    counts={}; result={}
    for n in nodes:
        stem=(n[0], n[1] if n[0] in ['property','symbol','pin','project','path'] and len(n)>1 and isinstance(n[1],str) else '')
        i=counts.get(stem,0);counts[stem]=i+1
        result[(stem,i)]=n
    return result
def preserve(old,new,raw):
    if old==new: return raw
    if [x for x in old if not isinstance(x,list)] != [x for x in new if not isinstance(x,list)]: return dump(new)
    oc=[x for x in old if isinstance(x,list)];nc=[x for x in new if isinstance(x,list)]
    locations=list(spans(raw))
    assert len(locations)==len(oc)
    ok,nk=keyed(oc),keyed(nc)
    edits=[]
    for (k,o),(a,b) in zip(ok.items(),locations):
        edits.append((a,b,preserve(o,nk[k],raw[a:b]) if k in nk else ''))
    for a,b,replacement in reversed(edits): raw=raw[:a]+replacement+raw[b:]
    additions=[dump(n) for k,n in nk.items() if k not in ok]
    return raw[:-1]+''.join('\n\t'+n for n in additions)+')'
old_by_uuid={child(x,'uuid')[1]:(x,src[a:b]) for x,(a,b) in zip(oldobjs,raws) if children(x,'uuid')}
rendered=[]
for x in doc[1:]:
    if not isinstance(x,list): continue
    if dump(x) in rawmap: rendered.append(rawmap[dump(x)]);continue
    if x[0]=='lib_symbols':
        i=next(i for i,o in enumerate(oldobjs) if o[0]=='lib_symbols')
        rendered.append(preserve(oldobjs[i],x,src[raws[i][0]:raws[i][1]]));continue
    key=child(x,'uuid')[1] if children(x,'uuid') else None
    if key in old_by_uuid:
        o,raw=old_by_uuid[key];rendered.append(preserve(o,x,raw))
    else: rendered.append(dump(x))
out='(kicad_sch\n'+'\n'.join('\t'+x for x in rendered)+'\n)\n'
def canonical(n):
    return (tuple(x for x in n if isinstance(x,str)),tuple(sorted(canonical(x) for x in n if isinstance(x,list))))
assert canonical(parse(out))==canonical(doc)
diff=list(difflib.unified_diff(TARGET.read_text(encoding='utf-8').splitlines(),out.splitlines(),n=3))
print('*** Begin Patch')
print('*** Update File: '+TARGET.as_posix())
for line in diff[2:]: print('@@' if line.startswith('@@') else line)
print('*** End Patch')
