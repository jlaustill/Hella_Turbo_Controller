# Hella Universal Turbo Actuator I - CAN Protocol Reference

Reverse-engineered CAN bus protocol for the Hella Universal Turbo Actuator I
(G-222, part number 6NW008412). This document covers the complete communication
protocol as confirmed through testing.

## CAN Bus Configuration

- **Bitrate**: 500 kbit/s
- **Frame type**: Standard 11-bit IDs, 8-byte data
- **SLCAN baudrate**: 128000 (for USB-CAN adapters)

## CAN IDs

| ID | Direction | Purpose |
|----|-----------|---------|
| 0x3F0 | TX (host→actuator) | Programming/command interface |
| 0x3E8 | RX (actuator→host) | EEPROM read data response |
| 0x3EA | RX (actuator→host) | Status/position during motor ops |
| 0x3EB | RX (actuator→host) | Ready/handshake response |
| 0x658 | RX (actuator→host) | Continuous position broadcast |

### CAN ID Encoding in EEPROM

CAN IDs are stored in EEPROM as 2-byte pairs:
```
CAN_ID = byte1 * 8 + (byte2 >> 5)
pkt_size = byte2 & 0x0F
```

Known EEPROM CAN ID locations:
- 0x09-0x0A: Command CAN ID (0x7D, 0x08 → 0x3E8)
- 0x27-0x28: Feedback CAN ID (0xCB, 0x08 → 0x658, swapped byte order)

## Command Protocol

All commands are sent on **0x3F0** with 8-byte frames.

### Opcodes

| Opcode | Name | Format | Description |
|--------|------|--------|-------------|
| 0x49 | Init/Handshake | `49 00 00 00 00 00 00 00` | Wake actuator, enter programming mode |
| 0x31 | Register Select | `31 HI LO 00 00 00 00 00` | Select register at address HI:LO |
| 0x57 | Write Value | `57 00 00 VAL 00 00 00 00` | Write VAL to selected register |
| 0x44 | Commit | `44 00 00 00 00 00 00 00` | Commit/save pending changes |

### Special Register Addresses

| Address (HI:LO) | Usage |
|------------------|-------|
| 0x00:0x94 | Prepare/NOP (used between register operations) |
| 0x01:0x5D | Mode register |
| 0x01:0x63 | Speed/velocity register |
| 0x00:0x80 | Motor enable register |
| 0x01:0x61 | Direction register |
| 0x0C:ADDR | EEPROM access (read/write at ADDR) |

### Mode Register Values (0x015D)

| Value | Meaning |
|-------|---------|
| 0x02 | Lock (normal operation) |
| 0x05 | Calibration/programming unlock |

## Init Sequence

Every programming session starts with init:

```
TX: 49 00 00 00 00 00 00 00    (Init)
RX: [0x3EB response with byte[7]=0x53 ('S') means ready]
```

The actuator must be in ready state (0x3EB with byte[7]=0x53) before
accepting register commands.

## EEPROM Read Protocol

Read one byte from EEPROM address:

```
1. Send init (0x49) and wait for 0x3EB ready
2. For each byte:
   a. Wait for 0x3EB ready (byte[7]=0x53)
   b. Send: 31 0C ADDR 00 00 00 00 00    (select EEPROM address)
   c. Wait for 0x3E8 response → byte[0] = value
```

## EEPROM Write Protocol

Writing requires unlock, sector write-enable, write, then lock+commit.

### Sector Write-Enable Codes

The EEPROM has sector-based write protection. A write-enable code must be
written to register 0x0094 before writing to EEPROM addresses in that sector:

| Address Range | Write-Enable Code | Confirmed |
|--------------|-------------------|-----------|
| 0x00-0x0E | 0x2D | Yes (addrs 0x03-0x06) |
| 0x0F-0x1F | Unknown / write-protected | Tested 0x0D-0xED, none worked |
| 0x20-0x3F | 0x8D | Yes (addrs 0x22, 0x29) |
| 0x40-0x7F | 0x8D | Yes (addrs 0x50, 0x51, 0x62, 0x69) |

**Note**: Addresses 0x0F-0x1F appear to be actuator-managed and write-protected
from CAN. The actuator updates these values internally during motor operations.

### Write Sequence (Single Byte)

```
1. Init: 49 00 00 00 00 00 00 00
2. Wait 500ms

3. Prepare:          31 00 94 00 00 00 00 00
4. Select mode reg:  31 01 5D 00 00 00 00 00
5. Mode=5 (unlock):  57 00 00 05 00 00 00 00

6. Prepare:          31 00 94 00 00 00 00 00
7. Prepare:          31 00 94 00 00 00 00 00
8. Write-enable:     57 00 00 WE 00 00 00 00    (WE = sector code)

9. Select EEPROM:    31 0C ADDR 00 00 00 00 00
10. Write value:     57 00 00 VAL 00 00 00 00

11. Prepare:         31 00 94 00 00 00 00 00
12. Disable write:   57 00 00 00 00 00 00 00

13. Prepare:         31 00 94 00 00 00 00 00
14. Write-enable:    57 00 00 WE 00 00 00 00    (re-enable for verify)
15. Re-select addr:  31 0C ADDR 00 00 00 00 00  (read-back trigger)

16. Prepare:         31 00 94 00 00 00 00 00
17. Disable write:   57 00 00 00 00 00 00 00

18. Prepare:         31 00 94 00 00 00 00 00
19. Select mode:     31 01 5D 00 00 00 00 00
20. Mode=2 (lock):   57 00 00 02 00 00 00 00

21. Prepare:         31 00 94 00 00 00 00 00
22. Commit:          44 00 00 00 00 00 00 00

(20ms delay between each command)
```

## Motor Control Protocol

