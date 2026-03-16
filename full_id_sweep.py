#!/usr/bin/python3
"""
Full CAN ID sweep - try every possible 11-bit CAN ID (0x000-0x7FF)
with position commands, monitoring 0x658 for movement.

Also tries register-write based position control via 0x3F0.
"""

import can
import time
import sys
import threading

TX_ID = 0x3F0
POSITION_ID = 0x658
RAW_POS_0PCT = 918
RAW_POS_100PCT = 174
THRESHOLD = 3.0


def raw_to_pct(raw):
    return round((raw - RAW_POS_0PCT) / (RAW_POS_100PCT - RAW_POS_0PCT) * 100.0, 1)


class Mon:
    def __init__(self, bus):
        self.bus, self.pct, self.raw = bus, 0.0, 0
        self.motor_load = 0
        self.lock = threading.Lock()
        self.last_update = 0
        self._run = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._run:
            m = self.bus.recv(timeout=0.05)
            if m and m.arbitration_id == POSITION_ID:
                r = (m.data[2] << 8) | m.data[3]
                ml = (m.data[6] << 8) | m.data[7]
                with self.lock:
                    self.raw, self.pct = r, raw_to_pct(r)
                    self.motor_load = ml
                    self.last_update = time.time()

    def get(self):
        with self.lock:
            return self.pct

    def get_load(self):
        with self.lock:
            return self.motor_load

    def stable(self, n=8):
        vals = []
        for _ in range(n):
            vals.append(self.get())
            time.sleep(0.025)
        return sum(vals) / len(vals)

    def stop(self):
        self._run = False


def send(bus, arb_id, data):
    bus.send(can.Message(is_extended_id=False, arbitration_id=arb_id, data=bytearray(data)))


