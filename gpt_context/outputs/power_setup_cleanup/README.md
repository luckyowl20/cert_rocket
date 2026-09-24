# Power-sheet cleanup — 2026-09-23

Scope: existing `power_setup` only. The user's section boxes, net names and circuitry were retained except for the requested USB protection replacement. The USB box was widened slightly to accommodate the array. No project sheet was added. `before/` is a recoverable snapshot; `after/` holds the staged project used for checks.

## USB protection

**D2 = STMicroelectronics USBLC6-4SC6**, one SOT-23-6 device replacing the old D2 and D3 through-hole placeholders. D3 is no longer a separate component.

- [DigiKey product, USBLC6-4SC6](https://www.digikey.com/en/products/detail/stmicroelectronics/USBLC6-4SC6/725216)
- [ST product](https://www.st.com/en/protections-and-emi-filters/usblc6-4.html)
- [ST datasheet](https://www.st.com/resource/en/datasheet/usblc6-4.pdf), Figure 1, Table 2, and §2.3.

The device provides four low-capacitance I/O protection channels (3 pF typical) plus a VBUS clamp. The spare I/O channels protect CC1 and CC2; their independent 5.1 kΩ sink resistors are unchanged. C37 is a 100 nF, 10 V local VBUS bypass following ST's layout guidance. Place D2 and C37 next to J4 with very short connections to the ground plane. This is an ESD network for fixed 5 V USB, **not a sustained-overvoltage disconnect or higher-voltage USB-PD solution**. Device-level ESD ratings do not guarantee board-level immunity; test the completed layout.

| D2 pin | Net |
|---|---|
| 1, I/O1 | USB_D+ |
| 2 | GND |
| 3, I/O2 | USB_D- |
| 4, I/O3 | USB_CC1 / J4 A5 |
| 5 | VIN_USB |
| 6, I/O4 | USB_CC2 / J4 B5 |

D2 has manufacturer, MPN, datasheet URL, product URL and footprint fields. Its manufacturer product link is also visible on the sheet.

## Capacitor voltage ratings

Each capacitor has a **visible Voltage field** and an X7R dielectric field; capacitance values remain separate for the BOM. These are minimum selection requirements, not a claim that a specific purchasable capacitor has been qualified.

| References | Rating | Reason |
|---|---|---|
| C1, C2 | 50 V | Buck input bypass, following TI's input-capacitor recommendation |
| C18 | 50 V | Raw switched pyro rail, potentially supplied by a 4S pack |
| C16, C17, C32, C33 | 35 V | Battery/raw rails, designed here for up to 16.8 V normal operation |
| C4, C5 | 16 V | Buck output; TI's typical capacitor table assumes 16 V X7R parts |
| C3 | 10 V | BOOT-to-SW differential, not BOOT-to-ground voltage |
| C12, C19, C31, C34, C35, C36, C37 | 10 V | 3.3 V/5 V, sense, timing or bypass nodes |

[TI LMR60406-Q1 datasheet](https://www.ti.com/lit/ds/symlink/lmr60406-q1.pdf), §§8.2.2.3–8.2.2.5: output-capacitor derating, input-capacitor voltage recommendations and minimum 10 V bootstrap capacitor. TI explicitly warns that ceramic capacitance falls with DC bias and temperature.

The impossible/unsuitable blanket 0201 assignments were corrected: C1 → 0805, C2 → 0402, C4 → 0603, C5 → 0805. Missing capacitor footprints were filled consistently; the other existing feasible sizes were retained. **Before ordering, select actual capacitor MPNs and check effective capacitance at bias, temperature and tolerance.** A voltage label alone does not establish adequate ripple/transient performance. Rated capacitors also do not protect the TPS inputs from battery hot-plug overshoot.

## Resistor tolerances

All **31 resistors** on the sheet have a Tolerance field and a visible tolerance next to their value:

- **0.1%:** R3, R4, R19, R22, R23, R24, R30, R31, R32, R33, R42, R43 — sensing and threshold divider ratios.
- **1%:** all other resistors on this page, including CC terminations, pull-ups, gate/control resistors and ILIM resistors.

As explicitly approved, **R1 was corrected from 15.2 Ω to 15.2 kΩ, 1%**. TI specifies 15.2 kΩ for nominal 2 MHz operation in the [LMR60406-Q1 electrical characteristics](https://www.ti.com/lit/ds/symlink/lmr60406-q1.pdf), §6.5. Other nominal resistance values were retained. Tolerance is not a substitute for checking resistor power, working voltage, temperature coefficient or comparator/reference error budgets.

The R3/R4 annotation was corrected: this divider measures `VIN_LOGIC`, not the raw main battery; its ratio is 47/(220+47) = 0.1760 and gives 2.957 V at 16.8 V input.

## Verification and remaining issues

`verify_cleanup.py` checks all 17 capacitor ratings, all 31 resistor tolerances, the six D2 pins, C37 and complete before/after net partitions. Excluding the intentionally replaced D2/D3 and added C37, **all pre-existing electrical connectivity is unchanged**. ERC comparison shows no new findings. Both staged before/after full projects report 160 findings (14 on `power_setup`); this is not an ERC-clean or flight-qualified design.

Outstanding items identified, not silently changed:

1. **D4 remains `BZT52Bxx`**, a generic Zener-family placeholder, not an orderable clamp voltage. Select and verify its low-current clamp behavior before fabrication.
2. USB_D+/USB_D−, the ADC outputs and several control/status nets still have no MCU-pin connection in the exported full-project netlist. Complete those assignments separately.
3. Some existing non-capacitor footprints are blank or unqualified custom names. This task does not constitute full BOM/PCB signoff.
4. R2 is still labelled with an old “check PG resistor” note. U1 PG is open drain, so it needs a pull-up; verify whether an internal MCU pull-up is intended before removing R2.
5. J4's shield is still intentionally marked no-connect in the original schematic. Review the connector shield/chassis/ground strategy during PCB layout and ESD testing.

The pre-edit sheet can be recovered from `before/power_setup.kicad_sch`. Do not overwrite future user edits with this snapshot or regenerate blindly.
