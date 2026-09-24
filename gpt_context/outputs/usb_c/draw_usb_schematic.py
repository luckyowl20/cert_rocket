"""Generate explanatory STM32G4 USB-C schematics as PNG and SVG using Pillow.

Not a manufacturing schematic. Exact MCU package and battery are unconfirmed.
Run: python draw_usb_schematic.py
See README.md for references, caveats, and distributor links.
"""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
INK = '#172B43'
WIRE = '#166A79'
POWER = '#AB4D14'
MUTED = '#526579'
LIGHT = '#EEF5FA'
FONT_DIR = Path('C:/Windows/Fonts')


class Sheet:
    def __init__(self, height, title, subtitle, number):
        self.w, self.h = 1800, height
        self.im = Image.new('RGB', (self.w * 2, self.h * 2), 'white')
        self.d = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="{height}" viewBox="0 0 1800 {height}">', '<rect width="100%" height="100%" fill="white"/>']
        self.text(70, 45, title, 42, True)
        self.text(70, 106, subtitle, 23, color=MUTED)
        self.line([(70, 153), (1730, 153)], '#CEDAE3', 2)
        self.text(70, height - 55, 'CONNECTION GUIDE ONLY  |  Confirm exact MCU/package, power budget and KiCad footprint before manufacture.', 21, color=MUTED)
        self.text(1660, height - 55, number, 21, True)

    def text(self, x, y, s, size=25, bold=False, color=INK):
        font = ImageFont.truetype(str(FONT_DIR / ('arialbd.ttf' if bold else 'arial.ttf')), size * 2)
        for i, row in enumerate(s.split('\n')):
            yy = y + i * (size + 10)
            self.d.text((x * 2, yy * 2), row, fill=color, font=font, anchor='lt')
            self.svg.append(f'<text x="{x}" y="{yy}" dominant-baseline="text-before-edge" font-family="Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(row)}</text>')

    def line(self, pts, color=WIRE, width=3):
        self.d.line([(x * 2, y * 2) for x, y in pts], fill=color, width=width * 2)
        self.svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="{width}"/>')

    def box(self, x, y, w, h, fill=LIGHT, color=INK):
        self.d.rectangle((x*2, y*2, (x+w)*2, (y+h)*2), fill=fill, outline=color, width=4)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{color}" stroke-width="2"/>')

    def dot(self, x, y):
        self.d.ellipse(((x-5)*2, (y-5)*2, (x+5)*2, (y+5)*2), fill=WIRE)
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

    def switch(self, x, y, vertical=False):
        if vertical:
            self.line([(x,y),(x,y+20)])
            self.line([(x,y+20),(x-22,y+68)])
            self.line([(x,y+75),(x,y+100)])
            self.dot(x,y+20); self.dot(x,y+75)
        else:
            self.line([(x,y),(x+20,y)])
            self.line([(x+20,y),(x+70,y-22)])
            self.line([(x+75,y),(x+100,y)])
            self.dot(x+20,y); self.dot(x+75,y)

    def net(self, x, y, name, color=WIRE):
        self.text(x,y-33,name,23,True,color)

    def arrow(self, x1, y, x2, color=POWER):
        self.line([(x1,y),(x2,y)],color,4)
        self.line([(x2-12,y-8),(x2,y),(x2-12,y+8)],color,4)

    def save(self, name):
        self.im.resize((self.w,self.h),Image.Resampling.LANCZOS).save(OUT / f'{name}.png')
        (OUT / f'{name}.svg').write_text('\n'.join(self.svg + ['</svg>']),encoding='utf-8')
        print(OUT / f'{name}.png')


