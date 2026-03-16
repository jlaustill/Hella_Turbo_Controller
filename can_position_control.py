#!/usr/bin/python3
"""
CAN Position Control for Hella Universal Turbo Actuator I

After enabling PWM-from-CAN mode (EEPROM 0x29 bit 4), the actuator
expects position commands via CAN instead of PWM.

This script tests sending position commands on various candidate CAN IDs
and monitors 0x658 for position changes.

Per wiki documentation:
  - Position steering CAN ID: 0x4EA (for G-222 variant)
  - Format: byte[0]=coarse, byte[1]=fine → 10-bit position (0-1023)
  - Must repeat every ~500ms or actuator returns to 0

Usage:
  python3 can_position_control.py <channel> <interface> [mode]

Modes:
  scan       - Try all candidate CAN IDs to find which one works (default)
  control    - Interactive position control on a known working ID
  hold       - Hold a position continuously (for testing)
"""

import can
import time
import sys
import threading
import struct

TX_ID = 0x3F0
POSITION_ID = 0x658
RAW_POS_0PCT = 918
RAW_POS_100PCT = 174
POSITION_THRESHOLD = 3.0


def raw_to_percent(raw):
    pct = (raw - RAW_POS_0PCT) / (RAW_POS_100PCT - RAW_POS_0PCT) * 100.0
    return round(pct, 1)


class PositionMonitor:
    def __init__(self, bus):
        self.bus = bus
        self.raw = 0
        self.pct = 0.0
        self.status = 0
        self.temp = 0
        self.motor_load = 0
        self.last_update = 0
        self.lock = threading.Lock()
        self._running = False

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            msg = self.bus.recv(timeout=0.05)
            if msg and msg.arbitration_id == POSITION_ID:
                raw = (msg.data[2] << 8) | msg.data[3]
                with self.lock:
                    self.raw = raw
                    self.pct = raw_to_percent(raw)
                    self.status = msg.data[0]
                    self.temp = msg.data[5]
                    self.motor_load = (msg.data[6] << 8) | msg.data[7]
                    self.last_update = time.time()

    def get(self):
        with self.lock:
            return self.pct, self.raw

    def get_full(self):
        with self.lock:
            return {
                "pct": self.pct, "raw": self.raw,
                "status": self.status, "temp": self.temp,
                "motor_load": self.motor_load,
            }

    def stable(self, n=10):
        vals = []
        for _ in range(n):
            pct, _ = self.get()
            vals.append(pct)
            time.sleep(0.025)
        return sum(vals) / len(vals)


def send_on_id(bus, arb_id, data):
    """Send a CAN frame on a specific arbitration ID."""
    bus.send(can.Message(
        is_extended_id=False,
        arbitration_id=arb_id,
        data=bytearray(data),
    ))


def encode_position_10bit(position):
    """Encode 10-bit position (0-1023) into 2 bytes [coarse, fine].
    Per wiki: byte[0] = coarse (high 8 bits), byte[1] = fine (low 2 bits shifted)."""
    pos = max(0, min(1023, position))
    coarse = (pos >> 2) & 0xFF
    fine = (pos & 0x03) << 6
    return [coarse, fine]


def encode_position_16bit(position):
    """Encode 16-bit position as big-endian 2 bytes."""
    pos = max(0, min(65535, position))
    return [(pos >> 8) & 0xFF, pos & 0xFF]


