# Logic power mux: USB default, MCU-selectable main battery

Revised 2026-09-18. **Prototype connection guide, not a fabrication release or flight-qualified design.** This revision removes the external USB comparator and the 4.4 V rejection requirement. It selects power for the existing buck; it does not implement that buck, the USB-C front end, battery charging or pyro firing stages.

## Files and revision changes

- `logic_power_single_sheet.png` / `.svg`: current single-sheet schematic.
- `draw_logic_schematic.py`: Python/Pillow renderer and arithmetic tests.
- `connections.json`: complete U4 and shared U3 pin maps; not an EDA/SPICE netlist.
- `calculated_values.json`: divider/control margins and source-selection cases.

Run `python draw_logic_schematic.py`. It imports drawing primitives from `../pyro_power/draw_pyro_schematic.py` without running that script's main routine or changing the pyro outputs. Keep the sibling folders together.

Changes from the previous logic-power revision:

| Ref / connection | Previous | Current |
|---|---|---|
| U5 | USB comparator TLV3011BIDCKR | Removed |
| C13 | Comparator bypass | Removed; reference number left unused |
| R18 | 25.5 kΩ, 0.1% | **15 kΩ, 1%**, USB priority divider upper leg |
| R19 | 10 kΩ, 0.1% | **10 kΩ, 1%**, USB priority divider lower leg |
| R20 | 22 kΩ USB blocking bias | **100 kΩ**, CP2-to-GND default pull-down |
| R21 | 22 kΩ USB blocking bias | **1 kΩ**, MCU_SELECT_MAIN-to-CP2 series resistor |
| U4 OV1 | Comparator/bias midpoint | **GND** |
| U4 CP2 | GND | **LOGIC_CP2**, driven by GPIO through R21 |

R22–R25 and C9–C12/C14 are unchanged. U3's three-channel allocation is unchanged. The new circuit removes one IC and one capacitor, needs no new FET/Zener, and uses one additional MCU GPIO. The old resistor reference numbers are reused with different roles; **do not update an existing PCB from values alone—check the new connections.** Only generated documentation/schematics are updated, not the user's KiCad files.

## Power architecture and defaults

USB_VBUS → U4 IN1; MAIN_BAT → U4 IN2; U4 OUT → LOGIC_RAW → existing LMR604063SBRAKRQ1 buck → 3V3.

Assumptions: fixed 5 V USB, **no higher-voltage USB-PD**, USB_VBUS at most 5.5 V; correctly polarized main 1–4S battery, at most 16.8 V; common ground. USB input protection and current permission remain front-end requirements. The dedicated pyro battery does not power this mux. No USB/LOGIC_RAW connection is made to the pyro mux output or ARMED_SUPPLY.

U4 remains **TPS2121RUXR**. PR1 is biased from USB before the MCU boots. R20 pulls CP2 down during GPIO high impedance. Both OV1 and OV2 are grounded: neither source has an external disqualification circuit.

| Sources after settling | MCU_SELECT_MAIN low / Hi-Z / reset | MCU_SELECT_MAIN high |
|---|---|---|
| USB and main both TPS-valid | USB | Main |
| USB only TPS-valid | USB | USB: main is unavailable |
| Main only TPS-valid | Main | Main |
| Neither TPS-valid | Hi-Z | Hi-Z |

Normal USB is 5 V; the divider is checked for priority throughout the TPS recommended 2.8–5.5 V USB-input range. The table is steady state, not a zero-delay startup guarantee. **High means “prefer main,” not “disable USB.”** This fallback is intentional: requesting main while it is missing does not deliberately disconnect a usable USB source.

With CP2 low and PR1 above the internal reference, IN1 has priority. With CP2 high above PR1, IN2 has priority. If only one input is internally valid, the TPS uses it regardless of preference. [TPS2121 datasheet, Table 9-3 and §9.5](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=18)

## What removing the comparator means

The comparator was needed for the **previous 4.4 V hardware rejection requirement**, not basic power multiplexing. That requirement is now deliberately removed. The mux still has its built-in undervoltage lockout: nominal 2.65 V rising / 2.55 V falling, with the datasheet's specified spread. Its recommended input range starts at 2.8 V. Below that recommended range, PR1 priority and UVLO can change at different thresholds; do not assign an exact new USB cutoff to the divider. [TPS2121 electrical characteristics, §§7.3–7.5](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=7)

A weak USB supply can remain selected even when it cannot sustain 3.3 V at the load. Consequently, the result may be failure to boot, brownout, or a reset/restart loop—not necessarily a clean power-off. A reset returns the GPIO to the USB-default state, so firmware cannot guarantee escape from a weak-USB reset loop. This is an accepted simplification, not a fault-tolerant weak-source detector. MCU brownout/reset settings and independent default-off pyro inhibits remain important.

## R18/R19: USB priority without firmware

R18 = **15 kΩ, 1%**, USB_VBUS to USB_PRIORITY. R19 = **10 kΩ, 1%**, USB_PRIORITY to GND. USB_PRIORITY connects to U4 PR1, not to the MCU:

\[
V_{PR1}=V_{USB}\frac{R19}{R18+R19}=0.4V_{USB}.
\]

