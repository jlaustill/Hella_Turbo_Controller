#!/usr/bin/python3
"""
CAN Opcode Fuzzer for Hella Universal Turbo Actuator I

Systematically probes all possible command bytes to discover
undocumented commands beyond the known set:
  0x31 - Read/Write memory
  0x44 - Commit/Save
  0x49 - Init/Handshake
  0x57 - Write value

Usage:
  python3 can_fuzzer.py <channel> <interface> [phase]

Examples:
  python3 can_fuzzer.py can0 socketcan           # Run all phases
  python3 can_fuzzer.py /dev/ttyACM0 slcan 1     # Phase 1 only
  python3 can_fuzzer.py can0 socketcan 2          # Phase 2 (after reviewing phase 1)
"""

import can
import time
import sys
import datetime
import json
import os

TX_ID = 0x3F0
KNOWN_RX_IDS = {0x3E8, 0x3EA, 0x3EB}
KNOWN_OPCODES = {0x31: "read/write", 0x44: "commit", 0x49: "init", 0x57: "write_value"}

# Opcodes that are likely destructive (write/erase/flash related ranges)
# We still probe them, but flag them in output
CAUTION_OPCODES = {0x44, 0x57, 0x45, 0x46, 0x55, 0x56, 0x58}

INTER_PROBE_DELAY = 0.05   # 50ms between probes (conservative)
RESPONSE_TIMEOUT = 0.15    # 150ms to wait for command responses (reduced from 300ms)
PHASE2_DELAY = 0.05


