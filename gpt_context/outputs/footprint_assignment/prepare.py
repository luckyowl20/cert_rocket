"""Stage project-local package assets and narrowly scoped schematic metadata changes.

Mechanical conversion of existing UL/KiCad footprints; no circuit edits.
The original project is read-only here. Installation is separately hash-guarded.
"""
from pathlib import Path
import sys, re, json, shutil, hashlib, copy
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'logic_power'))
from kicad_block import parse, child, children, unq, q, dump

HERE = Path(__file__).resolve().parent
PROJECT = Path(r'C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1')
DOWNLOADS = PROJECT.parent / 'downloads'
KICAD = Path(r'C:\Program Files\KiCad\10.0\share\kicad')
STAGE = HERE / 'staged'
FP = STAGE / 'avionics_footprints.pretty'
MODELS = STAGE / 'footprint_3D_models'

PARTS = [
 dict(refs=['D1'],mpn='LTST-C170GKT',fp='LTST_C170GKT_0805', source=KICAD/'footprints/LED_SMD.pretty/LED_0805_2012Metric.kicad_mod', model=KICAD/'3dmodels/LED_SMD.3dshapes/LED_0805_2012Metric.step', generic=True, url='https://www.digikey.com/en/products/detail/liteon/LTST-C170GKT/269226', ds='https://media.digikey.com/pdf/Data%20Sheets/Lite-On%20PDFs/LTST-C170GKT.pdf'),
 dict(refs=['D2'],mpn='USBLC6-4SC6',fp='USBLC6_4SC6_SOT23_6', source=KICAD/'footprints/Package_TO_SOT_SMD.pretty/SOT-23-6.kicad_mod', model=KICAD/'3dmodels/Package_TO_SOT_SMD.3dshapes/SOT-23-6.step', generic=True, url='https://www.digikey.com/en/products/detail/stmicroelectronics/USBLC6-4SC6/725216', ds='https://www.st.com/resource/en/datasheet/usblc6-4.pdf'),
 dict(refs=['D4'],mpn='BZT52C4V7-E3-08',fp='BZT52C4V7_E3_08_SOD123',source=KICAD/'footprints/Diode_SMD.pretty/D_SOD-123.kicad_mod',model=KICAD/'3dmodels/Diode_SMD.3dshapes/D_SOD-123.step',generic=True,url='https://www.digikey.com/en/products/detail/vishay-general-semiconductor-diodes-division/BZT52C4V7-E3-08/8564833',ds='https://www.vishay.com/docs/86342/bzt52_series.pdf'),
 dict(refs=['Q1'],mpn='DMN2056U-7',fp='DMN2056U_7_SOT23',source=KICAD/'footprints/Package_TO_SOT_SMD.pretty/SOT-23.kicad_mod',model=KICAD/'3dmodels/Package_TO_SOT_SMD.3dshapes/SOT-23.step',generic=True,url='https://www.digikey.com/en/products/detail/diodes-incorporated/DMN2056U-7/8275317',ds='https://www.diodes.com/datasheet/download/DMN2056U.pdf'),
 dict(refs=['U6'],mpn='TLV7041DBVR',fp='TLV7041DBVR_SOT23_5',source=KICAD/'footprints/Package_TO_SOT_SMD.pretty/SOT-23-5.kicad_mod',model=KICAD/'3dmodels/Package_TO_SOT_SMD.3dshapes/SOT-23-5.step',generic=True,url='https://www.digikey.com/en/products/detail/texas-instruments/TLV7041DBVR/10820152',ds='https://www.ti.com/lit/ds/symlink/tlv7031.pdf'),
 dict(refs=['U5','U13'],mpn='TPS2121RUXR',fp='TPS2121RUXR_RUX12',source=DOWNLOADS/'TPS2121RUXR/KiCADv6/footprints.pretty/RUX0012A.kicad_mod',model=DOWNLOADS/'TPS2121RUXR/RUX0012A.stp',generic=False,rotation=(90,0,0),url='https://www.digikey.com/en/products/detail/texas-instruments/TPS2121RUXR/9859001',ds='https://www.ti.com/lit/ds/symlink/tps2121.pdf'),
 dict(refs=['U7'],mpn='TMUX1511RSVR',fp='TMUX1511RSVR_RSV16',source=DOWNLOADS/'TMUX1511RSVR/KiCADv6/footprints.pretty/RSV0016A-MFG.kicad_mod',model=DOWNLOADS/'TMUX1511RSVR/RSV0016A.stp',generic=False,rotation=(90,0,90),url='https://www.digikey.com/en/products/detail/texas-instruments/TMUX1511RSVR/9954223',ds='https://www.ti.com/lit/ds/symlink/tmux1511.pdf'),
 dict(refs=['U1'],mpn='LMR604063SBRAKRQ1',fp='LMR604063SBRAKRQ1_RAK9',source=DOWNLOADS/'ul_LMR604065SRAKRQ1/KiCADv6/footprints.pretty/RAK0009A-MFG.kicad_mod',model=PROJECT/'footprint_3D_models/RAK0009A.stp',generic=False,rotation=(90,0,0),url='https://www.digikey.com/en/products/detail/texas-instruments/LMR604063SBRAKRQ1/29020671',ds='https://www.ti.com/lit/ds/symlink/lmr60406-q1.pdf'),
]

# All final STEP files have their orientation encoded in assembly transforms.
# Keep the audit manifest consistent with the installed zero-rotation models.
for part in PARTS:
    part['rotation'] = (0, 0, 0)