def scan_can_ids(bus, mon):
    """Try sending position commands on various CAN IDs and watch for movement."""
    print("\n" + "=" * 70)
    print("CAN ID SCAN - Finding the position steering ID")
    print("=" * 70)

    # Candidate CAN IDs to try:
    # 0x4EA  - Wiki documented position steering ID for G-222
    # 0x3E8  - EEPROM cmd CAN ID (also read response ID)
    # 0x3F0  - Known TX/programming ID
    # 0x4E8  - Nearby IDs in Hella range
    # 0x4EB  - Other Hella range IDs
    # Also try IDs derived from EEPROM bytes that might encode steering ID
    candidates = [
        (0x4EA, "Wiki G-222 position steering"),
        (0x3E8, "EEPROM cmd CAN ID"),
        (0x3F0, "Known programming TX ID"),
        (0x4E8, "Hella range nearby"),
        (0x4EB, "Hella range nearby"),
        (0x4EC, "Hella range nearby"),
        (0x7D0, "Common diagnostic ID"),
        (0x600, "Common control range"),
        (0x601, "Common control range"),
    ]

    # Also try the EEPROM-encoded CAN IDs
    # EEPROM 0x09-0x0A = 0x7D 0x08 → CAN ID = 0x7D*8 + (0x08>>5) = 0x3E8
    # EEPROM 0x27-0x28 = 0x08 0xCB → CAN ID = 0x08*8 + (0xCB>>5) = 0x46
    # That seems wrong... let me try other encodings
    # Maybe 0x27-0x28 encodes the response/steering ID differently
    # 0x0CB = 203, 0x08CB = 2251... try 0xCB*8 + (0x08>>5) = 0x658! That's the position broadcast.
    # So bytes are swapped: 0x28=0xCB first, 0x27=0x08 second
    # For cmd: 0x0A=0x08, 0x09=0x7D → 0x08*8 + (0x7D>>5) = 0x43? No...
    # Original: 0x7D*8 + (0x08>>5) = 0x3E8. OK that's confirmed.
    # So steering ID might be at a different EEPROM offset entirely.

    # Position encodings to try per CAN ID
    # We'll send a ~50% position command
    encodings = [
        ("10bit-512", encode_position_10bit(512) + [0, 0, 0, 0, 0, 0]),
        ("10bit-512 alt", [0x00] + encode_position_10bit(512) + [0, 0, 0, 0, 0]),
        ("16bit-512", encode_position_16bit(512) + [0, 0, 0, 0, 0, 0]),
        ("byte-128", [128, 0, 0, 0, 0, 0, 0, 0]),
        ("byte-50pct", [0x32, 0, 0, 0, 0, 0, 0, 0]),
    ]

    baseline = mon.stable()
    print(f"\n[+] Baseline position: {baseline:.1f}%\n")

    found_ids = []

    for can_id, desc in candidates:
        print(f"\n--- Testing CAN ID 0x{can_id:03X} ({desc}) ---")

        for enc_name, data in encodings:
            pre = mon.stable(5)

            # Send the position command repeatedly for 2 seconds
            print(f"  [{enc_name:15s}] Sending on 0x{can_id:03X}: "
                  f"{' '.join(f'{b:02X}' for b in data[:8])}", end="", flush=True)

            start = time.time()
            while time.time() - start < 2.0:
                send_on_id(bus, can_id, data[:8])
                time.sleep(0.1)  # ~10 Hz, well above 2 Hz minimum

            post = mon.stable(5)
            delta = abs(post - pre)
            state = mon.get_full()

            if delta > POSITION_THRESHOLD:
                print(f"  *** MOVED! {pre:.1f}% -> {post:.1f}% "
                      f"(delta={delta:.1f}%, load={state['motor_load']}) ***")
                found_ids.append((can_id, enc_name, delta))
                # Wait for return to baseline
                time.sleep(3.0)
            else:
                print(f"  no movement (pos={post:.1f}%, load={state['motor_load']})")

            time.sleep(0.5)

    # Summary
    print(f"\n{'═' * 70}")
    print("SCAN RESULTS")
    print(f"{'═' * 70}")
    if found_ids:
        print("CAN IDs that caused movement:")
        for can_id, enc, delta in found_ids:
            print(f"  0x{can_id:03X} [{enc}]: delta={delta:.1f}%")
    else:
        print("No movement detected on any candidate CAN ID.")
        print("\nPossible reasons:")
        print("  1. Position steering ID is not in our candidate list")
        print("  2. Message format is different than expected")
        print("  3. Actuator needs initialization before accepting position commands")
        print("  4. The mode bit enables a different CAN control mechanism")
        print("\nNext steps to try:")
        print("  - Sweep all 11-bit CAN IDs (0x000-0x7FF)")
        print("  - Try sending init (0x49) on 0x3F0 first, then position commands")
        print("  - Try other EEPROM register combinations")

    return found_ids


def sweep_all_ids(bus, mon):
    """Brute-force sweep all 2048 possible 11-bit CAN IDs."""
    print("\n" + "=" * 70)
    print("FULL CAN ID SWEEP (0x000-0x7FF)")
    print("Sending position command on each ID, watching for movement")
    print("=" * 70)

    # Use simple 50% position command
    data = encode_position_10bit(512) + [0, 0, 0, 0, 0, 0]

    found = []
    baseline = mon.stable()
    print(f"\n[+] Baseline: {baseline:.1f}%\n")

    for can_id in range(0x000, 0x800):
        pre_pct, _ = mon.get()

        # Send 5 frames quickly
        for _ in range(5):
            send_on_id(bus, can_id, data[:8])
            time.sleep(0.02)

        time.sleep(0.3)
        post_pct, _ = mon.get()
        delta = abs(post_pct - pre_pct)

        if delta > POSITION_THRESHOLD:
            print(f"  *** 0x{can_id:03X}: MOVED! {pre_pct:.1f}% -> {post_pct:.1f}% "
                  f"(delta={delta:.1f}%) ***")
            found.append((can_id, delta))
            time.sleep(3.0)  # Let it return
        elif can_id % 128 == 127:
            print(f"  [...] 0x{can_id-127:03X}-0x{can_id:03X}: no movement "
                  f"(pos={post_pct:.1f}%)")

    print(f"\n{'═' * 70}")
    if found:
        print("CAN IDs that caused movement:")
        for cid, d in found:
            print(f"  0x{cid:03X}: delta={d:.1f}%")
    else:
        print("No movement on any CAN ID with 10-bit encoding.")

    return found


