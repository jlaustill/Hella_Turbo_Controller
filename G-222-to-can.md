# G-222 CAN Position Control Conversion

## Overview
Converts a Hella G-222 actuator from PWM-only mode to CAN position control mode.
Tested on a G-222 (6NW008412) with L9805E chip, 2026-03-16.

## EEPROM Changes Required

| Addr | Addr(dec) | Original | New      | Mirror | Purpose                  |
|------|-----------|----------|----------|--------|--------------------------|
| 0x04 | 4         | 0xAE(174)| 0x1D(29) | 0x44   | Min position low byte    |
| 0x06 | 6         | 0x96(150)| 0xDE(222)| 0x46   | Max position low byte    |
| 0x22 | 34        | 0x00(0)  | 0xD0(208)| 0x62   | Rotation offset          |
| 0x24 | 36        | 0x00(0)  | 0x9D(157)| 0x64   | Command CAN ID high      |
| 0x25 | 37        | 0x08(8)  | 0x48(72) | 0x65   | Command CAN ID low       |
| 0x26 | 38        | 0x00(0)  | 0x06(6)  | 0x66   | Command format (0x06=16-bit) |
| 0x27 | 39        | 0xCB(203)| 0x9D(157)| 0x67   | Broadcast CAN ID high    |
| 0x28 | 40        | 0x08(8)  | 0x68(104)| 0x68   | Broadcast CAN ID low     |
| 0x29 | 41        | 0x62(98) | 0x2A(42) | 0x69   | Mode register            |

All changes must also be written to the mirror address.
0x03 and 0x05 (min/max high bytes) were already 0x00 and 0x03 respectively — unchanged.

## CAN ID Summary

| Function             | CAN ID | Notes                                    |
|----------------------|--------|------------------------------------------|
| Position command     | 0x4EA  | Send commands here                       |
| Position broadcast   | 0x4EB  | Actuator reports position here (~20ms)   |
| Programming TX       | 0x3F0  | Unchanged from original                  |
| Programming response | 0x3E8  | Unchanged from original                  |
| Programming ready    | 0x3EB  | Unchanged, byte[7]=0x53 means ready      |

## Position Command Format

Send on **0x4EA** every <50ms (watchdog timeout ~50ms):

### 16-bit mode (0x26=0x06, recommended)

```
Byte[0-1] = 16-bit position (big-endian), 0-1000
Byte[2-7] = 0x00
```

| Command | Behavior                               |
|---------|----------------------------------------|
| 0       | Full travel to min endstop             |
| 500     | Approximately 50% travel               |
| 1000    | Full travel to max endstop             |

Position feedback tracks command ~1:1 (cmd=600 → feedback≈602).

### 8-bit mode (0x26=0x00, legacy)

```
Byte[0] = position command (0-250)
Byte[1-7] = 0x00
```

| Command | Behavior                               |
|---------|----------------------------------------|
| 0       | Full travel to min endstop             |
| 125     | Approximately 50% travel               |
| 250     | Full travel to max endstop             |
| 251-255 | Return to default/rest position        |

Position feedback = command * 4 (approximately). Range: 0 to ~1000.

## Position Feedback Format

Broadcast on **0x4EB** every ~20ms:

```
Byte[0]   = unknown status byte
Byte[1]   = 0x08 when no commands received (>50ms), 0x00 when actively commanded
Byte[2-3] = 16-bit position (big-endian), 0-1000
Byte[4]   = 0x00
Byte[5]   = ~0x1C (unknown, nearly constant)
Byte[6-7] = 16-bit motor load/current (big-endian), 0 at rest, increases under load
```

Motor load (bytes 6-7):
- 0 when at target position and stationary
- Spikes during acceleration (~2000+)
- Increases proportionally when motor is working against resistance
- Confirmed by physically holding the arm — load climbs steadily as motor pushes harder

## CAN ID EEPROM Encoding

CAN IDs are stored across two bytes with the following bit layout:

```
High byte: CAN_ID >> 3       (upper 8 bits of the 11-bit CAN ID)
Low byte:  (CAN_ID & 0x07) << 5 | DLC_CONFIG
           ├── bits 7-5: lower 3 bits of the 11-bit CAN ID
           └── bits 4-0: frame DLC configuration (0x08 = 8-byte frames)
```

Decode: `CAN_ID = high_byte * 8 + (low_byte >> 5)`

**The lower 5 bits of the low byte control the CAN frame data length.**
Setting them to 0x00 produces zero-length frames. Must be 0x08 for normal 8-byte frames.

Example: 0x4EA = high=0x9D, low=0x48 (0x40 for ID bits + 0x08 for DLC)

## Rotation Offset (0x22)

Calibrates the position sensor so that position feedback reads 0 at the min endstop.
The scale is approximately **1 position count per 4 units of 0x22** (x4 scale).

| 0x22 value | cmd=0 feedback | Notes |
|------------|---------------|-------|
| 0x00 (0)   | 1001          | Overflow — way too low |
| 0xC0 (192) | 41            | Getting closer |
| 0xD0 (208) | 0             | Correct for first G-222 |
| 0xDC (220) | 3             | Slightly over |
| 0xE0 (224) | 4             | Over by 4 counts |

This value is **unit-specific** — depends on physical sensor/magnet alignment in the gearbox.
The `convert_to_can.py` script auto-calibrates this by sweeping values until cmd=0 gives pos=0.

## Key Notes

- **Mode register (0x29)** is an enum, not a bitmask. Only specific values are accepted:
  - 0x62 = PWM mode (original G-222)
  - 0x2A = CAN position control mode
  - 0x72 and 0x6A are rejected by firmware
- **Min/max positions** should be set to actual physical endstops using the register-level
  motor drive (mode=5, register 0x63). Values are unit-specific.
- **Watchdog timeout** is ~50ms. Commands must be sent at least every 50ms or the
  actuator returns to its default rest position.
- **Power cycle required** after changing mode register (0x29) for it to take full effect.
- **Broadcast ID change takes effect immediately** without power cycle.
- EEPROM backup saved as `G-222-canmode.bin`.
- Original EEPROM backup: `eeprom_backup.bin`.

## Reverting to Original

Restore all bytes from `eeprom_backup.bin` using `eeprom_restore.py`:
```
python3 eeprom_restore.py can0 socketcan restore
```