def usb():
    s = Sheet(1550, 'USB-C → STM32G4: data and connector wiring',
              'USB 2.0 full-speed DEVICE / 5 V SINK. G474 electrical reference; no USB-PD or USB-to-UART bridge required.', '1 / 2')
    s.text(90,195,'J1  USB4105-GF-A',29,True)
    s.text(90,237,'USB-C receptacle • USB 2.0',23,color=MUTED)
    s.box(90,285,390,725)
    pins = [(365,'A4, A9, B4, B9','VBUS'),(470,'A6 + B6','D+'),(550,'A7 + B7','D−'),(665,'A5','CC1'),(775,'B5','CC2'),(865,'A1, A12, B1, B12','GND'),(930,'A8, B8','SBU1/2'),(980,'Metal shell','SHIELD')]
    for y,pin,name in pins:
        s.text(110,y-27,pin,22)
        s.text(360,y-27,name,22,True)
    s.line([(480,365),(835,365)],POWER)
    s.net(560,365,'USB_VBUS (5 V)',POWER)
    s.text(545,382,'To protected power input on sheet 2',21,color=MUTED)
    s.line([(480,470),(1250,470)])
    s.line([(480,550),(1250,550)])
    s.net(650,470,'USB_DP'); s.net(650,550,'USB_DM')
    s.text(880,420,'Direct connections',22,True)
    s.text(880,573,'No external pull-up or\nseries termination on G474.',22,color=MUTED)
    for y,ref,net in [(665,'R1','USB_CC1'),(775,'R2','USB_CC2')]:
        s.line([(480,y),(790,y)])
        s.net(535,y,net)
        s.resistor(790,y)
        s.text(765,y+25,f'{ref}  5.1 kΩ, 1%',22)
        s.line([(890,y),(1035,y)])
        s.gnd(1035,y)
    s.line([(480,865),(565,865)]); s.gnd(565,865)
    s.line([(480,930),(550,930)])
    s.line([(544,924),(556,936)]); s.line([(544,936),(556,924)])
    s.text(580,907,'Not connected',22,color=MUTED)
    s.line([(480,980),(780,980)]); s.gnd(780,980)
    s.text(850,958,'Shell → PCB ground near connector*',22,color=MUTED)

    s.text(1250,195,'U1  STM32G4',29,True)
    s.text(1250,237,'Pin names, NOT package pad numbers',21,color=MUTED)
    s.box(1250,380,480,425)
    s.text(1275,445,'PA12 / USB_DP',25,True)
    s.text(1275,525,'PA11 / USB_DM',25,True)
    s.text(1275,615,'Application: USB CDC commands\nBootloader: USB DFU firmware\nClock: valid 48 MHz USB source',23)
    s.text(1275,737,'Other MCU circuitry omitted.',22,color=MUTED)
    s.line([(1490,315),(1490,380)],POWER)
    s.text(1225,283,'3V3 → VDDUSB (if separate)',23,True,POWER)
    s.line([(1490,335),(1170,335)],POWER); s.dot(1490,335)
    s.cap(1170,335); s.gnd(1170,413)
    s.text(1030,283,'C1 100 nF',22)

    s.text(90,1050,'CONNECTOR RULES',25,True)
    s.text(90,1100,'Join the two D+ contacts at the receptacle.\nJoin the two D− contacts at the receptacle.\nKeep CC1 and CC2 separate: one resistor each.\nAll repeated VBUS/GND contacts are connected.\nSame net label anywhere = same electrical net.',23)
    s.text(90,1310,'*Direct shell grounding is a starting choice;\nreview enclosure/chassis and EMC requirements.',21,color=MUTED)

    s.text(1100,1050,'U2  TPD4E05U06DQAR',27,True)
    s.box(1100,1100,630,280)
    for y,name,pin in [(1145,'USB_DP','1  D1+'),(1200,'USB_DM','2  D1−'),(1255,'USB_CC1','4  D2+'),(1310,'USB_CC2','5  D2−')]:
        s.line([(920,y),(1100,y)])
        s.net(920,y,name)
        s.text(1125,y-20,pin,23,True)
    s.text(1340,1125,'Four shunt clamps to GND.\nSignal wires do NOT pass\nthrough separate input/output\npins inside this IC.',22)
    s.text(1340,1280,'Pins 3, 8 → GND\nPins 6, 7, 9, 10 → NC here',22)
    s.line([(1520,1380),(1520,1390)]); s.gnd(1520,1390)
    s.text(1100,1440,'Place U2 beside J1; use short ground returns.',20,color=MUTED)
    s.save('01_usb_connections')


