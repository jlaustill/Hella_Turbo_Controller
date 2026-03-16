#!/usr/bin/python3
"""
Build up from the essential mode register pair to find the minimum
working combination for actuator movement.
"""

import can
import time
import sys
import threading
import datetime
import json
import os

TX_ID = 0x3F0
POSITION_ID = 0x658
THRESHOLD = 3.0


def raw_to_pct(raw):
    return round((raw - 918) / (174 - 918) * 100.0, 1)


class Mon:
    def __init__(self, bus):
        self.bus, self.pct, self.raw, self.lock = bus, 0.0, 0, threading.Lock()
        self.updated = False
        self._run = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._run:
            m = self.bus.recv(timeout=0.05)
            if m and m.arbitration_id == POSITION_ID:
                r = (m.data[2] << 8) | m.data[3]
                with self.lock:
                    self.raw, self.pct, self.updated = r, raw_to_pct(r), True

    def get(self):
        with self.lock:
            return self.pct

    def stable(self, n=10):
        vals = []
        for _ in range(n):
            vals.append(self.get())
            time.sleep(0.025)
        return sum(vals) / len(vals)

    def measure(self, dur):
        start, vals = time.time(), []
        while time.time() - start < dur:
            vals.append(self.get())
            time.sleep(0.02)
        return (min(vals), max(vals), vals[-1]) if vals else (0, 0, 0)

    def stop(self):
        self._run = False


def send(bus, data):
    bus.send(can.Message(is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data)))


def send_seq(bus, seq, delay=0.02):
    for d in seq:
        send(bus, d)
        time.sleep(delay)


# Named command fragments
MODE_ENTER = [
    [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],   # select mode register
    [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0], # mode = 5 (calibration?)
]

PREPARE = [[0x31, 0x00, 0x94, 0, 0, 0, 0, 0]]

SPEED_SET = [
    [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x28, 0, 0, 0, 0],
]