Thus PR1 is 2.0 V at nominal 5 V USB, 2.2 V at 5.5 V USB, and 1.12 V at 2.8 V. The divider intentionally makes PR1 lower than a 3.3 V GPIO high while retaining USB default priority. Wiring PR1 straight to 5 V would prevent a 3.3 V CP2 command from exceeding it.

Including independent 1% resistor corners and ±0.1 µA pin leakage, the script checks:

\[
V_{PR1,min}(2.8\text{ V})\approx1.1060\text{ V}>1.10\text{ V},
\qquad V_{PR1,max}(5.5\text{ V})\approx2.2271\text{ V}.
\]

The low-input margin is small and applies to the stated resistor/leakage assumptions; nominal 5 V USB has much more margin. Use appropriate resistor temperature coefficients if extending the corner analysis. The control thresholds/leakage are from the TPS electrical table. [TPS2121 §7.5](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=8)

## R20/R21 and the MCU control

R20 = **100 kΩ, 1%**, LOGIC_CP2 to GND. This is the hardware default: an unpowered or high-impedance MCU leaves CP2 low, allowing automatic USB priority. The TPS leakage contribution alone is at most approximately 10.1 mV across the worst-case pull-down; include MCU GPIO leakage in the final pin-specific check.

R21 = **1 kΩ, 1%**, MCU_SELECT_MAIN to LOGIC_CP2. This modest series resistor limits transient pin current and isolates the GPIO slightly from pin capacitance; it is not a level shifter, reverse-current isolator or gate driver. R20 is on the **TPS side** of R21.

\[
V_{CP2,H}\approx V_{GPIO,H}\frac{100k}{100k+1k},
\qquad V_{CP2,H}(3.3\text{ V})\approx3.2673\text{ V}.
\]

Steady GPIO high current is approximately 3.3/101k = 32.7 µA. For a deliberately conservative **required GPIO high of at least 2.4 V**, 1% resistor corners and TPS leakage give CP2 ≥ approximately 2.376 V. That is more than 0.148 V above the worst PR1 value at 5.5 V USB, exceeding the TPS's 40 mV maximum comparison-offset figure. The renderer checks this inequality. Select an MCU pad/output configuration that meets this VOH requirement with the regulated supply; this is not a guarantee through brownout. [TPS2121 comparison offset, §7.5](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=8)

Firmware sequence:

1. Leave the selected GPIO high impedance at reset, with no internal pull-up or conflicting boot/alternate function. R20 establishes USB priority.
2. Preload the GPIO output latch low before changing it to push-pull output, avoiding an unintended main-selection glitch.
3. To prefer main, verify ADC_MAIN against the configured pack and adequate buck headroom, then drive MCU_SELECT_MAIN high. Read LOGIC_ST after settling to confirm which source actually won.
4. Drive low to return to USB-default behavior. Firmware can also choose main based on ADC_USB while the MCU is still operating, but cannot guarantee recovery after its own power collapses.

This GPIO is **separate from MCU_MAIN_ALLOW on the pyro sheet**. One selects the logic source; the other permits main power to the pyro mux. Neither is an arming command. The MCU GPIO pad is not assigned in this guide.

## Voltage monitoring: reuse U3

The main-battery divider R15/R16 and filter C7 remain on the pyro sheet; do not duplicate them. R24 = **49.9 kΩ**, USB_VBUS to USB_DIV; R25 = **10 kΩ**, USB_DIV to GND; both 0.1%. C14 = **10 nF** to GND:

\[
V_{ADC,USB}=V_{USB}/5.99,\qquad
V_{USB}=\frac{ADC_{code}}{4095}V_{ADCref}\times5.99.
\]

USB at 5 V gives 0.83472 V at the ADC; 5.5 V gives 0.91820 V nominal, at most approximately 0.91973 V from divider tolerance alone. Thévenin resistance is 8.33 kΩ, giving an 83.3 µs RC time constant. Allow ordinary settling and choose a suitable ADC acquisition time; reference, ADC and switch errors still apply.

One existing **TMUX1511RSVR U3** serves all three measurements:

| Measurement | U3 source pin → drain pin | Enable |
|---|---|---|
| OUT_DIV → ADC_TPS_OUT | 2 S1 → 3 D1 | 1 SEL1 = SENSE_EN |
| MAIN_DIV → ADC_MAIN | 5 S2 → 6 D2 | 4 SEL2 = SENSE_EN |
| USB_DIV → ADC_USB | 10 S3 → 9 D3 | 11 SEL3 = SENSE_EN |