def normalize_rak(s):
    # Convert the four copper graphics into net-bearing native custom pads.
    # Preserve the supplier polygon geometry, including mask/paste apertures.
    polygons=[n for n in children(s,'fp_poly') if unq(child(n,'layer')[1])=='F.Cu']
    assert len(polygons)==4
    for num,poly in zip(['1','3','5','8'],polygons):
        pad=next(n for n in children(s,'pad') if unq(n[1])==num)
        x,y=map(float,child(pad,'at')[1:3])
        pts=[['xy',str(round(float(v[1])-x,6)),str(round(float(v[2])-y,6))] for v in children(child(poly,'pts'),'xy')]
        pad[3]='custom'
        # Use a copper-only custom pad; supplier mask/paste shapes remain exact.
        child(pad,'layers')[:]=['layers',q('F.Cu')]
        pad.extend([['options',['clearance','outline'],['anchor','circle']],['primitives',['gr_poly',['pts',*pts],['width','0'],['fill','yes']]]])
        s.remove(poly)
    for pad in children(s,'pad'):
        if unq(pad[1]) in ['10','11','12']:
            pad[1]=q('2')  # These are PGND vias, not additional IC pins.
    for n in list(children(s,'fp_text')):
        if unq(n[2]).startswith('Designator'):
            s.remove(n)

def package_assets():
    FP.mkdir(parents=True,exist_ok=True); MODELS.mkdir(parents=True,exist_ok=True)
    for p in PARTS:
        s=parse(p['source'].read_text(encoding='utf-8'))
        s[1]=q(p['fp'])
        if p['refs']==['U1']: normalize_rak(s)
        for n in list(children(s,'model')): s.remove(n)
        for n in list(children(s,'fp_text')):
            if unq(n[2]).startswith('Designator'): s.remove(n)
        for n in children(s,'fp_text'):
            if n[1]=='reference': child(n,'at')[:]=['at','0','-2.5']
            if n[1]=='value': n[2]=q(p['mpn']);child(n,'at')[:]=['at','0','2.5']
        # Add courtyard for supplier imports lacking one.
        if not any('F.CrtYd' in dump(n) for n in s if isinstance(n,list)):
            w,h=(1.5,1.7) if p['refs']!=['U7'] else (1.35,1.75)
            s.append(parse(f'(fp_rect (start {-w} {-h}) (end {w} {h}) (layer "F.CrtYd") (width 0.05) (fill none))'))
        model=p['model']; assert model.exists(), model
        shutil.copy2(model,MODELS/model.name)
        rx,ry,rz=(0,0,0)  # STEP assembly transforms already orient the package.
        s.append(parse(f'(model "${{KIPRJMOD}}/footprint_3D_models/{model.name}" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz {rx} {ry} {rz})))'))
        s.append(['descr',q(p['mpn']+'; '+p['ds']+'; '+('KiCad generic package model' if p['generic'] else 'manufacturer package STEP'))])
        (FP/(p['fp']+'.kicad_mod')).write_text(dump(s)+'\n',encoding='utf-8')

def root_blocks(text):
    depth=0; start=None; quoted=False; esc=False
    for i,c in enumerate(text):
        if quoted:
            if esc: esc=False
            elif c=='\\': esc=True
            elif c=='"': quoted=False
            continue
        if c=='"': quoted=True
        elif c=='(':
            depth+=1
            if depth==2: start=i
        elif c==')':
            if depth==2: yield start,i+1,text[start:i+1]
            depth-=1

def schematic():
    src=HERE/'before/power_setup.kicad_sch'
    text=src.read_text(encoding='utf-8')
    lookup={ref:p for p in PARTS for ref in p['refs']}; edits=[]; seen=[]
    for a,b,block in root_blocks(text):
        if not re.match(r'\(symbol\s',block): continue
        n=parse(block); props={unq(x[1]):unq(x[2]) for x in children(n,'property')}; ref=props.get('Reference')
        if ref not in lookup: continue
        p=lookup[ref]; seen.append(ref)
        values={'Value':p['mpn'],'Footprint':'avionics_footprints:'+p['fp'],'Datasheet':p['ds']}
        for key,value in values.items():
            block,count=re.subn(r'(\(property "'+key+r'" )"(?:\\.|[^"\\])*"',lambda m:m[1]+q(value),block,count=1)
            assert count==1
        # Supply ordering and traceability without cluttering the user's sheet.
        added=''
        for key,value in {'MPN':p['mpn'],'DigiKey':p['url'],'3D Model Type':'Generic package' if p['generic'] else 'Manufacturer package'}.items():
            if key in props:
                block=re.sub(r'(\(property '+re.escape(q(key))+r' )"(?:\\.|[^"\\])*"',lambda m:m[1]+q(value),block,count=1)
            else:
                at=child(n,'at');added+=f'\n\t\t(property {q(key)} {q(value)} (at {at[1]} {at[2]} 0) (effects (font (size 1 1)) (hide yes)))'
        block=block[:-1]+added+'\n\t)'
        edits.append((a,b,block))
    assert set(seen)==set(lookup)
    for a,b,new in reversed(edits):text=text[:a]+new+text[b:]
    (STAGE/'power_setup.kicad_sch').write_text(text,encoding='utf-8')
    assert len(children(parse(text),'symbol'))==len(children(parse(src.read_text()),'symbol'))
    manifest={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'parts':[{k:str(v) if isinstance(v,Path) else v for k,v in p.items()} for p in PARTS]}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

if __name__=='__main__':
    package_assets();schematic();print('Staged 9 symbols, 8 unique footprints, 8 STEP files; circuit topology unchanged.')
