"""Render the TPS2121 power-selection connection guide (PNG + SVG).

Run: python draw_pyro_schematic.py
Dependency: Pillow. Outputs are written beside this script.
Engineering prototype, not a flight-qualified or manufacturing schematic.
See README.md for assumptions, tolerances, references and validation limits.
Drawing style follows ../usb_c/draw_usb_schematic.py; no dependency on it.
"""
from pathlib import Path
from html import escape
from itertools import product
import json
import math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
INK, WIRE, POWER = '#172B43', '#166A79', '#AB4D14'
MUTED, LIGHT = '#526579', '#EEF5FA'
FONT_DIR = Path('C:/Windows/Fonts')

# Ohms, farads, volts. These are shared by the drawings and calculations.
R = {'R1': 20000, 'R2': 10000, 'R3': 18200, 'R4': 10000,
     'R5': 47000, 'R6': 47000, 'R7': 10000, 'R8': 100000,
     'R9': 1000, 'R10': 22100, 'R11': 10000, 'R12': 2200,
     'R13': 49900, 'R14': 10000, 'R15': 49900, 'R16': 10000,
     'R17': 100000}
C = {'C1': 10e-6, 'C2': 10e-6, 'C3': 10e-6, 'C4': 100e-9,
     'C5': 100e-9, 'C6': 10e-9, 'C7': 10e-9, 'C8': 100e-9}

# Electrical connectivity, not a simulator model or PCB netlist.
IC_PINS = {
    'U1 TPS2121RUXR': {1: 'TPS_OUT', 2: 'MAIN_BAT', 3: 'GND',
        4: 'OV2_BLOCK', 5: 'OV1_BLOCK', 6: 'PYRO_SENSE', 7: 'PYRO_BAT',
        8: 'TPS_OUT', 9: 'TPS_ST', 10: 'ILIM_SET', 11: 'SS_SET', 12: 'GND'},
    'U2 TLV7041DBVR': {1: 'OV1_BLOCK', 2: 'GND', 3: 'REF_1V170',
        4: 'PYRO_SENSE', 5: '3V3'},
    'U3 TMUX1511RSVR': {1: 'SENSE_EN', 2: 'OUT_DIV', 3: 'ADC_TPS_OUT',
        4: 'SENSE_EN', 5: 'MAIN_DIV', 6: 'ADC_MAIN', 7: 'NC', 8: 'GND',
        9: 'ADC_USB', 10: 'USB_DIV', 11: 'SENSE_EN', 12: 'NC', 13: 'GND', 14: 'GND',
        15: 'GND', 16: '3V3'},
    'Q1 DMN2056U-13': {1: 'MAIN_GATE', 2: 'GND', 3: 'OV2_BLOCK'},
}
PASSIVES = {
    'R1': ('PYRO_BAT', 'PYRO_SENSE'), 'R2': ('PYRO_SENSE', 'GND'),
    'R3': ('3V3', 'REF_1V170'), 'R4': ('REF_1V170', 'GND'),
    'R5': ('PYRO_BAT', 'OV1_BLOCK'), 'R6': ('OV1_BLOCK', 'GND'),
    'R7': ('MAIN_BAT', 'OV2_BLOCK'), 'R8': ('MAIN_GATE', 'GND'),
    'R9': ('MCU_MAIN_ALLOW', 'MAIN_GATE'), 'R10': ('ILIM_SET', 'GND'),
    'R11': ('3V3', 'TPS_ST'), 'R12': ('TPS_OUT', 'GND'),
    'R13': ('TPS_OUT', 'OUT_DIV'), 'R14': ('OUT_DIV', 'GND'),
    'R15': ('MAIN_BAT', 'MAIN_DIV'), 'R16': ('MAIN_DIV', 'GND'),
    'R17': ('SENSE_EN', 'GND'),
    'C1': ('PYRO_BAT', 'GND'), 'C2': ('MAIN_BAT', 'GND'),
    'C3': ('TPS_OUT', 'GND'), 'C4': ('SS_SET', 'GND'),
    'C5': ('3V3', 'GND'), 'C6': ('OUT_DIV', 'GND'),
    'C7': ('MAIN_DIV', 'GND'), 'C8': ('3V3', 'GND'),
    'D1 BZT52C4V7-7-F': ('K:OV2_BLOCK', 'A:GND'),
    'SW1 physical arm disconnect': ('TPS_OUT', 'ARMED_SUPPLY'),
}


def parallel(a, b):
    return a * b / (a + b)


