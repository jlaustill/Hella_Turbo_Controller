#!/usr/bin/python3
"""
EEPROM Restore for Hella Universal Turbo Actuator I

Reads the full 128-byte EEPROM, compares against eeprom_backup.bin,
and writes any differing bytes using the proven write protocol from hella_prog.py.

Usage:
  python3 eeprom_restore.py <channel> <interface> [mode]

Modes:
  dump      - Dump current EEPROM and compare to backup (default)
  restore   - Write differing bytes to match backup
  verify    - Dump and compare only, no writes
"""

import can
import time
import sys
import os

TX_ID = 0x3F0
BACKUP_FILE = os.path.join(os.path.dirname(__file__), "eeprom_backup.bin")


def send(bus, data):
    bus.send(can.Message(
        is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data)
    ))


def drain_bus(bus, duration=0.5):
    """Drain messages from the bus for a fixed duration."""
    deadline = time.time() + duration
    while time.time() < deadline:
        bus.recv(timeout=0.1)


def wait_ready(bus, timeout=2.0):
    """Wait for 0x3EB ready response (byte[7]=0x53='S')."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == 0x3EB and msg.data[7] == 0x53:
            return True
    return False


def init_and_ready(bus):
    """Send init (0x49) and wait for ready state."""
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    return wait_ready(bus)


def read_byte(bus, addr):
    """Read a single EEPROM byte. Bus must be in ready state.

    Follows the exact protocol from hella_prog.py readmemory():
    1. Wait for 0x3EB ready (byte[7]=0x53)
    2. Send 0x31 0x0C addr
    3. Wait for 0x3E8 response, byte[0] = value
    """
    # Send read command
    send(bus, [0x31, 0x0C, addr, 0, 0, 0, 0, 0])

    # Wait for 0x3E8 response
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg is None:
            continue
        if msg.arbitration_id == 0x3E8:
            return msg.data[0]
        # If we get a 0x3EB ready, that's fine - keep waiting for 0x3E8

    return None


def read_eeprom_full(bus):
    """Read full 128-byte EEPROM following hella_prog.py readmemory() protocol."""
    print("[*] Reading full EEPROM (128 bytes)...")

    # Fresh init
    if not init_and_ready(bus):
        print("[!] Init failed - no ready response")
        return None

    data = bytearray(128)
    failures = []

    for addr in range(128):
        # Wait for ready state before each read (like hella_prog.py)
        ready_deadline = time.time() + 2.0
        ready = False
        while time.time() < ready_deadline:
            msg = bus.recv(timeout=0.5)
            if msg and msg.arbitration_id == 0x3EB and msg.data[7] == 0x53:
                ready = True
                break

        if not ready:
            # Try re-init
            if not init_and_ready(bus):
                print(f"  [!] 0x{addr:02X}: no ready state, re-init failed")
                failures.append(addr)
                continue

        val = read_byte(bus, addr)
        if val is not None:
            data[addr] = val
            if addr % 16 == 0:
                sys.stdout.write(f"\r  Reading 0x{addr:02X}...")
                sys.stdout.flush()
        else:
            print(f"\n  [!] 0x{addr:02X}: read failed")
            failures.append(addr)

    print(f"\r  Read complete. {len(failures)} failures.")

    if failures:
        print(f"  Failed addresses: {', '.join(f'0x{a:02X}' for a in failures)}")

    return data, failures


def write_byte_eeprom(bus, addr, value):
    """Write a single EEPROM byte using the proven protocol from hella_prog.py.

    Protocol:
    1. Init (0x49)
    2. Mode=5 (calibration unlock)
    3. Write-enable for the sector
    4. Select EEPROM address and write value
    5. Disable write
    6. Mode=2 (lock)
    7. Commit (0x44)
    """
    # Determine write-enable code based on address sector
    # From hella_prog.py: 0x2D for addresses 0x00-0x1F, 0x8D for 0x20+
    if addr < 0x20:
        write_enable = 0x2D
    else:
        write_enable = 0x8D

    seq = [
        # Prepare + mode=5 unlock
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0],
        # Prepare + write enable
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, write_enable, 0, 0, 0, 0],
        # Select EEPROM address and write value
        [0x31, 0x0C, addr, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, value, 0, 0, 0, 0],
        # Disable write
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
        # Re-select address (read-back / verify trigger)
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, write_enable, 0, 0, 0, 0],
        [0x31, 0x0C, addr, 0, 0, 0, 0, 0],
        # Disable write again
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
        # Mode=2 lock + commit
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x02, 0, 0, 0, 0],
        [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
        [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
    ]

    # Init first
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)

    # Send write sequence
    for cmd in seq:
        send(bus, cmd)
        time.sleep(0.02)

    # Wait for processing
    time.sleep(0.3)
    drain_bus(bus, duration=0.3)


def hexdump(data, start=0):
    """Pretty-print hex dump."""
    for i in range(0, len(data), 16):
        addr = start + i
        hex_str = ' '.join(f'{data[i+j]:02X}' if i+j < len(data) else '  '
                           for j in range(16))
        ascii_str = ''.join(chr(data[i+j]) if 32 <= data[i+j] < 127 else '.'
                            for j in range(16) if i+j < len(data))
        print(f"  {addr:04X}: {hex_str}  {ascii_str}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    channel = sys.argv[1]
    interface = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "dump"

    # Load backup
    if not os.path.exists(BACKUP_FILE):
        print(f"[!] Backup file not found: {BACKUP_FILE}")
        sys.exit(1)

    with open(BACKUP_FILE, 'rb') as f:
        backup = bytearray(f.read())

    if len(backup) != 128:
        print(f"[!] Backup file is {len(backup)} bytes, expected 128")
        sys.exit(1)

    print(f"[+] Loaded backup: {BACKUP_FILE} ({len(backup)} bytes)")

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)

    try:
        # Step 1: Read current EEPROM
        result = read_eeprom_full(bus)
        if result is None:
            print("[!] EEPROM read failed completely")
            return

        current, failures = result

        print("\n[+] Current EEPROM contents:")
        hexdump(current)

        print("\n[+] Original backup contents:")
        hexdump(backup)

        # Compare
        diffs = []
        for i in range(128):
            if i in failures:
                diffs.append((i, None, backup[i], "READ FAILED"))
            elif current[i] != backup[i]:
                diffs.append((i, current[i], backup[i], "DIFFERS"))

        if not diffs:
            print("\n[+] EEPROM matches backup perfectly!")
            return

        print(f"\n[+] {len(diffs)} byte(s) differ from backup:")
        print(f"  {'Addr':>6s}  {'Current':>8s}  {'Backup':>8s}  {'Note'}")
        print(f"  {'─'*6}  {'─'*8}  {'─'*8}  {'─'*12}")
        for addr, cur, bak, note in diffs:
            cur_str = f"0x{cur:02X}" if cur is not None else "FAIL"
            print(f"  0x{addr:02X}    {cur_str:>8s}  0x{bak:02X}      {note}")

        if mode == "verify" or mode == "dump":
            if diffs:
                print(f"\n[*] Run with 'restore' mode to write {len(diffs)} byte(s)")
            return

        if mode == "restore":
            print(f"\n{'=' * 60}")
            print(f"RESTORING {len(diffs)} byte(s) to match backup")
            print(f"{'=' * 60}")

            for idx, (addr, cur, bak, note) in enumerate(diffs):
                cur_str = f"0x{cur:02X}" if cur is not None else "FAIL"
                print(f"  [{idx+1}/{len(diffs)}] Writing 0x{addr:02X}: {cur_str} -> 0x{bak:02X}",
                      flush=True)
                write_byte_eeprom(bus, addr, bak)
                print(f"    Done.", flush=True)

            # Verify by re-reading
            print(f"\n{'=' * 60}")
            print("VERIFICATION - Re-reading EEPROM")
            print(f"{'=' * 60}")

            # Wait a moment for EEPROM to settle
            time.sleep(1.0)

            result2 = read_eeprom_full(bus)
            if result2 is None:
                print("[!] Verification read failed")
                return

            verify, vfailures = result2

            print("\n[+] Post-write EEPROM contents:")
            hexdump(verify)

            # Compare verification against backup
            vdiffs = []
            for i in range(128):
                if i in vfailures:
                    vdiffs.append((i, None, backup[i]))
                elif verify[i] != backup[i]:
                    vdiffs.append((i, verify[i], backup[i]))

            if not vdiffs:
                print("\n[+] SUCCESS! EEPROM now matches backup perfectly!")
            else:
                print(f"\n[!] Still {len(vdiffs)} difference(s) after write:")
                for addr, cur, bak in vdiffs:
                    cur_str = f"0x{cur:02X}" if cur is not None else "FAIL"
                    print(f"  0x{addr:02X}: got {cur_str}, expected 0x{bak:02X}")

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
