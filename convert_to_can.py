#!/usr/bin/python3
"""
Convert Hella G-222 actuator from PWM mode to CAN position control mode.

This script:
1. Reads the current EEPROM and saves a backup
2. Finds physical endstops using register-level motor drive
3. Calculates rotation offset (0x22) by sweeping values
4. Writes all required EEPROM changes
5. Verifies all writes
6. Tests position control

Usage:
  python3 convert_to_can.py <channel> <interface>

Example:
  python3 convert_to_can.py can0 socketcan
"""

import can
import time
import sys
import os

# G-222 programming CAN IDs
TX_ID = 0x3F0
RESP_ID = 0x3E8
READY_ID = 0x3EB
RAW_POS_ID = 0x3EA

# Target CAN IDs for position control
CMD_CAN_ID = 0x4EA
BROADCAST_CAN_ID = 0x4EB

# Encode CAN ID into EEPROM format: high_byte * 8 + (low_byte >> 5)
# Lower 5 bits of low byte control frame config (0x08 = 8 byte DLC)
def encode_can_id(can_id, dlc_bits=0x08):
    hi = can_id >> 3
    lo = ((can_id & 0x07) << 5) | (dlc_bits & 0x1F)
    return hi, lo

# Mode register values
MODE_PWM = 0x62
MODE_CAN = 0x2A


def send(bus, data):
    bus.send(can.Message(
        is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data)
    ))


def drain(bus, duration=0.3):
    deadline = time.time() + duration
    while time.time() < deadline:
        bus.recv(timeout=0.1)