def calculations():
    k_pyro = R['R2'] / (R['R1'] + R['R2'])
    ref = 3.3 * R['R4'] / (R['R3'] + R['R4'])
    k_adc = R['R14'] / (R['R13'] + R['R14'])
    re = parallel(R['R12'], R['R13'] + R['R14'])
    # Explicit design bound: total capacitance on TPS_OUT, including connected
    # downstream circuitry, must be <=22 uF at its maximum tolerance.
    tau_max = re * 1.01 * 22e-6
    # Include a 10 uA allowance for all other leakage/backfeed. Above 5 V,
    # conservatively apply the <=22 V leakage limit to BOTH mux inputs.
    # Below 5 V, the 0..4.2 V IN1 can use the <=5 V leakage specification.
    def v_after(i_high, i_low):
        high_floor = (i_high+10e-6)*re*1.01
        low_floor = (i_low+10e-6)*re*1.01
        t_to_5 = tau_max*math.log((16.8-high_floor)/(5-high_floor))
        return low_floor+(5-low_floor)*math.exp(-(.5-t_to_5)/tau_max)
    # Sensitivity envelope, NOT a guaranteed full-temperature trip specification:
    # hysteresis range is specified at 25 C; reference range is an assumption.
    falling = []
    for vcc, a, b, c, d, offset, hyst, pin_leak in product(
        (3.24, 3.35), (.999, 1.001), (.999, 1.001), (.999, 1.001),
        (.999, 1.001), (-.008, .008), (.002, .017), (-.1e-6, .1e-6)):
        r1, r2, r3, r4 = R['R1']*a, R['R2']*b, R['R3']*c, R['R4']*d
        threshold = vcc*r4/(r3+r4) + offset - hyst/2
        falling.append((threshold + pin_leak*parallel(r1, r2)) / (r2/(r1+r2)))
    result = {
        'reference_V': ref, 'pyro_divider_ratio': k_pyro,
        'falling_trip_nominal_V': (ref - .007/2)/k_pyro,
        'rising_reconnect_nominal_V': (ref + .007/2)/k_pyro,
        'illustrative_falling_envelope_V': [min(falling), max(falling)],
        'adc_ratio': k_adc, 'adc_at_16V8_V': 16.8*k_adc,
        'main_thresholds': [{'cells': n, 'pack_V': 3.5*n,
            'adc_V': 3.5*n*k_adc, 'code_12bit_3V3': round(4095*3.5*n*k_adc/3.3)}
            for n in range(1, 5)],
        'bleed_max_power_W': 16.8**2/(R['R12']*.99),
        'discharge_tau_bound_s': tau_max,
        'vout_after_500ms_85C_V': v_after(70e-6, 40e-6),
        'vout_after_500ms_125C_V': v_after(1000e-6, 580e-6),
        'adc_filter_tau_s': parallel(R['R13'], R['R14'])*C['C6'],
        'current_limit_formula_A': 65.2/((R['R10']/1000)**.861),
    }
    assert 3.499 < result['falling_trip_nominal_V'] < 3.501
    assert result['rising_reconnect_nominal_V'] > result['falling_trip_nominal_V']
    assert result['adc_at_16V8_V'] < 3.0
    assert result['vout_after_500ms_85C_V'] < .5
    assert result['vout_after_500ms_125C_V'] < 2.0
    assert set(PASSIVES) >= set(R) | set(C)
    for ic, count in [('U1 TPS2121RUXR', 12), ('U2 TLV7041DBVR', 5),
                      ('U3 TMUX1511RSVR', 16), ('Q1 DMN2056U-13', 3)]:
        assert set(IC_PINS[ic]) == set(range(1, count+1)), ic
    # Intended steady-state truth table, assuming regulated 3V3 and valid inputs.
    source = lambda pyro_good, main_valid, allow: 'IN1' if pyro_good else (
        'IN2' if main_valid and allow else 'Hi-Z')
    for p, m, a in product((False, True), repeat=3):
        selected = source(p, m, a)
        assert not (selected == 'IN2' and not a)
        assert not (selected == 'IN1' and not p)
    return result


def rval(ref):
    return f'{ref}  {R[ref]/1000:g} kΩ'


