# Hella Universal Turbo Actuator I — EEPROM Memory Map

128 bytes of on-chip EEPROM inside the **L9805E** (STMicroelectronics "Super Smart Power Motor Driver").
Accessed via CAN protocol on 0x3F0. Previously assumed to be a separate 93C66 chip, but
the L9805E integrates 128 bytes of EEPROM, 16K EPROM (firmware), 256 bytes RAM, CAN controller,
H-bridge motor driver, 10-bit ADC, PWM, and an ST7 8-bit MCU — all in one package.

Hella uses a custom mask-ROM version with their firmware burned into the 16K EPROM at fabrication.
Write-protection of EEPROM regions (e.g., 0x0F-0x1F) is enforced by firmware, not hardware.

### L9805E EEPROM Hardware Details (from datasheet, Section 5.9)

The EEPROM is a **flat 128-byte memory space** at MCU addresses `0x0C00h–0x0C7Fh`. There are
**no hardware sectors, no hardware write protection**. The silicon treats all 128 bytes identically.
It is organized as 32 rows × 4 bytes. Up to 4 bytes can be programmed in one cycle if they
share the same row (same upper address bits A7:A2). Programming is controlled by the EEPCR
register at `0x002Ch` with bits E2PGM (start program), E2LAT (write mode), and E2ITE (interrupt).

**The write-enable codes (0x2D, 0x8D) and the write-protection of 0x0F-0x1F are entirely
Hella firmware constructs** — the CAN protocol handler in the mask-ROM firmware checks these
unlock codes before allowing EEPROM writes. The L9805E hardware itself imposes no such restriction.

The last 4 bytes (`0x0C7C–0x0C7F`, i.e., EEPROM addresses `0x7C–0x7F`) are reserved by ST
for **temperature sensor trimming** (see Section 5.5.6 of L9805E datasheet):
- `0x7C`: T0H (temperature reference high byte)
- `0x7D`: T0L (temperature reference low byte)
- `0x7E`: VT0H (voltage-temperature coefficient high byte)
- `0x7F`: VT0L (voltage-temperature coefficient low byte)

### L9805E Key MCU Registers (from datasheet, Table 2)

| MCU Addr | Register | Description | Relevance to CAN Protocol |
|----------|----------|-------------|--------------------------|
| 0x0021h | PBCSR | Power Bridge Control Status Register | Motor EN, DIR, PWM_EN, SC, OVT flags |
| 0x0022h | DCSR | Dedicated Control Status Register | CAN transceiver control |
| 0x002Ch | EEPCR | EEPROM Control Register | E2PGM, E2LAT, E2ITE bits |
| 0x005Ah | CANISR | CAN Interrupt Status Register | CAN message handling |
| 0x005Ch | CANCSR | CAN Control/Status Register | CAN bus configuration |
| 0x005Dh | CANBRPR | CAN Baud Rate Prescaler | 500 kbit/s configuration |

**PBCSR (0x0021h) bit field:**
```
Bit 7: PIE    — Power bridge interrupt enable
Bit 6: OVT    — Overtemperature flag (read-only, clears on EN clear)
Bit 5: SC     — Short circuit flag (read-only, clears on EN clear)
Bit 4: DIR    — Motor direction (latched on PWM edge)
Bit 3: IN2    — Right half-bridge control / driving mode select
Bit 2: IN1    — Left half-bridge control / driving mode select
Bit 1: PWM_EN — PWM driving enable (0=Direct, 1=PWM mode)
Bit 0: EN     — Power bridge master enable (0=inhibit, outputs Hi-Z)
```

## Sensor IC: onsemi NCV77320

The angular position sensor is an **onsemi NCV77320** — a Contactless Inductive Position Sensor
Interface (Hella brands this as "CIPOS" technology). The NCV77320 has its **own separate EEPROM**
(64 × 16-bit words) for calibration, PWL linearization, and SENT configuration. The MCU communicates
with the NCV77320 via SPI.

**Architecture:**
```
[NCV77320 sensor IC] --SPI--> [L9805E MCU] --CAN--> [external tool]
     own EEPROM                   own EEPROM
     (64 words, SPI access)       (128 bytes, CAN access — this document)
     - 15-pt PWL linearization    - CAN IDs, min/max, mode
     - pos_shift (zero adjust)    - NCV77320 cal data (stored for SPI programming at boot)
     - coupling compensation      - motor control parameters
     - SENT config                - device identification
```

