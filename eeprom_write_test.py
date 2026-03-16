#!/usr/bin/python3
"""
Test different write-enable codes for EEPROM addresses 0x0F-0x1F.
These addresses failed with 0x2D write-enable.
"""

import can
import time
import sys

TX_ID = 0x3F0


def send(bus, data):
    bus.send(can.Message(
        is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data)
    ))


def drain_bus(bus, duration=0.3):
    deadline = time.time() + duration
    while time.time() < deadline:
        bus.recv(timeout=0.1)


def init(bus):
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == 0x3EB and msg.data[7] == 0x53:
            return True
    return False


def read_byte(bus, addr):
    """Read one EEPROM byte (bus must be in ready state)."""
    # Wait for ready
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == 0x3EB and msg.data[7] == 0x53:
            break

    send(bus, [0x31, 0x0C, addr, 0, 0, 0, 0, 0])
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == 0x3E8:
            return msg.data[0]
    return None


def write_byte(bus, addr, value, write_enable):
    """Write one EEPROM byte with specified write-enable code."""
    seq = [
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, write_enable, 0, 0, 0, 0],
        [0x31, 0x0C, addr, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, value, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, write_enable, 0, 0, 0, 0],
        [0x31, 0x0C, addr, 0, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x02, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
    ]

    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)
    for cmd in seq:
        send(bus, cmd)
        time.sleep(0.02)
    time.sleep(0.3)
    drain_bus(bus)


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "can0"
    interface = sys.argv[2] if len(sys.argv) > 2 else "socketcan"

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)

    # Test address: 0x0F (currently 0x02, want 0x0E)
    test_addr = 0x0F
    target_val = 0x0E

    # Write-enable codes to try
    # 0x2D already failed. Try others based on bit pattern analysis.
    codes = [0x0D, 0x2D, 0x4D, 0x6D, 0x8D, 0xAD, 0xCD, 0xED]

    try:
        # First read current value
        if not init(bus):
            print("[!] Init failed")
            return
        cur = read_byte(bus, test_addr)
        print(f"[+] Current 0x{test_addr:02X} = 0x{cur:02X}" if cur is not None
              else f"[!] Read failed")

        if cur == target_val:
            print("[+] Already at target value!")
            return

        for code in codes:
            print(f"\n  Trying write-enable 0x{code:02X}...", flush=True)
            write_byte(bus, test_addr, target_val, code)

            # Read back
            if not init(bus):
                print("    Init failed for verify")
                continue
            val = read_byte(bus, test_addr)
            if val is not None:
                if val == target_val:
                    print(f"    *** SUCCESS! 0x{code:02X} works for addr 0x{test_addr:02X} ***")
                    break
                else:
                    print(f"    Read back 0x{val:02X} (unchanged)")
            else:
                print(f"    Verify read failed")

        else:
            print(f"\n[!] No write-enable code worked for 0x{test_addr:02X}")
            print("    These addresses may be write-protected by the actuator.")

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
