# Hella Universal Turbo Actuator I — EEPROM Memory Map

128 bytes of on-chip EEPROM inside the **L9805E** (STMicroelectronics "Super Smart Power Motor Driver").
Accessed via CAN protocol on 0x3F0. Previously assumed to be a separate 93C66 chip, but
the L9805E integrates 128 bytes of EEPROM, 16K EPROM (firmware), 256 bytes RAM, CAN controller,
H-bridge motor driver, 10-bit ADC, PWM, and an ST7 8-bit MCU — all in one package.

Hella uses a custom mask-ROM version with their firmware burned into the 16K EPROM at fabrication.
Write-protection of EEPROM regions (e.g., 0x0F-0x1F) is enforced by firmware, not hardware.

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

---

## Known Registers — First Half (Active?)

### 0x00-0x0E: Device Configuration

| Addr | Value | Description | Confidence |
|------|-------|-------------|------------|
| 0x00-0x02 | 05 0E 55 | Unknown. Device ID? Firmware version? | UNKNOWN |
| 0x03-0x04 | 00 AE | Min position (16-bit big-endian). Written by `set_min()`. | CONFIRMED |
| 0x05-0x06 | 03 96 | Max position (16-bit big-endian). Written by `set_max()`. | CONFIRMED |
| 0x07-0x08 | FF FF | Unknown. Always 0xFF? | UNKNOWN |
| 0x09-0x0A | 7D 08 | CAN ID encoding. Decodes to: `0x7D * 8 + (0x08 >> 5)` = **0x3E8** (response ID). | CONFIRMED |
| 0x0B-0x0C | CE 0A | CAN ID encoding. Decodes to: `0xCE * 8 + (0x0A >> 5)` = **0x670**, pkt_size=0x0A. Purpose unknown — possibly position steering RX ID? | PARTIALLY CONFIRMED (decode formula confirmed, purpose UNKNOWN) |
| 0x0D-0x0E | 01 2A | Unknown. | UNKNOWN |

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
| 0x22 | 00 | Range calibration. Written by `set_min`/`set_max` (hardcoded to 99=0x63 in code, but our unit had 0x00 from factory and 0xBA after experiments). Formula unclear. | PARTIALLY CONFIRMED |
| 0x23 | 2D | Unknown. Referenced in write sequences (re-selected after 0x22 write) but never written to. | UNKNOWN |
| 0x24-0x26 | 00 08 00 | Unknown. | UNKNOWN |
| 0x27-0x28 | CB 08 | CAN ID encoding (byte-swapped?). If read as 0x08, 0xCB: `0x08 * 8 + (0xCB >> 5)` = **0x46** — doesn't match. If 0xCB08 decoded differently: needs investigation. Believed to encode feedback CAN ID **0x658** but formula unclear. | UNCERTAIN |
| 0x29 | 62 | Mode/config register. Bit 4 (0x10): PWM-from-CAN mode. Bit 6 (0x40): CAN TX enable. 0x62=PWM mode, 0x72=CAN mode. | CONFIRMED |
| 0x2A-0x2F | A0 96 06 02 1D 09 | Unknown. | UNKNOWN |

**Write-enable code:** 0x8D (confirmed working for 0x22, 0x29)

### 0x30-0x3F: Extended Configuration

| Addr | Value | Description | Confidence |
|------|-------|-------------|------------|
| 0x30-0x35 | 00 2A 03 D5 00 00 | Unknown. Not present in second half (0x70-0x75 = 0xFF). | UNKNOWN |
| 0x36-0x3F | 20 FF 20 20 0A 54 01 8E 01 AC | Unknown. Matches 0x76-0x7F. | UNKNOWN |

---

## Known Registers — Second Half (Factory Backup?)

### 0x40-0x4E: Mirror of 0x00-0x0E

Byte-for-byte identical to first half. Never written to by `hella_prog.py`.

### 0x4F-0x5F: Factory Calibration?

Completely different from 0x0F-0x1F. Not write-protected (0x8D works for this range).

| Addr | Value | Notes |
|------|-------|-------|
| 0x4F | FF | Factory default? (vs 0x0F = 0x0E) |
| 0x50-0x51 | 45 45 | Factory values? (vs 0x10-0x11 = 00 00). After our experiments these changed to 0x0F 0x0F, restored back to 0x45 0x45. |
| 0x52-0x5F | 10 2E 5B 00 5E 09 BA 71 21 22 22 01 61 05 | Unknown. Completely different data from 0x12-0x1F. |

**QUESTION:** If these are factory backup values, why are 0x50-0x51 different from original 0x10-0x11? And why did they change during our experiments (to 0x0F) if this is supposed to be backup?

### 0x60-0x6F: Mirror of 0x20-0x2F

Byte-for-byte identical. Writing to 0x62 and 0x69 (mirrors of 0x22 and 0x29) works with write-enable 0x8D, and changes persist.

### 0x70-0x7F: Partial Mirror of 0x30-0x3F

| Addr | Value | First-half equivalent | Notes |
|------|-------|-----------------------|-------|
| 0x70-0x75 | FF FF FF FF FF FF | 00 2A 03 D5 00 00 | Factory blank vs active data |
| 0x76-0x7F | 20 FF 20 20 0A 54 01 8E 01 AC | Same as 0x36-0x3F | Matches |

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

## Open Questions

1. **Which half is active?** Does the actuator boot from 0x00-0x3F or 0x40-0x7F? Does it compare them?
2. **What is 0x0B-0x0C (CAN ID 0x670)?** Could this be the position steering receive ID that we couldn't find?
3. **What's in 0x0F-0x1F?** Circular buffer? Endpoint calibration log? Motor run counter?
4. **Why did 0x50-0x51 change?** If 0x40-0x7F is factory backup, these shouldn't have changed during experiments. Maybe the actuator updates both halves for some registers?
5. **What's the range formula?** 0x22 encodes range but the relationship between the value and physical travel is unclear. `hella_prog.py` hardcodes 99, also has commented formula `255 - (pos/1024)*255`.
6. **0x27-0x28 CAN ID decoding:** How does CB 08 encode 0x658? Different formula? Byte-swapped? Need to verify.
7. **Addresses 0x00-0x02, 0x07-0x08, 0x0D-0x0E, 0x20-0x21, 0x23-0x26, 0x2A-0x2F, 0x30-0x3F:** All unknown purpose.
8. **Can a factory reset be triggered?** Does the actuator have a command to copy backup→active?

---

## Write-Enable Sector Map

| Sector code | Known working addresses | Known failing addresses |
|-------------|------------------------|------------------------|
| 0x2D | 0x03, 0x04, 0x05, 0x06 | 0x0F, 0x10, 0x11, 0x14-0x16, 0x18, 0x1A, 0x1C, 0x1F |
| 0x8D | 0x22, 0x29, 0x50, 0x51, 0x62, 0x69 | (none known) |
| 0x0D, 0x4D, 0x6D, 0xAD, 0xCD, 0xED | (none) | 0x0F (all tested, all failed) |

---

*Last updated: 2026-03-06. Based on G-222 unit (6NW008412, BMW 3 Series).*
*To be updated when G-277 (6NW009420, Mercedes OM642) EEPROM is dumped for comparison.*