The 128 bytes documented here are the **MCU's EEPROM**, not the NCV77320's. The MCU stores
NCV77320 calibration data in its own EEPROM and programs it into the NCV77320 via SPI at power-on.

**Datasheet:** onsemi NCV77320/D (Rev. 3, March 2026), 39 pages. TSSOP-16 package.
Key NCV77320 features relevant to this EEPROM:
- `pos_shift[15:0]`: 16-bit zero angle adjustment — analogous to MCU address 0x22
- `pos_out[15:0]`: 16-bit position output (0-65535 maps to 360° electrical)
- `dcc_c12`, `dcc_c23`: Direct coupling compensation coefficients (per-unit factory cal)
- `temp[11:0]`: Die temperature sensor, formula: `temp = round(8 * (T[K] - 200) / 1)`
- 15-point PWL correction table for angle linearization (addresses 13-43 in NCV77320)
- CRC-16 checksums protecting EEPROM sectors (polynomial 0x13D65, seed 0xFFFF)

## Reference Dump (Original Backup)

```
       00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
0x00:  05 0E 55 00 AE 03 96 FF FF 7D 08 CE 0A 01 2A 0E
0x10:  00 00 04 00 04 20 00 00 04 00 00 00 04 00 04 20
0x20:  34 15 00 2D 00 08 00 CB 08 62 A0 96 06 02 1D 09
0x30:  00 2A 03 D5 00 00 20 FF 20 20 0A 54 01 8E 01 AC
0x40:  05 0E 55 00 AE 03 96 FF FF 7D 08 CE 0A 01 2A FF
0x50:  45 45 10 2E 5B 00 5E 09 BA 71 21 22 22 01 61 05
0x60:  34 15 00 2D 00 08 00 CB 08 62 A0 96 06 02 1D 09
0x70:  FF FF FF FF FF FF 20 FF 20 20 0A 54 01 8E 01 AC
```

## Two-Half Structure

The 128 bytes are split into two 64-byte halves: 0x00-0x3F and 0x40-0x7F.

### What matches between halves

| First half | Second half | Match? | Notes |
|-----------|-------------|--------|-------|
| 0x00-0x0E | 0x40-0x4E | IDENTICAL | Device config, CAN IDs, min/max position |
| 0x0F-0x1F | 0x4F-0x5F | DIFFERENT | See "Unknown Regions" below |
| 0x20-0x2F | 0x60-0x6F | IDENTICAL | User-configurable (range, mode, CAN IDs) |
| 0x30-0x35 | 0x70-0x75 | DIFFERENT | First half has data, second half is 0xFF |
| 0x36-0x3F | 0x76-0x7F | IDENTICAL | Misc config |

### Which half is "active" vs "backup"?

**Best theory (unconfirmed):** 0x00-0x3F is the **active/working** copy, 0x40-0x7F is the **factory backup**.

Evidence for this:
- `hella_prog.py` `set_min`/`set_max` write to 0x03-0x06 and 0x22 (first half only)
- `hella_prog.py` never writes to the second half (0x40-0x7F)
- 0x4F = 0xFF (factory default?) vs 0x0F = 0x0E (updated during use)
- 0x50-0x51 = 0x45, 0x45 (factory?) vs 0x10-0x11 = 0x00, 0x00 (modified)
- 0x70-0x75 = all 0xFF (factory blank?) vs 0x30-0x35 has real data

**UNKNOWN:** Does the actuator ever read from the second half? Does it use it for fallback/recovery? Can it be restored from? We don't know.

**Note on 0x3C-0x3F / 0x7C-0x7F:** These bytes always match between halves because they are the
L9805E's **hardware temperature sensor trim values** (T0H, T0L, VT0H, VT0L), factory-programmed
by ST at chip fabrication. They exist at fixed MCU addresses 0x0C7C-0x0C7F regardless of any
two-half EEPROM structure imposed by Hella's firmware. The "matching" is coincidental — both
halves happen to include the same physical bytes because the temp trim is at the end of each
64-byte half.

---

## Known Registers — First Half (Active?)

### 0x00-0x0E: Device Configuration

