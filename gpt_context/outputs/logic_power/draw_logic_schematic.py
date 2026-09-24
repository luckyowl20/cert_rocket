"""Render one USB-priority logic-power sheet (PNG + SVG).

Run with Python + Pillow. Uses the existing pyro renderer's drawing primitives;
does not execute its main routine or change its output files.
Prototype connection guide, not a manufacturing schematic. See README.md.
"""
from pathlib import Path
import importlib.util
import json
from itertools import product
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'pyro_drawing_primitives', OUT.parent / 'pyro_power' / 'draw_pyro_schematic.py')
draw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draw)
# Sheet.save uses its module's OUT; this is a private imported module instance.
draw.OUT = OUT
Sheet, WIRE, POWER, MUTED = draw.Sheet, draw.WIRE, draw.POWER, draw.MUTED

R = {'R18': 15000, 'R19': 10000, 'R20': 100000, 'R21': 1000,
     'R22': 80600, 'R23': 10000, 'R24': 49900, 'R25': 10000}
C = {'C9': 1e-6, 'C10': 10e-6, 'C11': 10e-6, 'C12': 100e-9,
     'C14': 10e-9}
PINS = {
    'U4 TPS2121RUXR': {1: 'LOGIC_RAW', 2: 'MAIN_BAT', 3: 'LOGIC_CP2',
        4: 'GND', 5: 'GND', 6: 'USB_PRIORITY', 7: 'USB_VBUS',
        8: 'LOGIC_RAW', 9: 'LOGIC_ST', 10: 'LOGIC_ILIM',
        11: 'LOGIC_SS', 12: 'GND'},
    'U3 TMUX1511RSVR shared with pyro sheet': {
        1: 'SENSE_EN', 2: 'OUT_DIV', 3: 'ADC_TPS_OUT', 4: 'SENSE_EN',
        5: 'MAIN_DIV', 6: 'ADC_MAIN', 7: 'NC', 8: 'GND', 9: 'ADC_USB',
        10: 'USB_DIV', 11: 'SENSE_EN', 12: 'NC', 13: 'GND',
        14: 'GND', 15: 'GND', 16: '3V3'},
}
PASSIVES = {
    'R18': ('USB_VBUS', 'USB_PRIORITY'), 'R19': ('USB_PRIORITY', 'GND'),
    'R20': ('LOGIC_CP2', 'GND'), 'R21': ('MCU_SELECT_MAIN', 'LOGIC_CP2'),
    'R22': ('LOGIC_ILIM', 'GND'), 'R23': ('3V3', 'LOGIC_ST'),
    'R24': ('USB_VBUS', 'USB_DIV'), 'R25': ('USB_DIV', 'GND'),
    'C9': ('USB_VBUS', 'GND'), 'C10': ('MAIN_BAT', 'GND'),
    'C11': ('LOGIC_RAW', 'GND'), 'C12': ('LOGIC_SS', 'GND'),
    'C14': ('USB_DIV', 'GND'),
}


