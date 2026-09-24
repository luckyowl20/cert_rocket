# Sensors sheet review

Installed on 2026-09-24. All 10 installed files were hash-verified against the reviewed staging manifest. The project was reopened in KiCad and the sensors sheet visually checked. Installed-project ERC reports 0 findings on /sensors/ and 117 findings across the other sheets (qa/installed_erc.json). Original modified files are retained in before/.

Scope: U8, U9, U10, C22-C26 and R9-R11 on sensors.kicad_sch. Original circuit placement, wires, labels and sheet boxes are retained. Only C24 changes from a nonpolarized symbol to a polarized symbol with pin 1 positive and pin 2 ground.

## Footprint comparison

| Sensor | Existing footprint | Datasheet comparison | Action |
|---|---|---|---|
| U8 LPS22DFTR | QFN_22DFTR_STM | 10 pads; 0.5 mm pitch; 2 x 2 mm HLGA body; pin 1 upper left in PCB top view. Existing pad size 0.3048 x 0.3302 mm and row offset 0.7874 mm reflect supplier maximum-dimension/mil rounding rather than exact nominal terminal dimensions (0.25 x 0.275 mm). Numbering and terminal overlap agree with the package. | Retain pad geometry, qualify library reference, attach local model. The old filename says QFN, but the device package is HLGA. |
| U9 ADXL375BCCZ-RL7 | LGA_CC-14-1_ADI | Correct 14-pad sequence, 0.8 mm pitch and 3 x 5 mm body. Existing side pads were 1.1178 x 0.4492 mm at x=+/-1.370901 mm; end pads were 0.5 x 0.813 mm at y=+/-1.718498 mm. These differ from ADI's recommended PCB pattern. | Correct to Fig. 38: side pads 1.145 x 0.55 mm at x=+/-1.0975 mm; end pads 0.55 x 1.145 mm at y=+/-2.0975 mm. Overall copper span 3.34 x 5.34 mm; 0.25 mm gaps. Preserve pin numbering. |
| U10 LSM6DSV32XTR | LGA-14L_2p5X3p0X0p86_STM | 14 pads; 0.5 mm pitch; 3 x 2.5 mm body in footprint orientation; pin 1 upper left in PCB top view. Existing 0.3048 x 0.5334 mm pads reflect supplier maximum-dimension/mil rounding versus 0.25 x 0.475 mm nominal terminals. Numbering and terminal overlap agree with the package. | Retain pad geometry, qualify library reference, attach local model. |

ST footprints are compatible package land patterns, not exact copies of nominal package terminal drawings. A package terminal drawing is not itself a complete solder stencil specification. ST references TN0018 for assembly guidance.

## Circuit and component results

- U8: supply pins 1/10 at 3.3 V; ground/reserved pins 3/8/9 grounded; one shared 100 nF bypass is allowed when VDD and VDD_IO share the supply. SPI clock/data/chip-select mapping matches the datasheet; unused interrupt marked no-connect.
- U9: supply pins 1/6 at 3.3 V, ground pins 2/4/5 grounded. Reserved pins 3 and 11 may be left open; unused interrupts and NC are marked. Corrected Datasheet property from the EP variant to the standard part.
- U10: mode 1 primary SPI wiring, grounded pins 2/3 with Qvar/analog hub disabled, auxiliary pins 10/11 left unconnected, 100 nF on each supply, ground pins 6/7 connected. Interrupt outputs are unused and marked.
- R9-R11 remain 10 kohm. Set 1% tolerance, 0.05 W rating and 25 V working voltage. Pull-up load at 3.3 V is approximately 0.33 mA and 1.1 mW. These are CS defaults; the host must actively drive CS and meet timing, particularly on the shared SPI bus.
- C22/C23/C25/C26: 100 nF, 10%, 10 V X7R; existing 0201 footprints and installed KiCad models retained.
- C24: 1 uF, 10%, 16 V tantalum, KYOCERA AVX TAJA105K016RNJ, 3216-18 A case. ADI recommends tantalum on VS, but does not establish that ceramic can never work. This revision follows the explicit recommendation rather than assuming an untested ceramic substitution. Positive pin 1 connects to 3.3 V.
- Corrected imported sensor pin electrical types in the sheet cache and the same three project-library symbols. This changes ERC interpretation, not connectivity or pin position.

## Models and boundaries

Three previously downloaded supplier STEP models are copied into footprint_3D_models and linked using ${KIPRJMOD}. No new internet 3D download was needed. C24 uses a local copy of KiCad's generic 3216-18 model. Supplier sensor models are nominal visualizations, with rounded dimensions and simplified features; use manufacturer package drawings for mechanical tolerances. 3D top views confirm orientation and seating, including pin-1 markers. The PCB itself is not updated by this schematic operation.

The complete project had pre-existing ERC problems on other sheets. See qa/before_erc.json and qa/after_erc.json. Correcting falsely driven sensor ground pins exposes a project ground-driver declaration issue; the source/return should be declared appropriately during the power-sheet review rather than adding a fictitious sensor power output. Cross-sheet SPI warnings also remain because the radio symbol uses unspecified pin types. This is not a full-project ERC sign-off or a hardware noise/assembly qualification.

## Sources

- [LPS22DF DS13316 Rev 3](https://www.st.com/resource/en/datasheet/lps22df.pdf), pins p.3, application p.19, package Fig.25 p.44.
- [LSM6DSV32X DS13511 Rev 2](https://www.st.com/resource/en/datasheet/lsm6dsv32x.pdf), pins pp.9-11, mode 1 p.47, package Fig.33 p.175.
- [ADXL375 Rev B](https://www.analog.com/media/en/technical-documentation/data-sheets/ADXL375.pdf), pins p.6, decoupling p.26, PCB pattern Fig.38 p.31 and package Fig.40 p.32. The manufacturer figures were also visually inspected in an [archived Rev 0 copy](https://www.alldatasheet.com/html-pdf/528262/AD/ADXL375/924/31/ADXL375.html); their dimensions agree with the Rev B source.
- [KYOCERA AVX TAJ datasheet](https://datasheets.kyocera-avx.com/TAJ.pdf), A-case dimensions and part code.
- [C24 DigiKey listing](https://www.digikey.com/en/products/detail/kyocera-avx/TAJA105K016RNJ/563757). No parts purchased.
