"""Build a native, importable KiCad block; never writes the user's project.

Import with KiCad Place > Import Sheet, with Place as sheet disabled.
"""
import json
import re
import uuid
import math
from pathlib import Path

PROJECT = Path(r"C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1")
HERE = Path(__file__).resolve().parent

def parse(text):
    stack = [[]]
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text):
        if token == '(':
            stack.append([])
        elif token == ')':
            item = stack.pop()
            stack[-1].append(item)
        else:
            stack[-1].append(token)
    assert len(stack) == 1 and len(stack[0]) == 1
    return stack[0][0]

def q(s): return json.dumps(str(s))
def unq(s): return json.loads(s) if s.startswith('"') else s
def child(n, key): return next(x for x in n if isinstance(x, list) and x[0] == key)
def children(n, key): return [x for x in n if isinstance(x, list) and x[0] == key]
def dump(n): return '(' + ' '.join(dump(x) if isinstance(x, list) else str(x) for x in n) + ')'
def uid(): return str(uuid.uuid4())

def build():
    src = parse((PROJECT / 'power_setup.kicad_sch').read_text(encoding='utf-8'))
    libs = {unq(s[1]): s for s in children(child(src, 'lib_symbols'), 'symbol')}
    root = uid()
    parts, used, roles = [], {}, {}
    maxima = {'U': 0, 'R': 0, 'C': 0}
    for f in PROJECT.glob('*.kicad_sch'):
        if f.name.startswith('_'): continue
        for letter, number in re.findall(r'\(property "Reference" "([URC])(\d+)"', f.read_text(encoding='utf-8')):
            maxima[letter] = max(maxima[letter], int(number))
    def add(raw): parts.append(parse(raw))
    def sym(lib, value, x, y, angle=0, footprint='', role=''):
        used[lib] = libs[lib]
        letter = 'U' if 'TPS2121' in lib else ('C' if lib == 'Device:C_Small' else 'R')
        maxima[letter] += 1
        ref = letter + str(maxima[letter])
        if lib.startswith('power:'): ref = '#PWR' + str(len(parts) + 100)
        body = f'(symbol (lib_id {q(lib)}) (at {x} {y} {angle}) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {q(uid())})'
        if letter == 'U':
            rx, ry, vx, vy = x, y-28, x, y
        elif angle == 90:
            rx, ry, vx, vy = x, y-5, x, y-2.5
        else:
            rx, ry, vx, vy = x+6, y-1.27, x+6, y+1.27
        for key, val, px, py, hide in [('Reference',ref,rx,ry,False),('Value',value,vx,vy,False),('Footprint',footprint,x,y,True),('Datasheet','https://www.ti.com/lit/ds/symlink/tps2121.pdf' if letter=='U' else '',x,y,True)]:
            body += f'(property {q(key)} {q(val)} (at {px} {py} 0) (effects (font (size 1 1)){" hide" if hide else ""}))'
        body += f'(instances (project "logic_mux_block" (path "/{root}" (reference {q(ref)}) (unit 1)))))'
        add(body)
        roles[role or ref] = ref
        pins = {}
        for sub in children(libs[lib], 'symbol'):
            for pin in children(sub, 'pin'):
                at = child(pin, 'at'); px, py = float(at[1]), float(at[2]); a = math.radians(angle)
                pins[unq(child(pin,'number')[1])] = (round(x+px*math.cos(a)-py*math.sin(a),5), round(y-px*math.sin(a)-py*math.cos(a),5))
        return pins
    def wire(a,b):
        assert a != b
        add(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid {q(uid())}))')
    def path(*points):
        for a,b in zip(points,points[1:]): wire(a,b)
    def dot(x,y): add(f'(junction (at {x} {y}) (diameter 0) (color 0 0 0 0) (uuid {q(uid())}))')
    def gl(name,x,y,angle=0):
        add(f'(global_label {q(name)} (shape passive) (at {x} {y} {angle}) (effects (font (size 1 1)) (justify {"left" if angle==0 else "right"})) (uuid {q(uid())}))')
    def gnd(x,y):
        # Global GND is electrically identical to the existing power:GND symbols.
        gl('GND',x,y,0)
    def resistor(role,value,x,y,a=0): return sym('Device:R_Small_US',value,x,y,a,'Resistor_SMD:R_0201_0603Metric',role)
    def cap(role,value,x,y,fp='C_0402_1005Metric'): return sym('Device:C_Small',value,x,y,0,'Capacitor_SMD:'+fp,role)
    def note(t,x,y): add(f'(text {q(t)} (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid {q(uid())}))')

    u = sym('rocketry_library:TPS2121RUXR','TPS2121RUXR',63.5,35.56,footprint='Package_DFN_QFN:Texas_VQFN-HR-12_2x2.5mm_P0.5mm',role='logic_mux')
    gl('VIN_USB',10.16,15.24,180)
    path((10.16,15.24),(20.32,15.24),(33.02,15.24),u['7'])
    r = resistor('USB_priority_upper','15k',33.02,20.32)
    wire((33.02,15.24),r['1']); wire(r['2'],u['6']); dot(33.02,15.24)
    r = resistor('USB_priority_lower','10k',33.02,27.94)
    wire((33.02,22.86),r['1']); gnd(*r['2']); dot(33.02,22.86)
    c = cap('USB_input','1u / 10V',20.32,25.4)
    wire((20.32,15.24),c['1']); gnd(*c['2']); dot(20.32,15.24)
    gl('VIN_MAIN_BATT',10.16,62.23,180)
    path((10.16,62.23),(20.32,62.23),u['2'])
    c = cap('main_input','10u / 35V',20.32,68.58,'C_0805_2012Metric')
    wire((20.32,62.23),c['1']); gnd(*c['2']); dot(20.32,62.23)
    for pin in ['4','5']:
        p=u[pin]; wire(p,(p[0]-5.08,p[1])); gnd(p[0]-5.08,p[1])
    path(u['1'],(88.9,15.24),(99.06,15.24),(116.84,15.24))
    path(u['8'],(88.9,17.78),(88.9,15.24)); dot(88.9,15.24)
    gl('VIN_LOGIC',116.84,15.24)
    c = cap('mux_output','10u / 35V',99.06,25.4,'C_0805_2012Metric')
    wire((99.06,15.24),c['1']); gnd(*c['2']); dot(99.06,15.24)
    r = resistor('status_pullup','10k',99.06,41.91)
    gl('+3.3V',99.06,36.83); wire((99.06,36.83),r['1'])
    wire(r['2'],(99.06,49.53)); path(u['9'],(99.06,49.53),(116.84,49.53)); dot(99.06,49.53)
    gl('LOGIC_PMUX_ST',116.84,49.53)
    r = resistor('current_limit','80.6k',93.98,71.12)
    path(u['10'],(93.98,66.04),r['1']); gnd(*r['2'])
    wire(u['12'],(63.5,86.36)); gnd(63.5,86.36)
    c = cap('soft_start','100n / 10V',68.58,93.98)
    wire(u['11'],c['1']); gnd(*c['2'])
    r = resistor('override_series','1k',111.76,81.28,90)
    path(u['3'],(101.6,81.28),r['1']); wire(r['2'],(119.38,81.28)); gl('MCU_SELECT_MAIN',119.38,81.28)
    r = resistor('override_pulldown','100k',101.6,91.44)
    wire((101.6,81.28),r['1']); dot(101.6,81.28); gnd(*r['2'])
    r = resistor('USB_adc_upper','49.9k 0.1%',20.32,119.38)
    gl('VIN_USB',20.32,111.76,180); wire((20.32,111.76),r['1']); wire(r['2'],(20.32,124.46))
    r = resistor('USB_adc_lower','10k 0.1%',20.32,132.08)
    wire((20.32,124.46),r['1']); gnd(*r['2']); dot(20.32,124.46)
    path((20.32,124.46),(38.1,124.46),(58.42,124.46)); gl('USB_POWER_SENS',58.42,124.46)
    c = cap('USB_adc_filter','10n / 10V',38.1,132.08)
    wire((38.1,124.46),c['1']); gnd(*c['2']); dot(38.1,124.46)
    r = resistor('sense_enable_pulldown','100k',91.44,132.08)
    gl('SENSE_EN',91.44,124.46); wire((91.44,124.46),r['1']); gnd(*r['2'])
    c = cap('TMUX_bypass','100n / 10V',116.84,132.08)
    gl('+3.3V',116.84,124.46); wire((116.84,124.46),c['1']); gnd(*c['2'])
    note('LOGIC POWER: USB default; MCU high prefers main',0,0)
    note('Fixed 5V USB only. No external 4.4V cutoff.\nMCU low / Hi-Z: USB priority, main fallback.\nMCU high: main priority, USB fallback.',0,150)
    note('To existing U7 (TMUX1511): USB_POWER_SENS -> S3.\nST is source indication, NOT power-good.\nCurrent limit ~1.49A nominal; not USB authorization.',0,160)
    document = ['kicad_sch',['version','20260306'],['generator','"eeschema"'],['generator_version','"10.0"'],['uuid',q(root)],['paper','"A3"'],['lib_symbols',*used.values()],*parts,['sheet_instances',['path','"/"',['page','"1"']]]]
    (HERE/'logic_mux_block.kicad_sch').write_text(dump(document)+'\n',encoding='utf-8')
    (HERE/'kicad_block_refs.json').write_text(json.dumps(roles,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(roles,indent=2))

    # Separate wire/label harness around existing U7: import and align to its VDD pin.
    parts.clear(); used.clear()
    tm = next(s for s in children(src,'symbol') if unq(child(s,'lib_id')[1])=='rocketry_library:TMUX1511RSVR')
    tl = libs['rocketry_library:TMUX1511RSVR']
    nets={'16':'+3.3V','2':'PYRO_POWER_SENS','5':'MAIN_BAT_SENS','10':'USB_POWER_SENS','14':'GND','1':'SENSE_EN','4':'SENSE_EN','11':'SENSE_EN','15':'GND','3':'ADC_TPS_OUT','6':'ADC_MAIN','9':'ADC_USB','13':'GND','8':'GND'}
    for sub in children(tl,'symbol'):
        for pin in children(sub,'pin'):
            num=unq(child(pin,'number')[1]); at=child(pin,'at'); x,y=float(at[1]),-float(at[2])
            if num in ['7','12']:
                add(f'(no_connect (at {x} {y}) (uuid {q(uid())}))')
                continue
            px=x-10.16 if x==0 else x+10.16
            wire((x,y),(px,y)); gl(nets[num],px,y,180 if x==0 else 0)
    harness=['kicad_sch',['version','20260306'],['generator','"eeschema"'],['uuid',q(uid())],['paper','"A3"'],['lib_symbols'],*parts]
    (HERE/'tmux_harness.kicad_sch').write_text(dump(harness)+'\n',encoding='utf-8')

if __name__ == '__main__':
    build()
    doc = parse((PROJECT / 'power_setup.kicad_sch').read_text(encoding='utf-8'))
    for s in children(child(doc, 'lib_symbols'), 'symbol'):
        name = unq(s[1])
        if name in ['rocketry_library:TPS2121RUXR', 'rocketry_library:TMUX1511RSVR', 'Device:R_Small_US', 'Device:C_Small', 'power:GND']:
            print(name)
            for part in children(s, 'symbol'):
                for pin in children(part, 'pin'):
                    print(' ', child(pin, 'number')[1], child(pin, 'name')[1], child(pin, 'at')[1:])
    for s in children(doc, 'symbol'):
        ref = next(unq(p[2]) for p in children(s, 'property') if unq(p[1]) == 'Reference')
        if ref in ['U7', 'U5']:
            print(ref, child(s, 'at'), child(s, 'lib_id'))