def sweep_all_ids(bus, mon):
    """Sweep all 2048 CAN IDs with multiple position encodings."""
    print("\n" + "=" * 70)
    print("PHASE 1: Full 11-bit CAN ID sweep (0x000-0x7FF)")
    print("Sending position commands on each ID, watching for movement")
    print("=" * 70)

    # Try two different payloads per ID (50% position in two encodings)
    payloads = [
        [0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # 10-bit 512 = ~50%
        [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # 16-bit 512
    ]

    baseline = mon.stable()
    print(f"[+] Baseline: {baseline:.1f}%\n")
    found = []

    for can_id in range(0x000, 0x800):
        # Skip our own position broadcast ID to avoid confusion
        if can_id == POSITION_ID:
            continue

        pre = mon.get()

        # Send each payload 3 times quickly
        for payload in payloads:
            for _ in range(3):
                send(bus, can_id, payload)
                time.sleep(0.01)

        # Quick check
        time.sleep(0.2)
        post = mon.get()
        load = mon.get_load()
        delta = abs(post - pre)

        if delta > THRESHOLD:
            print(f"  *** 0x{can_id:03X}: MOVED! {pre:.1f}% -> {post:.1f}% "
                  f"(delta={delta:.1f}%, load={load}) ***")
            found.append((can_id, delta, post))
            # Wait for return
            time.sleep(3.0)
        elif load > 50:
            # Motor load without position change could indicate the actuator
            # is trying to move but is already at the commanded position
            print(f"  [LOAD] 0x{can_id:03X}: no pos change but load={load}")
        elif can_id % 256 == 255:
            print(f"  [...] 0x{can_id-255:03X}-0x{can_id:03X}: no movement "
                  f"(pos={post:.1f}%)")

    return found


def try_register_position(bus, mon):
    """Try using the register-write protocol to set a position setpoint.

    In CAN mode, the actuator might accept position values via register
    writes on 0x3F0 rather than via a separate CAN ID.
    """
    print("\n" + "=" * 70)
    print("PHASE 2: Register-write position control via 0x3F0")
    print("Testing if position can be set via register writes")
    print("=" * 70)

    def write_reg(addr_hi, addr_lo, value):
        """Select register and write value."""
        send(bus, TX_ID, [0x31, addr_hi, addr_lo, 0, 0, 0, 0, 0])
        time.sleep(0.02)
        send(bus, TX_ID, [0x57, 0x00, (value >> 8) & 0xFF, value & 0xFF, 0, 0, 0, 0])
        time.sleep(0.02)

    def commit():
        send(bus, TX_ID, [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0])
        time.sleep(0.02)

    def init():
        send(bus, TX_ID, [0x49, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)

    # Candidate position registers to try writing
    # Some of these are speculative based on nearby address ranges
    position_registers = [
        (0x01, 0x63, "0x0163 (speed/pos)"),
        (0x01, 0x60, "0x0160"),
        (0x01, 0x62, "0x0162"),
        (0x01, 0x64, "0x0164"),
        (0x01, 0x65, "0x0165"),
        (0x00, 0x81, "0x0081"),
        (0x00, 0x82, "0x0082"),
        (0x00, 0x83, "0x0083"),
        (0x00, 0x90, "0x0090"),
        (0x00, 0x91, "0x0091"),
        (0x01, 0x00, "0x0100"),
    ]

    # Test pattern: mode=5 unlock, write position to register, motor enable, commit
    for addr_hi, addr_lo, name in position_registers:
        init()

        pre = mon.stable(5)

        # Unlock with mode=5
        write_reg(0x01, 0x5D, 0x05)
        # Set target position (try 50% = ~546 raw, or just 0x28 like speed)
        write_reg(addr_hi, addr_lo, 0x0028)
        # Motor enable
        write_reg(0x00, 0x80, 0x01)
        # Direction forward
        write_reg(0x01, 0x61, 0x01)
        # Commit
        commit()

        time.sleep(2.0)
        post = mon.stable(5)
        delta = abs(post - pre)
        load = mon.get_load()

        status = "*** MOVED ***" if delta > THRESHOLD else "no movement"
        print(f"  Reg {name}: {pre:.1f}% -> {post:.1f}% "
              f"delta={delta:.1f}% load={load}  {status}")

        if delta > THRESHOLD:
            # Return home
            init()
            write_reg(0x01, 0x5D, 0x05)
            write_reg(0x01, 0x61, 0x00)  # direction = 0 (return)
            write_reg(0x00, 0x80, 0x00)  # motor off
            write_reg(0x01, 0x61, 0x01)  # direction = 1 (return)
            commit()
            time.sleep(2.0)
            # Stop
            write_reg(0x01, 0x61, 0x00)
            write_reg(0x01, 0x5D, 0x02)  # lock
            commit()
            time.sleep(3.0)


def try_position_values_on_0163(bus, mon):
    """Now that we know the register write protocol works in CAN mode,
    try different values on 0x0163 to see if it controls position vs speed."""
    print("\n" + "=" * 70)
    print("PHASE 3: Position values via register 0x0163")
    print("Testing if CAN mode changes 0x0163 from speed to position control")
    print("=" * 70)

    def write_reg(addr_hi, addr_lo, value):
        send(bus, TX_ID, [0x31, addr_hi, addr_lo, 0, 0, 0, 0, 0])
        time.sleep(0.02)
        send(bus, TX_ID, [0x57, 0x00, (value >> 8) & 0xFF, value & 0xFF, 0, 0, 0, 0])
        time.sleep(0.02)

    def commit():
        send(bus, TX_ID, [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0])
        time.sleep(0.02)

    def init():
        send(bus, TX_ID, [0x49, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)

    def go_home():
        init()
        write_reg(0x01, 0x61, 0x00)
        write_reg(0x00, 0x80, 0x00)
        write_reg(0x01, 0x61, 0x01)
        commit()
        time.sleep(2.0)
        write_reg(0x01, 0x61, 0x00)
        write_reg(0x01, 0x5D, 0x02)
        commit()
        for _ in range(30):
            if mon.get() > 90:
                break
            time.sleep(0.2)
        time.sleep(1.0)

    # Test: send command with SMALL speed values and short durations
    # to see if position settles at different points
    test_values = [0x05, 0x0A, 0x10, 0x15, 0x20]

    for val in test_values:
        init()
        pre = mon.stable(5)

        # Mode=5, set speed/pos, motor enable, direction, commit
        write_reg(0x01, 0x5D, 0x05)
        write_reg(0x01, 0x63, val)
        write_reg(0x00, 0x80, 0x01)
        write_reg(0x01, 0x61, 0x01)
        commit()

        # Watch for 3 seconds
        readings = []
        start = time.time()
        while time.time() - start < 3.0:
            readings.append((time.time() - start, mon.get()))
            time.sleep(0.05)

        final = mon.stable(5)
        min_pct = min(r[1] for r in readings) if readings else 0
        print(f"  val=0x{val:02X} ({val:3d}): {pre:.1f}% -> min={min_pct:.1f}% "
              f"final={final:.1f}%")

        go_home()


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "can0"
    interface = sys.argv[2] if len(sys.argv) > 2 else "socketcan"
    mode = sys.argv[3] if len(sys.argv) > 3 else "all"

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)
    mon = Mon(bus)
    time.sleep(1.0)

    pct = mon.get()
    if mon.last_update == 0:
        print("[!] No position data. Exiting.")
        bus.shutdown()
        sys.exit(1)
    print(f"[+] Position: {pct:.1f}%")

    try:
        if mode in ("all", "sweep"):
            found = sweep_all_ids(bus, mon)
            if found:
                print(f"\n[+] Found {len(found)} working CAN ID(s)!")
                for cid, d, p in found:
                    print(f"  0x{cid:03X}: delta={d:.1f}%, settled={p:.1f}%")

        if mode in ("all", "register"):
            try_register_position(bus, mon)

        if mode in ("all", "position"):
            try_position_values_on_0163(bus, mon)

    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        # Emergency stop
        send(bus, TX_ID, [0x49, 0, 0, 0, 0, 0, 0, 0])
    finally:
        mon.stop()
        bus.shutdown()


if __name__ == "__main__":
    main()