class Sheet:
    def __init__(self, title, subtitle, number, height=1600, width=1800):
        self.w, self.h = width, height
        self.im = Image.new('RGB', (self.w*2, self.h*2), 'white')
        self.d = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>']
        self.text(70, 40, title, 39, True)
        self.text(70, 100, subtitle, 22, color=MUTED)
        self.line([(70, 150), (width-70, 150)], '#CEDAE3', 2)
        self.text(70, height-48, 'PROTOTYPE CONNECTION GUIDE | Same net label = same wire. Read README.md before implementation.', 20, color=MUTED)
        self.text(width-150, height-48, '1 / 1' if width != 1800 else f'{number} / 3', 20, True)

    def text(self, x, y, value, size=23, bold=False, color=INK):
        name = 'arialbd.ttf' if bold else 'arial.ttf'
        font = ImageFont.truetype(str(FONT_DIR/name) if (FONT_DIR/name).exists()
                                  else ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), size*2)
        for i, row in enumerate(value.split('\n')):
            yy = y+i*(size+9)
            # Catch clipping mechanically as well as inspecting rendered PNGs.
            assert x+self.d.textlength(row, font=font)/2 < self.w-25, row
            assert yy+size < self.h-12, row
            self.d.text((x*2, yy*2), row, fill=color, font=font, anchor='lt')
            self.svg.append(f'<text x="{x}" y="{yy}" dominant-baseline="text-before-edge" font-family="Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(row)}</text>')

    def line(self, pts, color=WIRE, width=3):
        self.d.line([(x*2, y*2) for x,y in pts], fill=color, width=width*2)
        self.svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="{width}"/>')

    def box(self, x, y, w, h, fill=LIGHT, color=INK):
        self.d.rectangle((x*2,y*2,(x+w)*2,(y+h)*2), fill=fill, outline=color, width=4)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{color}" stroke-width="2"/>')

    def dot(self, x, y):
        self.d.ellipse(((x-5)*2,(y-5)*2,(x+5)*2,(y+5)*2), fill=WIRE)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{WIRE}"/>')

    def gnd(self, x, y):
        self.line([(x,y),(x,y+15)])
        for dy, half in [(15,22),(23,14),(31,6)]:
            self.line([(x-half,y+dy),(x+half,y+dy)])

    def resistor(self, x, y, vertical=False):
        if vertical:
            self.line([(x,y),(x,y+18)])
            self.box(x-12,y+18,24,64,'white',WIRE)
            self.line([(x,y+82),(x,y+100)])
        else:
            self.line([(x,y),(x+18,y)])
            self.box(x+18,y-12,64,24,'white',WIRE)
            self.line([(x+82,y),(x+100,y)])

    def cap(self, x, y):
        self.line([(x,y),(x,y+33)])
        self.line([(x-20,y+33),(x+20,y+33)])
        self.line([(x-20,y+45),(x+20,y+45)])
        self.line([(x,y+45),(x,y+78)])

    def net(self, x, y, name, color=WIRE):
        self.text(x,y-32,name,22,True,color)

    def save(self, name):
        self.im.resize((self.w,self.h),Image.Resampling.LANCZOS).save(OUT/f'{name}.png')
        svg = '\n'.join(self.svg+['</svg>'])
        ET.fromstring(svg)
        (OUT/f'{name}.svg').write_text(svg,encoding='utf-8')
        with Image.open(OUT/f'{name}.png') as check:
            assert check.size == (self.w,self.h)
        print(OUT/f'{name}.png')