| Addr | Value | Description | Confidence |
|------|-------|-------------|------------|
| 0x00-0x01 | 05 0E | Per-unit device ID (16-bit). Differs between physical units: G-222 unit1=0x050E, unit2=0x0522; G-221 dl=0x07B2, hw=0x051E. Same between halves. | STRONG HYPOTHESIS |
| 0x02 | 55 | Magic number / format identifier. Always 0x55 across all known units. | CONFIRMED (constant) |
| 0x03-0x04 | 00 AE | Min position (16-bit big-endian). Written by `set_min()`. | CONFIRMED |
| 0x05-0x06 | 03 96 | Max position (16-bit big-endian). Written by `set_max()`. | CONFIRMED |
| 0x07-0x08 | FF FF | Unknown. Always 0xFF? | UNKNOWN |
| 0x09-0x0A | 7D 08 | CAN ID encoding. Decodes to: `0x7D * 8 + (0x08 >> 5)` = **0x3E8** (response ID). | CONFIRMED |
| 0x0B-0x0C | CE 0A | CAN ID encoding. Decodes to: `0xCE * 8 + (0x0A >> 5)` = **0x670**, pkt_size=0x0A. Purpose unknown — possibly position steering RX ID? | PARTIALLY CONFIRMED (decode formula confirmed, purpose UNKNOWN) |
| 0x0D-0x0E | 01 2A | Model/gearbox configuration ID. Constant per G-number variant: G-222=0x012A (298), G-221=0x0155 (341). Survives reprogramming. Identifies the hardware variant (gear ratio, travel limits). | STRONG HYPOTHESIS |

**Write-enable code:** 0x2D (confirmed working for 0x03-0x06)

### 0x0F-0x1F: Actuator-Managed Region

**WRITE-PROTECTED** from CAN. Tested all 8 write-enable codes (0x0D, 0x2D, 0x4D, 0x6D, 0x8D, 0xAD, 0xCD, 0xED) — none worked.

These bytes changed during motor control experiments (register-write motor driving). The actuator updates them internally.

| Addr | Original | After experiments | Notes |
|------|----------|-------------------|-------|
| 0x0F | 0x0E | 0x02 | Changed |
| 0x10-0x11 | 00 00 | 04 20 | Changed — same values as 0x14-0x15 original |
| 0x12-0x13 | 04 00 | 04 00 | Unchanged |
| 0x14-0x15 | 04 20 | 00 00 | Changed — values moved to 0x10-0x11 |
| 0x16-0x17 | 00 00 | 04 00 | Changed |
| 0x18-0x19 | 04 00 | 00 00 | Changed |
| 0x1A-0x1B | 00 00 | 04 00 | Changed |
| 0x1C-0x1D | 04 00 | 00 00 | Changed |
| 0x1E-0x1F | 04 20 | 04 00 | Partially changed |

**Pattern:** Values 0x04 and 0x20 appear to rotate/shift through this region. May be a circular buffer of calibration data, endpoint history, or motor run statistics.

**UNKNOWN:** Exact purpose. What triggers updates. Whether all motor movements update these or only certain operations.

### 0x20-0x2F: User-Configurable Region

| Addr | Value | Description | Confidence |
|------|-------|-------------|------------|
| 0x20-0x21 | 34 15 | Unknown. | UNKNOWN |
| 0x22 | 00 | Position zero offset. Analogous to NCV77320's `pos_shift[15:0]` register, but 8-bit. The MCU applies this offset after reading the NCV77320's 16-bit angle to align "position 0" with the physical minimum endstop. Scale: ~4 position counts per unit of 0x22. Written during calibration. | STRONG HYPOTHESIS (analogous to NCV77320 pos_shift, not independently confirmed) |
| 0x23 | 2D | Unknown. Referenced in write sequences (re-selected after 0x22 write) but never written to. | UNKNOWN |
| 0x24-0x26 | 00 08 00 | Unknown. | UNKNOWN |
| 0x27-0x28 | CB 08 | CAN ID encoding (byte-swapped?). If read as 0x08, 0xCB: `0x08 * 8 + (0xCB >> 5)` = **0x46** — doesn't match. If 0xCB08 decoded differently: needs investigation. Believed to encode feedback CAN ID **0x658** but formula unclear. | UNCERTAIN |
| 0x29 | 62 | Mode/config register. Bit 4 (0x10): PWM-from-CAN mode. Bit 6 (0x40): CAN TX enable. 0x62=PWM mode, 0x72=CAN mode. | CONFIRMED |
| 0x2A | A0 | Unknown. Constant across all known units. | UNKNOWN (constant) |
| 0x2B | 96 | Unknown. Constant across all known units. | UNKNOWN (constant) |
| 0x2C | 06 | Model-specific config. G-222=0x06, G-221=0x32. Differentiates G-number variants alongside 0x0D-0x0E. Possibly PWM frequency config or position sensor scaling. | STRONG HYPOTHESIS (model differentiator) |
| 0x2D | 02 | Unknown. Constant across all known units. | UNKNOWN (constant) |
| 0x2E | 1D | Model-specific config. G-222=0x1D, G-221=0x1F. Possibly position sensor scaling or motor control parameter. | STRONG HYPOTHESIS (model differentiator) |
| 0x2F | 09 | Unknown. Constant across all known units. | UNKNOWN (constant) |