Reuse C8 = 100 nF and R17 = 100 kΩ. U3 pin 16 = 3V3, pin 8 = GND; pins 13/14/15 grounded; pins 7/12 unconnected. Do not populate a second U3. All three ADC pad assignments remain an integration task. U3 powered-off protection is retained; enable sensing only with valid MCU analog power/reference, and validate intermediate brownout behavior. [TMUX1511 datasheet](https://www.ti.com/lit/ds/symlink/tmux1511.pdf)

## Remaining support parts and limits

R22 = **80.6 kΩ, 1%** from ILIM to GND retains a nominal raw-rail current limit:

\[
I_{LIM,nom}\approx65.2/80.6^{0.861}=1.489\text{ A}.
\]

This is not an exact cap, a 600 mA output regulator or USB current authorization. R23 = **10 kΩ, 1%** pulls LOGIC_ST to 3V3. ST low means main selected; high means USB **or neither valid**, not power-good. [TPS2121 current-limit and status specifications](https://www.ti.com/lit/ds/symlink/tps2121.pdf)

| Capacitor | Value/rating | Role |
|---|---|---|
| C9 | 1 µF, X7R, ≥10 V | USB-side bypass |
| C10 | 10 µF, X7R, ≥35 V | Main-input bypass |
| C11 | 10 µF, X7R, ≥35 V | Raw mux-output bypass, plus the buck's own network |
| C12 | 100 nF, ≥10 V | TPS settling/soft-start control |
| C14 | 10 nF, ≥10 V, C0G preferred | USB ADC filter |

These remain starting values; include bias/tolerance and total USB attach capacitance/inrush. Reset-free transitions are not established. Default operation has CP2 low, whereas main-override operation has CP2 high; do not assume the advertised fast-mode timing applies to every transition. Test USB insertion/removal and GPIO-controlled source changes at maximum load, including switching to a lower-voltage 1S pack.

The 600 mA limit at 3.3 V already includes the user's margin. At an illustrative 85% buck efficiency, 1.98 W output requires approximately 466 mA from 5 V or 529 mA from 4.4 V before other overhead. The latter is just a power-budget example, **not a retained cutoff**. USB enumeration, suspend, Type-C current advertisement, input protection and inrush requirements still apply; two 5.1 kΩ CC resistors alone do not authorize arbitrary current. [USB Type-C source/sink current requirements](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/USB-Type_2D00_C-Spec-R2.4-_2D00_-October-2024.pdf)

The existing **LMR604063SBRAKRQ1** B-UVLO variant has rising UVLO up to 3.7 V. Selecting a 3.5 V 1S pack therefore does not guarantee cold startup, nor full-load 3.3 V regulation after mux losses. This is unchanged by removing U5. [Buck datasheet, ordering options and §6.5](https://www.ti.com/lit/ds/symlink/lmr60406-q1.pdf)

Remove any parallel USB-to-logic power path that would bypass this mux. The older USB tutorial's BQ24074/TPS63031 conditional architecture is not part of this circuit. No charging is provided.

## U4 complete pin map

| TPS2121RUXR pin | Connection |
|---|---|
| 1 OUT, 8 OUT | LOGIC_RAW; join both pins; feed existing buck VIN |
| 2 IN2 | MAIN_BAT |
| 3 CP2 | LOGIC_CP2; R20 to GND, R21 to MCU_SELECT_MAIN |
| 4 OV2 | GND |
| 5 OV1 | GND |
| 6 PR1 | USB_PRIORITY; R18/R19 midpoint |
| 7 IN1 | USB_VBUS |
| 9 ST | LOGIC_ST; R23 to 3V3 and MCU GPIO |
| 10 ILIM | R22 to GND |
| 11 SS | C12 to GND |
| 12 GND | GND |

## Incremental BOM

| Ref | Quantity | Part/value | Purpose |
|---|---:|---|---|
| U4 | 1 | [TPS2121RUXR, DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/TPS2121RUXR/9859001) | Same mux as pyro side |
| U3 | 0 new | Existing TMUX1511RSVR | Shared ADC isolation |
| R18 | 1 | 15 kΩ, 1% | USB priority upper leg |
| R19, R23 | 2 | 10 kΩ, 1% | Priority lower leg / ST pull-up |
| R20 | 1 | 100 kΩ, 1% | Default-low CP2 |
| R21 | 1 | 1 kΩ, 1% | GPIO series resistor |
| R22 | 1 | 80.6 kΩ, 1% | Raw-rail current limit |
| R24 | 1 | 49.9 kΩ, 0.1% | USB ADC upper leg |
| R25 | 1 | 10 kΩ, 0.1% | USB ADC lower leg |
| C9–C12, C14 | 5 | Values above | Bypass / soft start / ADC filtering |

U5 and C13 are removed, not DNP options shown on the current sheet. Signal resistors may use suitable 0402/0603 packages; choose capacitors by effective capacitance. Distributor link identifies the part, not reserved stock.

## Verification

The script checks **147 nominal settled source/control combinations**, PR1/CP2 resistor/leakage margins, complete active-IC pin coverage, shared-U3 consistency, resistor-label uniqueness, SVG syntax and PNG dimensions. This is arithmetic and truth-table testing, not transistor-level simulation or startup/brownout validation. The rendered drawing is visually reviewed; no hardware, SPICE or PCB ERC/DRC pass is claimed.

Test with inert loads: USB-only and main-only boot, both-source boot, main override with each source absent, 1–4S main, weak USB, GPIO reset/Hi-Z behavior, source-change transients, USB current/inrush/backfeed and MCU brownout. Preserve independent default-off pyro arming/inhibits. Do not connect live initiators during bring-up.