def try_with_init(bus, mon):
    """Try sending init on 0x3F0 first, then position commands on candidates."""
    print("\n" + "=" * 70)
    print("INIT + POSITION COMMAND TEST")
    print("Sending 0x49 init first, then trying position commands")
    print("=" * 70)

    # Init the actuator first (wake it up for programming)
    print("\n[*] Sending init (0x49) on 0x3F0...")
    send_on_id(bus, TX_ID, [0x49, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)

    candidates = [0x4EA, 0x3E8, 0x3F0]
    encodings = [
        ("10bit-50%", encode_position_10bit(512) + [0, 0, 0, 0, 0, 0]),
        ("10bit-0%", encode_position_10bit(0) + [0, 0, 0, 0, 0, 0]),
        ("10bit-100%", encode_position_10bit(1023) + [0, 0, 0, 0, 0, 0]),
        ("raw-174", encode_position_16bit(174) + [0, 0, 0, 0, 0, 0]),
        ("raw-918", encode_position_16bit(918) + [0, 0, 0, 0, 0, 0]),
        ("raw-546", encode_position_16bit(546) + [0, 0, 0, 0, 0, 0]),
    ]

    for can_id in candidates:
        print(f"\n--- 0x{can_id:03X} (after init) ---")
        for enc_name, data in encodings:
            # Re-init before each test
            send_on_id(bus, TX_ID, [0x49, 0, 0, 0, 0, 0, 0, 0])
            time.sleep(0.3)

            pre = mon.stable(5)
            start = time.time()
            while time.time() - start < 2.0:
                send_on_id(bus, can_id, data[:8])
                time.sleep(0.1)

            post = mon.stable(5)
            delta = abs(post - pre)

            status = "*** MOVED ***" if delta > POSITION_THRESHOLD else "no movement"
            print(f"  [{enc_name:12s}] {pre:.1f}% -> {post:.1f}% "
                  f"delta={delta:.1f}%  {status}")

            if delta > POSITION_THRESHOLD:
                time.sleep(3.0)

    # Also try: send the full mode=5 unlock sequence, then position commands
    print("\n--- Mode=5 unlock + position commands ---")
    mode_unlock = [
        [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
        [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0],
    ]
    for cmd in mode_unlock:
        send_on_id(bus, TX_ID, cmd)
        time.sleep(0.02)

    for can_id in [0x4EA, 0x3E8]:
        pre = mon.stable(5)
        data = encode_position_10bit(512) + [0, 0, 0, 0, 0, 0]
        start = time.time()
        while time.time() - start < 2.0:
            send_on_id(bus, can_id, data[:8])
            time.sleep(0.1)

        post = mon.stable(5)
        delta = abs(post - pre)
        status = "*** MOVED ***" if delta > POSITION_THRESHOLD else "no movement"
        print(f"  0x{can_id:03X} [10bit-50%] after unlock: {pre:.1f}% -> {post:.1f}% "
              f"delta={delta:.1f}%  {status}")

        if delta > POSITION_THRESHOLD:
            time.sleep(3.0)


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "can0"
    interface = sys.argv[2] if len(sys.argv) > 2 else "socketcan"
    mode = sys.argv[3] if len(sys.argv) > 3 else "scan"

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)
    mon = PositionMonitor(bus)
    mon.start()
    time.sleep(1.0)

    pct, raw = mon.get()
    if mon.last_update == 0:
        print("[!] No position data on 0x658. Is actuator powered?")
        bus.shutdown()
        sys.exit(1)

    state = mon.get_full()
    print(f"[+] Position: {pct:.1f}% (raw={raw})")
    print(f"    Status: 0x{state['status']:02X}, Temp: {state['temp']}, "
          f"Motor load: {state['motor_load']}")

    try:
        if mode == "scan":
            found = scan_can_ids(bus, mon)
            if not found:
                print("\n[*] Trying with init prefix...")
                try_with_init(bus, mon)
        elif mode == "sweep":
            sweep_all_ids(bus, mon)
        elif mode == "init":
            try_with_init(bus, mon)
        else:
            print(f"Unknown mode: {mode}")
            print("Modes: scan, sweep, init")

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
    finally:
        mon.stop()
        bus.shutdown()


if __name__ == "__main__":
    main()
