# TPS2121 source selection and voltage monitoring

Engineering prototype / connection guide, 2026-09-17. **Not a flight-qualified schematic or a complete deployment controller.** This covers battery selection and measurement, not the channel firing stages, their hardware inhibit, or the buck/USB power path.

Integration update, 2026-09-18: [the logic-power companion](../logic_power/README.md) adds a second TPS2121 before the existing buck and reuses **channel 3 of this same U3** for USB voltage sensing. U3 pins 9/10/11 are no longer grounded; the current renderer, pin map and manifest reflect this. The pyro source-selection circuitry and R1–R17/C1–C8 values are unchanged. Older legacy images may retain the unused-channel grounding and must not be used for integration.

## Files and running the renderer

- `draw_pyro_schematic.py`: self-contained Python/Pillow renderer and arithmetic checks.
- **`pyro_power_single_sheet.png` / `.svg`: current single-sheet schematic**, including TPS2121, comparator, main-input permission, ADC sensing and physical arm disconnect.
- `connections.json`: generated pin-by-pin connection manifest, not an EDA/SPICE netlist.
- `calculated_values.json`: generated calculation results.

Run from this directory with Python and Pillow installed:

```powershell
python draw_pyro_schematic.py
```

The script writes one PNG and one SVG beside itself, regardless of the working directory. It follows the drawing style of `../usb_c/draw_usb_schematic.py` without modifying or importing that file. Pin numbers refer to the exact package named, not symbol position. Repeated net names mean the same electrical connection. Dots indicate junctions; jumpovers indicate unconnected crossings.

The TPS symbol arrangement follows the supplied datasheet screenshot: IN1, PR1, OV1, IN2 and OV2 on the left; OUT, CP2, ST, SS and ILIM on the right; GND below. **Only the symbol arrangement is adopted**, not the screenshot's manual-CP2-control circuit or example resistor values. This revision changes presentation, not the electrical design. Every resistor R1-R17 appears once with its value; the calculations below use those same reference numbers. In particular, R1/R2 feed PR1 and U2 IN−, R3/R4 feed U2 IN+, and U2's output connects directly to OV1 and the R5/R6 bias midpoint.

The earlier `01_power_mux`, `02_comparator_threshold` and `03_monitor_and_inhibit` images are retained as legacy files; the renderer no longer regenerates them. Use the single-sheet files above as the current drawing.

## What this circuit implements

Assumptions: dedicated `PYRO_BAT` is **1S only, 0-4.2 V**; `MAIN_BAT` is a configured 1-4S pack, up to 16.8 V; both have correct polarity and share ground. `3V3` comes from the existing MCU regulator, independently of TPS_OUT and the arm switch. USB never connects to the TPS power inputs or output.

1. A healthy dedicated battery is selected automatically, without MCU commands, **once the 3.3 V rail is regulated**.
2. Below the comparator threshold, IN1 is made unavailable through OV1, not merely deprioritized.
3. IN2 is unavailable until `MCU_MAIN_ALLOW` is driven high. This implements the request to let firmware decide what happens after IN1 becomes unavailable.
4. Neither source available means TPS_OUT is high impedance; the bleed resistor discharges its capacitance.
5. Selecting a source does not arm or fire anything. SW1 is a physical power disconnect; the downstream channel drivers still need independent default-off hardware and firmware inhibits.

The selection basis is TI's TPS2121 Table 9-3: OV-invalid inputs are excluded; with CP2 low and PR1 high, valid IN1 has priority. Both invalid gives Hi-Z. ST high is ambiguous between IN1 and Hi-Z. [TPS family datasheet, §9.5, p.18](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=18)

| Dedicated battery state | Main present and internally valid | MCU_MAIN_ALLOW | TPS_OUT source |
|---|---|---|---|
| Qualified by comparator | Either | Either | IN1 |
| Disqualified or absent | Yes | High | IN2 |
| Disqualified or absent | Yes | Low or reset/Hi-Z | Neither |
| Disqualified or absent | No | Either | Neither |
| No batteries; USB only | No | Either | Neither |

