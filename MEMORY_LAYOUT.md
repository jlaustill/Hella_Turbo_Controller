# Hella Turbo Actuator Memory Layout Documentation

This document explains the memory layout and meaning of values in the 128-byte memory dump from Hella Universal turbo actuators, based on reverse engineering work from the community.

⚠️ **DANGER**: Modifying certain memory locations can permanently brick your actuator! Always backup before making changes.

## Overview

The Hella actuators contain 128 bytes of EEPROM configuration memory that determines:

- CAN bus vs PWM control mode
- CAN message IDs for communication
- Position limits and calibration
- Motor direction and PWM frequency
- Safety parameters

## Known Memory Map

Based on community reverse engineering work:

| Address   | Purpose                 | Description                                    | Notes                  |
| --------- | ----------------------- | ---------------------------------------------- | ---------------------- |
| 0x03-0x04 | **Min Position**        | Minimum actuator position (16-bit, big-endian) | Safe to modify         |
| 0x05-0x06 | **Max Position**        | Maximum actuator position (16-bit, big-endian) | Safe to modify         |
| 0x09-0x0A | **Command CAN ID**      | CAN ID for position commands                   | ⚠️ Dangerous to modify |
| 0x22      | **Range Calculation**   | Used in position range calculations            | Usually (max-min)/4    |
| 0x24-0x25 | **Request CAN ID**      | CAN ID for memory/config requests              | ⚠️ Dangerous to modify |
| 0x27-0x28 | **Response CAN ID**     | CAN ID for status responses                    | ⚠️ Dangerous to modify |
| 0x29      | **Control Mode Config** | Bit flags for CAN/PWM control                  | ⚠️ Very dangerous!     |
| 0x41      | **Interface Config**    | Control interface configuration                | ⚠️ Very dangerous!     |

### Critical Configuration Bytes

#### Address 0x29 - Control Mode

- Controls which CAN ID is used for programming
- Wrong value can make actuator unresponsive
- **Known values**:
  - `0x2A` = Use 0x3F0 for programming
  - Other values may use different IDs

#### Address 0x41 - Interface Configuration

- **Bit 0**: Motor direction (0=CW, 1=CCW)
- **Bit 4**: Get PWM from CAN (enables CAN position control)
- **Bit 6**: Enable CAN TX (enables status broadcasts)
- **Example**: `0x50` = CAN control enabled with status broadcasts

## Actuator Variants and CAN IDs

Different G-code actuators use different CAN message IDs:

### G-221 (Ford TDCI 6NW008412)

- **Request ID**: 0x4EA
- **Response ID**: 0x4EB
- **Position control**: Via 0x4EA with `aa bb 00 00 00 00 00 00` (aa=rough, bb=precise)

### G-22 (Various applications)

- **Position command**: 0x386 (4 bytes: first byte 0-3, second 0-255)
- **Status response**: 0x71C
- **Position range**: 0-1023 (needs refresh every 500ms)

### G-222 (User jlaustill's actuator)

- **Status broadcasts**: 0x658
- **Currently PWM controlled** (CAN control desired but not enabled)

### Standard Programming Interface

- **Request ID**: 0x3F0, 0x660, 0x4EA
- **Response IDs**: 0x3E8 (memory), 0x3EA (position), 0x3EB (ack), 0x4EB

## Position Value Interpretation

### Standard Position Format

- **Range**: 0x0000 to 0xFFFF (0 to 65535)
- **Typical usage**: 0x0100 to 0x0400 (256 to 1024)
- **Physical meaning**: Stepper motor steps or encoder counts
- **Resolution**: Each unit = one step of actuator movement

### From Your Sample Data (G-222)

Looking at your memory dump, the position values are:

- **Min Position (0x03-0x04)**: Not clearly visible in text format
- **Max Position (0x05-0x06)**: Not clearly visible in text format

To properly decode your dump, convert the text format to binary first.

## CAN Protocol Commands

### Basic Communication

```
Keepalive: 49 00 00 00 00 00 00 00 → Send to 0x3F0
Response:  Expected on 0x3E8/0x3EA/0x3EB
```

### Position Control (G-221 style)

```
Command: aa bb 00 00 00 00 00 00 → Send to 0x4EA
Where: aa = rough position, bb = fine position
```

### Position Control (G-22 style)

```
Command: xx yy zz ww → Send to 0x386
Where: First byte 0-3, second byte 0-255
Must repeat every 500ms or position resets to 0
```

### Memory Access

```
Set target: 31 A0 A1 00 00 00 00 00 → Sets memory target 0xA0A1
Write data: 57 aa 00 dd 00 00 00 00 → Writes 'dd' to target 'aa'
```

## Configuration Examples

### Converting PWM to CAN Control

**⚠️ EXTREMELY DANGEROUS - Can brick actuator!**

To enable CAN position control on a PWM actuator:

1. **Backup EEPROM first!**
2. Modify address 0x41:
   - Set bit 4 (PWM from CAN)
   - Set bit 6 (Enable CAN TX)
3. Configure appropriate CAN IDs in addresses 0x24-0x28
4. Test carefully with position commands

### Changing CAN IDs

If you need different CAN IDs:

1. **Backup EEPROM first!**
2. Calculate new ID values using formula: `byte1 * 8 + byte2 >> 5`
3. Update addresses 0x24-0x25 (request), 0x27-0x28 (response)
4. May need to update 0x09-0x0A (command ID)

## Safety Guidelines

### Before Modifying Memory

- ✅ **Always backup** original memory dump
- ✅ **Document** what you're changing and why
- ✅ **Start small** - change one bit at a time
- ✅ **Test immediately** after each change
- ❌ **Never guess** at critical configuration bytes

### Recovery from Brick

- Some actuators may have "factory reset" capability
- Try different programming CAN IDs (0x3F0, 0x660, 0x4EA, 0x61C, 0x618)
- Boot mode may exist for recovery (not documented)

### Known Dangerous Areas

- **Address 0x29**: Programming CAN ID selector
- **Address 0x41**: Interface control bits
- **Address 0x10**: Unknown critical function
- **Addresses 0x09-0x0A**: Command CAN ID

## Decoding Your Memory Dump

For your G-222 dump, to enable CAN control:

1. **Convert text dump to binary** first
2. **Identify current config** at address 0x41
3. **Find CAN ID config** at addresses 0x24-0x28
4. **Plan modifications** to enable CAN control
5. **Test with extreme caution**

Would you like help creating a script to safely attempt enabling CAN control on your G-222?

## Community Resources

- **Original project**: [Hella_Turbo_Controller](https://github.com/djwlindenaar/Hella_Turbo_Controller)
- **Commercial tools**: TurboTechnics ATP-100, TurboIT ETP Tester
- **$100 bounty**: User jlaustill offers reward for G-222 CAN control solution

---

**Sources**: Community reverse engineering work by djwlindenaar, test3210-d, awpe, peterschumann, jlaustill, and others.
