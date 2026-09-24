"""Check actual KiCad-exported nets, not just drawing coordinates."""
import json
import sys
from pathlib import Path
from kicad_block import parse, child, children, unq, HERE

netfile = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'logic_mux_block.net'
doc = parse(netfile.read_text(encoding='utf-8'))
nets = {}
for net in children(child(doc, 'nets'), 'net'):
    name = unq(child(net, 'name')[1])
    nets[name] = {(unq(child(n, 'ref')[1]), unq(child(n, 'pin')[1])) for n in children(net, 'node')}
roles = json.loads((HERE / 'kicad_block_refs.json').read_text())
u = roles['logic_mux']
def node(role, pin): return (roles[role], str(pin))
expected = {
    'VIN_USB': {(u,'7'), node('USB_input',1),node('USB_priority_upper',1),node('USB_adc_upper',1)},
    'VIN_MAIN_BATT': {(u,'2'),node('main_input',1)},
    'VIN_LOGIC': {(u,'1'),(u,'8'),node('mux_output',1)},
    'GND': {(u,'4'),(u,'5'),(u,'12'), *[node(r,2) for r in ['USB_priority_lower','USB_input','main_input','mux_output','current_limit','soft_start','override_pulldown','USB_adc_lower','USB_adc_filter','sense_enable_pulldown','TMUX_bypass']]},
    '+3.3V': {node('status_pullup',1),node('TMUX_bypass',1)},
    'LOGIC_PMUX_ST': {(u,'9'),node('status_pullup',2)},
    'MCU_SELECT_MAIN': {node('override_series',2)},
    'USB_POWER_SENS': {node('USB_adc_upper',2),node('USB_adc_lower',1),node('USB_adc_filter',1)},
    'SENSE_EN': {node('sense_enable_pulldown',1)},
}
for name, nodes in expected.items():
    assert nodes <= nets.get(name,set()), (name, nodes - nets.get(name,set()))
for nodes in [
    {(u,'6'),node('USB_priority_upper',2),node('USB_priority_lower',1)},
    {(u,'3'),node('override_series',1),node('override_pulldown',1)},
    {(u,'10'),node('current_limit',1)},
    {(u,'11'),node('soft_start',1)},
]:
    assert any(nodes == actual for actual in nets.values()), nodes
assert len({name for name,nodes in nets.items() if (u,'7') in nodes}) == 1
for pin, name in [('7','VIN_USB'),('2','VIN_MAIN_BATT'),('1','VIN_LOGIC'),('8','VIN_LOGIC')]:
    assert [n for n, pins in nets.items() if (u,pin) in pins] == [name]
assert len({frozenset(nets[n]) for n in ['VIN_USB','VIN_MAIN_BATT','VIN_LOGIC','GND','+3.3V']}) == 5
if len(sys.argv)>2 and sys.argv[2]=='--integrated':
    extra={
        'VIN_USB': {('J4','A4')},
        'VIN_MAIN_BATT': {('J1','2'),('R30','1'),('U5','2')},
        'VIN_LOGIC': {('U1','1')},
        '+3.3V': {('U7','16')},
        'GND': {('U7','8'),('U7','13'),('U7','14'),('U7','15')},
        'PYRO_POWER_SENS': {('U7','2')},
        'MAIN_BAT_SENS': {('U7','5')},
        'USB_POWER_SENS': {('U7','10')},
        'ADC_TPS_OUT': {('U7','3')},
        'ADC_MAIN': {('U7','6')},
        'ADC_USB': {('U7','9')},
        'SENSE_EN': {('U7','1'),('U7','4'),('U7','11')},
    }
    for name,nodes in extra.items():
        assert nodes <= nets.get(name,set()), (name,nodes-nets.get(name,set()))
print(f'PASS: {len(expected)+4} logic-mux groups, exact internal nets, and distinct power rails checked in {netfile.name}')
if len(sys.argv)>2 and sys.argv[2]=='--integrated':
    print(f'PASS: {len(extra)} integration groups checked, including U7 and J1')