def power():
    s = Sheet('Battery selection and MCU-controlled main permission',
              'IN1: dedicated 1S battery. IN2: main 1-4S battery. USB powers logic only; never connect USB to either input.', 1, 1640)
    s.box(630,250,480,650)
    s.text(690,280,'U1  TPS2121RUXR',28,True)
    for y,label,net in [(370,'7  IN1','PYRO_BAT'),(455,'2  IN2','MAIN_BAT'),
                        (555,'6  PR1','PYRO_SENSE'),(640,'5  OV1','OV1_BLOCK'),
                        (725,'4  OV2','OV2_BLOCK')]:
        s.line([(370,y),(630,y)]);s.net(375,y,net)
        s.text(650,y-17,label,23,True)
    s.line([(540,815),(630,815)]);s.gnd(540,815)
    s.text(650,795,'3  CP2 = GND',23,True)
    for y,label,net in [(370,'1 + 8 OUT','TPS_OUT'),(475,'9  ST','TPS_ST'),
                        (620,'10  ILIM','ILIM_SET'),(755,'11  SS','SS_SET')]:
        s.text(925,y-18,label,22,True)
        s.line([(1110,y),(1370,y)]);s.net(1160,y,net)
    s.text(810,848,'12  GND',22,True)
    s.line([(865,900),(865,925)]);s.gnd(865,925)
    s.resistor(1370,620);s.gnd(1495,620);s.line([(1470,620),(1495,620)])
    s.text(1360,665,rval('R10')+'  1%',21)
    s.text(1360,701,'4.5 A typical limit*',21,color=MUTED)
    s.cap(1370,755);s.gnd(1370,833)
    s.text(1410,772,'C4 100 nF',22)
    s.text(1130,875,'Both OUT pads must be connected.\nPhysical pad layout is not shown.',21,color=MUTED)
    # Input and output bypass capacitors, electrically connected by net labels.
    for x,net,ref,voltage in [(120,'PYRO_BAT','C1','10 V'),(120,'MAIN_BAT','C2','35 V')]:
        y=330 if ref=='C1' else 630
        s.net(x-30,y,net,POWER);s.cap(x,y);s.gnd(x,y+78)
        s.text(x+40,y+16,ref+' 10 µF\nX7R, '+voltage,21)
    s.text(85,185,'Common battery negatives → GND; route load returns away from analog sense ground.',22,color=MUTED)
    s.line([(70,990),(1730,990)],'#CEDAE3',2)
    s.text(80,1025,'MAIN PATH: OFF UNTIL THE MCU ALLOWS IT',27,True)
    s.net(100,1150,'MAIN_BAT',POWER);s.line([(100,1150),(270,1150)])
    s.resistor(270,1150);s.text(245,1180,rval('R7'),21)
    s.line([(370,1150),(1210,1150)]);s.net(550,1150,'OV2_BLOCK → U1 pin 4')
    s.dot(535,1150);s.line([(535,1150),(535,1230)])
    # Zener represented as a labeled two-terminal device to avoid polarity ambiguity.
    s.box(450,1230,170,100,'#FFF4E9');s.text(465,1242,'D1  4.7 V\nK top / A bottom',18,True)
    s.line([(535,1330),(535,1350)]);s.gnd(535,1350)
    s.text(350,1403,'BZT52C4V7-7-F',20)
    s.box(1040,1230,350,115)
    s.text(1060,1240,'Q1  DMN2056U-13',23,True)
    s.text(1060,1290,'1 G        3 D         2 S',20)
    s.line([(1210,1150),(1210,1230)]);s.text(1225,1190,'D',20)
    s.line([(1320,1345),(1320,1380)]);s.gnd(1320,1380)
    s.net(730,1320,'MCU_MAIN_ALLOW');s.line([(730,1320),(805,1320)])
    s.resistor(805,1320);s.line([(905,1320),(1040,1320)])
    s.text(815,1350,rval('R9'),20)
    s.dot(980,1320);s.line([(980,1320),(980,1360)])
    s.resistor(980,1360,True);s.gnd(980,1460)
    s.text(1010,1390,rval('R8'),20)
    s.text(1430,1150,'GPIO low / Hi-Z:\nIN2 blocked.\n\nGPIO high:\nIN2 permitted;\nIN1 still has priority.',21)
    s.text(80,1520,'*Not a channel-count limiter. Validate load transients, fault response and thermal limits with inert dummy loads.',21,color=POWER)
    s.save('01_power_mux')


def comparator():
    s = Sheet('Automatic IN1 qualification: nominal 3.50 V cutoff',
              'U2 is TLV7041 (open-drain), not TLV7031 (push-pull). Thresholds apply only while 3V3 is regulated.', 2)
    for x,net,top,bottom,node in [(150,'PYRO_BAT','R1','R2','PYRO_SENSE'),
                                (630,'3V3','R3','R4','REF_1V170')]:
        s.net(x-35,265,net,POWER);s.line([(x,265),(x,305)])
        s.resistor(x,305,True);s.text(x+40,325,rval(top)+'\n0.1%',22)
        s.line([(x,405),(x,470)]);s.dot(x,440)
        s.line([(x,440),(x+285,440)]);s.net(x+35,440,node)
        s.resistor(x,470,True);s.gnd(x,570)
        s.text(x+40,492,rval(bottom)+'\n0.1%',22)
    s.text(85,650,'PYRO_SENSE also connects to U1 pin 6 (PR1).\nAt 3.5 V: PYRO_SENSE = 1.1667 V.\nReference divider: REF_1V170 = 1.17021 V.',23)
    s.box(1090,335,475,360)
    s.text(1120,360,'U2  TLV7041DBVR',27,True)
    for y,label,net in [(475,'3  IN+','REF_1V170'),(575,'4  IN−','PYRO_SENSE')]:
        s.line([(865,y),(1090,y)]);s.net(865,y,net);s.text(1110,y-20,label,22,True)
    s.line([(1315,265),(1315,335)],POWER);s.net(1260,265,'3V3 → 5 VCC',POWER)
    s.text(1170,640,'2 VEE → GND',22,True);s.line([(1270,695),(1270,730)]);s.gnd(1270,730)
    s.text(1420,500,'1 OUT',22,True);s.line([(1565,525),(1710,525)])
    s.text(1575,565,'OV1_BLOCK',20,True,WIRE)
    s.text(1060,795,'Output sinks LOW for a healthy IN1.\nOutput releases for low IN1 / comparator POR.',23)
    s.line([(70,900),(1730,900)],'#CEDAE3',2)
    s.text(80,940,'BATTERY-DERIVED BLOCK BIAS',26,True)
    s.net(200,1055,'PYRO_BAT',POWER);s.line([(200,1055),(200,1090)])
    s.resistor(200,1090,True);s.text(240,1115,rval('R5')+'  1%',22)
    s.line([(200,1190),(200,1260)]);s.dot(200,1220)
    s.line([(200,1220),(770,1220)]);s.net(320,1220,'OV1_BLOCK → U2.1 and U1.5')
    s.resistor(200,1260,True);s.gnd(200,1360)
    s.text(240,1285,rval('R6')+'  1%',22)
    s.text(450,1290,'U2 released: OV1 ≈ Vpyro / 2 → blocks IN1.\nU2 sinking: OV1 ≈ 0 V → permits IN1.',22)
    s.net(960,1060,'3V3',POWER);s.cap(960,1060);s.gnd(960,1138)
    s.text(1000,1080,'C5 100 nF\nBeside U2 pins 5/2',22)
    s.box(930,1200,770,240,'#FFF4E9')
    s.text(955,1225,'EXPECTED NOMINAL TRIPS',25,True)
    s.text(955,1275,'Falling: 3.500 V    |    Rising: 3.521 V\nIncludes typical 7 mV internal hysteresis.\nBuck tolerance, comparator offset and hysteresis\nspread move these thresholds. See calculations.',22)
    s.text(80,1480,'A buck rail is not an independent precision reference. Startup/brownout behavior still needs system-level inhibition.',21,color=POWER)
    s.save('02_comparator_threshold')