**Write-enable code:** 0x8D (confirmed working for 0x22, 0x29)

### 0x30-0x3F: Extended Configuration

| Addr | Value | Description | Confidence |
|------|-------|-------------|------------|
| 0x30 | 00 | Unknown. Constant (0x00) across units. | UNKNOWN |
| 0x31 | 2A | Motor/gearbox travel parameter. G-222=0x2A(42), G-221=0x2C/0x2D(44-45), G-222 unit2=0x28(40). Complementary to 0x33: `0x31 + 0x33 ≈ 0xFF`. Likely encodes physical travel angle or gear ratio. | STRONG HYPOTHESIS |
| 0x32 | 03 | Unknown. | UNKNOWN |
| 0x33 | D5 | One's complement of 0x31. Redundancy check: `0x31 + 0x33 = 0xFE or 0xFF`. | STRONG HYPOTHESIS |
| 0x34-0x35 | 00 00 | Unknown. Varies slightly between units (0x00-0x04). | UNKNOWN |
| 0x36 | 20 | Unknown. Constant across units. | UNKNOWN |
| 0x37 | FF | Unknown. Constant across units. | UNKNOWN |
| 0x38-0x39 | 20 20 | Unknown. Constant across units. | UNKNOWN |
| 0x3A | 0A | Unknown. Constant across units. | UNKNOWN |
| 0x3B | 54 or 52 | Model-specific. G-222=0x54, G-221=0x52. | UNKNOWN (model differentiator) |
| 0x3C-0x3D | 01 8E | L9805E temperature sensor trim (T0H, T0L). Factory-programmed per-chip. Per L9805E datasheet Section 5.5.6, these are at MCU address 0x0C7C-0x0C7D. Constant across time on same unit. | CONFIRMED (L9805E datasheet) |
| 0x3E-0x3F | 01 AC | L9805E temperature sensor trim (VT0H, VT0L). Factory-programmed per-chip. MCU address 0x0C7E-0x0C7F. Per-unit: G-222 unit1=0x01AC, unit2=0x01A7; G-221 dl=0x01B0, hw=0x01AE. | CONFIRMED (L9805E datasheet) |

---

## Known Registers — Second Half (Factory Backup?)

### 0x40-0x4E: Mirror of 0x00-0x0E

Byte-for-byte identical to first half. Never written to by `hella_prog.py`.

### 0x4F-0x5F: NCV77320 Sensor Calibration + Identification

This region stores data related to the NCV77320 inductive position sensor IC. It is NOT a mirror
of 0x0F-0x1F. Not write-protected (0x8D works for this range).

