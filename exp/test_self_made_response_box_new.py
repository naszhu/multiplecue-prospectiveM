#!/usr/bin/env python3
"""Continuous self-made response box tester.

Mirrors multiplecue-prospectiveM/exp/testmain_demo.py serial handling:
  1. reset_input_buffer()
  2. write(b"S") + flush
  3. read(1) for 'A' ack
  4. buffer-read loop until first valid "pin,latency_us" OR Arduino "timeout"
  5. print result, then immediately start next trial
"""

from __future__ import annotations

import argparse
import sys
import time

import serial
from serial.tools import list_ports

CEDRUS_VID = 0x0403
CEDRUS_PID = 0x6001
BAUDRATE = 115200
SERIAL_TIMEOUT_SEC = 0.001  # same as testmain_demo.py
ARDUINO_BOOT_DELAY_SEC = 2.0
MAX_RESPONSE_WAIT_SEC = 3.0  # backup if Arduino never sends timeout
DEVICE_NAME_CHOICES = ["KB", "RB", "SRB1", "SRB2", "SRB3", "SRB4", "SRB5", "SRB6"]

PIN_LABELS = {
    "5": "5 - right 3",
    "6": "6 - left 2",
    "7": "7 - left 1",
    "8": "8 - right 1",
    "9": "9 - right 2",
}


def _serial_candidates() -> list[str]:
    return [
        port.device
        for port in list_ports.comports()
        if not (port.vid == CEDRUS_VID and port.pid == CEDRUS_PID)
        and port.device.startswith(("/dev/ttyACM", "/dev/ttyUSB", "COM"))
    ]


def query_srb_identity(port_name: str) -> tuple[str | None, str | None]:
    try:
        with serial.Serial(port_name, baudrate=BAUDRATE, timeout=0.5) as box:
            time.sleep(ARDUINO_BOOT_DELAY_SEC)
            box.reset_input_buffer()
            box.write(b"I")
            box.flush()
            reply = box.readline().decode("ascii", errors="ignore").strip()
    except Exception as exc:
        print(f"  identity query failed on {port_name}: {exc}", file=sys.stderr)
        return None, None

    if not reply:
        return None, None

    parts = reply.split(",")
    device_name = parts[0].strip() if parts else None
    firmware_version = parts[1].strip() if len(parts) > 1 else None
    if device_name not in DEVICE_NAME_CHOICES:
        return None, firmware_version
    return device_name, firmware_version


def auto_detect_srb() -> tuple[str, str | None, str | None]:
    candidates = _serial_candidates()
    if not candidates:
        raise SystemExit("No self-made response box serial ports found.")

    for port_name in candidates:
        device_name, firmware_version = query_srb_identity(port_name)
        if device_name is not None:
            return port_name, device_name, firmware_version

    return candidates[0], None, None


def wait_for_self_made_response(box: serial.Serial, debug: bool = False) -> tuple[str, str | None, float | None]:
    """Same read loop as testmain_demo._wait_for_self_made_response_box.

    Returns (outcome, pin, device_rt_ms) where outcome is 'press', 'timeout', or 'expired'.
    """
    buffer = ""
    start = time.monotonic()

    while time.monotonic() - start < MAX_RESPONSE_WAIT_SEC:
        buffer += box.read(box.in_waiting or 1).decode("ascii", errors="ignore")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            if debug:
                print(f"  raw: {line}", flush=True)

            if line.lower() == "timeout":
                return "timeout", None, None

            parts = line.split(",")
            if len(parts) != 2:
                continue

            pin, latency_us = parts[0].strip(), parts[1].strip()
            if pin not in PIN_LABELS:
                if debug:
                    print(f"  (skipped pin {pin!r})", flush=True)
                continue

            try:
                device_rt_ms = float(latency_us) / 1000.0
            except ValueError:
                device_rt_ms = float("nan")
            return "press", pin, device_rt_ms

    return "expired", None, None


def run_trial(box: serial.Serial, trial: int, debug: bool = False) -> None:
    """One trial: reset, S, ack, wait for one outcome, print."""
    box.reset_input_buffer()
    box.write(b"S")
    box.flush()

    ack = box.read(1)
    if ack == b"A":
        print(f"Trial {trial}: sent S -> Arduino ack A", flush=True)
    else:
        print(f"Trial {trial}: sent S -> WARNING: no 'A' ack (got {ack!r})", flush=True)

    outcome, pin, device_rt_ms = wait_for_self_made_response(box, debug=debug)

    if outcome == "press" and pin is not None:
        label = PIN_LABELS[pin]
        if device_rt_ms is not None and device_rt_ms == device_rt_ms:
            print(f"  response: {label}  (device RT = {device_rt_ms:.3f} ms)", flush=True)
        else:
            print(f"  response: {label}", flush=True)
    elif outcome == "timeout":
        print("  (Arduino timeout — no button press this trial)", flush=True)
    else:
        print("  (no response before Python deadline)", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Serial port override.")
    parser.add_argument("--debug", action="store_true", help="Print every raw serial line.")
    args = parser.parse_args()

    if args.port:
        port_name = args.port
        device_name, firmware_version = query_srb_identity(port_name)
    else:
        port_name, device_name, firmware_version = auto_detect_srb()

    print(f"Port: {port_name}")
    if device_name:
        fw = f", firmware {firmware_version}" if firmware_version else ""
        print(f"Device name: {device_name}{fw}")
    else:
        print("Device name: (identity query failed or unsupported firmware)")

    print("Pin map:", ", ".join(PIN_LABELS[p] for p in sorted(PIN_LABELS, key=int)))
    print("Each S arms the box for one press. Ctrl+C to quit.\n", flush=True)

    trial = 0
    with serial.Serial(port_name, baudrate=BAUDRATE, timeout=SERIAL_TIMEOUT_SEC) as box:
        time.sleep(ARDUINO_BOOT_DELAY_SEC)
        box.reset_input_buffer()

        try:
            while True:
                trial += 1
                run_trial(box, trial, debug=args.debug)
        except KeyboardInterrupt:
            print("\nDone.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
