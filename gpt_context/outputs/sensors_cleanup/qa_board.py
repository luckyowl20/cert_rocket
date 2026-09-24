from pathlib import Path
import pcbnew as k,json
B=Path(__file__).resolve().parent;K=Path('C:/Program Files/KiCad/10.0/share/kicad');board=k.BOARD()
parts=[('U8','QFN_22DFTR_STM',B/'staged/avionics_footprints.pretty'),('U9','LGA_CC-14-1_ADI',B/'staged/avionics_footprints.pretty'),('U10','LGA-14L_2p5X3p0X0p86_STM',B/'staged/avionics_footprints.pretty'),('C24','TAJA105K016RNJ_3216_18',B/'staged/avionics_footprints.pretty'),('C22/23/25/26','C_0201_0603Metric',K/'footprints/Capacitor_SMD.pretty'),('R9/10/11','R_0201_0603Metric',K/'footprints/Resistor_SMD.pretty')]
for i,(r,n,lib) in enumerate(parts):
 f=k.FootprintLoad(str(lib),n);assert f
 f.SetReference(r);f.SetPosition(k.VECTOR2I(k.FromMM(6+i%3*10),k.FromMM(7+i//3*10)))
 for m in f.Models():
  if '${KIPRJMOD}' in m.m_Filename:m.m_Filename=str(B/'staged/footprint_3D_models'/Path(m.m_Filename).name)
  elif '${KICAD10_3DMODEL_DIR}' in m.m_Filename:m.m_Filename=m.m_Filename.replace('${KICAD10_3DMODEL_DIR}',str(K/'3dmodels'))
  assert Path(m.m_Filename).exists(),m.m_Filename
 board.Add(f)
for a,b in [((1,1),(31,1)),((31,1),(31,22)),((31,22),(1,22)),((1,22),(1,1))]:
 s=k.PCB_SHAPE();s.SetShape(k.SHAPE_T_SEGMENT);s.SetLayer(k.Edge_Cuts);s.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1])));s.SetEnd(k.VECTOR2I(k.FromMM(b[0]),k.FromMM(b[1])));s.SetWidth(k.FromMM(.05));board.Add(s)
k.SaveBoard(str(B/'qa/inspection.kicad_pcb'),board)
f=B/'qa/inspection.kicad_pcb'
t=f.read_text().replace('${KIPRJMOD}/footprint_3D_models/',(B/'staged/footprint_3D_models').as_posix()+'/').replace('${KICAD10_3DMODEL_DIR}',(K/'3dmodels').as_posix())
f.write_text(t)
print('Inspection board created; all six model paths resolve.')