def calculations():
    k = R['R19'] / (R['R18'] + R['R19'])
    ka = R['R25'] / (R['R24'] + R['R25'])
    cases = []
    for usb, main, command in product((0, 2.8, 3.5, 4.3, 4.5, 5, 5.5),
                             (0, 2.8, 3.5, 4.2, 8.4, 12.6, 16.8),
                             ('Hi-Z', 'LOW', 'HIGH')):
        # Settled cases within the recommended range; startup/reset and
        # GPIO loss of power are not transistor-level modeled here.
        usb_ok = usb >= 2.8
        main_ok = main >= 2.8
        pr1 = usb * k
        cp2 = 3.3 * R['R20'] / (R['R20'] + R['R21']) if command == 'HIGH' else 0
        if not usb_ok and not main_ok:
            actual = 'Hi-Z'
        elif not main_ok:
            actual = 'USB'
        elif not usb_ok:
            actual = 'MAIN'
        elif cp2 < 1.06 and pr1 >= 1.06:
            actual = 'USB'
        elif cp2 >= 1.06:
            actual = 'MAIN' if pr1 <= cp2 else 'USB'
        else:
            actual = 'MAIN' if main >= usb else 'USB'
        expected = ('MAIN' if command == 'HIGH' and main_ok else
                    'USB' if usb_ok else 'MAIN' if main_ok else 'Hi-Z')
        assert actual == expected, (usb, main, actual, expected)
        cases.append({'USB_V': usb, 'MAIN_V': main, 'GPIO': command, 'source': actual})
    # 1% resistor corners and +/-0.1 uA control-pin leakage. GPIO high is
    # required to be >=2.4 V while deliberately commanding MAIN.
    pr_corners, cp_corners = [], []
    for a, b, leak in product((.99, 1.01), (.99, 1.01), (-.1e-6, .1e-6)):
        rt, rb = R['R18'] * a, R['R19'] * b
        pr_corners.append((2.8 * rb/(rt+rb) + leak*rt*rb/(rt+rb),
                           5.5 * rb/(rt+rb) + leak*rt*rb/(rt+rb)))
        rs, rp = R['R21'] * a, R['R20'] * b
        cp_corners.append(2.4 * rp/(rs+rp) + leak*rs*rp/(rs+rp))
    pr_min = min(x[0] for x in pr_corners)
    pr_max = max(x[1] for x in pr_corners)
    cp_min = min(cp_corners)
    adc_max = 5.5 * (10000 * 1.001) / (49900 * .999 + 10000 * 1.001)
    assert pr_min > 1.10
    assert cp_min - pr_max > .040
    assert adc_max < 1 and 5.5 * k < 5.5
    assert set(PASSIVES) == set(R) | set(C)
    for name, count in [('U4 TPS2121RUXR', 12),
                        ('U3 TMUX1511RSVR shared with pyro sheet', 16)]:
        assert set(PINS[name]) == set(range(1, count + 1))
    assert draw.IC_PINS['U3 TMUX1511RSVR'] == PINS['U3 TMUX1511RSVR shared with pyro sheet']
    report = {'USB_priority_ratio': k, 'PR1_at_USB_5V_V': 5*k,
        'PR1_min_at_USB_2V8_V': pr_min, 'PR1_max_at_USB_5V5_V': pr_max,
        'CP2_min_for_GPIO_2V4_V': cp_min,
        'CP2_minus_PR1_min_margin_V': cp_min-pr_max,
        'CP2_at_GPIO_3V3_V': 3.3*R['R20']/(R['R20']+R['R21']),
        'adc_ratio': ka, 'adc_at_USB_5V_V': 5 * ka,
        'adc_max_at_USB_5V5_with_0p1pct_resistors_V': adc_max,
        'adc_filter_tau_s': R['R24'] * R['R25'] / (R['R24'] + R['R25']) * C['C14'],
        'ILIM_equation_typical_A': 65.2 / ((R['R22'] / 1000) ** .861),
        'buck_input_estimate_5V_85pct_A': 3.3 * .6 / (5 * .85),
        'buck_input_estimate_4V4_85pct_A': 3.3 * .6 / (4.4 * .85),
        'steady_state_test_cases': cases}
    return report


