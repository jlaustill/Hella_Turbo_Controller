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

Send on **0x4EA** every ~20ms (watchdog timeout if commands stop):

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

## Position Feedback Format

Broadcast on **0x4EB** every ~20ms:

```
Byte[0]   = 0x00 when commanded, other values when idle
Byte[1]   = 0x08 when idle, 0x00 when actively commanded
Byte[2-3] = 16-bit position (big-endian) = command * 4
Byte[4]   = 0x00
Byte[5]   = ~0x1C (unknown, nearly constant)
Byte[6-7] = 0x00
```

Position feedback = command value * 4 (approximately).
Full range: 0 to ~1000 in feedback units.

## Key Notes

- **Mode register (0x29)** is an enum, not a bitmask. Only specific values are accepted:
  - 0x62 = PWM mode (original G-222)
  - 0x2A = CAN position control mode
  - 0x72 and 0x6A are rejected by firmware
- **Rotation offset (0x22)** calibrates the position sensor to report 0 at the min endstop.
  Value is unit-specific — depends on physical sensor alignment. 0xD0 is correct for this G-222.
- **Min/max positions** should be set to actual physical endstops using the register-level
  motor drive (mode=5, register 0x63). Values are unit-specific.
- **Power cycle required** after changing mode register (0x29) for it to take full effect.
- **Broadcast ID change takes effect immediately** without power cycle.
- EEPROM backup saved as `G-222-canmode.bin`.
- Original EEPROM backup: `eeprom_backup.bin`.

## Reverting to Original

Restore all bytes from `eeprom_backup.bin` using `eeprom_restore.py`:
```
python3 eeprom_restore.py can0 socketcan restore
```
