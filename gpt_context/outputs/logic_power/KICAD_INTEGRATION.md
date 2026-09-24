# KiCad integration — 2026-09-23

The generated contents were imported **flat** into the existing `power_setup` sheet using KiCad 10.0.3. No hierarchical sheet was added. Generated source schematics and verification reports remain in this `gpt_context/outputs/logic_power` directory. KiCad itself created normal project backup ZIPs/autosave data in the project directory.

U5 was already `TPS2121RUXR`; its value field is now visible. It remains the pyro mux. The new logic mux is **U13, TPS2121RUXR**. The standalone explanatory drawing uses different reference numbers; use this mapping for the actual KiCad sheet:

| KiCad reference | Value / function |
|---|---|
| U13 | TPS2121RUXR logic mux |
| R36 / R37 | 15 kΩ / 10 kΩ USB-to-PR1 divider |
| R38 | 10 kΩ ST pull-up to 3.3 V |
| R39 | 80.6 kΩ ILIM resistor |
| R40 / R41 | 1 kΩ GPIO series / 100 kΩ CP2 pull-down |
| R42 / R43 | 49.9 kΩ / 10 kΩ, 0.1%, USB ADC divider |
| R44 | 100 kΩ SENSE_EN pull-down |
| C31 | 1 µF / 10 V USB input bypass |
| C32 / C33 | 10 µF / 35 V main input / mux output bypass |
| C34 | 100 nF soft start |
| C35 | 10 nF USB ADC filter |
| C36 | 100 nF existing U7 supply bypass; place at U7 on PCB |

U13 IN1 uses `VIN_USB`; IN2 uses `VIN_MAIN_BATT`; joined OUT pins feed `VIN_LOGIC` and existing buck U1. Low/Hi-Z `MCU_SELECT_MAIN` prefers USB; high prefers main, subject to TPS source-validity/fallback behavior. There is no external 4.4 V USB qualification comparator. This is fixed 5 V USB, not higher-voltage PD.

Existing U7 TMUX1511 receives `PYRO_POWER_SENS`, `MAIN_BAT_SENS`, and `USB_POWER_SENS` on S1–S3. Outputs are `ADC_TPS_OUT`, `ADC_MAIN`, and `ADC_USB`. SEL1–SEL3 use `SENSE_EN`; unused S4/D4/SEL4 are grounded. NC pins 7/12 are marked no-connect. U7's 3.3 V supply and ground are connected.

The main connector J1 label was changed from `VIN_BATT` to `VIN_MAIN_BATT` to join the existing battery rail. A comparison with the Git baseline found no removed original top-level schematic objects and no changed original wire or junction geometry; this connector-label rename was the only original net-label change.

## Verification and remaining work

- `power_setup_verified.net`: exported from the saved, complete project using KiCad.
- `verify_kicad_logic.py ... --integrated`: passes the intended connection groups, exact internal mux nets, separated supply nets, and J1/U7 integration checks.
- `power_setup_erc.json`: full-project ERC report. **Not ERC-clean:** 147 reported violations, 14 on `power_setup`. These include undriven power-input declarations, existing custom-symbol electrical pin types, and pyro-side issues. These were not suppressed or broadly redesigned in this task.
- MCU GPIO/ADC pin assignments are not completed by global labels alone. Connect and check `MCU_SELECT_MAIN`, `LOGIC_PMUX_ST`, `SENSE_EN`, and the ADC signals on the MCU sheet before layout/firmware integration.
- Existing custom footprints and symbol pin types still need project-wide review. U13 uses `Package_DFN_QFN:Texas_VQFN-HR-12_2x2.5mm_P0.5mm`.
- This is schematic connectivity verification, not hardware qualification. Verify USB current allowance/inrush, effective capacitor values, source switching, startup, reset and brownout on inert loads before flight use.
