#!/usr/bin/env python3
"""
Memory Dump Comparison and Bit Analysis Tool

This tool compares multiple memory dumps to identify:
1. Common bytes vs. varying bytes across different actuators
2. Bit patterns and potential bit-field configurations
3. Potential CAN ID calculations using bit manipulation
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

def load_binary_dump(filename: str) -> bytes:
    """Load a binary dump file."""
    try:
        with open(filename, 'rb') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return b''

def analyze_bit_patterns(data: bytes, address: int) -> Dict[str, any]:
    """Analyze bit patterns for a specific byte."""
    if address >= len(data):
        return {}
    
    byte_val = data[address]
    return {
        'value': byte_val,
        'hex': f'0x{byte_val:02X}',
        'binary': f'{byte_val:08b}',
        'bits': {
            'bit_7': (byte_val >> 7) & 1,
            'bit_6': (byte_val >> 6) & 1,
            'bit_5': (byte_val >> 5) & 1,
            'bit_4': (byte_val >> 4) & 1,
            'bit_3': (byte_val >> 3) & 1,
            'bit_2': (byte_val >> 2) & 1,
            'bit_1': (byte_val >> 1) & 1,
            'bit_0': byte_val & 1,
        },
        'nibbles': {
            'high': (byte_val >> 4) & 0xF,
            'low': byte_val & 0xF,
        }
    }

def compare_dumps(dump_files: List[str]) -> None:
    """Compare multiple memory dumps and analyze patterns."""
    
    dumps = {}
    max_size = 0
    
    # Load all dumps
    for filename in dump_files:
        data = load_binary_dump(filename)
        if data:
            dumps[filename] = data
            max_size = max(max_size, len(data))
    
    if not dumps:
        print("No valid dump files found!")
        return
    
    print("=" * 80)
    print("MEMORY DUMP COMPARISON AND BIT ANALYSIS")
    print("=" * 80)
    print(f"Comparing {len(dumps)} dumps, max size: {max_size} bytes")
    print()
    
    # Show loaded dumps
    print("Loaded dumps:")
    for filename, data in dumps.items():
        print(f"  {filename}: {len(data)} bytes")
    print()
    
    # Byte-by-byte comparison
    print("BYTE-BY-BYTE COMPARISON:")
    print("=" * 40)
    
    common_bytes = []
    varying_bytes = []
    
    for addr in range(max_size):
        values = []
        for filename, data in dumps.items():
            if addr < len(data):
                values.append(data[addr])
            else:
                values.append(None)
        
        # Check if all non-None values are the same
        non_none_values = [v for v in values if v is not None]
        if len(set(non_none_values)) == 1:
            common_bytes.append((addr, non_none_values[0]))
        else:
            varying_bytes.append((addr, values))
    
    print(f"Common bytes (same across all dumps): {len(common_bytes)}")
    print(f"Varying bytes (different between dumps): {len(varying_bytes)}")
    print()
    
    # Show common bytes
    if common_bytes:
        print("COMMON BYTES (first 20):")
        for i, (addr, value) in enumerate(common_bytes[:20]):
            bit_analysis = analyze_bit_patterns(bytes([value]), 0)
            print(f"  0x{addr:02X}: {value:02X} ({bit_analysis['binary']}) - likely configuration/firmware constants")
        if len(common_bytes) > 20:
            print(f"  ... and {len(common_bytes) - 20} more")
        print()
    
    # Show varying bytes with detailed analysis
    if varying_bytes:
        print("VARYING BYTES (calibration/ID specific):")
        for addr, values in varying_bytes[:20]:
            print(f"  0x{addr:02X}:")
            for i, (filename, data) in enumerate(dumps.items()):
                if addr < len(data):
                    val = data[addr]
                    bit_analysis = analyze_bit_patterns(data, addr)
                    print(f"    {filename}: {val:02X} ({bit_analysis['binary']}) "
                          f"H:{bit_analysis['nibbles']['high']:X} L:{bit_analysis['nibbles']['low']:X}")
                else:
                    print(f"    {filename}: -- (no data)")
            print()
        if len(varying_bytes) > 20:
            print(f"  ... and {len(varying_bytes) - 20} more")
        print()
    
    # CAN ID bit manipulation analysis
    print("CAN ID BIT MANIPULATION ANALYSIS:")
    print("=" * 40)
    
    # Known interesting addresses from your analysis
    can_id_regions = [
        (0x24, 0x28, "Request/Response CAN ID region"),
        (0x28, 0x30, "Potential message format config"),
        (0x68, 0x70, "Duplicate config block"),
    ]
    
    for start_addr, end_addr, description in can_id_regions:
        print(f"{description} (0x{start_addr:02X}-0x{end_addr-1:02X}):")
        
        for filename, data in dumps.items():
            if end_addr <= len(data):
                region_data = data[start_addr:end_addr]
                hex_str = ' '.join(f'{b:02X}' for b in region_data)
                print(f"  {filename}: {hex_str}")
                
                # Try various CAN ID calculations
                if len(region_data) >= 4:
                    # Standard big-endian 16-bit pairs
                    id1 = (region_data[0] << 8) | region_data[1]
                    id2 = (region_data[2] << 8) | region_data[3]
                    print(f"    16-bit pairs: 0x{id1:04X}, 0x{id2:04X}")
                    
                    # Try bit manipulations that might give 0x658
                    target = 0x658
                    for i in range(len(region_data)-1):
                        val = (region_data[i] << 8) | region_data[i+1]
                        if val == target:
                            print(f"    DIRECT MATCH: bytes {i},{i+1} = 0x{target:03X}")
                        
                        # Try XOR, bit shifts, etc.
                        xor_val = val ^ 0x200
                        if xor_val == target:
                            print(f"    XOR 0x200: 0x{val:04X} ^ 0x200 = 0x{target:03X}")
                        
                        shift_val = val >> 1
                        if shift_val == target:
                            print(f"    SHIFT >>1: 0x{val:04X} >> 1 = 0x{target:03X}")
                            
                        inv_bytes = (region_data[i+1] << 8) | region_data[i]
                        if inv_bytes == target:
                            print(f"    BYTE SWAP: 0x{inv_bytes:03X}")
        print()

def main():
    parser = argparse.ArgumentParser(description='Compare memory dumps and analyze bit patterns')
    parser.add_argument('dumps', nargs='*', help='Memory dump files to compare')
    parser.add_argument('--all', action='store_true', help='Compare all .bin files in current directory')
    
    args = parser.parse_args()
    
    if args.all:
        dump_files = [f for f in os.listdir('.') if f.endswith('.bin') and os.path.getsize(f) > 0]
    else:
        dump_files = args.dumps
    
    if not dump_files:
        print("No dump files specified. Use --all to compare all .bin files, or specify files.")
        print("Example: python3 compare_dumps.py actuator_dump_1750432231.bin other_dump.bin")
        return
    
    compare_dumps(dump_files)

if __name__ == "__main__":
    main()