Inside the comparator's hysteresis window, its previous state matters. At startup, use the rising/reconnection threshold, not the falling threshold. These are steady-state conditions, not zero-delay timing guarantees.

## 1. Comparator choice and cutoff math

Use **TLV7041DBVR**, the open-drain member of the family, rather than TLV7031. Its POR releases the output and its inputs tolerate a connected sense voltage while unpowered. That permits a battery-derived OV1 block bias. The DBV package is SOT-23-5; do not substitute an S/L suffix without checking its different pinout. [DigiKey part and datasheet link](https://www.digikey.com/en/products/detail/texas-instruments/TLV7041DBVR/10820152), [TI family datasheet, Table 4-1, §§6.4-6.4.3](https://www.ti.com/lit/ds/symlink/tlv7031.pdf#page=17)

### Battery divider: R1 = 20.0 kΩ, R2 = 10.0 kΩ, both 0.1%

R1 is from PYRO_BAT to PYRO_SENSE. R2 is from PYRO_SENSE to ground.

\[
k_P=\frac{R2}{R1+R2}=\frac{10}{20+10}=\frac13
\]

\[
V_{sense}=V_{pyro}/3
\]

Connect this node to U2 pin 4 (IN−) and U1 pin 6 (PR1). At a 3.5 V battery it is 1.16667 V; at 4.2 V it is 1.4 V. Sharing this divider saves two resistors. PR1 is above the TPS's 1.10 V maximum rising reference when the nominal battery cutoff is reached; OV1, not PR1, establishes the 3.5 V exclusion.

### Reference divider: R3 = 18.2 kΩ, R4 = 10.0 kΩ, both 0.1%

R3 is from regulated 3V3 to REF_1V170. R4 is from REF_1V170 to ground. Connect the node to U2 pin 3 (IN+).

\[
V_R=3.3\frac{10}{18.2+10}=1.1702128\text{ V}
\]

The comparator's internal hysteresis is 7 mV typical, 2-17 mV specified at 25 °C; input offset is up to ±8 mV under the stated electrical-characteristic conditions. Use its transfer-curve model, not just equality of the two divider voltages. [TI comparator datasheet, §5.7 p.8 and §6.4.2 p.18](https://www.ti.com/lit/ds/symlink/tlv7031.pdf#page=18)

With zero offset, the **nominal falling disable** and **rising reconnect** levels are:

\[
V_{fall}=\frac{V_R-H/2}{k_P}
=3(1.1702128-0.0035)=3.500138\text{ V}
\]

\[
V_{rise}=\frac{V_R+H/2}{k_P}
=3(1.1702128+0.0035)=3.521138\text{ V}
\]

Thus 18.2 kΩ / 10.0 kΩ was chosen to place the falling trip close to 3.500 V **including typical hysteresis**. Ignoring hysteresis gives a 3.51064 V equality point, which is not the same as the falling trip. The battery-level typical hysteresis is only 21 mV: this is not a guarantee against chatter when a loaded battery recovers after being disconnected.

### Accuracy and reference limitations

**This is a nominal 3.5 V design, not a guaranteed rule that IN1 can never be used below exactly 3.500 V.** A divider cannot eliminate buck tolerance, comparator offset or hysteresis variation.

For illustration, the script sweeps a 3.24-3.35 V reference rail, four independent 0.1% resistors, ±8 mV offset, 2-17 mV hysteresis and ±0.1 µA PR1 leakage. Its falling-trip sensitivity envelope is approximately **3.386-3.596 V**. This is not a guaranteed full-temperature limit: the hysteresis specification has different test conditions, and dynamic noise, resistor drift and comparator bias uncertainty are not bounded by this sweep. PR1 loading alone contributes about ±2 mV referred to the battery:

\[
\Delta V_{pyro}=\frac{I_{PR1}(20k\parallel10k)}{1/3}
=\pm2\text{ mV}
\]

The 3.24-3.35 V values come from the fixed-3.3-V buck specification under its stated operating conditions. Your 3.3 V orderable option is **LMR604063SBRAKRQ1**, whereas the previously typed LMR604065SRAKRQ1 is a 5 V option. Check the actual BOM. A buck cannot maintain 3.3 V indefinitely from a declining 1S pack; startup UVLO and dropout require separate verification. [LMR60406-Q1 datasheet, Table 4-2 and §6.5](https://www.ti.com/lit/ds/symlink/lmr60406-q1.pdf)

If 3.500 V is a hard safety minimum across temperature and power sequencing, this requested buck-referenced circuit is insufficient as-is. Use an independent precision supervisor/reference with a complete tolerance budget and a guarded trip level. While 3V3 ramps or droops but U2 is above its own POR level, the comparison threshold follows 3V3 downward. **POR behavior alone does not qualify the 3.3 V reference.** The system hardware inhibit must remain asserted through startup, brownout and reset; that circuit is outside these sheets.

## 2. OV1 bias, PR1 and CP2

R5 = R6 = 47 kΩ, 1%, form a second divider from PYRO_BAT to ground. Its midpoint is OV1_BLOCK, connected to U2's open-drain output and U1 OV1.

- Healthy battery: U2 sinks the midpoint toward ground, permitting IN1.
- Low battery or U2 POR: U2 releases it; `OV1 ≈ Vpyro/2`, blocking IN1.

At 3.5 V, released OV1 is 1.75 V; at 4.2 V it is 2.1 V. Even at 2.4 V it is about 1.2 V, leaving overlap with the TPS's own low-voltage lockout. The healthy-state sink current is at most approximately 4.2/47k = 89 µA. Check VOL and leakage over the intended temperature range during prototype validation.

CP2 is **grounded**. There is no CP2 divider tied to the main battery and no comparison between the numerical battery voltages. PR1 reuses PYRO_SENSE to establish IN1 preference; OV1 supplies the exclusion function. With CP2 grounded, do not assume the advertised fast-comparison switchover mode. [TPS datasheet, §7.5 and Table 9-3](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=18)

## 3. Main input permission, including reset

### Q1: a control-node pull-down, not a firing driver

Q1 is a small N-channel MOSFET used as an **inverting, open-drain-style interface** between the MCU GPIO and the TPS2121 OV2 input. It does not carry the pyro load current, drive a channel MOSFET gate, or switch MAIN_BAT directly. It only sinks the small current supplied through R7.

The TPS interprets a high OV2 voltage as an invalid main input. This circuit deliberately uses that overvoltage input as a permission/inhibit input: Q1 off means main input blocked; Q1 on pulls OV2 low and removes that block. The TPS's other input-validity conditions still apply. This does **not** measure whether the main battery exceeds the configured 3.5/7.0/10.5/14.0 V threshold; firmware makes that decision from ADC_MAIN. [TPS2121 datasheet, OV2 pin description and selection truth table](https://www.ti.com/lit/ds/symlink/tps2121.pdf)

Q1 also separates the battery-derived OV2 node from the GPIO. A direct GPIO connection would expose the MCU to that node when the MCU is unpowered and would lose the intended default-block behavior if its bias depended only on 3V3. Q1's gate is driven by the MCU; its drain can remain biased independently. This is level interfacing, **not galvanic isolation**, and it does not replace a physical arming disconnect.

### R7, R8 and R9: three different jobs

| Part | Connection | Purpose |
|---|---|---|
| R7, 10 kΩ | MAIN_BAT to OV2_BLOCK / Q1 drain | Battery-powered pull-up that establishes the default **blocked** state. Also limits current into D1 when clamping and through Q1 when it pulls the node low. |
| R8, 100 kΩ | Q1 gate to source/GND, after R9 | Gate pull-down that keeps Q1 off when the GPIO is high impedance during reset or loss of MCU power. Discharges stored gate charge instead of leaving the gate floating. |
| R9, 1 kΩ | MCU_MAIN_ALLOW to Q1 gate | Series gate resistor that limits brief gate charging/discharging current and damps switching edges/ringing. It does not establish the default state and is not a battery-voltage divider resistor. |

R7 must not be replaced by a wire: with Q1 on, that would short MAIN_BAT to ground through Q1; with Q1 off, D1 would have no intentional current limiting. Its pull-up works even without MCU power because its source is MAIN_BAT, not 3V3.

R8 is needed because a MOSFET gate stores charge and a reset GPIO is not necessarily driving low. Its 100 kΩ value gives a weak but defined pull-down without heavily loading the GPIO. It is not a guarantee against every transient: gate discharge time, GPIO reset behavior and layout still require verification.

R9 and R8 produce a small DC attenuation when the GPIO is high. Ignoring gate leakage and GPIO output resistance:

\[
V_{GS}\approx3.3\frac{R8}{R8+R9}
=3.3\frac{100k}{100k+1k}=3.267\text{ V},
\quad I_{GPIO,DC}\approx\frac{3.3}{101k}=32.7\text{ µA}.
\]

The initial gate-charging current is approximately bounded by 3.3 V / 1 kΩ = 3.3 mA for an initially discharged gate, before accounting for GPIO resistance. Once charged, the gate itself draws essentially no DC current; the steady current above flows through R8. R9 is edge conditioning, not the safety element that creates the default block. Removing it would require checking GPIO drive and switching behavior; no such schematic change is made here.

### D1: a small-signal Zener clamp, not a power-rail TVS

D1 is a **4.7 V nominal Zener diode**, BZT52C4V7-7-F. It is used in reverse breakdown to clamp the low-current OV2 control node. Although a TVS also clamps voltage, this part is not being used or qualified as a high-energy battery-rail surge suppressor. It neither clamps MAIN_BAT itself nor provides battery reverse-polarity protection. Its anode goes to GND and its cathode to OV2_BLOCK; R7 limits its current. [D1 manufacturer datasheet, device description and electrical characteristics](https://www.diodes.com/datasheet/download/BZT52Cxx.pdf)

R7 = 10 kΩ pulls OV2_BLOCK toward MAIN_BAT. D1, BZT52C4V7-7-F, has **cathode at OV2_BLOCK, anode at ground**. It limits the control-pin voltage when a multi-cell pack is connected. It is a clamp, not a 3.5 V detector. A plain divider cannot both exceed 1.10 V with a low 1S pack and stay below 5.5 V with a full 4S pack with useful margin.

Q1, DMN2056U-13, connects drain to OV2_BLOCK, source to ground and gate to MCU_MAIN_ALLOW through R9 = 1 kΩ. R8 = 100 kΩ from gate to source keeps Q1 off during MCU reset. GPIO high pulls OV2 low and permits the main input. GPIO low/Hi-Z leaves it blocked. Its bias comes from MAIN_BAT, so it does not disappear when 3V3 is absent.

At 16.8 V, Q1 on gives about 1.68 mA through R7 and 28.2 mW resistor dissipation. With Q1 off and approximately 4.7 V clamp voltage, the current is about 1.21 mA and zener power about 5.7 mW. At the low end the node follows MAIN_BAT, not an assumed regulated 4.7 V. D1's 25 °C table gives 4.4-5.0 V at 5 mA and leakage at 2 V; verify the clamp and off-state blocking at temperature, low current and hot-plug transients. Q1 has characterized low-voltage gate drive. [D1 manufacturer datasheet, p.2](https://www.diodes.com/datasheet/download/BZT52Cxx.pdf), [Q1 manufacturer datasheet](https://www.diodes.com/datasheet/download/DMN2056U.pdf)

Permission is not forced selection: asserting MAIN_ALLOW does not override a healthy IN1. Pre-authorizing an acceptable main pack allows hardware fallback when IN1 is excluded; leaving MAIN_ALLOW low deliberately creates a supply gap while firmware decides. This design does not latch out a sagging IN1: it reconnects when its comparator recovers.

In short: **R7 requests blocking, D1 limits the blocking voltage, R8 makes Q1 default off, and R9 conditions the MCU's gate drive. Q1 overrides the pull-up only when the MCU actively grants main-input permission.** This default applies after the control node settles; startup and power-loss timing must still be tested.

## 4. MCU monitoring and pack-dependent thresholds

Use R13/R14 for TPS_OUT and R15/R16 for MAIN_BAT. Each pair is **49.9 kΩ top / 10.0 kΩ bottom, 0.1%**. C6/C7 = 10 nF from each divider midpoint to ground.

\[
k_A=\frac{10}{49.9+10}=0.1669449082,
\quad V_{raw}=5.99V_{ADC}
\]

At 16.8 V, the ADC node is 2.80467 V nominal, or approximately 2.8094 V at the worst 0.1% ratio. This leaves headroom below a normally operating 3.3 V ADC supply; it does not qualify the circuit for arbitrary overvoltage or brownout.

\[
R_{TH}=49.9k\parallel10k=8.33055\text{ kΩ},\quad
\tau_{ADC}=R_{TH}(10\text{ nF})=83.3\text{ µs}
\]

Allow at least 1 ms for ordinary divider settling after enabling sensing, then use an acquisition time appropriate for the exact MCU ADC. Input sampling capacitance, ADC leakage, switch leakage, offset and gain error still need inclusion. Calibrate using the actual ADC reference, not an assumed perfect 3.300 V.

| Configured main pack | Requested low-energy threshold | Divider voltage | Illustrative 12-bit code, VREF = 3.300 V |
|---|---:|---:|---:|
| 1S | 3.5 V | 0.58431 V | 725 |
| 2S | 7.0 V | 1.16861 V | 1450 |
| 3S | 10.5 V | 1.75292 V | 2175 |
| 4S | 14.0 V | 2.33723 V | 2900 |

\[
V_{main}=\frac{ADC_{code}}{4095}V_{ADCref}\,5.99,
\quad V_{low}=3.5N_{cells}
\]

These are the user's policy thresholds, **not measured minimum ignition voltages**. Set cell count explicitly and reject an absent/implausible pack. Low voltage should set a supervised low-energy fault; it must not by itself command deployment during USB testing, startup or ground handling. No firing firmware is supplied here. Do not implement a simple cutoff that removes the selected supply during an already authorized deployment operation without analyzing the consequences.

### Why include U3?

U3, **TMUX1511RSVR**, is an analog signal isolation switch between the measurement dividers and the MCU ADC inputs. It is not a regulator, voltage clamp, pyro power switch or hardware firing inhibit. Two channels serve this sheet; a third now serves the logic-power companion:

| Monitored rail | Divider and filter | U3 signal path | MCU measurement |
|---|---|---|---|
| TPS_OUT, supplied by whichever battery the TPS selects | R13/R14 and C6 | OUT_DIV → channel 1 → ADC_TPS_OUT | Selected supply voltage, before SW1 |
| MAIN_BAT, upstream of the TPS | R15/R16 and C7 | MAIN_DIV → channel 2 → ADC_MAIN | Main battery voltage, even when IN2 is not selected |
| USB_VBUS, on the logic-power companion | R24/R25 and C14 | USB_DIV → channel 3 → ADC_USB | USB port voltage; same physical U3 |

**Either monitored rail can remain energized while the MCU's 3V3 supply is absent.** For example, a healthy pyro battery can maintain TPS_OUT after the main-powered MCU supply fails. MAIN_BAT can also remain present when its buck is disabled or has stopped regulating. USB removal, startup and shutdown introduce other supply-order combinations. The divided voltage is still present on the battery side of U3 in those situations.

Without isolation, a divider can apply voltage to an ADC pin whose analog supply/reference is near zero. Depending on the pin structure and analog configuration, that violates its input limits and can cause current injection, unintended back-powering or damage. The divider limits current but does not by itself establish that injection is permitted. At 16.8 V these dividers produce approximately 2.805 V: acceptable with the intended healthy 3.3 V ADC reference, but not automatically acceptable as the MCU supply collapses.

U3's documented powered-off protection disconnects its signal paths with VDD = 0; its specified powered-off signal range includes the approximately 2.81 V worst-case divider voltage here. With U3 powered normally, SENSE_EN low opens all three used channels and high closes them. R17 = 100 kΩ defaults SENSE_EN low when the MCU GPIO is high impedance; C8 is U3's local supply bypass capacitor. Firmware should enable sensing only after the analog supply/reference is valid and disable it before a controlled shutdown. [TMUX1511 datasheet, pin functions, recommended operating conditions and powered-off protection](https://www.ti.com/lit/ds/symlink/tmux1511.pdf)

**Powered-off protection is not a blanket brownout guarantee.** A collapsing supply passes through intermediate voltages before reaching zero; check U3's behavior, enable timing, MCU reset timing and leakage throughout that transition. Firmware cannot be assumed to execute a shutdown routine during abrupt power loss. An open switch also has finite leakage and capacitance; it is not ideal or galvanic isolation.

### Can U3 be omitted with the STM32G474RET6?

The selected MCU is now **STM32G474RET6, LQFP64**; the drawing still leaves the ADC pad assignments uncommitted. PC0 (pin 8, ADC12_IN6) and PC2 (pin 10, ADC12_IN8) are FT_a candidates for a reduced-part-count interface. They differ from ordinary TT_a ADC pins and must be evaluated using their actual input structure and supply conditions. [STM32G474 datasheet, Tables 12 and 17](https://www.st.com/resource/en/datasheet/stm32g474re.pdf)

Do not treat the FT designation as unconditional protection while an analog input is active. ST specifies supply/reference-relative limits for active ADC, comparator and op-amp inputs even on FT_a pins. A nominal 2.805 V signal reaches the supply-plus-0.3 V boundary when the applicable analog supply/reference falls to about 2.505 V; correct conversion range is a separate, stricter requirement. [ST GPIO voltage guidance](https://community.st.com/t5/stm32-mcus/what-is-the-maximum-input-voltage-that-can-be-applied-to-my/ta-p/49613)

U3 is therefore **a conditional design choice, not inherently mandatory for every STM32G474 interface**. Removing it requires a demonstrated safe direct interface during normal operation, startup, reset, shutdown and abrupt brownout, including the internal analog-switch state and applicable pin limits. The MCU part number alone does not establish that. Retain U3 in this prototype until that analysis is complete; neither its removal nor a new ADC pin assignment is implemented by this documentation update.

## 5. Output bleed and invalid-supply detection

R12 = **2.2 kΩ, 1%, 0.5 W** from TPS_OUT to ground. C3 = 10 µF, X7R, 35 V. R12 is intentionally higher-power than the small signal resistors:

\[
I_{bleed}(16.8)=16.8/2200=7.64\text{ mA}
\]

\[
P_{bleed,max}=16.8^2/(2200\times0.99)=0.1296\text{ W}
\]

Select a resistor whose temperature derating still permits that dissipation; do not populate an ordinary 0402. At 3.5 V its nominal dissipation is only 5.57 mW. This consumption comes from the selected battery, not the MCU's 600 mA logic regulator budget.

Including the output measurement divider:

\[
R_E=2.2k\parallel59.9k=2.1221\text{ kΩ}
\]

For a **maximum total connected output capacitance of 22 µF**, including tolerance, downstream capacitance when SW1 is closed and other attached circuits:

\[
\tau_{max}\le1.01R_E(22\text{ µF})=47.15\text{ ms}
\]

With constant leakage into the disconnected output:

\[
V(t)=I_LR_E+[V(0)-I_LR_E]e^{-t/(R_EC)}
\]

Zero leakage alone would predict about 166 ms to fall from 16.8 V to 0.5 V. **Do not ignore leakage:** the TPS table permits up to 35 µA per input through 85 °C and 500 µA per input through 125 °C for large voltage differences; tighter figures apply within 5 V. [TPS datasheet, §7.5 leakage table, p.7](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=7)

The script conservatively uses the large-difference bound on both inputs until VOUT falls below 5 V, then the tighter IN1 bound for the dedicated 0-4.2 V pack. It also budgets **10 µA maximum additional current entering TPS_OUT from all other circuitry**. After 500 ms, from an initial 16.8 V, calculated upper estimates are approximately:

- Through 85 °C: **0.108 V**.
- Through 125 °C: **1.266 V**.

Accordingly, use two distinct diagnostic concepts:

- `VOUT < 0.5 V`: near-zero indication, expected after the wait under the stated lower-temperature/leakage assumptions.
- `VOUT < 2.0 V`: clearly unusable for this application's 3.5 V minimum, including the larger leakage estimate.

Values between 2 V and the expected selected-source voltage are **not automatically valid**. Qualify output voltage against the selected source and application requirements. A short, overload, leakage, residual charge or open source can produce overlapping readings. ST cannot resolve that ambiguity; source-status and voltage measurements are diagnostics, not proof of output impedance or available current.

The 500 ms interval is for absence/disabled-supply diagnosis, not a permitted interruption in flight or a delay before an urgent operation. It starts after both inputs are actually unavailable; the software cannot force that condition while healthy IN1 remains automatically selected. More capacitance or external backfeed requires recalculation. The monitor is before SW1, so it does not verify arm-switch closure or discharge of stored energy beyond that switch.

## 6. TPS support values and complete pin map

R10 = 22.1 kΩ, 1%, ILIM to ground. TI's equation gives:

\[
I_{LIM}\approx\frac{65.2}{[R_{ILIM}(\text{kΩ})]^{0.861}}
=\frac{65.2}{22.1^{0.861}}=4.537\text{ A}
\]

Use the electrical table's **4.0 / 4.5 / 5.0 A min/typ/max** at this nominal resistor, not the equation as an exact limit. Additional resistor tolerance applies. C4 = 100 nF on SS is a prototype starting point; newly permitted inputs can incur settling/soft-start delays. [TPS datasheet, §7.5 and §9.3.1-9.3.2](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=13)

Current limiting has finite response time. It neither limits the number of active channels nor guarantees sufficient delivered energy. Current limiting from 4S into a low-voltage load can create substantial dissipation and shutdown. Do not treat a nominal “1 A” initiator as a constant-current load. Load/thermal/fault validation remains required; this guide does not approve a firing pulse profile.

U1 is **TPS2121RUXR**, not the incomplete name TPS212RUXR. [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/TPS2121RUXR/9859001), [TI pin table, p.4](https://www.ti.com/lit/ds/symlink/tps2121.pdf#page=4)

| U1 pin | Name | Connection |
|---:|---|---|
| 1 | OUT | TPS_OUT; join pin 8 |
| 2 | IN2 | MAIN_BAT; C2 to GND |
| 3 | CP2 | GND |
| 4 | OV2 | OV2_BLOCK: R7, D1 cathode, Q1 drain |
| 5 | OV1 | OV1_BLOCK: R5/R6 midpoint, U2 output |
| 6 | PR1 | PYRO_SENSE: R1/R2 midpoint, U2 IN− |
| 7 | IN1 | PYRO_BAT; C1 to GND |
| 8 | OUT | TPS_OUT; join pin 1 |
| 9 | ST | TPS_ST; R11 10 kΩ to 3V3; MCU GPIO |
| 10 | ILIM | R10 22.1 kΩ to GND |
| 11 | SS | C4 100 nF to GND |
| 12 | GND | GND |

| U2 pin, TLV7041DBVR | Connection |
|---|---|
| 1 OUT | OV1_BLOCK |
| 2 VEE | GND |
| 3 IN+ | REF_1V170 |
| 4 IN− | PYRO_SENSE |
| 5 VCC | 3V3; C5 100 nF to GND |

| U3 pins, TMUX1511RSVR only | Connection |
|---|---|
| 1 SEL1, 4 SEL2, 11 SEL3 | SENSE_EN; MCU output and R17 to GND |
| 2 S1 / 3 D1 | OUT_DIV / ADC_TPS_OUT |
| 5 S2 / 6 D2 | MAIN_DIV / ADC_MAIN |
| 7, 12 NC | Leave unconnected |
| 8 GND | GND |
| 10 S3 / 9 D3 | USB_DIV / ADC_USB; see logic-power companion; do not ground |
| 13 D4, 14 S4, 15 SEL4 | GND, unused channel |
| 16 VDD | 3V3; C8 100 nF to GND |

## Prototype BOM

Stock is not reserved; verify availability and exact footprints when ordering. Passive values are specifications, not a procurement-ready manufacturer-part-number BOM.

| Ref | Value / exact active part | Package / reason |
|---|---|---|
| U1 | [TPS2121RUXR](https://www.digikey.com/en/products/detail/texas-instruments/TPS2121RUXR/9859001) | 12-pin RUX, 2 × 2.5 mm; two-source power mux |
| U2 | [TLV7041DBVR](https://www.digikey.com/en/products/detail/texas-instruments/TLV7041DBVR/10820152) | SOT-23-5; open-drain comparator, battery-derived disable bias |
| U3 | [TMUX1511RSVR](https://www.digikey.com/en/products/detail/texas-instruments/TMUX1511RSVR/9954223) | 16-pin RSV, 2.6 × 1.8 mm; ADC isolation when unpowered |
| Q1 | [DMN2056U-13](https://www.digikey.com/en/products/detail/diodes-incorporated/DMN2056U-13/7352908) | SOT-23; 1 gate / 2 source / 3 drain; logic-level OV2 pull-down |
| D1 | [BZT52C4V7-7-F](https://www.digikey.com/en/products/detail/diodes-incorporated/BZT52C4V7-7-F/775770) | SOD-123; OV2 clamp, not power-rail surge protection |
| R1 / R2 | 20.0 kΩ / 10.0 kΩ, 0.1% | 0402/0603, low temperature coefficient; battery sense |
| R3 / R4 | 18.2 kΩ / 10.0 kΩ, 0.1% | 0402/0603, low temperature coefficient; reference sense |
| R5, R6 | 47 kΩ each, 1% | 0402/0603; OV1 bias |
| R7 | 10 kΩ, 1%, ≥0.063 W | Main-derived OV2 bias |
| R8, R17 | 100 kΩ each, 1% | Default-low controls |
| R9 | 1 kΩ, 1% | Q1 gate series resistor |
| R10 | 22.1 kΩ, 1% | TPS current-limit setting |
| R11 | 10 kΩ, 1% | ST pull-up |
| R12 | 2.2 kΩ, 1%, 0.5 W | Typically 1206 high-power; verify derating |
| R13, R15 | 49.9 kΩ each, 0.1% | ADC divider upper resistors |
| R14, R16 | 10.0 kΩ each, 0.1% | ADC divider lower resistors |
| C1 | 10 µF, X7R, ≥10 V | IN1 bypass; verify effective capacitance |
| C2, C3 | 10 µF each, X7R, ≥35 V | IN2/OUT bypass; package depends on DC-bias curves |
| C4 | 100 nF, X7R, ≥10 V | SS starting value |
| C5, C8 | 100 nF each, X7R, ≥10 V | Local IC bypass |
| C6, C7 | 10 nF each, ≥10 V | ADC filtering; C0G preferred if space permits |
| SW1 | Physical arm switch or removable link | Select for DC fault/load current and voltage; no part selected here |

Use short, wide TPS power connections, both OUT pads, local bypass capacitors and appropriate thermal copper. Keep sense grounds separate from high-current routing until the intended common return point. Connector reversal protection, battery fusing, hot-plug transients, buck input selection, complete hardware arming and exact MCU ADC protection remain system integration tasks.

## Validation performed and required next

Performed: datasheet pin/selection-table inspection, executable threshold/divider/discharge arithmetic, complete active-part pin coverage, intended truth-table checks, SVG parsing, PNG dimension checks, verification that all R1-R17 value labels appear exactly once, and visual review of the single-sheet drawing. The truth-table checks verify the declared policy only; they are not a transistor-level simulation. No SPICE, PCB ERC/DRC or hardware tests have been performed.

Before any flight use, validate with inert loads: all supply combinations and power-up/down orders; actual cutoff/reconnect including noise and sag; reset/default-off behavior; reference dropout; main permission across 1-4S; unpowered ADC injection; source-change delay; output decay with worst-case capacitance; and current-limit/thermal fault behavior. A qualified rocketry safety review is still needed. Do not connect live initiators during initial bring-up.