MOTOR_ENABLE = [
    [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
]

DIRECTION_FWD = [
    [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
]

COMMIT = [[0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0]]

# Return/stop sequences
RETURN_SEQ = [
    [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
]

STOP_SEQ = [
    [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
    [0x57, 0x00, 0x00, 0x02, 0, 0, 0, 0],
    [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
    [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
]


def go_home(bus, mon):
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.3)
    send_seq(bus, RETURN_SEQ)
    time.sleep(2.0)
    send_seq(bus, STOP_SEQ)
    for _ in range(50):
        if mon.get() > 90:
            break
        time.sleep(0.2)
    time.sleep(1.0)
    return mon.stable()


def test_combo(bus, mon, name, seq):
    """Test a command sequence and report if it caused movement."""
    send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.3)

    pre = mon.stable()
    send_seq(bus, seq)
    lo, hi, post = mon.measure(3.0)
    delta = max(abs(hi - pre), abs(lo - pre))
    moved = delta > THRESHOLD

    status = "*** MOVED ***" if moved else "no movement"
    print(f"  {name:45s}: {pre:6.1f}% -> [{lo:.1f}%, {hi:.1f}%] "
          f"delta={delta:6.1f}%  {status}")

    if moved:
        go_home(bus, mon)

    return moved, delta


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "can0"
    interface = sys.argv[2] if len(sys.argv) > 2 else "socketcan"

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)
    mon = Mon(bus)
    time.sleep(1.0)
    print(f"[+] Position: {mon.get():.1f}%")

    results = {}

    try:
        # Test combinations building up from MODE_ENTER
        combos = [
            ("mode_only",
             MODE_ENTER),

            ("mode + commit",
             MODE_ENTER + COMMIT),

            ("mode + prepare + commit",
             MODE_ENTER + PREPARE + COMMIT),

            ("mode + motor_enable",
             MODE_ENTER + MOTOR_ENABLE),

            ("mode + motor_enable + commit",
             MODE_ENTER + MOTOR_ENABLE + COMMIT),

            ("mode + direction",
             MODE_ENTER + DIRECTION_FWD),

            ("mode + direction + commit",
             MODE_ENTER + DIRECTION_FWD + COMMIT),

            ("mode + motor + direction",
             MODE_ENTER + MOTOR_ENABLE + DIRECTION_FWD),

            ("mode + motor + direction + commit",
             MODE_ENTER + MOTOR_ENABLE + DIRECTION_FWD + COMMIT),

            ("mode + speed",
             MODE_ENTER + SPEED_SET),

            ("mode + speed + commit",
             MODE_ENTER + SPEED_SET + COMMIT),

            ("mode + speed + motor",
             MODE_ENTER + SPEED_SET + MOTOR_ENABLE),

            ("mode + speed + direction",
             MODE_ENTER + SPEED_SET + DIRECTION_FWD),

            ("mode + speed + motor + direction",
             MODE_ENTER + SPEED_SET + MOTOR_ENABLE + DIRECTION_FWD),

            ("mode + speed + motor + direction + commit",
             MODE_ENTER + SPEED_SET + MOTOR_ENABLE + DIRECTION_FWD + COMMIT),

            ("mode + speed + motor + commit",
             MODE_ENTER + SPEED_SET + MOTOR_ENABLE + COMMIT),

            ("mode + speed + direction + commit",
             MODE_ENTER + SPEED_SET + DIRECTION_FWD + COMMIT),

            # Try with prepares between each section (like original)
            ("mode + P + speed + P + motor + P + dir + commit",
             MODE_ENTER + PREPARE + SPEED_SET + PREPARE + MOTOR_ENABLE + PREPARE + DIRECTION_FWD + COMMIT),

            # Try varying mode values
            ("mode=1 + speed + motor + dir + commit",
             [[0x31, 0x01, 0x5D, 0, 0, 0, 0, 0], [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0]]
             + SPEED_SET + MOTOR_ENABLE + DIRECTION_FWD + COMMIT),

            ("mode=3 + speed + motor + dir + commit",
             [[0x31, 0x01, 0x5D, 0, 0, 0, 0, 0], [0x57, 0x00, 0x00, 0x03, 0, 0, 0, 0]]
             + SPEED_SET + MOTOR_ENABLE + DIRECTION_FWD + COMMIT),

            ("mode=4 + speed + motor + dir + commit",
             [[0x31, 0x01, 0x5D, 0, 0, 0, 0, 0], [0x57, 0x00, 0x00, 0x04, 0, 0, 0, 0]]
             + SPEED_SET + MOTOR_ENABLE + DIRECTION_FWD + COMMIT),

            ("mode=6 + speed + motor + dir + commit",
             [[0x31, 0x01, 0x5D, 0, 0, 0, 0, 0], [0x57, 0x00, 0x00, 0x06, 0, 0, 0, 0]]
             + SPEED_SET + MOTOR_ENABLE + DIRECTION_FWD + COMMIT),
        ]

        print(f"\n{'=' * 80}")
        print("COMBINATION TESTS")
        print(f"{'=' * 80}")

        for name, seq in combos:
            moved, delta = test_combo(bus, mon, name, seq)
            results[name] = {"moved": moved, "delta": round(delta, 1), "cmds": len(seq)}

        # Summary
        print(f"\n{'═' * 80}")
        print("WORKING COMBINATIONS:")
        print(f"{'═' * 80}")
        for name, r in results.items():
            if r["moved"]:
                print(f"  [{r['cmds']:2d} cmds] {name}")

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        send(bus, [0x49, 0, 0, 0, 0, 0, 0, 0])
        send_seq(bus, STOP_SEQ)
    finally:
        mon.stop()
        bus.shutdown()

    os.makedirs("fuzz_results", exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    with open(f"fuzz_results/combo_test_{ts}.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Saved: fuzz_results/combo_test_{ts}.json")


if __name__ == "__main__":
    main()