def monitors():
    s = Sheet('Supply monitors, discharge path and physical isolation',
              'Low VOUT is evidence of an invalid supply, not proof that the TPS output is electrically high impedance.', 3, 1830)
    s.net(100,270,'TPS_OUT',POWER);s.line([(100,270),(1130,270)],POWER)
    s.dot(180,270);s.cap(180,270);s.gnd(180,348)
    s.text(85,405,'C3 10 µF\n35 V, X7R',22)
    s.dot(470,270);s.resistor(470,270,True);s.gnd(470,370)
    s.text(515,304,rval('R12')+'\n1%, 0.5 W bleed',22)
    s.line([(1130,270),(1150,270)],POWER);s.dot(1150,270)
    s.line([(1150,270),(1220,245)],POWER);s.dot(1235,270)
    s.line([(1235,270),(1680,270)],POWER)
    s.text(1060,195,'SW1  PHYSICAL ARM',24,True)
    s.net(1390,270,'ARMED_SUPPLY',POWER)
    s.text(1050,320,'Disconnect downstream load power for USB testing.\nChannel drivers also require a separate default-low\nhardware inhibit and firmware arming. Not drawn here.',22)
    s.text(80,495,'TWO IDENTICAL ADC DIVIDERS (0.1%): each raw voltage = ADC voltage × 5.99',25,True)
    for y,source,top,bot,cap,node in [(620,'TPS_OUT','R13','R14','C6','OUT_DIV'),
                                    (890,'MAIN_BAT','R15','R16','C7','MAIN_DIV')]:
        s.net(100,y,source);s.line([(100,y),(275,y)])
        s.resistor(275,y);s.text(255,y-75,rval(top),22)
        s.line([(375,y),(1040,y)]);s.net(835,y,node)
        s.dot(485,y);s.resistor(485,y,True);s.gnd(485,y+100)
        s.text(520,y+32,rval(bot),22)
        s.dot(740,y);s.cap(740,y);s.gnd(740,y+78)
        s.text(785,y+36,cap+' 10 nF',21)
    s.box(1040,545,435,520)
    s.text(1065,565,'U3 TMUX1511RSVR',24,True)
    s.text(1065,615,'2 S1 → D1 3',22,True)
    s.line([(1475,640),(1710,640)]);s.net(1485,640,'ADC_TPS_OUT')
    s.text(1065,885,'5 S2 → D2 6',22,True)
    s.line([(1475,910),(1710,910)]);s.net(1490,910,'ADC_MAIN')
    s.text(1065,690,'16 VDD → 3V3; 8 → GND\n1,4,11 → SENSE_EN\n10 → USB_DIV; 9 → ADC_USB\n13,14,15 → GND\n7,12 NC → unconnected',20)
    s.text(1065,960,'Isolates ADCs when unpowered.\nEnable only with valid MCU supply.\nNo MCU package pins assigned.',20,color=MUTED)
    s.line([(70,1135),(1730,1135)],'#CEDAE3',2)
    s.net(120,1220,'MCU_SENSE_EN');s.line([(120,1220),(470,1220)])
    s.net(380,1220,'SENSE_EN');s.dot(300,1220)
    s.resistor(300,1220,True);s.gnd(300,1320)
    s.text(345,1255,rval('R17'),21)
    s.net(600,1220,'3V3',POWER);s.cap(600,1220);s.gnd(600,1298)
    s.text(640,1237,'C8 100 nF\nBeside U3',21)
    s.net(970,1220,'3V3',POWER);s.line([(970,1220),(1090,1220)])
    s.resistor(1090,1220);s.line([(1190,1220),(1650,1220)])
    s.net(1350,1220,'TPS_ST → MCU GPIO')
    s.text(1080,1255,rval('R11'),21)
    s.text(970,1310,'ST low: IN2. ST high: IN1 OR Hi-Z.\nInterpret together with the output ADC.',22)
    s.box(80,1400,800,285)
    s.text(105,1420,'MAIN-PACK FIRMWARE POLICY',24,True)
    s.text(105,1470,'1S: 3.5 V      2S: 7.0 V\n3S: 10.5 V    4S: 14.0 V\nConfigure cell count explicitly; do not infer it\nfrom pack voltage. Low voltage alone must\nnever issue a deployment command.',23)
    s.box(930,1400,770,285,'#FFF4E9')
    s.text(955,1420,'DISCHARGE / ADC CHECK',24,True)
    s.text(955,1470,'Use a 500 ms diagnostic wait (not firing latency).\nAssumes total TPS_OUT capacitance ≤ 22 µF.\nBelow 0.5 V: near-zero under stated conditions.\nBelow 2.0 V: clearly invalid for this supply.\nLeakage and temperature limits: see README.',22)
    s.text(80,1730,'Monitor BEFORE SW1: an energized TPS_OUT does not mean the armed rail is connected or any channel is enabled.',21,color=POWER)
    s.save('03_monitor_and_inhibit')


