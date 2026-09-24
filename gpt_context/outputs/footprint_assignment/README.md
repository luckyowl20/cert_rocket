# Power_setup footprint and model assignment

Completed for **power_setup only**. Nine symbols use eight unique project-local footprints and eight STEP files. No wiring, passive values, other schematic sheets, or project PCB were edited. The original sheet and existing footprint library snapshot are in `before/`.

## Installed parts

All footprint identifiers below use the `avionics_footprints:` library prefix. Product links are also stored in each symbol's hidden **DigiKey** field; manufacturer datasheet URLs are in **Datasheet**.

| References | Part / DigiKey link | Footprint name | STEP provenance |
|---|---|---|---|
| U1 | [LMR604063SBRAKRQ1](https://www.digikey.com/en/products/detail/texas-instruments/LMR604063SBRAKRQ1/29020671) | LMR604063SBRAKRQ1_RAK9 | Manufacturer RAK0009A.stp, supplied by user |
| U5, U13 | [TPS2121RUXR](https://www.digikey.com/en/products/detail/texas-instruments/TPS2121RUXR/9859001) | TPS2121RUXR_RUX12 | Manufacturer RUX0012A.stp |
| U7 | [TMUX1511RSVR](https://www.digikey.com/en/products/detail/texas-instruments/TMUX1511RSVR/9954223) | TMUX1511RSVR_RSV16 | Manufacturer RSV0016A.stp |
| U6 | [TLV7041DBVR](https://www.digikey.com/en/products/detail/texas-instruments/TLV7041DBVR/10820152) | TLV7041DBVR_SOT23_5 | Generic KiCad SOT-23-5.step |
| Q1 | [DMN2056U-7](https://www.digikey.com/en/products/detail/diodes-incorporated/DMN2056U-7/8275317) | DMN2056U_7_SOT23 | Generic KiCad SOT-23.step |
| D1 | [LTST-C170GKT](https://www.digikey.com/en/products/detail/liteon/LTST-C170GKT/269226) | LTST_C170GKT_0805 | Generic KiCad LED_0805_2012Metric.step |
| D2 | [USBLC6-4SC6](https://www.digikey.com/en/products/detail/stmicroelectronics/USBLC6-4SC6/725216) | USBLC6_4SC6_SOT23_6 | Generic KiCad SOT-23-6.step |
| D4 | [BZT52C4V7-E3-08](https://www.digikey.com/en/products/detail/vishay-general-semiconductor-diodes-division/BZT52C4V7-E3-08/8564833) | BZT52C4V7_E3_08_SOD123 | Generic KiCad D_SOD-123.step |

Installed directories:

- `C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1\avionics_footprints.pretty`
- `C:\Users\mdsch\Desktop\rocketry\avionics\avionics_rev1\footprint_3D_models`

Every footprint uses `${KIPRJMOD}/footprint_3D_models/<filename>` with unit scale and zero offset/rotation. The STEP assembly transforms already provide the correct orientation. No model files are missing. Five models are **generic package representations**, not exact manufacturer-body models; do not use them as guaranteed mechanical envelopes, especially LED height.

## Footprint sources and corrections

U1, U5/U13 and U7 reuse the downloaded Ultra Librarian/TI footprints. The remaining five reuse compatible standard footprints from the installed official KiCad 10 library, copied under project-local names. They were not newly downloaded as manufacturer-specific CAD. Standard footprints follow KiCad land-pattern conventions and are not claimed to reproduce every manufacturer's recommended land geometry exactly.

For the buck's supplier footprint, the three thermal vias originally numbered 10–12 were corrected to **pad 2 (PGND)**. Four L-shaped copper graphics were converted to electrically connected custom pads 1, 3, 5 and 8 while preserving supplier copper geometry and mask/paste artwork. Reference text artifacts were removed and missing courtyards added. The package is shared between voltage variants; U1 remains the **3.3 V** orderable part, not the 5 V variant named in the original download directory. See the [LMR60406-Q1 datasheet](https://www.ti.com/lit/ds/symlink/lmr60406-q1.pdf) and [RAK package drawing and land pattern](https://www.ti.com/lit/pdf/MPQF742E).

D4's placeholder was replaced by **BZT52C4V7-E3-08**, a nominal 4.7 V Zener in **SOD-123**, not SOD-123F. Pad 1 is cathode and pad 2 anode. Its specified Zener range is measured at 5 mA; the existing high-value pull-up produces less current, so the exact clamp behavior still needs bench/tolerance verification. This footprint assignment is not qualification of the protection circuit. See the [Vishay datasheet](https://www.vishay.com/docs/86342/bzt52_series.pdf).

Other package/pinout references: [TPS2121](https://www.ti.com/lit/ds/symlink/tps2121.pdf), [TMUX1511](https://www.ti.com/lit/ds/symlink/tmux1511.pdf), [TLV7041](https://www.ti.com/lit/ds/symlink/tlv7031.pdf), [DMN2056U](https://www.diodes.com/datasheet/download/DMN2056U.pdf), [USBLC6-4](https://www.st.com/resource/en/datasheet/usblc6-4.pdf), and [LTST-C170GKT](https://media.digikey.com/pdf/Data%20Sheets/Lite-On%20PDFs/LTST-C170GKT.pdf).

## Verification and limits

- KiCad 10 native footprint parser accepted all eight footprints.
- Pad-number sets were checked against the assigned symbols, including repeated pad 2 for the buck thermal vias.
- Before/after netlists have identical connectivity.
- `verify.py` confirms the installed assets match staging, all model paths resolve, assignments match the manifest, and schematic changes are limited to allowed metadata on the nine selected symbols.
- All eight models rendered on the disposable inspection board; see `inspection_top.png` and `inspection_iso.png`. This board is in the GPT context directory, not the avionics project PCB.
- U1 was inspected in KiCad's Footprint Editor. Its checker reported **0 errors and 1 warning**: an SMD footprint contains plated through-hole pads. These are intentional PGND thermal vias; the IC is correctly classified as SMD.
- This is not a complete board DRC, circuit ERC cleanup, assembly-process approval, or flight-safety qualification. Review stencil, via treatment and board clearances with the PCB layout and assembler before fabrication.

`prepare.py` stages assets; `install.ps1` is a hash-guarded one-time installer already executed. Do not rerun it over subsequent user edits. `manifest.json` records sources and ordering links. Original files remain in `before/` for recovery.
