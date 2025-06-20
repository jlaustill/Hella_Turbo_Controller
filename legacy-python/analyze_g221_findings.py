#!/usr/bin/env python3
"""
Analyze G-221 findings based on insider information
"""

def main():
    # Load both dumps
    with open('dumps/6NW-008-412/G-222/20250124_initial_dump.bin', 'rb') as f:
        g222_data = f.read()
    with open('dumps/6NW-008-412/G-221/G-221.bin', 'rb') as f:
        g221_data = f.read()

    print('DEEP CAN ID INVESTIGATION')
    print('=' * 40)
    print()

    # Search for 0x658 in G-222 dump
    target = 0x658
    print(f'Looking for 0x{target:03X} in the G-222 dump...')
    print()

    print('Method 1: Direct 16-bit combinations that equal 0x658:')
    found_any = False
    for i in range(len(g222_data) - 1):
        # Big endian
        be_val = (g222_data[i] << 8) | g222_data[i+1]
        if be_val == target:
            print(f'  Big-endian at 0x{i:02X}-0x{i+1:02X}: 0x{g222_data[i]:02X}{g222_data[i+1]:02X}')
            found_any = True
        
        # Little endian  
        le_val = (g222_data[i+1] << 8) | g222_data[i]
        if le_val == target:
            print(f'  Little-endian at 0x{i:02X}-0x{i+1:02X}: 0x{g222_data[i]:02X}{g222_data[i+1]:02X}')
            found_any = True

    if not found_any:
        print('  No direct 16-bit matches found')
    print()

    # Test insider formula on various address combinations
    print('Method 2: Testing insider formula on various addresses...')
    print('Formula: byte1 * 8 + (byte2 >> 5)')
    print()

    test_addresses = [
        (0x24, 0x25, 'Traditional CAN ID area'),
        (0x27, 0x28, 'Response area from our analysis'),
        (0x28, 0x29, '0x28 block start'),
        (0x29, 0x2A, '0x28 block middle'),
        (0x36, 0x37, 'Insider: Request ID'),
        (0x39, 0x40, 'Insider: Response ID'),
    ]

    for addr1, addr2, desc in test_addresses:
        if addr1 < len(g222_data) and addr2 < len(g222_data):
            byte1 = g222_data[addr1]
            byte2 = g222_data[addr2]
            
            # Test different bit shifts
            for shift in [1, 2, 3, 4, 5]:
                result = byte1 * 8 + (byte2 >> shift)
                if result == target:
                    print(f'✅ MATCH! {desc} (0x{addr1:02X}, 0x{addr2:02X}):')
                    print(f'   {byte1} * 8 + ({byte2} >> {shift}) = {result} (0x{result:03X})')
                    break
            else:
                # No match, show original formula result
                result = byte1 * 8 + (byte2 >> 5)
                print(f'{desc} (0x{addr1:02X}, 0x{addr2:02X}): 0x{byte1:02X}, 0x{byte2:02X} → 0x{result:03X}')

    print()

    # Check what G-221 CAN IDs the formula would produce
    print('G-221 CAN ID predictions using insider formula:')
    print('-' * 45)
    
    # Request ID for G-221
    if len(g221_data) > 0x37:
        req_byte1 = g221_data[0x36]
        req_byte2 = g221_data[0x37]
        req_id = req_byte1 * 8 + (req_byte2 >> 5)
        print(f'G-221 Request ID: {req_byte1} * 8 + ({req_byte2} >> 5) = 0x{req_id:03X}')

    # Response ID for G-221  
    if len(g221_data) > 0x40:
        resp_byte1 = g221_data[0x39]
        resp_byte2 = g221_data[0x40]
        resp_id = resp_byte1 * 8 + (resp_byte2 >> 5)
        print(f'G-221 Response ID: {resp_byte1} * 8 + ({resp_byte2} >> 5) = 0x{resp_id:03X}')

    print()
    print('Key Questions to Resolve:')
    print('1. What CAN ID does the G-221 actually transmit on?')
    print('2. Is our G-222 dump from when CAN was disabled?')
    print('3. Are there multiple CAN ID calculation methods?')
    print('4. Does the 0x28 block control message format vs. CAN IDs?')

if __name__ == '__main__':
    main()