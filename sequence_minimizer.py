#!/usr/bin/python3
"""
Sequence Minimizer for Hella Turbo Actuator

Takes the known working 17-command sequence and systematically removes
commands to find the minimum viable set that causes movement.
Then varies the 0x0163 register value to test position control.

Usage:
  python3 sequence_minimizer.py <channel> <interface> [mode]

Modes:
  minimize   - Find minimum command sequence (default)
  position   - Test position control via 0x0163 value
  all        - Both
"""

import can
import time
import sys
import datetime
import json
import os
import threading

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
        self.raw_position = 0
        self.percent = 0.0
        self.lock = threading.Lock()
        self.last_update = 0
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
                    self.raw_position = raw
                    self.percent = raw_to_percent(raw)
                    self.last_update = time.time()

    def get(self):
        with self.lock:
            return self.percent, self.raw_position

    def stable(self, samples=10):
        readings = []
        for _ in range(samples):
            pct, _ = self.get()
            readings.append(pct)
            time.sleep(0.025)
        return sum(readings) / len(readings)

    def wait_and_measure(self, duration):
        start = time.time()
        readings = []
        while time.time() - start < duration:
            pct, _ = self.get()
            readings.append(pct)
            time.sleep(0.02)
        if not readings:
            return 0, 0, 0
        return min(readings), max(readings), readings[-1]


def send(bus, data):
    bus.send(can.Message(is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data)))


def send_seq(bus, seq, delay=0.02):
    for data in seq:
        send(bus, data)
        time.sleep(delay)


def init(bus):
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)


# The full working sequence that drives to 0%
FULL_FORWARD = [
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   #  0: prepare
    [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],   #  1: mode register select
    [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0], #  2: mode = 0x05
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   #  3: prepare
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   #  4: prepare
    [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],   #  5: speed/position register
    [0x57, 0x00, 0x00, 0x28, 0, 0, 0, 0], #  6: value = 0x28 (40)
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   #  7: prepare
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   #  8: prepare
    [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],   #  9: motor enable register
    [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0], # 10: enable = 1
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   # 11: prepare
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   # 12: prepare
    [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],   # 13: direction register
    [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0], # 14: direction = 1
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],   # 15: prepare
    [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0], # 16: commit
]

# The return sequence (drives back to ~100%)
FULL_RETURN = [
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],  # direction = 0
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],  # motor enable = 0
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],  # direction = 1 (return)
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
]