def single_sheet():
    """Same electrical design, explicit interconnects on one landscape sheet.

    TPS symbol positions follow the supplied datasheet example, NOT its values
    or manual-CP2-control topology. Junction dots connect; jumpovers do not.
    """
    s = Sheet('TPS2121 battery selector | comparator lockout and MCU monitoring',
              'Dedicated 1S battery preferred; main 1-4S battery requires MCU permission. Resistor calculations and limitations: README.md.',
              1, height=2300, width=3300)

    def wire(pts, power=False):
        s.line(pts, POWER if power else WIRE)

    def vr(ref,x,y,tx=None,ty=None):
        s.resistor(x,y,True)
        s.text(x+28 if tx is None else tx,y+33 if ty is None else ty,rval(ref),22)

    def hr(ref,x,y,tx=None,ty=None):
        s.resistor(x,y)
        s.text(x-15 if tx is None else tx,y-47 if ty is None else ty,rval(ref),22)

    def jump(x,y):
        # Horizontal wire stays continuous; vertical wire bridges over it.
        s.line([(x,y-12),(x,y+12)],'white',9)
        s.line([(x-14,y),(x+14,y)])
        s.line([(x,y-12),(x+12,y-7),(x+12,y+7),(x,y+12)])

    # Main IC follows the reference image: IN1 / PR1 / OV1 / IN2 / OV2 left;
    # OUT / CP2 / ST / SS / ILIM right, ground at bottom.
    s.box(1300,250,420,1250,fill='white')
    s.text(1390,1000,'U1\nTPS2121RUXR',29,True)
    for y,label in [(350,'7  IN1'),(550,'6  PR1'),(900,'5  OV1'),
                    (1150,'2  IN2'),(1350,'4  OV2')]:
        s.text(1320,y-17,label,25)
    for y,label in [(350,'OUT  1,8'),(650,'CP2  3'),(800,'ST  9'),
                    (1100,'SS  11'),(1350,'ILIM  10')]:
        s.text(1545,y-17,label,25)
    s.text(1440,1450,'GND 12',25)
    wire([(1510,1500),(1510,1540)]);s.gnd(1510,1540)

    # Dedicated battery and the directly wired shared R1/R2 sense divider.
    s.net(80,350,'PYRO_BAT  (1S, max 4.2 V)',POWER)
    wire([(80,350),(1300,350)],True)
    s.dot(160,350);s.cap(160,350);s.gnd(160,428)
    s.text(80,465,'C1 10 µF / 10 V',21)
    s.dot(350,350);wire([(350,350),(350,390)])
    vr('R1',350,390);wire([(350,490),(350,570)])
    s.dot(350,550);wire([(350,550),(1300,550)])
    s.net(700,550,'PYRO_SENSE')
    vr('R2',350,570);s.gnd(350,670)
    s.dot(590,550);wire([(590,550),(590,730),(850,730)])
    # Comparator triangle; IN- at top, IN+ at bottom.
    s.line([(850,680),(1070,800),(850,920),(850,680)],INK)
    s.text(865,711,'−  4',24);s.text(865,848,'+  3',24)
    s.text(1080,763,'1',21)
    s.text(810,1060,'U2 TLV7041DBVR',25,True)
    s.text(810,1095,'Open-drain comparator',20,color=MUTED)
    s.net(650,700,'3V3',POWER)
    wire([(650,700),(650,750)],True);vr('R3',650,750,675,775)
    wire([(650,850),(650,920)]);s.dot(650,870)
    wire([(650,870),(850,870)]);s.net(690,870,'REF_1V170')
    vr('R4',650,920);s.gnd(650,1020)
    s.net(940,610,'3V3',POWER);wire([(940,610),(940,729)],True)
    s.text(950,710,'5',20)
    s.dot(940,620);wire([(940,620),(1030,620)],True)
    s.cap(1030,620);s.gnd(1030,698);s.text(995,560,'C5 100 nF',20)
    wire([(940,871),(940,910)]);s.gnd(940,910);s.text(955,886,'2',20)
    # Pull-up/down bias actually connects to IN1 and the comparator output.
    s.dot(1220,350);wire([(1220,350),(1220,650)])
    vr('R5',1220,650,1060,655)
    wire([(1220,750),(1220,930)])
    wire([(1070,800),(1220,800)]);s.dot(1220,800)
    wire([(1220,900),(1300,900)]);s.dot(1220,900)
    s.text(1090,840,'OV1_BLOCK',20,True,WIRE)
    vr('R6',1220,930,1060,970);s.gnd(1220,1030)
    jump(1220,550);jump(650,730)

    # Main pack and default-disabled OV2 path.
    s.net(80,1150,'MAIN_BAT  (1-4S, max 16.8 V)',POWER)
    wire([(80,1150),(1300,1150)],True)
    s.dot(170,1150);s.cap(170,1150);s.gnd(170,1228)
    s.text(80,1265,'C2 10 µF / 35 V',21)
    s.dot(750,1150);wire([(750,1150),(750,1200)])
    vr('R7',750,1200);wire([(750,1300),(750,1450)])
    s.dot(750,1350);wire([(750,1350),(1300,1350)])
    s.net(1000,1350,'OV2_BLOCK')
    s.dot(990,1350);wire([(990,1350),(990,1410)])
    # Conventional zener symbol, cathode uppermost.
    s.line([(966,1403),(966,1410),(1014,1410),(1014,1417)],INK)
    s.line([(990,1410),(969,1445),(1011,1445),(990,1410)],INK)
    wire([(990,1445),(990,1485)]);s.gnd(990,1485)
    s.text(1035,1405,'D1 4.7 V\nBZT52C4V7-7-F\nK top / A bottom',21)
    s.box(600,1450,240,130,fill='white')
    s.text(617,1475,'Q1 N-MOS',23,True)
    s.text(615,1532,'1 G    3 D    2 S',19)
    wire([(790,1580),(790,1630)]);s.gnd(790,1630)
    s.text(680,1680,'DMN2056U-13',22)
    wire([(350,1530),(450,1530)]);hr('R9',450,1530,405,1465)
    wire([(550,1530),(600,1530)]);s.dot(570,1530)
    wire([(570,1530),(570,1600)]);vr('R8',570,1600,390,1645);s.gnd(570,1700)

    # Output power, local discharge and physical arm disconnect.
    wire([(1720,350),(2680,350)],True);s.net(1850,350,'TPS_OUT',POWER)
    for x in (1900,2120):s.dot(x,350)
    s.cap(1900,350);s.gnd(1900,428);s.text(1830,465,'C3 10 µF / 35 V',21)
    vr('R12',2120,350,2160,390);s.gnd(2120,450)
    s.text(2160,430,'0.5 W',20)
    s.dot(2680,350);s.line([(2680,350),(2750,320)],POWER);s.dot(2765,350)
    wire([(2765,350),(3200,350)],True)
    s.text(2620,245,'SW1 PHYSICAL ARM',24,True)
    s.net(2830,350,'ARMED_SUPPLY',POWER)
    s.text(2830,385,'To inhibited channel drivers\n(not included here)',22,color=MUTED)
    # Output divider connects from the actual OUT rail to U3.
    s.dot(1800,350);wire([(1800,350),(1800,600),(1900,600)])
    hr('R13',1900,600,1840,545);wire([(2000,600),(2300,600),(2300,800),(2450,800)])
    s.dot(2020,600);wire([(2020,600),(2020,630)])
    vr('R14',2020,630,1840,675);s.gnd(2020,730)
    s.dot(2200,600);wire([(2200,600),(2200,630)])
    s.cap(2200,630);s.gnd(2200,708);s.text(2110,770,'C6 10 nF',20)
    s.net(2330,800,'OUT_DIV')

    # CP2 grounded, as in the existing automatic-priority design.
    wire([(1720,650),(1770,650)]);s.gnd(1770,650)
    # ST route and pull-up, visibly reaching the MCU.
    wire([(1720,800),(1840,800),(1840,1200),(2950,1200)])
    s.net(1870,1200,'TPS_ST')
    s.dot(2060,1200);wire([(2060,1200),(2060,1060)])
    vr('R11',2060,960,2090,982);s.net(2010,960,'3V3',POWER)
    wire([(1720,1100),(1775,1100)]);s.cap(1775,1100);s.gnd(1775,1178)
    s.text(1870,1250,'C4 100 nF',20)
    wire([(1720,1350),(1830,1350)]);vr('R10',1830,1350,1860,1380);s.gnd(1830,1450)

    # ADC isolation and MCU: all functional signal paths are drawn.
    s.box(2450,700,350,400,fill='white')
    s.text(2470,720,'U3 TMUX1511RSVR',23,True)
    s.text(2470,784,'2 S1       D1 3',22)
    s.text(2470,934,'5 S2       D2 6',22)
    s.text(2470,1032,'SEL1 1 + SEL2 4',21)
    wire([(2800,800),(2950,800)]);wire([(2800,950),(2950,950)])
    s.net(2620,560,'3V3',POWER);wire([(2620,560),(2620,700)],True)
    s.text(2635,674,'16 VDD',20)
    s.dot(2620,590);wire([(2620,590),(2740,590)],True)
    s.cap(2740,590);s.gnd(2740,668);s.text(2780,610,'C8\n100 nF',20)
    s.text(2480,837,'8,13,14,15 → GND; 7,12 NC\n10 USB_DIV; 9 ADC_USB; 11 SENSE_EN\nChannel 3: see logic_power sheet',16,color=MUTED)
    wire([(2500,1100),(2500,1140)]);s.gnd(2500,1140)
    wire([(2680,1100),(2680,1300),(2950,1300)])
    s.dot(2800,1300);wire([(2800,1300),(2800,1350)])
    vr('R17',2800,1350,2580,1385);s.gnd(2800,1450)
    s.net(2685,1300,'SENSE_EN')
    s.box(2950,700,285,1350,fill=LIGHT)
    s.text(2990,730,'MCU / 3V3',26,True)
    for y,label in [(800,'ADC_TPS_OUT'),(950,'ADC_MAIN'),(1200,'GPIO: TPS_ST'),
                    (1300,'GPIO: SENSE_EN'),(2000,'GPIO: MAIN_ALLOW')]:
        s.text(2970,y-15,label,20,True)
    s.text(2970,1470,'Exact MCU pins\nnot assigned.\n\nReset defaults:\nMAIN_ALLOW = low\nSENSE_EN = low\n\nSeparate hardware\nand firmware\narming required.',21)
    # Direct main-battery measurement path, routed below the power selector.
    s.dot(100,1150);wire([(100,1150),(100,1800),(1900,1800)])
    hr('R15',1900,1800,1860,1740)
    wire([(2000,1800),(2350,1800),(2350,950),(2450,950)])
    s.dot(2070,1800);wire([(2070,1800),(2070,1840)])
    vr('R16',2070,1840,2100,1875);s.gnd(2070,1940)
    s.dot(2250,1800);wire([(2250,1800),(2250,1840)])
    s.cap(2250,1840);s.gnd(2250,1918);s.text(2300,1860,'C7 10 nF',20)
    s.net(2400,1750,'MAIN_DIV')
    # Firmware permission route loops under the battery-monitor line.
    wire([(2950,2000),(350,2000),(350,1530)])
    s.net(650,2000,'MCU_MAIN_ALLOW')
    jump(350,1800);jump(2350,1200);jump(2680,1200)
    # Small legends only: derivations and detailed logic stay in the MD file.
    s.text(80,2110,'Junction dot = connected. Wire jump = NOT connected. All ground symbols share GND. 3V3 comes from the independent MCU buck/USB power path.',23)
    s.text(80,2150,'R1-R4 and R13-R16: 0.1%. Other resistors: 1%. Nominal 3.5 V cutoff only; reference tolerance and power sequencing remain design constraints.',23,color=POWER)
    s.text(80,2190,'USB never connects to IN1/IN2/OUT. Source selection is not arming. Inert-load verification required before implementation.',23,color=MUTED)
    s.save('pyro_power_single_sheet')
    root = ET.parse(OUT/'pyro_power_single_sheet.svg').getroot()
    labels = [el.text for el in root.iter('{http://www.w3.org/2000/svg}text')]
    for ref in R:
        assert labels.count(rval(ref)) == 1, f'Missing or duplicated value label: {ref}'


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    report = calculations()
    single_sheet()
    (OUT/'calculated_values.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (OUT/'connections.json').write_text(json.dumps({'IC_pins':IC_PINS,
        'passive_connections':PASSIVES,'resistors_ohm':R,'capacitors_F':C},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    print('Checks passed: arithmetic, expected source policy, pin coverage, SVG XML, PNG dimensions.')