### Drive Forward (toward 0%)

```
1. Init:            49 00 00 00 00 00 00 00     (wait 500ms)
2. Prepare:         31 00 94 00 00 00 00 00
3. Mode select:     31 01 5D 00 00 00 00 00
4. Mode=5:          57 00 00 05 00 00 00 00
5. Prepare:         31 00 94 00 00 00 00 00
6. Prepare:         31 00 94 00 00 00 00 00
7. Speed select:    31 01 63 00 00 00 00 00
8. Speed=0x28:      57 00 00 28 00 00 00 00     (40 = moderate speed)
9. Prepare:         31 00 94 00 00 00 00 00
10. Prepare:        31 00 94 00 00 00 00 00
11. Motor select:   31 00 80 00 00 00 00 00
12. Motor enable:   57 00 00 01 00 00 00 00
13. Prepare:        31 00 94 00 00 00 00 00
14. Prepare:        31 00 94 00 00 00 00 00
15. Dir select:     31 01 61 00 00 00 00 00
16. Dir=forward:    57 00 00 01 00 00 00 00
17. Prepare:        31 00 94 00 00 00 00 00
18. Commit:         44 00 00 00 00 00 00 00
```

### Minimum Working Sequence

Through systematic minimization (combo_test.py, sequence_minimizer.py),
the minimum commands needed for motor movement are:

1. Mode select + Mode=5 (unlock)
2. Speed select + Speed value
3. Motor enable select + Enable=1
4. Direction select + Direction=1
5. Commit

The prepare commands (0x31 0x00 0x94) are optional padding/NOPs.

### Return to Home (~100%)

```
Dir=0 (reverse), Motor=0 (disable), Dir=1 (trigger return), Commit
```
Then lock with Mode=2 and Commit.

### Speed Register (0x0163) Values

| Value | Behavior |
|-------|----------|
| 0x00 | No movement |
| 0x05-0x10 | Very slow |
| 0x20-0x28 | Moderate speed |
| 0x40+ | Fast |
| 0xFF | Maximum speed |

This register controls motor **speed**, not position. The actuator drives
in the selected direction at the given speed until stopped.

## Position Feedback (0x658)

The actuator continuously broadcasts position data on 0x658:

```
Byte:  [0]     [1]   [2:3]        [4]   [5]     [6:7]
Field: status  ???   raw_position  ???   temp    motor_load
Size:  1       1     2 (BE)        1     1       2 (BE)
```

### Position Conversion

```python
RAW_0_PERCENT = 918    # Fully retracted
RAW_100_PERCENT = 174  # Fully extended
percent = (raw - 918) / (174 - 918) * 100.0
```

**Note**: raw=1023 is a sensor artifact (register read glitch), not a valid position.

## EEPROM Map (128 bytes, on-chip L9805E)

### Structure

The 128-byte EEPROM has a partial mirror: bytes 0x00-0x3F are partially
duplicated at 0x40-0x7F. Key registers exist in both halves.

### Known Registers

| Addr | Mirror | Description | Values |
|------|--------|-------------|--------|
| 0x03-0x04 | | Min position (16-bit) | Calibration endpoint |
| 0x05-0x06 | | Max position (16-bit) | Calibration endpoint |
| 0x09-0x0A | | Command CAN ID | Encoded (default: 0x3E8) |
| 0x0B-0x0C | | Unknown CAN ID | Encoded (decodes to 0x670) |
| 0x0F-0x1F | | Actuator-managed data | Write-protected, changes during motor ops |
| 0x22 | 0x62 | Range calibration | 0xBA=typical, 0x00=uncalibrated |
| 0x27-0x28 | | Feedback CAN ID | Encoded, swapped (default: 0x658) |
| 0x29 | 0x69 | Mode/config register | See below |

### Mode Register (0x29) Bit Map

| Bit | Mask | Description |
|-----|------|-------------|
| 4 | 0x10 | PWM-from-CAN mode (0=PWM input, 1=CAN position control) |
| 6 | 0x40 | CAN TX enable |

- **0x62** = PWM mode (original/default)
- **0x72** = CAN mode (bit 4 set)

### CAN Mode Behavior

When bit 4 of register 0x29 is set (CAN mode):
- Motor register writes are **disabled** (raw=1023 artifact, motor_load=0)
- EEPROM reads via 0x31 0x0C are **blocked** (no 0x3E8 response)
- Init (0x49) still works and gets 0x3EB ready response
- Position broadcast on 0x658 continues normally
- Blind EEPROM writes still work (write without read verification)
- Wiki-documented position steering IDs (0x4EA, 0x660) do **NOT** work
- Full sweep of all 2048 CAN IDs found **NO** position steering ID

## Tools

| Script | Purpose |
|--------|---------|
| `hella_prog.py` | Original programming tool (read EEPROM, set min/max/range) |
| `eeprom_restore.py` | Dump, compare, and restore EEPROM to backup |
| `eeprom_write_test.py` | Test write-enable codes for specific addresses |
| `can_position_control.py` | CAN position command scanner (test candidate IDs) |
| `full_id_sweep.py` | Full 2048 CAN ID sweep for position control |
| `deep_probe.py` | Deep probe of registers and alternative protocols |
| `combo_test.py` | Systematic command combination testing |
| `sequence_minimizer.py` | Find minimum viable motor control sequence |
| `register_fuzzer.py` | Register address space fuzzing |
| `position_fuzzer.py` | Position control value fuzzing |
| `can_fuzzer.py` | General CAN fuzzer |

## Prerequisites

```bash
pip install python-can
# For SocketCAN:
sudo ip link set can0 up type can bitrate 500000
# For SLCAN:
# Use channel='/dev/ttyACM0', interface='slcan'
```
