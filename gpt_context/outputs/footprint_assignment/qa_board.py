"""Build a disposable footprint inspection board, never the user's PCB."""
from pathlib import Path
import pcbnew as k, json
BASE=Path(__file__).resolve().parent
board=k.BOARD()
parts=json.loads((BASE/'manifest.json').read_text())['parts']
for i,p in enumerate(parts):
    f=k.FootprintLoad(str(BASE/'staged/avionics_footprints.pretty'),p['fp'])
    assert f is not None,p['fp']
    f.SetReference('/'.join(p['refs']))
    f.SetValue(p['mpn'])
    f.SetPosition(k.VECTOR2I(k.FromMM(10+(i%4)*12),k.FromMM(10+(i//4)*12)))
    for m in f.Models():
        m.m_Filename=str(BASE/'staged/footprint_3D_models'/Path(m.m_Filename).name)
    board.Add(f)
    t=k.PCB_TEXT(board);t.SetText('/'.join(p['refs']));t.SetPosition(k.VECTOR2I(k.FromMM(10+(i%4)*12),k.FromMM(14+(i//4)*12)))
    t.SetLayer(k.F_SilkS);board.Add(t)
for a,b in [((5,5),(52,5)),((52,5),(52,29)),((52,29),(5,29)),((5,29),(5,5))]:
    s=k.PCB_SHAPE();s.SetShape(k.SHAPE_T_SEGMENT);s.SetLayer(k.Edge_Cuts)
    s.SetStart(k.VECTOR2I(k.FromMM(a[0]),k.FromMM(a[1])));s.SetEnd(k.VECTOR2I(k.FromMM(b[0]),k.FromMM(b[1])));s.SetWidth(k.FromMM(.05));board.Add(s)
k.SaveBoard(str(BASE/'inspection.kicad_pcb'),board)
print('Inspection board generated; user PCB not touched.')