class HellaFuzzer:
    def __init__(self, channel, interface):
        self.channel = channel
        self.interface_name = interface
        self.bus = None
        self.results = {}
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.log_dir = "fuzz_results"
        self.background_ids = set()  # Arb IDs that broadcast without commands
        os.makedirs(self.log_dir, exist_ok=True)

    def connect(self):
        kwargs = {"channel": self.channel, "interface": self.interface_name, "bitrate": 500000}
        if self.interface_name == "slcan":
            kwargs["ttyBaudrate"] = 128000
        self.bus = can.interface.Bus(**kwargs)
        print(f"[+] Connected: {self.interface_name} on {self.channel} @ 500kbit/s")

    def disconnect(self):
        if self.bus:
            self.bus.shutdown()
            print("[+] Disconnected")

    def send_and_listen(self, data, timeout=RESPONSE_TIMEOUT, filter_background=True):
        """Send a CAN frame and collect responses, filtering background noise."""
        msg = can.Message(is_extended_id=False, arbitration_id=TX_ID, data=bytearray(data))
        self.bus.send(msg)

        responses = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            answer = self.bus.recv(timeout=remaining)
            if answer is None:
                continue
            # Skip background broadcast traffic
            if filter_background and answer.arbitration_id in self.background_ids:
                continue
            responses.append({
                "arb_id": hex(answer.arbitration_id),
                "data": [f"0x{b:02X}" for b in answer.data],
                "dlc": answer.dlc,
                "timestamp": answer.timestamp,
            })
        return responses

    def drain_bus(self, timeout=0.1):
        """Drain any pending messages from the bus."""
        while True:
            msg = self.bus.recv(timeout=timeout)
            if msg is None:
                break

    def baseline_listen(self, duration=2.0):
        """Passively listen to identify periodic broadcast traffic (no commands sent)."""
        print(f"\n[*] Baseline listen ({duration}s) - identifying background traffic...")
        self.drain_bus(timeout=0.1)

        seen = {}  # arb_id -> count
        deadline = time.time() + duration
        while time.time() < deadline:
            msg = self.bus.recv(timeout=0.1)
            if msg is not None:
                aid = msg.arbitration_id
                seen[aid] = seen.get(aid, 0) + 1

        if seen:
            print("[+] Background traffic detected:")
            for aid, count in sorted(seen.items()):
                rate = count / duration
                print(f"    0x{aid:03X}: {count} msgs ({rate:.1f}/sec)")
                if rate > 5:  # More than 5 msgs/sec = periodic broadcast
                    self.background_ids.add(aid)

            if self.background_ids:
                print(f"[+] Filtering out periodic broadcasts: "
                      f"{[f'0x{x:03X}' for x in sorted(self.background_ids)]}")
            else:
                print("[+] No high-frequency broadcasts detected")
        else:
            print("[+] Bus is quiet - no background traffic")

        self.results["baseline"] = {
            f"0x{k:03X}": {"count": v, "rate_hz": round(v / duration, 1)}
            for k, v in sorted(seen.items())
        }
        self.drain_bus()

    def init_actuator(self, verbose=True):
        """Send the known init command to wake the actuator."""
        if verbose:
            print("[*] Sending init (0x49) to wake actuator...")
        init_data = [0x49, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        responses = self.send_and_listen(init_data, timeout=0.5)
        if verbose:
            if responses:
                print(f"[+] Actuator responded to init: {len(responses)} message(s)")
                for r in responses[:5]:  # Show first 5 only
                    print(f"    {r['arb_id']}: {' '.join(r['data'])}")
                if len(responses) > 5:
                    print(f"    ... and {len(responses) - 5} more")
            else:
                print("[!] No response to init - is the actuator powered and connected?")
        self.drain_bus()
        return len(responses) > 0

    # ------------------------------------------------------------------
    # Phase 1: Sweep all 256 possible first-byte opcodes
    # ------------------------------------------------------------------
    def phase1_opcode_sweep(self):
        """Probe all 256 opcodes with zeroed payload bytes."""
        print("\n" + "=" * 60)
        print("PHASE 1: Full opcode sweep (0x00 - 0xFF)")
        print("  Filtering background IDs: "
              f"{[f'0x{x:03X}' for x in sorted(self.background_ids)]}")
        print("=" * 60)

        responding = {}
        silent_count = 0

        for opcode in range(256):
            label = KNOWN_OPCODES.get(opcode, "")
            caution = " [CAUTION]" if opcode in CAUTION_OPCODES else ""
            tag = f" ({label})" if label else ""

            data = [opcode, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            responses = self.send_and_listen(data)

            if responses:
                responding[opcode] = responses
                resp_ids = set(r["arb_id"] for r in responses)
                novel = resp_ids - {hex(x) for x in KNOWN_RX_IDS}
                novel_tag = f" ** NEW ARB ID: {novel} **" if novel else ""
                print(f"  [RESP] 0x{opcode:02X}{tag}{caution}: "
                      f"{len(responses)} response(s) from {resp_ids}{novel_tag}")
                for r in responses[:3]:  # Show first 3
                    print(f"         {r['arb_id']}: {' '.join(r['data'])}")
                if len(responses) > 3:
                    print(f"         ... and {len(responses) - 3} more")
            else:
                silent_count += 1
                # Progress indicator every 32 opcodes
                if opcode % 32 == 31:
                    print(f"  [...] swept through 0x{opcode:02X}, "
                          f"{len(responding)} responding so far")

            time.sleep(INTER_PROBE_DELAY)

            # Re-init periodically to keep actuator awake
            if opcode % 64 == 63 and opcode < 255:
                self.drain_bus()
                self.init_actuator(verbose=False)
                self.drain_bus()

        # Summary
        print(f"\n{'─' * 60}")
        print(f"Phase 1 Summary: {len(responding)}/256 opcodes got responses "
              f"({silent_count} silent)")
        print(f"Responding opcodes: {[f'0x{k:02X}' for k in sorted(responding.keys())]}")

        unknown = set(responding.keys()) - set(KNOWN_OPCODES.keys())
        if unknown:
            print(f"\n*** UNDOCUMENTED RESPONDING OPCODES: "
                  f"{[f'0x{k:02X}' for k in sorted(unknown)]} ***")

        self.results["phase1"] = {
            "responding": {f"0x{k:02X}": v for k, v in responding.items()},
            "silent_count": silent_count,
        }
        self._save_results("phase1")
        return responding

    # ------------------------------------------------------------------
    # Phase 2: Deep probe responding opcodes with sub-command variations
    # ------------------------------------------------------------------
    def phase2_subcmd_probe(self, responding_opcodes=None):
        """For each responding opcode, vary byte 1 (sub-command) across 0x00-0xFF."""
        if responding_opcodes is None:
            responding_opcodes = self._load_phase1_opcodes()

        print("\n" + "=" * 60)
        print("PHASE 2: Sub-command sweep on responding opcodes")
        print("=" * 60)

        for opcode in sorted(responding_opcodes):
            print(f"\n--- Probing 0x{opcode:02X} with sub-commands 0x00-0xFF ---")
            subcmd_results = {}

            self.drain_bus()
            self.init_actuator(verbose=False)
            self.drain_bus()

            for subcmd in range(256):
                data = [opcode, subcmd, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
                responses = self.send_and_listen(data)

                if responses:
                    subcmd_results[subcmd] = responses
                    print(f"  [RESP] 0x{opcode:02X} 0x{subcmd:02X}: "
                          f"{len(responses)} response(s)")
                    for r in responses[:2]:
                        print(f"         {r['arb_id']}: {' '.join(r['data'])}")

                time.sleep(PHASE2_DELAY)

                if subcmd % 64 == 63 and subcmd < 255:
                    self.drain_bus()
                    self.init_actuator(verbose=False)
                    self.drain_bus()

            print(f"  => 0x{opcode:02X}: {len(subcmd_results)}/256 sub-commands responded")
            self.results.setdefault("phase2", {})[f"0x{opcode:02X}"] = {
                f"0x{k:02X}": v for k, v in subcmd_results.items()
            }

        self._save_results("phase2")

    # ------------------------------------------------------------------
    # Phase 3: Extended memory read - try reading beyond 0x7F
    # ------------------------------------------------------------------
    def phase3_extended_memory_read(self):
        """Try reading all 256 addresses using the known read command (0x31 0x0C addr)."""
        print("\n" + "=" * 60)
        print("PHASE 3: Extended memory read (0x00 - 0xFF)")
        print("  Known range is 0x00-0x7F (128 bytes)")
        print("  Probing 0x80-0xFF for hidden memory")
        print("=" * 60)

        self.drain_bus()
        self.init_actuator()
        self.drain_bus()

        memory = {}
        for addr in range(256):
            if addr % 32 == 0 and addr > 0:
                self.drain_bus()
                self.init_actuator(verbose=False)
                self.drain_bus()

            data = [0x31, 0x0C, addr, 0x00, 0x00, 0x00, 0x00, 0x00]
            responses = self.send_and_listen(data)

            data_responses = [r for r in responses if r["arb_id"] == "0x3e8"]
            if data_responses:
                val = data_responses[0]["data"][0]
                memory[addr] = val
                region = "KNOWN" if addr < 0x80 else "** EXTENDED **"
                print(f"  [0x{addr:02X}] = {val}  {region}")
            else:
                if addr >= 0x80:
                    print(f"  [0x{addr:02X}] = (no response)")

            time.sleep(INTER_PROBE_DELAY)

        extended_count = sum(1 for a in memory if a >= 0x80)
        print(f"\n{'─' * 60}")
        print(f"Phase 3: Read {len(memory)} bytes total, "
              f"{extended_count} beyond known 128-byte range")

        if extended_count > 0:
            print("*** Found data beyond documented address space! ***")

        self.results["phase3"] = {f"0x{k:02X}": v for k, v in memory.items()}
        self._save_results("phase3")

        # Dump raw binary
        if memory:
            binfile = os.path.join(self.log_dir, f"memory_full_{self.timestamp}.bin")
            with open(binfile, "wb") as f:
                for addr in range(max(memory.keys()) + 1):
                    val = memory.get(addr, 0)
                    if isinstance(val, str):
                        val = int(val, 16)
                    f.write(bytes([val]))
            print(f"[+] Full memory dump saved: {binfile}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _save_results(self, phase_name):
        path = os.path.join(self.log_dir, f"fuzz_{phase_name}_{self.timestamp}.json")
        with open(path, "w") as f:
            json.dump(self.results.get(phase_name, self.results), f, indent=2, default=str)
        print(f"[+] Results saved: {path}")

    def _load_phase1_opcodes(self):
        """Load responding opcodes from most recent phase 1 results."""
        candidates = sorted(
            [f for f in os.listdir(self.log_dir) if f.startswith("fuzz_phase1_")],
            reverse=True,
        )
        if not candidates:
            print("[!] No phase 1 results found. Run phase 1 first.")
            sys.exit(1)
        path = os.path.join(self.log_dir, candidates[0])
        print(f"[*] Loading phase 1 results from {path}")
        with open(path) as f:
            data = json.load(f)
        responding = data.get("responding", {})
        return [int(k, 16) for k in responding.keys()]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    channel = sys.argv[1]
    interface = sys.argv[2]
    phase = int(sys.argv[3]) if len(sys.argv) > 3 else 0  # 0 = all

    fuzzer = HellaFuzzer(channel, interface)
    fuzzer.connect()

    try:
        # Always run baseline first to fingerprint background traffic
        fuzzer.baseline_listen(duration=2.0)

        alive = fuzzer.init_actuator()
        if not alive:
            print("[!] WARNING: Actuator not responding. Continuing anyway...\n")
        fuzzer.drain_bus()

        if phase in (0, 1):
            responding = fuzzer.phase1_opcode_sweep()

        if phase in (0, 2):
            fuzzer.phase2_subcmd_probe()

        if phase in (0, 3):
            fuzzer.phase3_extended_memory_read()

    except KeyboardInterrupt:
        print("\n[!] Interrupted - saving partial results")
        fuzzer._save_results("interrupted")
    finally:
        fuzzer.disconnect()

    print("\n[+] Done. Results in ./fuzz_results/")


if __name__ == "__main__":
    main()
