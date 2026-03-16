#!/usr/bin/python3
"""
Position-Aware CAN Fuzzer for Hella Universal Turbo Actuator I

Monitors the actuator's real-time position on 0x658 while probing
opcodes, to identify which CAN command controls actuator position.

The 0x658 frame format:
  byte[0]    = status
  byte[2:3]  = rawPosition (16-bit), 918=0%, 174=100%
  byte[5]    = temperature
  byte[6:7]  = motorLoad (16-bit)

Usage:
  python3 position_fuzzer.py <channel> <interface>

Examples:
  python3 position_fuzzer.py can0 socketcan
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
KNOWN_RX_IDS = {0x3E8, 0x3EA, 0x3EB}

# Position mapping from user's code: map(rawPosition, 918, 174, 0, 100)
RAW_POS_0PCT = 918
RAW_POS_100PCT = 174

INTER_PROBE_DELAY = 0.1    # 100ms between probes
SETTLE_TIME = 1.5           # Wait for actuator to physically move
POSITION_THRESHOLD = 5.0    # % change to count as movement


def raw_to_percent(raw):
    """Convert raw position to percentage (matching user's map function)."""
    if RAW_POS_0PCT == RAW_POS_100PCT:
        return 0.0
    pct = (raw - RAW_POS_0PCT) / (RAW_POS_100PCT - RAW_POS_0PCT) * 100.0
    return round(pct, 1)


class PositionMonitor:
    """Background thread that continuously reads 0x658 position frames."""

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
        # Track position history for movement detection
        self.history = []

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _read_loop(self):
        """Continuously parse 0x658 frames (runs in background thread)."""
        while self._running:
            msg = self.bus.recv(timeout=0.1)
            if msg is None:
                continue
            if msg.arbitration_id != POSITION_ID:
                continue

            raw = (msg.data[2] << 8) | msg.data[3]
            with self.lock:
                self.raw_position = raw
                self.percent = raw_to_percent(raw)
                self.status = msg.data[0]
                self.temp = msg.data[5]
                self.motor_load = (msg.data[6] << 8) | msg.data[7]
                self.last_update = time.time()
                self.history.append((time.time(), self.percent, raw))
                # Keep last 500 samples
                if len(self.history) > 500:
                    self.history = self.history[-500:]

    def get_position(self):
        with self.lock:
            return self.percent, self.raw_position

    def get_full_state(self):
        with self.lock:
            return {
                "percent": self.percent,
                "raw": self.raw_position,
                "status": self.status,
                "temp": self.temp,
                "motor_load": self.motor_load,
            }

    def wait_and_measure(self, duration):
        """Wait for duration, return (min_pct, max_pct, final_pct) during that window."""
        start = time.time()
        readings = []
        while time.time() - start < duration:
            pct, _ = self.get_position()
            readings.append(pct)
            time.sleep(0.02)
        if not readings:
            return 0, 0, 0
        return min(readings), max(readings), readings[-1]


class PositionFuzzer:
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

    def send_raw(self, data):
        """Send a CAN frame (no listening, monitor thread handles RX)."""
        msg = can.Message(is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data))
        self.bus.send(msg)

    def start_monitoring(self):
        """Start the position monitor and verify we're getting data."""
        self.monitor = PositionMonitor(self.bus)
        self.monitor.start()
        print("[*] Position monitor started, waiting for data...")
        time.sleep(1.0)
        pct, raw = self.monitor.get_position()
        if self.monitor.last_update > 0:
            state = self.monitor.get_full_state()
            print(f"[+] Actuator position: {pct}% (raw={raw})")
            print(f"    Status: 0x{state['status']:02X}, "
                  f"Temp: {state['temp']}, "
                  f"Motor load: {state['motor_load']}")
            return True
        else:
            print("[!] No 0x658 frames received - is the actuator powered?")
            return False

    def get_baseline_position(self, samples=20):
        """Read position over a short window to get stable baseline."""
        readings = []
        for _ in range(samples):
            pct, _ = self.monitor.get_position()
            readings.append(pct)
            time.sleep(0.025)
        avg = sum(readings) / len(readings)
        spread = max(readings) - min(readings)
        return avg, spread

    # ------------------------------------------------------------------
    # Main sweep: send each opcode and watch for position changes
    # ------------------------------------------------------------------
    def sweep_for_movement(self):
        """Send each opcode and monitor position for movement."""
        print("\n" + "=" * 60)
        print("POSITION-AWARE OPCODE SWEEP")
        print("Sending each opcode, watching for actuator movement")
        print(f"Movement threshold: {POSITION_THRESHOLD}% change")
        print("=" * 60)

        baseline_pct, baseline_spread = self.get_baseline_position()
        print(f"\n[*] Baseline position: {baseline_pct:.1f}% "
              f"(noise: +/-{baseline_spread:.1f}%)\n")

        movers = {}      # Opcodes that caused movement
        responders = {}   # Opcodes that got non-0x658 CAN responses
        all_results = {}

        for opcode in range(256):
            # Get position before sending
            pre_pct, pre_raw = self.monitor.get_position()

            # Send the probe
            data = [opcode, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            self.send_raw(data)

            # Wait and measure position during settle window
            min_pct, max_pct, post_pct = self.monitor.wait_and_measure(SETTLE_TIME)
            delta = max(abs(max_pct - pre_pct), abs(min_pct - pre_pct))

            result = {
                "opcode": f"0x{opcode:02X}",
                "pre_pct": round(pre_pct, 1),
                "post_pct": round(post_pct, 1),
                "min_pct": round(min_pct, 1),
                "max_pct": round(max_pct, 1),
                "delta": round(delta, 1),
                "moved": delta > POSITION_THRESHOLD,
            }
            all_results[opcode] = result

            if delta > POSITION_THRESHOLD:
                movers[opcode] = result
                print(f"  *** 0x{opcode:02X}: MOVED! "
                      f"{pre_pct:.1f}% -> range [{min_pct:.1f}%, {max_pct:.1f}%] "
                      f"-> settled {post_pct:.1f}% (delta={delta:.1f}%) ***")

                # Wait for actuator to return to baseline before next probe
                print(f"      Waiting for actuator to settle...")
                time.sleep(3.0)
                new_baseline, _ = self.get_baseline_position()
                print(f"      Settled at {new_baseline:.1f}%")
            else:
                # Progress indicator
                if opcode % 16 == 15:
                    print(f"  [...] 0x{opcode - 15:02X}-0x{opcode:02X}: "
                          f"no movement (pos={post_pct:.1f}%)")

            time.sleep(INTER_PROBE_DELAY)

            # Re-init periodically
            if opcode % 64 == 63 and opcode < 255:
                print(f"  [*] Re-init at opcode 0x{opcode:02X}...")
                self.send_raw([0x49, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                time.sleep(0.5)

        # Summary
        print(f"\n{'═' * 60}")
        print("RESULTS SUMMARY")
        print(f"{'═' * 60}")
        print(f"Scanned: 256 opcodes")
        print(f"Movement detected: {len(movers)} opcode(s)")

        if movers:
            print(f"\nOPCODES THAT CAUSE MOVEMENT:")
            for opcode, result in sorted(movers.items()):
                print(f"  0x{opcode:02X}: "
                      f"{result['pre_pct']}% -> [{result['min_pct']}%, {result['max_pct']}%] "
                      f"(delta={result['delta']}%)")
        else:
            print("\nNo movement detected with single-byte opcodes.")
            print("The movement command may require specific byte[1] sub-commands.")

        self.results["position_sweep"] = {
            "baseline_pct": round(baseline_pct, 1),
            "movers": {f"0x{k:02X}": v for k, v in movers.items()},
            "all_results": {f"0x{k:02X}": v for k, v in all_results.items()},
        }
        self._save_results("position_sweep")
        return movers

    # ------------------------------------------------------------------
    # Deep probe: for movers, vary byte[1] and byte[3] (possible position arg)
    # ------------------------------------------------------------------
    def probe_mover_params(self, opcode):
        """For an opcode that causes movement, try different payload values."""
        print(f"\n{'=' * 60}")
        print(f"DEEP PROBE: 0x{opcode:02X} - varying payload bytes")
        print(f"{'=' * 60}")

        results = {}

        # Try varying byte[1] (sub-command)
        print(f"\n--- Varying byte[1] (sub-command) ---")
        for b1 in range(256):
            pre_pct, _ = self.monitor.get_position()
            data = [opcode, b1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            self.send_raw(data)
            min_pct, max_pct, post_pct = self.monitor.wait_and_measure(SETTLE_TIME)
            delta = max(abs(max_pct - pre_pct), abs(min_pct - pre_pct))

            if delta > POSITION_THRESHOLD:
                print(f"  0x{opcode:02X} 0x{b1:02X}: MOVED {pre_pct:.1f}% -> "
                      f"[{min_pct:.1f}%, {max_pct:.1f}%] settled {post_pct:.1f}%")
                results[f"byte1_0x{b1:02X}"] = {
                    "delta": round(delta, 1),
                    "post_pct": round(post_pct, 1),
                }
                time.sleep(3.0)  # Let it settle
            else:
                if b1 % 32 == 31:
                    print(f"  [...] byte1 0x{b1-31:02X}-0x{b1:02X}: no movement")

            time.sleep(INTER_PROBE_DELAY)

        # Try varying byte[3] as a position value (could be target position)
        print(f"\n--- Varying byte[3] (possible position argument) ---")
        for target in [0x00, 0x20, 0x40, 0x60, 0x80, 0xA0, 0xC0, 0xFF]:
            pre_pct, _ = self.monitor.get_position()
            data = [opcode, 0x00, 0x00, target, 0x00, 0x00, 0x00, 0x00]
            self.send_raw(data)
            min_pct, max_pct, post_pct = self.monitor.wait_and_measure(2.0)
            delta = max(abs(max_pct - pre_pct), abs(min_pct - pre_pct))
            print(f"  byte[3]=0x{target:02X}: {pre_pct:.1f}% -> {post_pct:.1f}% "
                  f"(delta={delta:.1f}%)")
            results[f"byte3_0x{target:02X}"] = {
                "delta": round(delta, 1),
                "post_pct": round(post_pct, 1),
            }
            time.sleep(2.0)

        self.results[f"deep_0x{opcode:02X}"] = results
        self._save_results(f"deep_0x{opcode:02X}")

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

    fuzzer = PositionFuzzer(channel, interface)
    fuzzer.connect()

    try:
        if not fuzzer.start_monitoring():
            print("[!] Cannot proceed without position feedback. Exiting.")
            fuzzer.disconnect()
            sys.exit(1)

        # Init the actuator
        print("\n[*] Sending init command...")
        fuzzer.send_raw([0x49, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        time.sleep(1.0)

        # Sweep all opcodes watching for movement
        movers = fuzzer.sweep_for_movement()

        # Deep probe any opcodes that caused movement
        for opcode in sorted(movers.keys()):
            fuzzer.probe_mover_params(opcode)

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        fuzzer._save_results("interrupted")
    finally:
        fuzzer.disconnect()

    print("\n[+] Done. Results in ./fuzz_results/")


if __name__ == "__main__":
    main()
