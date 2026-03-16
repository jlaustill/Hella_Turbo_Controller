#!/usr/bin/python3
"""
Deep probe of CAN IDs that showed motor load, plus register scan
for a position setpoint register in CAN mode.
"""

import can
import time
import sys
import threading

TX_ID = 0x3F0
POSITION_ID = 0x658
THRESHOLD = 3.0


def raw_to_pct(raw):
    return round((raw - 918) / (174 - 918) * 100.0, 1)


class Mon:
    def __init__(self, bus):
        self.bus, self.pct, self.raw = bus, 0.0, 0
        self.motor_load, self.status = 0, 0
        self.lock = threading.Lock()
        self.last_update = 0
        self._run = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._run:
            m = self.bus.recv(timeout=0.05)
            if m and m.arbitration_id == POSITION_ID:
                r = (m.data[2] << 8) | m.data[3]
                with self.lock:
                    self.raw, self.pct = r, raw_to_pct(r)
                    self.motor_load = (m.data[6] << 8) | m.data[7]
                    self.status = m.data[0]
                    self.last_update = time.time()

    def get(self):
        with self.lock:
            return self.pct

    def get_load(self):
        with self.lock:
            return self.motor_load

    def get_status(self):
        with self.lock:
            return self.status

    def stable(self, n=10):
        vals = []
        for _ in range(n):
            vals.append(self.get())
            time.sleep(0.025)
        return sum(vals) / len(vals)

    def stop(self):
        self._run = False


def send(bus, arb_id, data):
    bus.send(can.Message(is_extended_id=False, arbitration_id=arb_id, data=bytearray(data)))