def support():
    s = Sheet(1650, 'Boot, debug and power connections',
              'Use SWD for first bring-up and recovery. USB firmware update depends on the exact MCU ROM and boot settings.', '2 / 2')
    s.text(80,195,'BOOT / RESET',28,True)
    s.text(80,250,'3V3',24,True,POWER)
    s.line([(140,285),(235,285)],POWER); s.switch(235,285)
    s.line([(335,285),(745,285)]); s.net(570,285,'BOOT0 / PB8*')
    s.text(235,224,'SW1  BOOT',23,True)
    s.dot(440,285); s.line([(440,285),(440,350)])
    s.resistor(440,350,True); s.gnd(440,450)
    s.text(490,373,'R3\n10 kΩ',23)
    s.text(80,390,'*Verify BOOT0 pin and\noption bytes for your G4.',23,color=MUTED)
    s.text(80,550,'3V3',24,True,POWER)
    s.line([(140,587),(235,587)],POWER); s.resistor(235,587)
    s.text(230,531,'R4  10 kΩ',23)
    s.line([(335,587),(770,587)]); s.net(667,587,'NRST')
    s.dot(440,587); s.line([(440,587),(440,655)]); s.cap(440,655); s.gnd(440,733)
    s.text(485,685,'C2  100 nF',22)
    s.dot(670,587); s.line([(670,587),(670,655)]); s.switch(670,655,True); s.gnd(670,755)
    s.text(685,670,'SW2\nRESET',22,True)
    s.text(80,835,'DFU: hold BOOT, pulse RESET, release BOOT.\nNormal boot: release BOOT and pulse RESET.\nRequires correct boot option bytes; keep SWD accessible.',23)

    s.text(925,195,'J2  STDC14 DEBUG HEADER',28,True)
    s.text(925,238,'FTSH-107-01-L-DV-K • STLINK-V3MINIE cable',23,color=MUTED)
    s.box(925,285,800,535)
    rows=[('3','3V3','Target voltage reference (not power input)'),('4','PA13','SWDIO'),('6','PA14','SWCLK'),('8','PB3','SWO (optional)'),('12','NRST','Reset / connect-under-reset'),('5, 7, 11','GND','Ground and ground-detect'),('1, 2, 9','NC','Reserved; leave disconnected'),('10, 13, 14','NC','Unused JTAG/UART in this drawing')]
    s.text(950,310,'PIN',21,True);s.text(1140,310,'MCU / NET',21,True);s.text(1320,310,'FUNCTION',21,True)
    for i,(pin,net,desc) in enumerate(rows):
        y=365+i*52
        s.text(950,y,pin,22,True);s.text(1140,y,net,22,True);s.text(1320,y,desc,18)
    s.text(925,842,'SWD can upload and debug firmware without USB.\nPower the target from its power circuit, not VTREF.\nCheck header orientation against the connector drawing.',23)

    s.line([(70,982),(1730,982)],'#CEDAE3',2)
    s.text(80,1020,'POWER: CONDITIONAL ARCHITECTURE — NOT A COMPLETE REGULATOR SCHEMATIC',26,True)
    s.text(80,1070,'Only if using a protected, rechargeable 1-cell Li-ion/LiPo battery (4.2 V charge). Other batteries require a different circuit.',23,color=MUTED)
    s.text(80,1140,'USB_VBUS\n5 V from J1',23,True,POWER)
    s.arrow(235,1180,320)
    s.box(320,1125,300,115)
    s.text(345,1144,'Input protection +\ninrush/current control',24,True)
    s.arrow(620,1180,710)
    s.box(710,1125,390,115)
    s.text(735,1144,'BQ24074  IN → OUT\nCharger + power path',25,True)
    s.arrow(1100,1180,1195)
    s.box(1195,1125,325,115)
    s.text(1220,1144,'TPS63031\n3.3 V buck-boost',25,True)
    s.arrow(1520,1180,1615)
    s.text(1625,1140,'3V3\nlogic',24,True,POWER)
    s.line([(900,1240),(900,1285)],POWER)
    s.box(710,1285,390,85,fill='#FFF4E9')
    s.text(735,1305,'BAT ↔ protected 1S battery',23,True)
    s.text(80,1285,'USB budget is shared by the running board\nand battery charging. No assumption of 3 A!\nUse 100 mA default / USB current policy.\nPower-good or safe VBUS sensing → GPIO.',22)
    s.text(1195,1285,'If battery is not 1S rechargeable:\ndo not use this charger circuit.\nUse a suitable source selector\nand regulated 3V3 supply.',22)
    s.text(80,1430,'Power sheet still needs: protection selection, current settings, suspend control, capacitors, inductor, thermal design and sensing.',22,color=MUTED)
    s.text(80,1475,'Prevent battery backfeed into USB. Keep deployment/pyrotechnic power physically inhibited during USB programming.',23,True,POWER)
    s.text(80,1525,'All board grounds share the intended return network. Never connect USB 5 V directly to MCU supply pins.',22)
    s.save('02_boot_debug_power')


if __name__ == '__main__':
    usb()
    support()
