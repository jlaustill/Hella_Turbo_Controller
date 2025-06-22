# Hella Actuator Memory Analysis

## Overview

This document tracks our reverse engineering progress of the Hella Universal Turbo Actuator I memory layout.

**⚠️ CRITICAL SAFETY NOTE:** Previous assumptions about memory layout were WRONG and led to bricked actuators. This analysis uses a systematic, read-only approach to understand the actual memory structure.

## Current Test Actuator

- **Model**: G-222
- **CAN ID Observed**: 0x658
- **Dump File**: `actuator_dump_1750432231.bin`
- **Date**: 2025-01-24

## Verified CAN Message Format (G-222)

Based on candump analysis and reverse engineering:

| Byte Position | Data Type   | Range/Format                       | Notes                                   |
| ------------- | ----------- | ---------------------------------- | --------------------------------------- |
| 0             | Status      | 0x04 observed                      | Unknown meaning                         |
| 2-3           | Position    | Big endian, 688 (0%) to 212 (100%) | **NOT bytes 5-6 as previously assumed** |
| 5             | Temperature | Celsius                            | 25-26°C observed                        |
| 6-7           | Motor Load  | Big endian                         | 0x0000 observed                         |

**Example Message**: `04 00 00 B2 00 19 00 00`

- Status: 0x04
- Position: 0x00B2 = 178 (mapped to VNT percentage via software)
- Temperature: 0x19 = 25°C
- Motor Load: 0x0000 = 0

## Memory Layout Analysis

### Key Configuration Blocks

#### Block 0x28-0x2F: CAN Message Format Configuration

```
Address: 0x28 0x29 0x2A 0x2B 0x2C 0x2D 0x2E 0x2F
Data:    08   62   A0   96   06   02   1D   09
```

**Analysis**:

- **0x2A (0x06)**: Appears to be high byte of CAN ID (0x6??)
- **0x2C (0x96)**: When bit-shifted `0x96 << 2 = 0x58`, gives low byte of observed CAN ID
- **0x2D (0x02)**: May indicate position data goes in CAN message bytes 2-3
- **0x29 (0x62)**: "Programming CAN ID selector" - affects calculation

#### Block 0x68-0x6F: Duplicate Configuration

Identical to 0x28-0x2F block - likely backup/redundancy.

### CAN ID Calculation Discovery

**Observed CAN ID 0x658 can be constructed from 0x28 block**:

```
Method 1: (0x06 << 8) | (0x08 + 0x50) = 0x658
Method 2: (0x06 << 8) | (0x08 | 0x50) = 0x658
Method 3: (0x06 << 8) | (0x96 << 2) = 0x658   ← Most likely
```

**Key Insight**: CAN ID is **calculated** using bit manipulation, not stored as simple 2-byte value.

### Position Configuration

| Address | Value        | Meaning                   |
| ------- | ------------ | ------------------------- |
| 0x03-04 | 0x0091 (145) | Actuator minimum position |
| 0x05-06 | 0x0328 (808) | Actuator maximum position |
| 0x22    | 0xBF (191)   | Range calculation byte    |

**Note**: These appear to be actuator hardware limits, not VNT vane percentages.

### Other Configuration Bytes

| Address | Value | Meaning                     | Notes                                   |
| ------- | ----- | --------------------------- | --------------------------------------- |
| 0x29    | 0x62  | Programming CAN ID selector | Affects CAN ID calculation              |
| 0x41    | 0x0E  | Interface configuration     | PWM from CAN: No, CAN TX: No, Motor: CW |

## Questions for Additional Actuators

When analyzing additional dumps, focus on these key questions:

### 1. CAN ID Variation

- [ ] What CAN ID does the new actuator transmit on?
- [ ] What are the values at 0x28-0x2F in its memory?
- [ ] Does the bit manipulation formula still work?
  - High byte from 0x2A?
  - Low byte from bit manipulation of 0x2C?

### 2. Message Format Consistency

- [ ] Does the new actuator use the same CAN message format?
  - Position in bytes 2-3?
  - Status in byte 0?
  - Temperature in byte 5?
- [ ] Is the 0x2D value still 0x02 (indicating bytes 2-3 for position)?

### 3. Common vs Variable Bytes

- [ ] Which bytes are identical across actuators (firmware constants)?
- [ ] Which bytes vary (calibration/configuration)?
- [ ] Are the duplicate blocks at 0x28 and 0x68 identical in all actuators?

### 4. Position Calibration

- [ ] Are the min/max position values (0x03-06) different?
- [ ] Does the range byte (0x22) calculation still hold?
- [ ] Are these hardware limits or configurable?

## Analysis Tools

### 1. Memory Dump Comparison

```bash
python3 compare_dumps.py actuator1.bin actuator2.bin actuator3.bin
```

### 2. CAN ID Analysis

```bash
python3 analyze_can_id.py
```

### 3. Enhanced Visualization

Use the menu system: "📊 View memory dump (visualization)"

## Safety Protocol

### Before Any Memory Modifications:

1. ✅ **ALWAYS backup original memory first**
2. ✅ **Verify CAN message format with candump**
3. ✅ **Test bit manipulation theories with read-only analysis**
4. ✅ **Compare with at least 2 other actuator dumps**
5. ❌ **NEVER modify bytes without understanding bit manipulation**

### Dangerous Areas (DO NOT MODIFY without full understanding):

- **0x28-0x2F**: CAN message format configuration
- **0x29**: Programming CAN ID selector
- **0x41**: Interface configuration
- **0x68-0x6F**: Duplicate configuration block

## Next Steps

1. **Acquire additional actuator dumps** for comparison
2. **Verify bit manipulation theories** across different models
3. **Map common vs variable bytes** systematically
4. **Understand the role of config byte 0x29** in CAN ID calculation
5. **Document safe modification procedures** once patterns are confirmed

## File Organization

- `actuator_dump_*.bin` - Memory dumps from different actuators
- `MEMORY_ANALYSIS.md` - This analysis document (keep updated)
- `compare_dumps.py` - Tool for comparing multiple dumps
- `analyze_can_id.py` - Tool for CAN ID bit manipulation analysis
- `FINDINGS_LOG.md` - Chronological log of discoveries