def render():
    s = Sheet('Logic power: USB default + MCU-selectable main battery',
        'Fixed 5 V USB only | no external USB comparator | MCU_SELECT_MAIN: low/Hi-Z = USB priority, high = main priority',
        1, height=2180, width=3260)

    def wire(points, power=False):
        s.line(points, POWER if power else WIRE)

    def res(ref, x, y, vertical=False, tx=None, ty=None):
        s.resistor(x, y, vertical)
        s.text(x + 30 if tx is None else tx,
               y + 30 if ty is None else ty,
               f'{ref}  {R[ref]/1000:g} kΩ', 22)

    def jump(x, y):
        s.line([(x, y-12), (x, y+12)], 'white', 10)
        wire([(x-14, y), (x+14, y)])
        wire([(x, y-12), (x+12, y-7), (x+12, y+7), (x, y+12)])

    # TPS arrangement matches the datasheet example and the companion sheet.
    s.box(1300, 220, 480, 910, fill='white')
    s.text(1390, 700, 'U4\nTPS2121RUXR', 30, True)
    for y, label in [(280, '7  IN1'), (470, '6  PR1'), (650, '5  OV1'),
                     (880, '2  IN2'), (1010, '4  OV2')]:
        s.text(1320, y-16, label, 25)
    for y, label in [(280, 'OUT 1,8'), (400, 'CP2 3'), (520, 'ST 9'),
                     (800, 'SS 11'), (1000, 'ILIM 10')]:
        s.text(1600, y-16, label, 25)
    s.text(1470, 1080, 'GND 12', 25)
    wire([(1540, 1130), (1540, 1170)]); s.gnd(1540, 1170)
    wire([(1240, 1010), (1300, 1010)]); s.gnd(1240, 1010)
    wire([(1240, 650), (1300, 650)]); s.gnd(1240, 650)

    # USB-derived PR1 establishes priority before the MCU is powered.
    s.net(90, 280, 'USB_VBUS  (5 V, no PD)', POWER)
    wire([(90, 280), (1300, 280)], True)
    s.dot(250, 280); s.cap(250, 280); s.gnd(250, 358)
    s.text(90, 400, 'C9  1 µF / 10 V', 22)
    s.dot(500, 280); wire([(500, 280), (500, 320)])
    res('R18', 500, 320, True)
    wire([(500, 420), (500, 510)]); s.dot(500, 470)
    wire([(500, 470), (1300, 470)])
    s.net(665, 470, 'USB_PRIORITY')
    res('R19', 500, 510, True); s.gnd(500, 610)
    s.text(90, 735, 'DEFAULTS WITHOUT FIRMWARE', 27, True)
    s.text(90, 795, 'USB present: prefer IN1, even if main has higher voltage.\nUSB absent: use main automatically.\nMCU reset / unpowered: R20 holds CP2 low.\nBoth OV pins grounded; no separate 4.4 V USB cutoff.', 25)
    s.text(90, 995, 'MCU high on CP2 prefers main when main is TPS-valid.\nIf main is absent, USB remains available as fallback.\nWeak USB can cause brownouts; not a clean-off guarantee.', 23, color=POWER)

    # MCU control: analog CP2 comparison is used as a logic preference input.
    wire([(1780, 400), (1940, 400), (1940, 710), (2100, 710)])
    res('R21', 2100, 710, tx=2070, ty=655)
    wire([(2200, 710), (2440, 710)])
    s.net(2280, 710, 'MCU_SELECT_MAIN')
    s.dot(2020, 710); res('R20', 2020, 710, True, 2060, 755)
    s.gnd(2020, 810)
    s.text(2460, 730, 'From STM32 3.3 V push-pull GPIO\nLOW / Hi-Z: USB default\nHIGH: prefer main (not a hard USB disable)', 22)

    # Main source has no MCU permission dependency (would prevent cold boot).
    s.net(90, 1200, 'MAIN_BAT  (1–4S, max 16.8 V)', POWER)
    wire([(90, 1200), (1200, 1200), (1200, 880), (1300, 880)], True)
    s.dot(250, 1200); s.cap(250, 1200); s.gnd(250, 1278)
    s.text(90, 1320, 'C10  10 µF / 35 V', 22)
    s.text(410, 1230, 'Same raw battery net as pyro IN2 and R15.\nNot connected to TPS_OUT / ARMED_SUPPLY.', 23)

    # Raw selected power drives the EXISTING buck; it is never an MCU VDD net.
    wire([(1780, 280), (2520, 280)], True)
    s.net(1980, 280, 'LOGIC_RAW → buck VIN', POWER)
    s.dot(2070, 280); s.cap(2070, 280); s.gnd(2070, 358)
    s.text(1990, 395, 'C11  10 µF / 35 V', 22)
    s.box(2520, 220, 440, 230, fill=draw.LIGHT)
    s.text(2540, 240, 'EXISTING 3.3 V BUCK', 26, True)
    s.text(2540, 295, 'LMR604063SBRAKRQ1\nInductor / support parts: separate\nFull logic load ≤ 600 mA', 22)
    wire([(2960, 280), (3160, 280)], True); s.net(3010, 280, '3V3', POWER)
    s.text(2535, 488, 'Do not retain a parallel USB→3V3 power path.\n1S cold-start / dropout needs validation.', 22, color=POWER)

    wire([(1780, 520), (2390, 520)])
    jump(1940, 520)
    s.net(1970, 520, 'LOGIC_ST → GPIO')
    s.dot(2300, 520); wire([(2300, 480), (2300, 520)])
    res('R23', 2300, 380, True, 2340, 413)
    wire([(2300, 350), (2300, 380)]); s.net(2270, 350, '3V3')
    s.text(2470, 560, 'ST low: main selected.\nST high: USB selected OR neither valid.', 22)
    wire([(1780, 800), (1860, 800)]); s.cap(1860, 800); s.gnd(1860, 878)
    s.text(1900, 900, 'C12  100 nF', 22)
    wire([(1780, 1000), (1860, 1000)])
    res('R22', 1860, 1000, True, 1900, 1030); s.gnd(1860, 1100)
    s.text(2200, 940, '≈1.49 A nominal raw-rail current limit.\nNot a USB current-permission circuit.\nSwitchover hold-up must be tested.', 23, color=POWER)

    # One physical U3 shown as a shared cross-sheet component, not a second IC.
    s.box(2250, 1240, 410, 600, fill='white')
    s.text(2270, 1260, 'U3 TMUX1511RSVR', 25, True)
    for y, left, right in [(1350, '2 S1', 'D1 3'), (1480, '5 S2', 'D2 6'),
                           (1630, '10 S3', 'D3 9')]:
        s.text(2270, y-16, left, 24); s.text(2540, y-16, right, 24)
    s.text(2270, 1710, 'SEL1/2/3 = pins 1/4/11\n16 VDD = 3V3; 8 GND = GND\n13/14/15 = GND; 7/12 = NC', 20)
    s.box(2850, 1240, 320, 600, fill=draw.LIGHT)
    s.text(2870, 1260, 'STM32G474RET6', 25, True)
    for y, label in [(1350, 'ADC_TPS_OUT'), (1480, 'ADC_MAIN'), (1630, 'ADC_USB')]:
        wire([(2660, y), (2850, y)])
        s.text(2870, y-16, label, 22, True)
    s.text(2870, 1710, 'ADC pads not assigned.\nAll channels share\nSENSE_EN.', 22)
    for y, name in [(1350, 'OUT_DIV'), (1480, 'MAIN_DIV')]:
        wire([(1940, y), (2250, y)]); s.net(1950, y, name)
    s.text(1560, 1250, 'Existing pyro-sheet dividers:\nR13/R14 → OUT_DIV\nR15/R16 → MAIN_DIV\nNo new main divider.', 22)

    s.net(90, 1630, 'USB_VBUS', POWER)
    wire([(90, 1630), (500, 1630)])
    res('R24', 500, 1630, tx=450, ty=1565)
    wire([(600, 1630), (2250, 1630)])
    s.dot(800, 1630); res('R25', 800, 1630, True); s.gnd(800, 1730)
    s.dot(1120, 1630); s.cap(1120, 1630); s.gnd(1120, 1708)
    s.text(1160, 1660, 'C14  10 nF', 22)
    s.net(1730, 1630, 'USB_DIV')
    wire([(2450, 1840), (2450, 1910), (3010, 1910), (3010, 1840)])
    s.net(2560, 1910, 'SENSE_EN')
    s.text(90, 1840, 'Shared U3: reuse existing C8 (100 nF) and R17 (100 kΩ SENSE_EN pull-down).\nChannel 3 is no longer grounded: pin 10 = USB_DIV, pin 9 = ADC_USB, pin 11 = SENSE_EN.\nThe companion pyro sheet / manifest are updated to match; only one U3 is populated.', 24)
    s.text(90, 2000, 'R24/R25: 0.1%; R18–R23: 1%. U5 and C13 removed. R18/R20/R21 changed. See README before updating an earlier schematic.', 22)
    s.text(90, 2045, 'This powers logic only. Fixed-5-V USB current authorization and input protection remain USB-front-end requirements. See README for limits.', 22, color=POWER)
    s.text(90, 2088, 'Dot = junction. Jump = no connection. Repeated net names connect across sheets. Common GND. No pyro battery feeds this mux.', 22)
    s.save('logic_power_single_sheet')
    root = ET.parse(OUT / 'logic_power_single_sheet.svg').getroot()
    labels = [el.text for el in root.iter('{http://www.w3.org/2000/svg}text')]
    for ref, value in R.items():
        assert labels.count(f'{ref}  {value/1000:g} kΩ') == 1, ref


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    report = calculations()
    render()
    (OUT / 'calculated_values.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (OUT / 'connections.json').write_text(json.dumps({'IC_pins': PINS,
        'passive_connections': PASSIVES, 'resistors_ohm': R,
        'capacitors_F': C, 'note': 'U3 is the EXISTING shared IC, not a new part.'}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'steady_state_test_cases'}, indent=2))
    print(f'PASS: {len(report["steady_state_test_cases"])} nominal source cases; pin coverage; labels; SVG; PNG.')
