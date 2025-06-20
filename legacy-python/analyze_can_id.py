#!/usr/bin/env python3
"""
CAN ID Bit Manipulation Analysis

Analyzes how the stored bytes might be manipulated to produce the observed CAN ID
"""

def analyze_can_id():
    stored = 0x0862
    observed = 0x658
    
    print('CAN ID BIT MANIPULATION ANALYSIS')
    print('=' * 50)
    print(f'Stored in memory: 0x{stored:04X} ({stored:016b})')
    print(f'Observed CAN ID:  0x{observed:03X} ({observed:012b})')
    print()
    
    # Simple arithmetic
    diff = stored - observed
    print(f'Difference: {stored} - {observed} = {diff} (0x{diff:X})')
    
    # XOR
    xor_result = stored ^ observed
    print(f'XOR: 0x{stored:04X} ^ 0x{observed:03X} = 0x{xor_result:X}')
    print()
    
    # The key block from memory
    block = [0x08, 0x62, 0xA0, 0x96, 0x06, 0x02, 0x1D, 0x09]
    print('Analyzing the 0x28 block:', ' '.join(f'0x{b:02X}' for b in block))
    print()
    
    # Key observation: 0x658 has 0x6 as high nibble, which appears in the block
    print('Key observations:')
    print(f'- Target CAN ID 0x{observed:03X} has 0x6 as high nibble')
    print(f'- Block contains 0x06 at position 4')
    print(f'- Block contains 0x62 at position 1 (config byte)')
    print()
    
    # Test theory: use 0x06 from position 4 and manipulate other bytes
    print('Theory 1: Use 0x06 from position 4 + manipulated byte')
    base = 0x06
    need_low = observed & 0xFF  # 0x58
    print(f'Need to make 0x{need_low:02X} from available bytes')
    
    for i, byte in enumerate(block):
        if i == 4:  # Skip the 0x06 byte itself
            continue
        # Try various manipulations
        manipulations = [
            (byte, f'direct 0x{byte:02X}'),
            (byte << 1, f'0x{byte:02X} << 1'),
            (byte << 2, f'0x{byte:02X} << 2'),
            (byte << 3, f'0x{byte:02X} << 3'),
            (byte << 4, f'0x{byte:02X} << 4'),
            (byte + 0x50, f'0x{byte:02X} + 0x50'),
            (byte | 0x50, f'0x{byte:02X} | 0x50'),
            (~byte & 0xFF, f'~0x{byte:02X}'),
        ]
        
        for result, desc in manipulations:
            if (result & 0xFF) == need_low:
                combined = (base << 8) | (result & 0xFF)
                if combined == observed:
                    print(f'  MATCH! Position {i}: {desc} = 0x{result & 0xFF:02X}')
                    print(f'         Combined: (0x{base:02X} << 8) | 0x{result & 0xFF:02X} = 0x{combined:03X}')
    
    print()
    print('Theory 2: Use config byte 0x62 with bit manipulation')
    config = 0x62
    print(f'Config byte: 0x{config:02X} = {config:08b}')
    
    # We need to get from 0x62? to 0x658
    # So we need the low part to be 0x58
    target_low = 0x58
    print(f'Need low byte: 0x{target_low:02X} = {target_low:08b}')
    
    # Check if any byte manipulation gives us 0x58
    for i, byte in enumerate(block):
        if byte == target_low:
            print(f'  Direct match: position {i} has 0x{target_low:02X}')
    
    print()
    print('Theory 3: Bit field extraction')
    # Maybe the CAN ID is constructed from bit fields across multiple bytes
    
    # Load the actual memory dump
    try:
        with open('actuator_dump_1750432231.bin', 'rb') as f:
            data = f.read()
        
        print('Searching entire memory for 0x58 byte:')
        for i, byte in enumerate(data):
            if byte == 0x58:
                print(f'  Found 0x58 at offset 0x{i:02X}')
                
        print()
        print('Searching for any 2-byte combination that equals 0x658:')
        found_any = False
        for i in range(len(data) - 1):
            # Big endian
            be_val = (data[i] << 8) | data[i+1]
            if be_val == observed:
                print(f'  Big-endian match at 0x{i:02X}-0x{i+1:02X}: {data[i]:02X} {data[i+1]:02X}')
                found_any = True
            
            # Little endian
            le_val = (data[i+1] << 8) | data[i]
            if le_val == observed:
                print(f'  Little-endian match at 0x{i:02X}-0x{i+1:02X}: {data[i]:02X} {data[i+1]:02X}')
                found_any = True
        
        if not found_any:
            print('  No direct 2-byte combinations found')
            
    except FileNotFoundError:
        print('Could not load memory dump file')

if __name__ == '__main__':
    analyze_can_id()