def wait_ready(bus, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == READY_ID and msg.data[7] == 0x53:
            return True
    return False


def init_and_ready(bus):
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    return wait_ready(bus)


def read_byte(bus, addr):
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == READY_ID and msg.data[7] == 0x53:
            break
    send(bus, [0x31, 0x0C, addr, 0, 0, 0, 0, 0])
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == RESP_ID:
            return msg.data[0]
    return None


def write_byte(bus, addr, value):
    write_enable = 0x2D if addr < 0x20 else 0x8D
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
    drain(bus, 0.3)


def read_eeprom_full(bus):
    print("[*] Reading full EEPROM (128 bytes)...")
    if not init_and_ready(bus):
        print("[!] Init failed")
        return None
    data = bytearray(128)
    for addr in range(128):
        val = read_byte(bus, addr)
        if val is not None:
            data[addr] = val
        if addr % 16 == 0:
            sys.stdout.write(f"\r    Reading 0x{addr:02X}...")
            sys.stdout.flush()
    print("\r    Read complete.          ")
    return data


def find_endstop(bus, direction):
    """Drive motor to an endstop and read raw position from 0x3EA.
    direction=1 for one end, direction=2 for the other."""
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)

    if direction == 1:
        drive_cmds = [
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x28, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
        ]
    else:
        drive_cmds = [
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x28, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
            [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
            [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
            [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
        ]

    for cmd in drive_cmds:
        send(bus, cmd)
        time.sleep(0.02)

    print("    Waiting 5 seconds for motor...")
    time.sleep(5)

    # Read position from 0x3EA (second frame has the endstop position)
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    positions = []
    deadline = time.time() + 3.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == RAW_POS_ID:
            pos = (msg.data[5] << 8) | msg.data[6]
            positions.append(pos)

    # Return to normal mode
    restore = [
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x02, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
    ]
    for cmd in restore:
        send(bus, cmd)
        time.sleep(0.02)

    # 0x3EA sends two frames: first is starting pos, second is endstop
    if len(positions) >= 2:
        return positions[-1]
    elif positions:
        return positions[0]
    return None


def find_rotation_offset(bus):
    """Sweep 0x22 to find value where cmd=0 gives pos=0."""
    print("[*] Finding rotation offset (0x22)...")
    print("    Sweeping values...")

    best_val = 0xD0
    best_pos = 9999

    # Coarse sweep
    for val in range(0xC0, 0x100, 4):
        write_byte(bus, 0x22, val)
        write_byte(bus, 0x62, val)

        # Command position 0 and read feedback
        start = time.time()
        last_pos = None
        while time.time() - start < 1.5:
            bus.send(can.Message(
                is_extended_id=False, arbitration_id=CMD_CAN_ID,
                data=bytearray([0, 0, 0, 0, 0, 0, 0, 0])
            ))
            msg = bus.recv(timeout=0.015)
            if msg and msg.arbitration_id == BROADCAST_CAN_ID and len(msg.data) >= 4:
                last_pos = (msg.data[2] << 8) | msg.data[3]
            time.sleep(0.005)

        if last_pos is not None and abs(last_pos) < abs(best_pos):
            best_pos = last_pos
            best_val = val
            if last_pos == 0:
                break

    # Fine sweep around best
    if best_pos != 0:
        for val in range(max(0, best_val - 8), min(256, best_val + 8)):
            write_byte(bus, 0x22, val)
            write_byte(bus, 0x62, val)

            start = time.time()
            last_pos = None
            while time.time() - start < 1.5:
                bus.send(can.Message(
                    is_extended_id=False, arbitration_id=CMD_CAN_ID,
                    data=bytearray([0, 0, 0, 0, 0, 0, 0, 0])
                ))
                msg = bus.recv(timeout=0.015)
                if msg and msg.arbitration_id == BROADCAST_CAN_ID and len(msg.data) >= 4:
                    last_pos = (msg.data[2] << 8) | msg.data[3]
                time.sleep(0.005)

            if last_pos is not None and abs(last_pos) < abs(best_pos):
                best_pos = last_pos
                best_val = val
                if last_pos == 0:
                    break

    print(f"    Best: 0x22=0x{best_val:02X}({best_val}) -> cmd=0 gives pos={best_pos}")
    return best_val


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    channel = sys.argv[1]
    interface = sys.argv[2]

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)

    try:
        # Step 1: Verify actuator is responding
        print("=" * 60)
        print("HELLA G-222 CAN CONVERSION")
        print("=" * 60)
        print()
        print("[*] Step 1: Checking actuator...")

        # Check for broadcast
        broadcast_id = None
        deadline = time.time() + 2.0
        while time.time() < deadline:
            msg = bus.recv(timeout=0.5)
            if msg and msg.arbitration_id in (0x658, 0x4EB):
                broadcast_id = msg.arbitration_id
                break

        if broadcast_id is None:
            print("[!] No broadcast detected. Is the actuator powered and connected?")
            return

        print(f"    Broadcasting on 0x{broadcast_id:03X}")

        # Check init
        if not init_and_ready(bus):
            print("[!] Init failed — no ready response on 0x3EB")
            return
        print("    Init OK")

        # Step 2: Backup current EEPROM
        print()
        print("[*] Step 2: Backing up current EEPROM...")
        original = read_eeprom_full(bus)
        if original is None:
            print("[!] EEPROM read failed")
            return

        backup_file = f"eeprom_backup_{time.strftime('%Y%m%d_%H%M%S')}.bin"
        with open(backup_file, 'wb') as f:
            f.write(original)
        print(f"    Saved to {backup_file}")

        # Check current mode
        current_mode = original[0x29]
        if current_mode == MODE_CAN:
            print(f"    Mode register is already 0x2A (CAN mode)")
            resp = input("    Continue anyway? (y/n): ")
            if resp.lower() != 'y':
                return

        # Step 3: Find physical endstops
        print()
        print("[*] Step 3: Finding physical endstops...")
        print("    Driving to endstop 1...")
        pos1 = find_endstop(bus, 1)
        print(f"    Endstop 1: {pos1}")

        time.sleep(2)

        print("    Driving to endstop 2...")
        pos2 = find_endstop(bus, 2)
        print(f"    Endstop 2: {pos2}")

        if pos1 is None or pos2 is None:
            print("[!] Failed to read endstop positions")
            return

        min_pos = min(pos1, pos2)
        max_pos = max(pos1, pos2)
        print(f"    Range: {min_pos} to {max_pos} = {max_pos - min_pos} counts")

        # Step 4: Write CAN IDs and mode register
        print()
        print("[*] Step 4: Writing CAN configuration...")

        cmd_hi, cmd_lo = encode_can_id(CMD_CAN_ID)
        bcast_hi, bcast_lo = encode_can_id(BROADCAST_CAN_ID)

        # Write everything EXCEPT mode register first, so we can verify
        writes_before_mode = [
            # Min/max positions
            (0x03, (min_pos >> 8) & 0xFF, "Min position high"),
            (0x04, min_pos & 0xFF, "Min position low"),
            (0x05, (max_pos >> 8) & 0xFF, "Max position high"),
            (0x06, max_pos & 0xFF, "Max position low"),
            # Command CAN ID
            (0x24, cmd_hi, f"Command CAN ID high (0x{CMD_CAN_ID:03X})"),
            (0x25, cmd_lo, f"Command CAN ID low"),
            # Broadcast CAN ID
            (0x27, bcast_hi, f"Broadcast CAN ID high (0x{BROADCAST_CAN_ID:03X})"),
            (0x28, bcast_lo, f"Broadcast CAN ID low"),
            # Mirrors (except mode register)
            (0x43, (min_pos >> 8) & 0xFF, "Mirror min high"),
            (0x44, min_pos & 0xFF, "Mirror min low"),
            (0x45, (max_pos >> 8) & 0xFF, "Mirror max high"),
            (0x46, max_pos & 0xFF, "Mirror max low"),
            (0x64, cmd_hi, "Mirror command CAN ID high"),
            (0x65, cmd_lo, "Mirror command CAN ID low"),
            (0x67, bcast_hi, "Mirror broadcast CAN ID high"),
            (0x68, bcast_lo, "Mirror broadcast CAN ID low"),
        ]
        # Mode register written last (changes actuator behavior immediately)
        writes_mode = [
            (0x29, MODE_CAN, "Mode register (CAN mode)"),
            (0x69, MODE_CAN, "Mirror mode register"),
        ]
        writes = writes_before_mode + writes_mode

        # Write pre-mode bytes
        for addr, val, desc in writes_before_mode:
            sys.stdout.write(f"    0x{addr:02X} = 0x{val:02X} ({desc})...")
            sys.stdout.flush()
            write_byte(bus, addr, val)
            print(" done")

        # Verify pre-mode writes (while actuator is still in original mode)
        print()
        print("[*] Verifying pre-mode writes...")
        time.sleep(1.0)
        all_ok = True
        for addr, expected, desc in writes_before_mode:
            actual = read_byte(bus, addr)
            ok = actual == expected
            if not ok:
                all_ok = False
            actual_str = f"0x{actual:02X}" if actual is not None else "FAIL"
            status = "OK" if ok else "MISMATCH"
            print(f"    0x{addr:02X} = {actual_str} ({status})")

        if not all_ok:
            print("[!] Some writes failed! Restoring original EEPROM...")
            for addr, _, _ in writes_before_mode:
                write_byte(bus, addr, original[addr])
            return

        # Now write mode register (changes behavior immediately)
        print()
        print("[*] Writing mode register...")
        for addr, val, desc in writes_mode:
            sys.stdout.write(f"    0x{addr:02X} = 0x{val:02X} ({desc})...")
            sys.stdout.flush()
            write_byte(bus, addr, val)
            print(" done")

        # Verify mode register
        print("[*] Verifying mode register...")
        for addr, expected, desc in writes_mode:
            actual = read_byte(bus, addr)
            ok = actual == expected
            if not ok:
                all_ok = False
            actual_str = f"0x{actual:02X}" if actual is not None else "FAIL"
            status = "OK" if ok else "MISMATCH"
            print(f"    0x{addr:02X} = {actual_str} ({status})")

        if not all_ok:
            print("[!] Mode register write failed!")
            return

        # Step 5: Find rotation offset
        print()
        print("[*] Step 5: Finding rotation offset...")
        rotation_offset = find_rotation_offset(bus)

        # Write the final rotation offset
        write_byte(bus, 0x22, rotation_offset)
        write_byte(bus, 0x62, rotation_offset)

        # Verify
        actual = read_byte(bus, 0x22)
        if actual != rotation_offset:
            print(f"[!] Rotation offset verify failed: got 0x{actual:02X}")
        else:
            print(f"    0x22 = 0x{rotation_offset:02X} (OK)")

        # Step 6: Test position control
        print()
        print("[*] Step 6: Testing position control...")
        print(f"    Command ID: 0x{CMD_CAN_ID:03X}")
        print(f"    Broadcast ID: 0x{BROADCAST_CAN_ID:03X}")
        print()

        test_ok = True
        for cmd_val in [0, 125, 250, 0]:
            start = time.time()
            last_pos = None
            while time.time() - start < 2.0:
                bus.send(can.Message(
                    is_extended_id=False, arbitration_id=CMD_CAN_ID,
                    data=bytearray([cmd_val, 0, 0, 0, 0, 0, 0, 0])
                ))
                msg = bus.recv(timeout=0.015)
                if msg and msg.arbitration_id == BROADCAST_CAN_ID and len(msg.data) >= 4:
                    last_pos = (msg.data[2] << 8) | msg.data[3]
                time.sleep(0.005)

            expected_approx = cmd_val * 4
            close = abs(last_pos - expected_approx) < 20 if last_pos else False
            status = "OK" if close else "UNEXPECTED"
            if not close:
                test_ok = False
            print(f"    cmd={cmd_val:>3d}  pos={last_pos:>5d}  expected~{expected_approx:>5d}  {status}")

        # Summary
        print()
        print("=" * 60)
        if test_ok:
            print("CONVERSION SUCCESSFUL!")
        else:
            print("CONVERSION COMPLETE (position test had unexpected values)")
        print("=" * 60)
        print()
        print(f"  Command ID:   0x{CMD_CAN_ID:03X}  (byte[0] = 0-250, every <50ms)")
        print(f"  Broadcast ID: 0x{BROADCAST_CAN_ID:03X}  (bytes[2:3] = position)")
        print(f"  Min endstop:  {min_pos}")
        print(f"  Max endstop:  {max_pos}")
        print(f"  Rotation:     0x{rotation_offset:02X} ({rotation_offset})")
        print(f"  Backup:       {backup_file}")
        print()
        print("  Power cycle the actuator for full effect.")
        print()

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