# Cleanup / stop sequence
STOP_SEQUENCE = [
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


def return_to_home(bus, mon):
    """Send return sequence and wait for actuator to reach home."""
    print("  [*] Returning to home position...")
    send_seq(bus, FULL_RETURN)
    time.sleep(2.0)
    send_seq(bus, STOP_SEQUENCE)
    # Wait up to 10s for position to stabilize near home
    for _ in range(50):
        pct, _ = mon.get()
        if pct > 90:
            break
        time.sleep(0.2)
    time.sleep(1.0)
    pct = mon.stable()
    print(f"  [*] Home position: {pct:.1f}%")
    return pct


def minimize_sequence(bus, mon):
    """Remove commands one at a time to find minimum viable set."""
    print("\n" + "=" * 60)
    print("SEQUENCE MINIMIZATION")
    print("Testing which commands can be removed from the 17-cmd sequence")
    print("=" * 60)

    # Label each command for readability
    labels = [
        "prepare_0", "mode_sel", "mode_val=5", "prepare_1", "prepare_2",
        "speed_sel", "speed_val=40", "prepare_3", "prepare_4",
        "motor_sel", "motor_val=1", "prepare_5", "prepare_6",
        "dir_sel", "dir_val=1", "prepare_7", "commit",
    ]

    # First verify the full sequence still works
    print("\n--- Verifying full sequence works ---")
    init(bus)
    pre = mon.stable()
    send_seq(bus, FULL_FORWARD)
    _, _, post = mon.wait_and_measure(3.0)
    delta = abs(post - pre)
    print(f"  Full sequence: {pre:.1f}% -> {post:.1f}% (delta={delta:.1f}%)")

    if delta < POSITION_THRESHOLD:
        print("[!] Full sequence didn't cause movement! Cannot minimize.")
        return

    return_to_home(bus, mon)

    # Try removing each command
    removable = []
    essential = []

    for i in range(len(FULL_FORWARD)):
        init(bus)
        time.sleep(0.3)

        reduced = FULL_FORWARD[:i] + FULL_FORWARD[i+1:]
        pre = mon.stable()

        send_seq(bus, reduced)
        _, _, post = mon.wait_and_measure(3.0)
        delta = abs(post - pre)

        if delta > POSITION_THRESHOLD:
            removable.append(i)
            tag = "REMOVABLE"
            return_to_home(bus, mon)
        else:
            essential.append(i)
            tag = "ESSENTIAL"

        print(f"  [{tag:9s}] Remove cmd {i:2d} ({labels[i]:15s}): "
              f"delta={delta:.1f}%")

    print(f"\n{'─' * 60}")
    print(f"Essential commands ({len(essential)}):")
    for i in essential:
        data_hex = ' '.join(f'{b:02X}' for b in FULL_FORWARD[i])
        print(f"  [{i:2d}] {labels[i]:15s}: {data_hex}")

    print(f"\nRemovable commands ({len(removable)}):")
    for i in removable:
        print(f"  [{i:2d}] {labels[i]}")

    # Build and test the minimal sequence
    minimal = [FULL_FORWARD[i] for i in essential]
    print(f"\n--- Testing minimal sequence ({len(minimal)} cmds) ---")
    init(bus)
    pre = mon.stable()
    send_seq(bus, minimal)
    _, _, post = mon.wait_and_measure(3.0)
    delta = abs(post - pre)
    print(f"  Minimal: {pre:.1f}% -> {post:.1f}% (delta={delta:.1f}%)")

    if delta > POSITION_THRESHOLD:
        print("  *** MINIMAL SEQUENCE WORKS! ***")
        print("\n  Minimal command set:")
        for i, cmd in enumerate(minimal):
            data_hex = ' '.join(f'{b:02X}' for b in cmd)
            print(f"    {i}: {data_hex}")
    else:
        print("  [!] Minimal sequence doesn't work - some removable cmds "
              "are needed in combination")

    return_to_home(bus, mon)

    return {"essential": essential, "removable": removable, "labels": labels}


def test_position_values(bus, mon):
    """Vary the 0x0163 register value (index 6 in sequence) to test position control."""
    print("\n" + "=" * 60)
    print("POSITION CONTROL TEST")
    print("Varying register 0x0163 value (currently 0x28=40)")
    print("Testing if this controls target position or speed")
    print("=" * 60)

    test_values = [0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30,
                   0x40, 0x50, 0x60, 0x80, 0xA0, 0xC0, 0xFF]

    results = {}

    for val in test_values:
        init(bus)
        time.sleep(0.3)

        # Build sequence with modified 0x0163 value
        seq = [cmd[:] for cmd in FULL_FORWARD]  # Deep copy
        seq[6] = [0x57, 0x00, 0x00, val, 0, 0, 0, 0]  # Modify speed/pos value

        pre = mon.stable()
        print(f"\n  0x0163 = 0x{val:02X} ({val:3d}):")
        print(f"    Pre: {pre:.1f}%")

        send_seq(bus, seq)

        # Watch position over 4 seconds to see speed and endpoint
        readings = []
        start = time.time()
        while time.time() - start < 4.0:
            pct, _ = mon.get()
            readings.append((time.time() - start, pct))
            time.sleep(0.05)

        min_pct = min(r[1] for r in readings)
        max_pct = max(r[1] for r in readings)
        final = readings[-1][1]

        # Find approximate time to reach minimum (how fast it moved)
        min_time = next(t for t, p in readings if p == min_pct)

        results[f"0x{val:02X}"] = {
            "value": val,
            "pre_pct": round(pre, 1),
            "min_pct": round(min_pct, 1),
            "final_pct": round(final, 1),
            "time_to_min": round(min_time, 2),
        }

        print(f"    Min: {min_pct:.1f}% (reached at {min_time:.1f}s)")
        print(f"    Final: {final:.1f}%")

        return_to_home(bus, mon)

    # Analyze: does the value control speed or endpoint?
    print(f"\n{'═' * 60}")
    print("ANALYSIS")
    print(f"{'═' * 60}")
    print(f"{'Value':>8s} {'Min%':>8s} {'Time':>8s} {'Final%':>8s}")
    print(f"{'─'*8:>8s} {'─'*8:>8s} {'─'*8:>8s} {'─'*8:>8s}")
    for key, r in results.items():
        print(f"{key:>8s} {r['min_pct']:8.1f} {r['time_to_min']:7.2f}s {r['final_pct']:8.1f}")

    return results


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    channel = sys.argv[1]
    interface = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "minimize"

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)
    print(f"[+] Connected: {interface} on {channel}")

    mon = PositionMonitor(bus)
    mon.start()
    time.sleep(1.0)

    pct, raw = mon.get()
    if mon.last_update == 0:
        print("[!] No position data. Exiting.")
        bus.shutdown()
        sys.exit(1)
    print(f"[+] Position: {pct:.1f}% (raw={raw})")

    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    results = {}

    try:
        if mode in ("all", "minimize"):
            results["minimize"] = minimize_sequence(bus, mon)

        if mode in ("all", "position"):
            results["position"] = test_position_values(bus, mon)

    except KeyboardInterrupt:
        print("\n[!] Interrupted - returning to home")
        init(bus)
        send_seq(bus, STOP_SEQUENCE)

    finally:
        mon.stop()
        bus.shutdown()

    os.makedirs("fuzz_results", exist_ok=True)
    path = f"fuzz_results/fuzz_minimize_{ts}.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n[+] Results saved: {path}")


if __name__ == "__main__":
    main()