def probe_ids_deeply(bus, mon):
    """Deep probe of IDs that showed motor load during sweep."""
    print("\n" + "=" * 70)
    print("PHASE 1: Deep probe of load-triggering CAN IDs")
    print("=" * 70)

    # IDs that showed motor load in the sweep
    hot_ids = [0x047, 0x110, 0x12E, 0x3AC, 0x3BC, 0x3CA, 0x3CF]
    # Also add the primary candidates
    hot_ids += [0x3E8, 0x4EA, 0x3F0]

    # Many possible payload formats to try
    payloads = [
        ("all-FF", [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),
        ("all-00", [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("all-80", [0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80]),
        ("50-00",  [0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("00-50",  [0x00, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("00-00-50", [0x00, 0x00, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("raw-546-be", [0x02, 0x22, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("raw-546-le", [0x22, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("pwm-50%", [0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("pwm-inv", [0x7F, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        # Mimic a typical ECU turbo control message
        ("ecu-style1", [0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("ecu-style2", [0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        ("ecu-style3", [0x00, 0x00, 0x00, 0x50, 0x00, 0x00, 0x00, 0x00]),
        # DLC=2 style (just 2 bytes)
        ("2byte-8000", [0x80, 0x00]),
        ("2byte-0200", [0x02, 0x00]),
        ("2byte-FFFF", [0xFF, 0xFF]),
    ]

    for can_id in hot_ids:
        print(f"\n--- 0x{can_id:03X} ---")
        for name, data in payloads:
            pre = mon.get()
            pre_load = mon.get_load()

            # Send repeatedly for 1.5 seconds
            start = time.time()
            max_load = 0
            while time.time() - start < 1.5:
                send(bus, can_id, data)
                time.sleep(0.05)
                load = mon.get_load()
                if load > max_load:
                    max_load = load

            post = mon.get()
            delta = abs(post - pre)

            if delta > THRESHOLD:
                print(f"  *** {name:15s}: MOVED! {pre:.1f}% -> {post:.1f}% "
                      f"(delta={delta:.1f}%, max_load={max_load}) ***")
                time.sleep(3.0)
            elif max_load > 50:
                print(f"  [LOAD] {name:15s}: {pre:.1f}% -> {post:.1f}% "
                      f"load={max_load}")

    print()


def scan_position_registers(bus, mon):
    """Scan register address space for a position setpoint register.

    In CAN mode, the actuator might have a register that accepts a target
    position (vs the speed/direction motor control we found before).
    Write various position values and watch for proportional control.
    """
    print("\n" + "=" * 70)
    print("PHASE 2: Register scan for position setpoint")
    print("Scanning registers 0x0000-0x01FF via 0x3F0 protocol")
    print("=" * 70)

    def s(d):
        send(bus, TX_ID, d)
        time.sleep(0.02)

    def init():
        s([0x49, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)

    def write_reg(hi, lo, val):
        s([0x31, hi, lo, 0, 0, 0, 0, 0])
        s([0x57, 0x00, (val >> 8) & 0xFF, val & 0xFF, 0, 0, 0, 0])

    def commit():
        s([0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0])

    # Scan address ranges that might contain position registers
    # Skip known dangerous ones (motor enable, direction, mode, speed)
    skip = {
        (0x00, 0x80),  # motor enable
        (0x01, 0x5D),  # mode
        (0x01, 0x61),  # direction
        (0x01, 0x63),  # speed
    }

    # First, scan without motor enable - just write register + commit
    # and see if anything happens
    print("\n--- Scan: write register + commit (no motor enable) ---")
    test_addrs = []
    for hi in range(2):
        for lo in range(0, 256, 4):  # Step by 4 for speed
            if (hi, lo) in skip:
                continue
            test_addrs.append((hi, lo))

    for i, (hi, lo) in enumerate(test_addrs):
        init()
        pre = mon.get()

        # Write a 50% position value
        write_reg(hi, lo, 0x0222)  # ~546 raw, ~50%
        commit()

        time.sleep(0.5)
        post = mon.get()
        load = mon.get_load()
        delta = abs(post - pre)

        if delta > THRESHOLD:
            print(f"  *** 0x{hi:02X}{lo:02X} = 0x0222: MOVED! "
                  f"{pre:.1f}% -> {post:.1f}% (delta={delta:.1f}%) ***")
            # CRITICAL: don't let it drive to endstop
            init()
            time.sleep(3.0)
        elif load > 50:
            print(f"  [LOAD] 0x{hi:02X}{lo:02X}: load={load}")

        if i % 32 == 31:
            print(f"  [...] scanned through 0x{hi:02X}{lo:02X} "
                  f"(pos={post:.1f}%)")

    # Now scan WITH mode=5 unlock but WITHOUT motor enable
    # Maybe some registers trigger the PID controller
    print("\n--- Scan: mode=5 + write register + commit (no motor enable) ---")
    for hi, lo in [(0x01, x) for x in range(0x50, 0x70, 2)] + \
                  [(0x00, x) for x in range(0x80, 0xA0, 2)]:
        if (hi, lo) in skip:
            continue

        init()
        pre = mon.get()

        write_reg(0x01, 0x5D, 0x05)  # mode = 5
        write_reg(hi, lo, 0x0032)     # target = 50
        commit()

        time.sleep(1.0)
        post = mon.get()
        load = mon.get_load()
        delta = abs(post - pre)

        if delta > THRESHOLD:
            print(f"  *** mode5 + 0x{hi:02X}{lo:02X} = 0x32: MOVED! "
                  f"{pre:.1f}% -> {post:.1f}% ***")
            init()
            time.sleep(3.0)
        elif load > 50:
            print(f"  [LOAD] mode5 + 0x{hi:02X}{lo:02X}: load={load}")

    print()


def test_can_mode_commands(bus, mon):
    """Test if CAN mode accepts different command protocols on 0x3F0."""
    print("\n" + "=" * 70)
    print("PHASE 3: Alternative command protocols on 0x3F0")
    print("=" * 70)

    def s(d):
        send(bus, TX_ID, d)
        time.sleep(0.02)

    # Try: init + direct position write (no mode unlock)
    # Maybe CAN mode has a simpler protocol
    tests = [
        ("direct 0x57 write 50%",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x02, 0x22, 0, 0, 0, 0]]),  # raw ~546

        ("direct 0x57 write 0x32",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x32, 0, 0, 0, 0]]),

        ("opcode 0x50 (position?)",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x50, 0x00, 0x02, 0x22, 0, 0, 0, 0]]),

        ("opcode 0x50 byte1=1",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x50, 0x01, 0x02, 0x22, 0, 0, 0, 0]]),

        ("opcode 0x43 (control?)",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x43, 0x00, 0x02, 0x22, 0, 0, 0, 0]]),

        ("opcode 0x53 (setpoint?)",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x53, 0x00, 0x00, 0x32, 0, 0, 0, 0]]),

        ("opcode 0x54 (target?)",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x54, 0x00, 0x00, 0x32, 0, 0, 0, 0]]),

        ("opcode 0x47 (go?)",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x47, 0x00, 0x00, 0x32, 0, 0, 0, 0]]),

        # Maybe the position is set as mode + commit only
        ("mode=5 + commit only",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x05, 0, 0, 0, 0],
          [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0]]),

        # Mode=3 might be "CAN position" mode
        ("mode=3 + 0x0163=50 + commit",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x03, 0, 0, 0, 0],
          [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x32, 0, 0, 0, 0],
          [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0]]),

        # Mode=4 might be "CAN position" mode
        ("mode=4 + 0x0163=50 + commit",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x04, 0, 0, 0, 0],
          [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x32, 0, 0, 0, 0],
          [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0]]),

        # Mode=6 position control?
        ("mode=6 + 0x0163=50 + motor + commit",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x06, 0, 0, 0, 0],
          [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x32, 0, 0, 0, 0],
          [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
          [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0]]),

        # Mode=7 ?
        ("mode=7 + 0x0163=50 + motor + commit",
         [[0x49, 0, 0, 0, 0, 0, 0, 0],
          [0x31, 0x01, 0x5D, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x07, 0, 0, 0, 0],
          [0x31, 0x01, 0x63, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x32, 0, 0, 0, 0],
          [0x31, 0x00, 0x80, 0, 0, 0, 0, 0],
          [0x57, 0x00, 0x00, 0x01, 0, 0, 0, 0],
          [0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0]]),
    ]

    for name, cmds in tests:
        pre = mon.stable(5)

        for cmd in cmds:
            s(cmd)
            if cmd[0] == 0x49:
                time.sleep(0.3)

        time.sleep(2.0)
        post = mon.stable(5)
        load = mon.get_load()
        delta = abs(post - pre)
        status = mon.get_status()

        tag = "*** MOVED ***" if delta > THRESHOLD else "no movement"
        extra = f" load={load}" if load > 50 else ""
        print(f"  {name:40s}: {pre:.1f}% -> {post:.1f}% "
              f"delta={delta:.1f}% st=0x{status:02X}{extra}  {tag}")

        if delta > THRESHOLD:
            # Emergency stop
            s([0x49, 0, 0, 0, 0, 0, 0, 0])
            time.sleep(0.3)
            s([0x31, 0x01, 0x5D, 0, 0, 0, 0, 0])
            s([0x57, 0x00, 0x00, 0x02, 0, 0, 0, 0])
            s([0x44, 0x00, 0x00, 0x00, 0, 0, 0, 0])
            time.sleep(3.0)


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "can0"
    interface = sys.argv[2] if len(sys.argv) > 2 else "socketcan"
    mode = sys.argv[3] if len(sys.argv) > 3 else "all"

    bus = can.interface.Bus(channel=channel, interface=interface, bitrate=500000)
    mon = Mon(bus)
    time.sleep(1.0)

    if mon.last_update == 0:
        print("[!] No position data. Exiting.")
        bus.shutdown()
        sys.exit(1)
    print(f"[+] Position: {mon.get():.1f}%")

    try:
        if mode in ("all", "ids"):
            probe_ids_deeply(bus, mon)
        if mode in ("all", "regs"):
            scan_position_registers(bus, mon)
        if mode in ("all", "cmds"):
            test_can_mode_commands(bus, mon)
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
        send(bus, TX_ID, [0x49, 0, 0, 0, 0, 0, 0, 0])
    finally:
        mon.stop()
        bus.shutdown()


if __name__ == "__main__":
    main()
