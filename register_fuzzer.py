#!/usr/bin/python3
"""
Register-Aware Position Fuzzer for Hella Universal Turbo Actuator I

The actuator uses a register-select-then-write protocol:
  0x31 HI LO  -> select register 0xHILO
  0x57 00 00 VAL -> write VAL to selected register
  0x44 -> commit/save

This fuzzer:
  1. First replays known movement sequences from find_end_positions()
  2. Then sweeps register addresses with value writes, watching position
  3. Tries to find a direct position control register

0x658 frame: byte[2:3]=rawPosition, map(raw, 918, 174, 0, 100)

Usage:
  python3 register_fuzzer.py <channel> <interface> [mode]

Modes:
  replay  - Replay known sequences from hella_prog.py
  regscan - Scan register addresses with writes
  all     - Run everything (default)
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
POSITION_THRESHOLD = 3.0  # % change to count as movement


def raw_to_percent(raw):
    pct = (raw - RAW_POS_0PCT) / (RAW_POS_100PCT - RAW_POS_0PCT) * 100.0
    return round(pct, 1)


class PositionMonitor:
    def __init__(self, bus):
        self.bus = bus
        self.raw_position = 0
        self.percent = 0.0
        self.status = 0
        self.temp = 0
        self.motor_load = 0
        self.last_update = 0
        self.lock = threading.Lock()
        self._running = False
        self._thread = None
        # Stash non-0x658 messages for the main thread
        self.rx_queue = []

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _read_loop(self):
        while self._running:
            msg = self.bus.recv(timeout=0.05)
            if msg is None:
                continue
            if msg.arbitration_id == POSITION_ID:
                raw = (msg.data[2] << 8) | msg.data[3]
                with self.lock:
                    self.raw_position = raw
                    self.percent = raw_to_percent(raw)
                    self.status = msg.data[0]
                    self.temp = msg.data[5]
                    self.motor_load = (msg.data[6] << 8) | msg.data[7]
                    self.last_update = time.time()
            else:
                with self.lock:
                    self.rx_queue.append({
                        "arb_id": hex(msg.arbitration_id),
                        "data": [f"0x{b:02X}" for b in msg.data],
                        "time": time.time(),
                    })
                    if len(self.rx_queue) > 200:
                        self.rx_queue = self.rx_queue[-200:]

    def get_position(self):
        with self.lock:
            return self.percent, self.raw_position

    def pop_rx(self):
        """Get and clear non-position CAN responses."""
        with self.lock:
            msgs = list(self.rx_queue)
            self.rx_queue.clear()
            return msgs

    def wait_and_measure(self, duration):
        start = time.time()
        readings = []
        while time.time() - start < duration:
            pct, _ = self.get_position()
            readings.append(pct)
            time.sleep(0.02)
        if not readings:
            return 0, 0, 0
        return min(readings), max(readings), readings[-1]

    def get_stable_position(self, samples=20):
        readings = []
        for _ in range(samples):
            pct, _ = self.get_position()
            readings.append(pct)
            time.sleep(0.025)
        return sum(readings) / len(readings)


class RegisterFuzzer:
    def __init__(self, channel, interface):
        self.channel = channel
        self.interface_name = interface
        self.bus = None
        self.monitor = None
        self.results = {}
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.log_dir = "fuzz_results"
        os.makedirs(self.log_dir, exist_ok=True)

    def connect(self):
        kwargs = {"channel": self.channel, "interface": self.interface_name, "bitrate": 500000}
        if self.interface_name == "slcan":
            kwargs["ttyBaudrate"] = 128000
        self.bus = can.interface.Bus(**kwargs)
        print(f"[+] Connected: {self.interface_name} on {self.channel} @ 500kbit/s")

    def disconnect(self):
        if self.monitor:
            self.monitor.stop()
        if self.bus:
            self.bus.shutdown()
            print("[+] Disconnected")

    def send(self, data):
        msg = can.Message(is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data))
        self.bus.send(msg)

    def send_sequence(self, seq, delay=0.02):
        """Send a list of CAN payloads with delay between each."""
        for data in seq:
            self.send(data)
            time.sleep(delay)

    def send_register_write(self, reg_hi, reg_lo, value):
        """Select register and write value: 0x31 HI LO -> 0x57 00 00 VAL."""
        self.send([0x31, reg_hi, reg_lo, 0x00, 0x00, 0x00, 0x00, 0x00])
        time.sleep(0.02)
        self.send([0x57, 0x00, 0x00, value, 0x00, 0x00, 0x00, 0x00])
        time.sleep(0.02)

    def start_monitoring(self):
        self.monitor = PositionMonitor(self.bus)
        self.monitor.start()
        time.sleep(1.0)
        pct, raw = self.monitor.get_position()
        if self.monitor.last_update > 0:
            print(f"[+] Position: {pct}% (raw={raw})")
            return True
        print("[!] No 0x658 frames - is actuator powered?")
        return False

    def init_actuator(self):
        self.send([0x49, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        time.sleep(0.5)
        self.monitor.pop_rx()  # Clear response queue

    # ------------------------------------------------------------------
    # Mode 1: Replay known sequences that should cause movement
    # ------------------------------------------------------------------
    def replay_known_sequences(self):
        """Replay command sequences from hella_prog.py find_end_positions()."""
        print("\n" + "=" * 60)
        print("REPLAY: Known command sequences from hella_prog.py")
        print("=" * 60)

        # Sequences extracted from find_end_positions()
        named_sequences = {
            "find_end_positions_phase1": [
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
            ],
            "find_end_positions_phase2_reverse": [
                [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
                [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
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
            ],
            "find_end_positions_phase3_cleanup": [
                [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
                [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
                [0x57, 0x00, 0x00, 0x00, 0, 0, 0, 0],
                [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
                [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
                [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
                [0x57, 0x00, 0x00, 0x02, 0, 0, 0, 0],
                [0x31, 0x00, 0x94, 0, 0, 0, 0, 0],
                [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0],
            ],
            # Minimal test: just the motor enable + direction bits
            "minimal_motor_enable": [
                [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
                [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
            ],
            "minimal_motor_direction": [
                [0x31, 0x01, 0x61, 0, 0, 0, 0, 0],
                [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
            ],
            # Try register 0x0163 with different values (speed/position?)
            "reg_0163_val40": [
                [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
                [0x57, 0x00, 0x00, 0x40, 0, 0, 0, 0],
            ],
        }

        results = {}
        for name, seq in named_sequences.items():
            self.init_actuator()
            pre_pct = self.monitor.get_stable_position()
            self.monitor.pop_rx()

            print(f"\n--- {name} ({len(seq)} cmds) ---")
            print(f"  Pre-position: {pre_pct:.1f}%")

            self.send_sequence(seq)

            # Watch for movement
            min_pct, max_pct, post_pct = self.monitor.wait_and_measure(3.0)
            delta = max(abs(max_pct - pre_pct), abs(min_pct - pre_pct))
            rx_msgs = self.monitor.pop_rx()

            results[name] = {
                "pre_pct": round(pre_pct, 1),
                "post_pct": round(post_pct, 1),
                "min_pct": round(min_pct, 1),
                "max_pct": round(max_pct, 1),
                "delta": round(delta, 1),
                "moved": delta > POSITION_THRESHOLD,
                "can_responses": rx_msgs[:10],
            }

            if delta > POSITION_THRESHOLD:
                print(f"  *** MOVED! {pre_pct:.1f}% -> [{min_pct:.1f}%, {max_pct:.1f}%] "
                      f"settled {post_pct:.1f}% ***")
            else:
                print(f"  No movement (delta={delta:.1f}%)")

            if rx_msgs:
                print(f"  CAN responses: {len(rx_msgs)}")
                for r in rx_msgs[:3]:
                    print(f"    {r['arb_id']}: {' '.join(r['data'])}")

            # Let actuator settle
            time.sleep(2.0)

        self.results["replay"] = results
        self._save_results("replay")
        return results

    # ------------------------------------------------------------------
    # Mode 2: Scan register addresses
    # ------------------------------------------------------------------
    def register_scan(self):
        """Scan register addresses, writing test values, watching position."""
        print("\n" + "=" * 60)
        print("REGISTER SCAN: Probing register addresses")
        print("Writing value 0x01 to each, then 0x80, watching for movement")
        print("=" * 60)

        # Known registers from hella_prog.py:
        # 0x0003-0x0006 = min/max position config (via 0x31 0x0C sub-cmd)
        # 0x0080 = motor enable?
        # 0x0094 = status/prepare?
        # 0x015D = mode selection
        # 0x0161 = direction control?
        # 0x0163 = speed/position?

        # Scan a focused range around known registers, plus broader sweep
        scan_ranges = [
            ("known_area_00xx", [(0x00, b) for b in range(256)]),
            ("known_area_01xx", [(0x01, b) for b in range(256)]),
        ]

        all_results = {}
        for range_name, addresses in scan_ranges:
            print(f"\n--- Scanning {range_name} ---")
            range_results = {}

            self.init_actuator()

            for reg_hi, reg_lo in addresses:
                pre_pct = self.monitor.get_stable_position(samples=5)

                # Prepare (like the real code does)
                self.send([0x31, 0x00, 0x94, 0, 0, 0, 0, 0])
                time.sleep(0.02)

                # Select register and write 0x01
                self.send_register_write(reg_hi, reg_lo, 0x01)

                # Commit
                self.send([0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0])
                time.sleep(0.02)

                # Check for movement
                min_pct, max_pct, post_pct = self.monitor.wait_and_measure(1.0)
                delta = max(abs(max_pct - pre_pct), abs(min_pct - pre_pct))

                if delta > POSITION_THRESHOLD:
                    range_results[f"0x{reg_hi:02X}{reg_lo:02X}"] = {
                        "value_written": "0x01",
                        "pre_pct": round(pre_pct, 1),
                        "post_pct": round(post_pct, 1),
                        "delta": round(delta, 1),
                    }
                    print(f"  *** REG 0x{reg_hi:02X}{reg_lo:02X} = 0x01: MOVED! "
                          f"{pre_pct:.1f}% -> {post_pct:.1f}% (delta={delta:.1f}%) ***")

                    # Undo: write 0x00 to same register
                    self.send_register_write(reg_hi, reg_lo, 0x00)
                    self.send([0x44, 0, 0, 0, 0, 0, 0, 0])
                    time.sleep(3.0)
                else:
                    if reg_lo % 32 == 31:
                        print(f"  [...] 0x{reg_hi:02X}{reg_lo-31:02X}-"
                              f"0x{reg_hi:02X}{reg_lo:02X}: no movement")

                time.sleep(0.05)

                # Re-init every 64 registers
                if reg_lo % 64 == 63:
                    self.init_actuator()

            all_results[range_name] = range_results

        self.results["register_scan"] = all_results
        self._save_results("register_scan")
        return all_results

    # ------------------------------------------------------------------
    # Mode 3: Try direct position commands (if we find the right register)
    # ------------------------------------------------------------------
    def try_position_control(self, reg_hi, reg_lo):
        """Try writing different values to a register to see if it controls position."""
        print(f"\n{'=' * 60}")
        print(f"POSITION CONTROL TEST: Register 0x{reg_hi:02X}{reg_lo:02X}")
        print(f"Writing values 0x00 through 0xFF, watching position")
        print(f"{'=' * 60}")

        results = {}
        test_values = list(range(0, 256, 8))  # Step by 8 for speed

        self.init_actuator()

        for val in test_values:
            pre_pct = self.monitor.get_stable_position(samples=5)

            # Prepare + write + commit
            self.send([0x31, 0x00, 0x94, 0, 0, 0, 0, 0])
            time.sleep(0.02)
            self.send_register_write(reg_hi, reg_lo, val)
            self.send([0x44, 0, 0, 0, 0, 0, 0, 0])

            min_pct, max_pct, post_pct = self.monitor.wait_and_measure(1.5)
            delta = max(abs(max_pct - pre_pct), abs(min_pct - pre_pct))

            results[f"0x{val:02X}"] = {
                "post_pct": round(post_pct, 1),
                "delta": round(delta, 1),
            }

            moved = "*" if delta > POSITION_THRESHOLD else " "
            print(f"  {moved} val=0x{val:02X} ({val:3d}): pos={post_pct:6.1f}% "
                  f"(delta={delta:.1f}%)")

            time.sleep(0.5)

        self.results[f"posctl_0x{reg_hi:02X}{reg_lo:02X}"] = results
        self._save_results(f"posctl_0x{reg_hi:02X}{reg_lo:02X}")

    def _save_results(self, name):
        path = os.path.join(self.log_dir, f"fuzz_{name}_{self.timestamp}.json")
        with open(path, "w") as f:
            json.dump(self.results.get(name, self.results), f, indent=2, default=str)
        print(f"[+] Results saved: {path}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    channel = sys.argv[1]
    interface = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "all"

    fuzzer = RegisterFuzzer(channel, interface)
    fuzzer.connect()

    try:
        if not fuzzer.start_monitoring():
            fuzzer.disconnect()
            sys.exit(1)

        fuzzer.init_actuator()

        if mode in ("all", "replay"):
            replay_results = fuzzer.replay_known_sequences()

            # If replay found movers, report them
            movers = [k for k, v in replay_results.items() if v["moved"]]
            if movers:
                print(f"\n[+] Sequences that caused movement: {movers}")

        if mode in ("all", "regscan"):
            fuzzer.register_scan()

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        fuzzer._save_results("interrupted")
    finally:
        fuzzer.disconnect()

    print("\n[+] Done. Results in ./fuzz_results/")


if __name__ == "__main__":
    main()
