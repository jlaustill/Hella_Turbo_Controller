# Actuator Testing Protocol

## Quick Reference for New Actuator Analysis

### Step 1: Initial Setup
```bash
# 1. Power up actuator and connect CAN interface
# 2. Run the menu system (it will auto-configure CAN interface)
./run_menu.sh

# 3. Monitor CAN traffic to identify actuator's CAN ID (if needed)
candump can0

# 4. Record the CAN ID and message format
# Example: can0  658   [8]  04 00 00 B2 00 19 00 00
```

**Note**: The menu system now automatically:
- Detects available CAN interfaces
- Checks interface status (UP/DOWN, bitrate)
- Configures interfaces with sudo prompts when needed
- No manual `sudo ip link set` commands required!

### Step 2: Memory Dump
```bash
# 4. Run the menu system
./run_menu.sh

# 5. Select "📁 Read memory dump"
# 6. Save with descriptive filename: actuator_[model]_[date].bin
```

### Step 3: Quick Analysis
```bash
# 7. Run automated analysis
python3 analyze_new_actuator.py actuator_[model]_[date].bin [CAN_ID_HEX]

# Example:
python3 analyze_new_actuator.py actuator_g350_20250125.bin 65A
```

### Step 4: Enhanced Visualization
```bash
# 8. Use menu visualization
./run_menu.sh
# Select "📊 View memory dump (visualization)"
# Review the detailed bit manipulation analysis
```

### Step 5: Documentation
```bash
# 9. Update the findings log
# Copy the template from FINDINGS_LOG.md
# Fill in the discovered information
```

## Key Things to Record

### CAN Message Analysis
- [ ] CAN ID (3 digits hex)
- [ ] Message format: `[byte0 byte1 byte2 byte3 byte4 byte5 byte6 byte7]`
- [ ] Position data location (verify if bytes 2-3)
- [ ] Status data location (verify if byte 0)
- [ ] Temperature data location (verify if byte 5)
- [ ] Motor load data location (verify if bytes 6-7)

### Memory Block Analysis
- [ ] Block 0x28-0x2F values
- [ ] Block 0x68-0x6F values (should be identical)
- [ ] CAN ID calculation verification
- [ ] Position configuration (0x03-06)
- [ ] Config bytes (0x29, 0x41)

### Bit Manipulation Test
- [ ] Does `(mem[0x2A] << 8) | (mem[0x2C] << 2) = observed_CAN_ID`?
- [ ] If not, what alternative calculation works?
- [ ] Are there new patterns not seen before?

## Safety Checklist

### Before ANY Memory Modifications:
- [ ] ✅ Memory dump completed and backed up
- [ ] ✅ CAN message format verified with candump  
- [ ] ✅ Bit manipulation pattern confirmed
- [ ] ✅ Compared with at least 2 other actuator dumps
- [ ] ✅ All team members reviewed the plan
- [ ] ❌ NEVER modify without understanding the bit manipulation

### Red Flag Warning Signs:
- ⚠️ Memory block 0x28 differs significantly from known patterns
- ⚠️ CAN ID calculation doesn't follow established pattern
- ⚠️ Message format uses different byte positions
- ⚠️ Duplicate blocks 0x28 and 0x68 are not identical

## File Naming Convention
```
Memory dumps: actuator_[model]_[YYYYMMDD].bin
Examples:
- actuator_g222_20250124.bin  
- actuator_g350_20250125.bin
- actuator_unknown_20250126.bin
```

## Quick Commands Reference
```bash
# CAN interface setup
sudo ip link set can0 up type can bitrate 500000
sudo ip link set can0 down

# Monitor CAN traffic
candump can0

# Memory analysis
python3 analyze_new_actuator.py [file] [can_id]
python3 compare_dumps.py *.bin
python3 analyze_can_id.py

# Menu system
./run_menu.sh
```

## Emergency Procedures

### If Actuator Stops Responding:
1. **DO NOT PANIC** - power cycle the actuator
2. **DO NOT** attempt memory writes without team consultation
3. **Document** exactly what was done before the issue
4. **Check** CAN traffic with candump to see if actuator is still transmitting

### If Modification Goes Wrong:
1. **Power cycle** the actuator immediately
2. **Restore** from backup memory dump if possible
3. **Document** the failure mode in FINDINGS_LOG.md
4. **Share** findings with team to prevent repeat issues

## Contact Information
- **Primary Researcher**: [Your contact info]
- **Backup Team**: [Team contact info]
- **Documentation**: All findings go in FINDINGS_LOG.md

---

**Remember**: The goal is understanding, not modification. Take time to verify patterns across multiple actuators before attempting any changes.