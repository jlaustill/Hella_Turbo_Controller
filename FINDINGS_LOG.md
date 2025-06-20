# Hella Actuator Reverse Engineering - Findings Log

## Date: 2025-01-24

### Actuator: G-222 (Primary Analysis)
- **Dump File**: `actuator_dump_1750432231.bin`
- **CAN ID Observed**: 0x658
- **Interface**: Candlelight adapter on can0

### Key Discoveries

#### 1. CAN Message Format Correction ⚠️ CRITICAL
**Previous (WRONG) assumptions that led to bricked actuators:**
- Position data in bytes 5-6 of CAN messages
- Hardcoded CAN IDs

**Verified G-222 format:**
```
Byte 0: Status (0x04 observed)
Byte 2-3: Position (big endian) - 688 (0%) to 212 (100%)
Byte 5: Temperature (25-26°C observed)  
Byte 6-7: Motor Load (big endian, 0x0000 observed)
```

**Evidence**: 
- Candump shows: `04 00 00 B2 00 19 00 00`
- Position 0x00B2 = 178 decimal (matches observed actuator movement)
- Temperature 0x19 = 25°C (reasonable)

#### 2. Memory Block 0x28-0x2F: CAN Configuration
```
0x28: 08 62 A0 96 06 02 1D 09
```

**Analysis**:
- Duplicated at 0x68-0x6F (backup/redundancy)
- Contains CAN ID calculation components
- Byte 0x2D = 0x02 may indicate "position at bytes 2-3"

#### 3. CAN ID Bit Manipulation Discovery 🎉
**Problem**: Memory shows 0x0862 but actuator transmits on 0x658

**Solution**: CAN ID is CALCULATED using bit manipulation:
```
Method: (0x06 << 8) | (0x96 << 2) = 0x658
Where:
- 0x06 from memory position 0x2A  
- 0x96 from memory position 0x2C
- Bit shift 0x96 << 2 = 0x58
```

**Verification**:
- 0x96 << 2 = 0x258, masked to 0x58 ✓
- (0x06 << 8) | 0x58 = 0x0600 | 0x58 = 0x658 ✓

#### 4. Configuration Bytes Identified
| Address | Value | Function | Safety |
|---------|-------|----------|--------|
| 0x29 | 0x62 | Programming CAN ID selector | ⚠️ DANGEROUS |
| 0x41 | 0x0E | Interface config (PWM/CAN/Motor) | ⚠️ DANGEROUS |
| 0x2A | 0x06 | CAN ID high byte component | ⚠️ DANGEROUS |
| 0x2C | 0x96 | CAN ID low byte (bit shifted) | ⚠️ DANGEROUS |

### Tools Developed
1. **Enhanced memory visualization** - Shows bit manipulation analysis
2. **compare_dumps.py** - Multi-actuator comparison tool
3. **analyze_can_id.py** - CAN ID bit manipulation analysis
4. **Safety warnings** added to all modification functions

### Critical Safety Insights
- **Byte positions matter**: Wrong assumptions = bricked actuators
- **Bit manipulation used**: Not simple byte storage
- **Configuration blocks**: Multiple bytes work together
- **Redundancy**: Important configs stored in multiple locations

### Next Required Steps
1. **Get 2nd actuator dump** to verify theories
2. **Compare bit manipulation patterns** across different CAN IDs
3. **Map common vs variable bytes** systematically
4. **Test modification safety** only after full understanding

### Questions for Next Actuator
- Does it use same message format (bytes 2-3 for position)?
- What CAN ID does it transmit on?
- What are values at 0x28-0x2F in its memory?
- Does the bit manipulation formula work for its CAN ID?
- Are the duplicate blocks at 0x28 and 0x68 identical?

---

## Template for Future Actuator Analysis

### Actuator: [MODEL] - Date: [DATE]
- **Dump File**: 
- **CAN ID Observed**: 
- **Interface Used**: 

#### CAN Message Analysis
```
candump output:
[paste raw candump data]

Message format verification:
- Byte 0 (Status): 
- Bytes 2-3 (Position): 
- Byte 5 (Temperature): 
- Bytes 6-7 (Motor Load): 
```

#### Memory Block Analysis
```
0x28-0x2F: [hex values]
0x68-0x6F: [hex values]
```

#### CAN ID Calculation Test
```
Expected CAN ID: 0x[???]
Memory 0x2A (high): 0x[??]
Memory 0x2C (shift): 0x[??]
Calculation: (0x[??] << 8) | (0x[??] << 2) = 0x[result]
Match: [YES/NO]
```

#### Differences from G-222
- [List any differences found]
- [Note which bytes vary vs stay same]

#### New Discoveries
- [Any new patterns or insights]