| Addr | Value | Description | Confidence |
|------|-------|-------------|------------|
| 0x4F | FF | Separator / unused. Always 0xFF. First half counterpart (0x0F) is firmware-managed. | CONFIRMED (constant) |
| 0x50-0x51 | 45 45 | **NOT factory-fixed.** Changes when config is modified (observed 0x45→0x79→0xA3 on same unit). Always byte[0]=byte[1]. Likely a CRC, hash, or checksum of a config sector, or a shadow copy of an NCV77320 register that changes with recalibration. | REVISED — not factory backup |
| 0x52 | 10 | NCV77320 sensor calibration. Constant (0x10) across all 4 known units. Possibly a config flag or scale factor. | CONFIRMED (constant across units) |
| 0x53-0x58 | 2E 5B 00 5E 09 BA | **Per-unit NCV77320 coupling compensation.** Stable across time on same physical unit, different between units. Likely contains the NCV77320's `dcc_c12`, `dcc_c23` direct coupling compensation coefficients that compensate for PCB coil manufacturing tolerances. The MCU stores these and programs them into the NCV77320 via SPI at boot. | STRONG HYPOTHESIS (NCV77320 cal data) |
| 0x59-0x5A | 71 21 | NCV77320 sensor identification. Constant across ALL known units. Likely `sent_sensor_type` from NCV77320 EEPROM address 44. | STRONG HYPOTHESIS |
| 0x5B | 22 | NCV77320 identification. Constant across all units (0x22). Likely part of `sent_manufacturer_code` from NCV77320 EEPROM address 45. | STRONG HYPOTHESIS |
| 0x5C | 22 or 21 | **G-number variant identifier.** 0x22 for all G-222 units, 0x21 for all G-221 units. Stored in NCV77320's SENT device configuration and copied to MCU EEPROM at factory programming. | STRONG HYPOTHESIS (confirmed pattern across 4 units) |
| 0x5D | 01 or 00 | Per-model config. G-222 unit1=0x01, unit2=0x00; G-221=0x00. | UNKNOWN |
| 0x5E-0x5F | 61 05 | Per-unit identifier or calibration. Varies between units, stable across time on same unit. | UNKNOWN |

**Key insight from NCV77320 datasheet:** The NCV77320's EEPROM (separate from this MCU EEPROM)
contains a 15-point piecewise-linear (PWL) correction table and coupling compensation coefficients
that are factory-calibrated per-unit to compensate for PCB coil geometry variations. The MCU
likely reads these from the NCV77320 at first boot and caches them at 0x53-0x58 for reference,
or stores them here to program the NCV77320 at every power-on.

### 0x60-0x6F: Mirror of 0x20-0x2F

Byte-for-byte identical. Writing to 0x62 and 0x69 (mirrors of 0x22 and 0x29) works with write-enable 0x8D, and changes persist.

### 0x70-0x7F: Partial Mirror of 0x30-0x3F

| Addr | Value | First-half equivalent | Notes |
|------|-------|-----------------------|-------|
| 0x70-0x75 | FF FF FF FF FF FF | 00 2A 03 D5 00 00 | Factory blank vs active data |
| 0x76-0x7B | 20 FF 20 20 0A 54 | Same as 0x36-0x3B | Matches |
| 0x7C-0x7D | 01 8E | L9805E temp trim T0H/T0L (same as 0x3C-0x3D). **Note:** This is MCU address 0x0C7C-0x0C7D per the L9805E datasheet — the EEPROM's "byte 0x7C" maps directly to the chip's reserved temp sensor trim location. | CONFIRMED (L9805E datasheet) |
| 0x7E-0x7F | 01 AC | L9805E temp trim VT0H/VT0L (same as 0x3E-0x3F). MCU address 0x0C7E-0x0C7F. | CONFIRMED (L9805E datasheet) |

---

## CAN ID Encoding

CAN IDs are stored as 2-byte pairs:
```
CAN_ID   = byte1 * 8 + (byte2 >> 5)
pkt_size = byte2 & 0x0F
```

| EEPROM addr | Raw bytes | Decoded CAN ID | Decoded pkt_size | Confirmed? |
|-------------|-----------|----------------|------------------|------------|
| 0x09-0x0A | 7D 08 | 0x3E8 | 8 | YES — this is the data response ID |
| 0x0B-0x0C | CE 0A | 0x670 | 10 | Decode YES, purpose UNKNOWN |
| 0x27-0x28 | CB 08 | ??? | ??? | Decode UNCERTAIN — believed to be 0x658 feedback ID but formula doesn't produce it cleanly |

**TODO:** Verify 0x27-0x28 decoding. The GitHub wiki says these encode the feedback CAN ID (0x658) but our formula gives 0x46 if read as-is.

---

## Position Feedback Temperature (CAN byte 5)

The temperature value in CAN feedback byte 5 (typically ~0x19-0x1C at room temperature) is derived
from the NCV77320's on-die temperature sensor. The NCV77320 formula is:

