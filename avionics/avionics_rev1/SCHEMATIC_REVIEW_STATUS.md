# Schematic review status — 24 September 2026

Applied changes cover approved passive specifications and telemetry corrections. Original TODO blocks, wires and flag types are preserved. All resistor/capacitor instances have voltage, tolerance, MPN and DigiKey fields. Existing visible rating fields remain visible; generic descriptions are hidden.

Telemetry: Molex 2111400100 is AE3, an off-board accessory connected to the radio module's U.FL. U12 pad 9 remains unconnected. MAX-M10S remains selected with possible tracking gaps above its 4 g airborne profile documented. The 10,000 ft radio range is an installation test requirement.

Local footprint corrections: SAW filter outer-pad positions, GPS antenna copper/paste artwork and feed-pad dimensions, and Wio solder-paste openings. MAX-M10S, SAW filter and Wio STEP files are assigned in the required project model folder. The GPS patch uses a clearly identified approximate datasheet-envelope VRML, not manufacturer CAD. PCB layout and fabrication output have not been updated.

## Missing BOM information

- J1 and J2: exact battery connector part numbers remain unresolved.
- L1: exact 10 µH inductor part number remains unresolved.
- J4: USB4105-GF-A approved and assigned, with DigiKey link.
- J3: Phoenix Contact 1751303 approved but not applied.
- Four additional gate pull-downs and one AND-gate bypass were approved but remain unapplied.
- The firing circuit, its remaining footprint work and its final design review are incomplete. No firing-circuit wiring changes were made in this pass.
- The full-project XLSX BOM is deferred at the user's request. Existing BOM files are not current.

## Verification and limits

Net membership is unchanged. All original wires, junctions, flag types and TODO text were checked against the saved snapshot. Schematic pages and telemetry model alignment were visually reviewed. Existing ERC findings remain and are listed below; this is not a completed project sign-off.

- warning: Symbol 'TLV7041DBV' doesn't match copy in library 'Comparator' — Symbol U6 [TLV7041DBV]
- warning: Symbol 'TPS2121RUXR' doesn't match copy in library 'rocketry_library' — Symbol U5 [TPS2121RUXR]
- warning: Symbol 'TPS2121RUXR' doesn't match copy in library 'rocketry_library' — Symbol U13 [TPS2121RUXR]
- warning: The current configuration does not include the footprint library '' — Symbol U3 [SIS932EDN-T1-GE3]
- warning: The current configuration does not include the footprint library '' — Symbol U4 [SIS932EDN-T1-GE3]
- error: Input Power pin not driven by any Output Power pins — Symbol U1 Pin 1 [VIN, Power input, Line]
- error: Input Power pin not driven by any Output Power pins — Symbol U5 Pin 7 [IN1, Power input, Line]
- error: Input Power pin not driven by any Output Power pins — Symbol U5 Pin 2 [IN2, Power input, Line]
- error: Input Power pin not driven by any Output Power pins — Symbol U5 Pin 1 [OUT, Power input, Line]
- error: Input Power pin not driven by any Output Power pins — Symbol U13 Pin 7 [IN1, Power input, Line]
- warning: Pins of type Unspecified and Passive are connected — Symbol U1 Pin 7 [MODE_SYNC, Unspecified, Line], Symbol R1 Pin 1 [Passive, Line]
- warning: Pins of type Unspecified and Passive are connected — Symbol U1 Pin 8 [RT, Unspecified, Line], Symbol R1 Pin 2 [Passive, Line]
- warning: Pins of type Unspecified and Passive are connected — Symbol U1 Pin 4 [BOOT, Unspecified, Line], Symbol C3 Pin 1 [Passive, Line]
- warning: Pins of type Unspecified and Passive are connected — Symbol U1 Pin 3 [SW, Unspecified, Line], Symbol C3 Pin 2 [Passive, Line]
- warning: Pins of type Unspecified and Passive are connected — Symbol U1 Pin 6 [FB, Unspecified, Line], Symbol L1 Pin 2 [2, Passive, Line]
- error: Input Power pin not driven by any Output Power pins — Symbol SN74LVC08AQPWRQ1 Pin 14 [VCC, Input, Line]
- error: Input Power pin not driven by any Output Power pins — Symbol SN74LVC08AQPWRQ1 Pin 7 [GND, Input, Line]
- warning: Pins of type Unspecified and Power input are connected — Symbol U3 Pin 1 [Unspecified, Line], Symbol #PWR021 Pin 1 [Power input, Line]
- warning: Pins of type Unspecified and Power input are connected — Symbol U4 Pin 1 [Unspecified, Line], Symbol #PWR014 Pin 1 [Power input, Line]
- warning: Pins of type Unspecified and Power input are connected — Symbol U3 Pin 3 [Unspecified, Line], Symbol #PWR016 Pin 1 [Power input, Line]
- warning: Pins of type Unspecified and Power input are connected — Symbol U4 Pin 3 [Unspecified, Line], Symbol #PWR015 Pin 1 [Power input, Line]
