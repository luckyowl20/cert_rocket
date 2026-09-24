# STM32G4 USB-C connection guide

These Python-generated drawings explain the connections; they are not an electrically checked KiCad design or a fabrication release. No KiCad project files were found in the supplied workspace. The exact STM32G4 ordering code, package, existing power circuitry, battery chemistry and operating current remain unconfirmed.

## Drawings

- [USB-C connector and MCU](01_usb_connections.png) — pin connections and four-channel ESD protection.
- [Boot, debug and power](02_boot_debug_power.png) — BOOT/RESET wiring, STDC14 pin mapping and a conditional power architecture.
- Matching `.svg` files provide scalable drawings. `draw_usb_schematic.py` generates both formats with Python and Pillow; Arial font paths currently assume Windows.

Net labels of the same name are electrically connected. Resistors are rectangles; crossing wires connect only where a junction dot is shown. The USB-C symbol groups duplicate physical connector contacts that must be joined on the PCB.

## Reference schematic found

[ST MB1428 / B-G474E-DPOW1 schematic](https://www.st.com/resource/en/schematic_pack/mb1428-g474re-b01_schematic.pdf): printed sheet 3 is MCU signals (PDF page 3), sheet 4 is MCU power (PDF page 4), and sheet 5 is USB Type-C/PD (PDF page 5). This is a genuine STM32G474 USB-C reference, but it implements a more complex PD/power-conversion system. Do not copy its entire power or CC circuit for a simple fixed-5-V USB peripheral. These drawings are an original simplified synthesis, not a reproduction of ST's sheet.

## Important electrical details

1. A passive 5-V sink needs separate 5.1-kΩ pull-downs on CC1 and CC2. Do not join CC1 and CC2. Do not assume these resistors alone authorize a 1.5-A or 3-A load; that requires detecting the source advertisement and applying the applicable USB current rules. No PD controller is required for the basic 5-V arrangement shown.
2. The [STM32G474 datasheet, USB electrical characteristics](https://www.st.com/resource/en/datasheet/stm32g474re.pdf) says its USB output matching impedance and D+ pull-up are internal. Thus no additional 22-Ω series resistors are shown. Verify this for the exact selected G4. Optional zero-ohm tuning footprints can be reserved, but do not automatically populate 22 Ω.
3. [TPD4E05U06 datasheet, pin table](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf): pins 1/2/4/5 connect to the four signal nets; pins 3 and 8 connect to ground. Pins 6/7/9/10 have no internal signal path and are left unconnected in this drawing. This is shunt protection, not a series IC. It does not provide USB VBUS power protection or sustained short-to-VBUS protection for CC.
4. The MCU supply must follow the exact package datasheet: connect all required VDD/VSS/VDDA/VSSA/reference pins and decouple them. C1 is only the illustrated USB-supply bypass, not the entire MCU decoupling network. If USB supply is internally shared with another supply pin, implement that package's arrangement instead of inventing a VDDUSB pin.
5. Implement USB CDC or another device class for runtime commands. USB DFU is a separate boot mode. Check [ST AN2606](https://www.st.com/resource/en/application_note/an2606-stm32microcontroller-system-memory-boot-mode-stmicroelectronics.pdf) for exact part, ROM revision, USB support and boot option bytes. BOOT0 hardware may be ignored with the wrong option-byte settings. Keep SWD available for initial programming and recovery; it is generally all that is needed instead of full JTAG.
6. The STDC14 mapping follows [STLINK-V3MINIE UM2910, connector table](https://www.st.com/resource/en/user_manual/um2910-stlinkv3minie-debuggerprogrammer-tiny-probe-for-stm32-microcontrollers-stmicroelectronics.pdf). The table shows electrical pin numbers, not physical viewing orientation. Pin 3 senses target voltage; it is not the board's power source. Pins 13/14 are optional UART and are not used here.
7. Run D+/D− together over a continuous ground plane, with a nominal 90-Ω differential target and short, balanced routing. Join duplicated connector contacts close to the receptacle. Place ESD protection beside the port and avoid long branch stubs. Confirm the GCT land pattern, board-edge position and shell mounting pads against its drawing.

## Conditional power block

The BQ24074 + TPS63031 chain applies only to a protected 1-cell 4.2-V-charge Li-ion/LiPo battery. It is not suitable for an arbitrary flight battery, a 2S pack, LiFePO4 or a primary cell. USB can power the logic through a correctly designed power path; it does not automatically power every high-current load.

For a full power schematic, start with the manufacturers' applications:

- [BQ24074 datasheet and typical application](https://www.ti.com/lit/ds/symlink/bq24074.pdf): input/battery/output capacitors, TS temperature monitoring, input limit, charge current, enable and thermal pad connections.
- [TPS63031 datasheet and typical application](https://www.ti.com/lit/ds/symlink/tps63031.pdf): inductor, capacitors, feedback, enable and layout.

Both BQ24074 EN pins need an appropriate control strategy: EN2/EN1 = 00 selects USB 100-mA mode, 01 selects USB 500-mA mode, 10 selects resistor-programmed current, and 11 suspends the input. Hard-wiring EN2 low prevents selecting input suspend through these pins. Startup and ROM DFU must have a sufficient power budget without relying on application firmware to raise the limit. Include a valid USB-presence signal for battery-powered operation; do not connect 5-V VBUS directly to an unverified MCU GPIO. Power-good may be useful with correct open-drain pull-up and semantics.

The power diagram intentionally omits component values and a specific input protector until source/load limits are known. It is not a complete charger/regulator circuit. Prevent reverse current into USB and keep any deployment/pyrotechnic supply physically inhibited during bench programming.

## Parts shown or named

Distributor links below identify candidate parts, not a stock/price commitment. Quantities cover the drawn USB/boot/debug circuits only, not the unfinished power stage. The exact MCU is deliberately not selected.

| Reference | Qty | Candidate part / value | Distributor |
|---|---:|---|---|
| J1 | 1 | GCT USB4105-GF-A, USB-C USB2 receptacle | [DigiKey](https://www.digikey.com/en/products/detail/gct/USB4105-GF-A/11198441) |
| U2 | 1 | TI TPD4E05U06DQAR, four-channel ESD array | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/TPD4E05U06DQAR/3996774) |
| R1, R2 | 2 | Yageo RC0402FR-075K1L, 5.1 kΩ 1% | [DigiKey](https://www.digikey.com/en/products/detail/yageo/RC0402FR-075K1L/726624) |
| R3, R4 | 2 | Yageo RC0402FR-0710KL, 10 kΩ 1% | [DigiKey](https://www.digikey.com/en/products/detail/yageo/RC0402FR-0710KL/729470) |
| C1, C2 | 2 | KEMET C0402C104K4RACTU, 100 nF | [DigiKey](https://www.digikey.com/en/products/detail/kemet/C0402C104K4RACTU/789653) |
| SW1, SW2 | 2 | C&K PTS815SJK250SMTR LFS, normally-open momentary switch | [DigiKey](https://www.digikey.com/en/products/detail/c-k/PTS815SJK250SMTR-LFS/9947849) |
| J2 | 1 | Samtec FTSH-107-01-L-DV-K, 2×7 1.27-mm header | [DigiKey](https://www.digikey.com/en/products/detail/samtec-inc/FTSH-107-01-L-DV-K/6678186) |
| Programming tool | 1 external | STLINK-V3MINIE | [DigiKey](https://www.digikey.com/en/products/detail/stmicroelectronics/STLINK-V3MINIE/16284301) |
| Optional power block | 1 | TI BQ24074RGTR charger/power-path IC | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/BQ24074RGTR/2047269) |
| Optional power block | 1 | TI TPS63031DSKR 3.3-V buck-boost IC | [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/TPS63031DSKR/2048021) |

Board validation still needs ERC, package-pad verification, layout review, current/inrush/backfeed checks, USB enumeration and DFU tests, battery/USB transition tests, and confirmation that programming cannot enable deployment outputs.