```
temp[11:0] = round(8 * (T[K] - 200K))
```

At 25°C (298K): `temp = 8 * 98 = 784 = 0x310`. The MCU scales this 12-bit value down to the
single byte transmitted in the CAN feedback frame.

---

## Open Questions

1. **Which half is active?** Does the actuator boot from 0x00-0x3F or 0x40-0x7F? Does it compare them?
2. **What is 0x0B-0x0C (CAN ID 0x670)?** Could this be the position steering receive ID that we couldn't find?
3. **What's in 0x0F-0x1F?** Circular buffer of 4-byte records. Values 0x04, 0x08, 0x20 rotate through the region during motor operations. Possibly motor fault/event log or endpoint calibration history.
4. ~~**Why did 0x50-0x51 change?**~~ **ANSWERED:** 0x50-0x51 is NOT factory backup — it's a live value (CRC/hash/counter) that changes with config modifications. Always byte[0]=byte[1].
5. **What's the range formula?** 0x22 is the MCU's position zero offset, analogous to NCV77320's `pos_shift`. Scale: ~4 position counts per unit. Exact conversion from NCV77320's 16-bit angle (0-65535) to MCU's position range needs further investigation.
6. **0x27-0x28 CAN ID decoding:** How does CB 08 encode 0x658? Different formula? Byte-swapped? Need to verify.
7. ~~**Addresses 0x00-0x02, 0x0D-0x0E, 0x2A-0x2F:**~~ **PARTIALLY ANSWERED:** 0x00-0x01 = per-unit device ID, 0x02 = 0x55 magic, 0x0D-0x0E = model config ID (G-222=0x012A, G-221=0x0155), 0x2C/0x2E = model-specific scaling. Remaining unknowns: 0x07-0x08, 0x20-0x21, 0x23, 0x2A-0x2B, 0x2D, 0x2F.
8. **Can a factory reset be triggered?** Does the actuator have a command to copy backup→active?
9. **NCV77320 SPI communication:** Can the MCU's SPI bus to the NCV77320 be probed? Reading the NCV77320's own EEPROM directly would reveal the PWL correction table and coupling compensation values, confirming whether 0x53-0x58 are indeed cached NCV77320 calibration data.
10. **0x31 + 0x33 complementary pair:** What physical parameter does 0x31 encode? It varies per model (G-222=0x2A, G-221=0x2C/0x2D) and 0x33 is its one's complement. Possibly gearbox ratio or sensor mechanical-to-electrical angle ratio.

---

## Write-Enable Sector Map

**Important:** These sectors are implemented entirely in Hella's firmware (mask-ROM), NOT in
the L9805E silicon. The EEPROM hardware has no sector concept — all 128 bytes are equally
writable at the hardware level. Hella's CAN protocol handler enforces these access controls
in software before passing writes through to the EEPCR register.

This means the write protection at 0x0F-0x1F could theoretically be bypassed by custom firmware,
but not through the CAN interface — the mask-ROM code is the gatekeeper.

| Sector code | Known working addresses | Known failing addresses |
|-------------|------------------------|------------------------|
| 0x2D | 0x03, 0x04, 0x05, 0x06 | 0x0F, 0x10, 0x11, 0x14-0x16, 0x18, 0x1A, 0x1C, 0x1F |
| 0x8D | 0x22, 0x29, 0x50, 0x51, 0x62, 0x69 | (none known) |
| 0x0D, 0x4D, 0x6D, 0xAD, 0xCD, 0xED | (none) | 0x0F (all tested, all failed) |

---

*Last updated: 2026-03-20. Based on G-222 (×2 physical units), G-221 (×2: downloaded + physical), 7 total EEPROM dumps.*
*NCV77320 sensor IC identification and EEPROM architecture added from onsemi NCV77320/D datasheet (Rev. 3).*
*L9805E MCU EEPROM hardware details, PBCSR register, and temperature trim bytes added from ST L9805E datasheet (Rev. 3, Sept 2013).*
*Datasheets: `datasheets/l9805e.pdf` (125 pages), `datasheets/ncv77320.pdf` (39 pages).*
*To be updated when G-277 (6NW009420, Mercedes OM642) EEPROM is dumped for comparison.*
