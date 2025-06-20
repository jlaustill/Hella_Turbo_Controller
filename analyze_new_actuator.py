#!/usr/bin/env python3
"""
New Actuator Analysis Script

Quick analysis script for new actuator dumps to compare against known patterns.
Run this when you get a new actuator to systematically analyze differences.
"""

import sys
import os
from pathlib import Path

def analyze_new_actuator(dump_file, observed_can_id=None):
    """Analyze a new actuator dump against known patterns."""
    
    if not os.path.exists(dump_file):
        print(f"Error: {dump_file} not found")
        return
    
    with open(dump_file, 'rb') as f:
        data = f.read()
    
    if len(data) != 128:
        print(f"Warning: Expected 128 bytes, got {len(data)} bytes")
    
    print("=" * 60)
    print(f"NEW ACTUATOR ANALYSIS: {dump_file}")
    print("=" * 60)
    print()
    
    # Basic info
    print("📋 BASIC INFO:")
    print(f"File size: {len(data)} bytes")
    if observed_can_id:
        print(f"Observed CAN ID: 0x{observed_can_id:03X}")
    print()
    
    # Key configuration blocks
    print("🔍 KEY CONFIGURATION BLOCKS:")
    
    if len(data) >= 0x30:
        block_28 = data[0x28:0x30]
        print(f"Block 0x28-0x2F: {' '.join(f'{b:02X}' for b in block_28)}")
        
        # Extract key bytes for CAN ID calculation
        if len(block_28) >= 8:
            high_byte = block_28[2]  # 0x2A relative to start
            shift_byte = block_28[4]  # 0x2C relative to start
            pos_indicator = block_28[5]  # 0x2D relative to start
            
            print(f"  High byte component (0x2A): 0x{high_byte:02X}")
            print(f"  Shift byte component (0x2C): 0x{shift_byte:02X}")
            print(f"  Position indicator (0x2D): 0x{pos_indicator:02X}")
            
            # Test CAN ID calculation
            calculated_low = (shift_byte << 2) & 0xFF
            calculated_id = (high_byte << 8) | calculated_low
            
            print(f"  Calculated CAN ID: (0x{high_byte:02X} << 8) | (0x{shift_byte:02X} << 2)")
            print(f"                     = (0x{high_byte:02X} << 8) | 0x{calculated_low:02X}")
            print(f"                     = 0x{calculated_id:03X}")
            
            if observed_can_id:
                if calculated_id == observed_can_id:
                    print("  ✅ CALCULATION MATCHES OBSERVED CAN ID!")
                else:
                    print(f"  ❌ Mismatch: calculated 0x{calculated_id:03X} vs observed 0x{observed_can_id:03X}")
                    
                    # Try alternative calculations
                    print("  🔄 Trying alternative calculations:")
                    alt1 = (high_byte << 8) | shift_byte
                    alt2 = (shift_byte << 8) | high_byte
                    alt3 = high_byte | (shift_byte << 4)
                    
                    if alt1 == observed_can_id:
                        print(f"    ✅ Alt 1: (0x{high_byte:02X} << 8) | 0x{shift_byte:02X} = 0x{alt1:03X}")
                    if alt2 == observed_can_id:
                        print(f"    ✅ Alt 2: (0x{shift_byte:02X} << 8) | 0x{high_byte:02X} = 0x{alt2:03X}")
                    if alt3 == observed_can_id:
                        print(f"    ✅ Alt 3: 0x{high_byte:02X} | (0x{shift_byte:02X} << 4) = 0x{alt3:03X}")
            print()
    
    if len(data) >= 0x70:
        block_68 = data[0x68:0x70]
        print(f"Block 0x68-0x6F: {' '.join(f'{b:02X}' for b in block_68)}")
        
        if block_28 == block_68:
            print("  ✅ Identical to 0x28 block (expected redundancy)")
        else:
            print("  ⚠️  Different from 0x28 block - investigate!")
        print()
    
    # Position configuration
    print("📍 POSITION CONFIGURATION:")
    if len(data) > 6:
        min_pos = (data[3] << 8) | data[4]
        max_pos = (data[5] << 8) | data[6]
        print(f"Min position (0x03-04): 0x{min_pos:04X} ({min_pos})")
        print(f"Max position (0x05-06): 0x{max_pos:04X} ({max_pos})")
        
        if max_pos > min_pos:
            range_val = max_pos - min_pos
            print(f"Range: {range_val} positions")
            
            if len(data) > 0x22:
                range_byte = data[0x22]
                expected_range = range_val // 4
                print(f"Range byte (0x22): 0x{range_byte:02X} ({range_byte})")
                print(f"Expected range/4: {expected_range}")
                if abs(range_byte - expected_range) <= 1:
                    print("  ✅ Range byte calculation matches")
                else:
                    print("  ⚠️  Range byte calculation differs")
        print()
    
    # Other key config bytes
    print("⚙️ OTHER CONFIGURATION:")
    if len(data) > 0x29:
        config_29 = data[0x29]
        print(f"Config byte (0x29): 0x{config_29:02X} - Programming CAN ID selector")
    
    if len(data) > 0x41:
        config_41 = data[0x41]
        print(f"Interface config (0x41): 0x{config_41:02X}")
        pwm_from_can = "Yes" if config_41 & 0x10 else "No"
        can_tx_enabled = "Yes" if config_41 & 0x40 else "No"
        motor_dir = "CCW" if config_41 & 0x01 else "CW"
        print(f"  PWM from CAN: {pwm_from_can}, CAN TX: {can_tx_enabled}, Motor: {motor_dir}")
    print()
    
    # Compare with G-222 baseline
    print("🔄 COMPARISON WITH G-222 BASELINE:")
    g222_block_28 = bytes([0x08, 0x62, 0xA0, 0x96, 0x06, 0x02, 0x1D, 0x09])
    
    if len(data) >= 0x30:
        current_block = data[0x28:0x30]
        if current_block == g222_block_28:
            print("  ✅ Block 0x28 identical to G-222")
        else:
            print("  🔍 Block 0x28 differences from G-222:")
            for i, (g222_byte, current_byte) in enumerate(zip(g222_block_28, current_block)):
                if g222_byte != current_byte:
                    addr = 0x28 + i
                    print(f"    0x{addr:02X}: G-222=0x{g222_byte:02X}, This=0x{current_byte:02X}")
    
    print()
    print("📝 ANALYSIS COMPLETE")
    print("Update FINDINGS_LOG.md with these results!")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_new_actuator.py <dump_file> [observed_can_id_hex]")
        print("Example: python3 analyze_new_actuator.py new_actuator.bin 65A")
        return
    
    dump_file = sys.argv[1]
    observed_can_id = None
    
    if len(sys.argv) > 2:
        try:
            observed_can_id = int(sys.argv[2], 16)
        except ValueError:
            print(f"Invalid CAN ID: {sys.argv[2]} (should be hex)")
            return
    
    analyze_new_actuator(dump_file, observed_can_id)

if __name__ == "__main__":
    main()