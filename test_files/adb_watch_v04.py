# adb_watch_v04.py
# Galaxy Trackpad USB Connection Manager

import socket
import subprocess
import time

from pathlib import Path


# ==========================================
# Configuration
# ==========================================

ADB = Path(
    r"C:\touchpad\platform-tools\adb.exe"
)

ADB_HOST = "127.0.0.1"
ADB_PORT = 5037

PORTS = [8765, 8766]


# ==========================================
# ADB commands
# ==========================================

def run_adb(*args):

    result = subprocess.run(
        [str(ADB), *args],
        capture_output=True,
        text=True,
        timeout=10
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr or result.stdout
        )

    return result.stdout


def configure_usb(serial):

    print("[USB] Configuring connection...")

    for port in PORTS:

        run_adb(
            "-s",
            serial,
            "reverse",
            f"tcp:{port}",
            f"tcp:{port}"
        )

    print("[USB] Port forwarding ready!")
    print("[USB] Galaxy Trackpad connected.")


# ==========================================
# Receive ADB events
# ==========================================

def read_exact(sock, length):

    data = bytearray()

    while len(data) < length:

        chunk = sock.recv(
            length - len(data)
        )

        if not chunk:
            raise ConnectionError(
                "ADB connection closed"
            )

        data.extend(chunk)

    return bytes(data)


def track_devices():

    command = b"host:track-devices"

    with socket.create_connection(
        (ADB_HOST, ADB_PORT)
    ) as sock:

        request = (
            f"{len(command):04x}".encode()
            + command
        )

        sock.sendall(request)

        response = read_exact(sock, 4)

        if response != b"OKAY":
            raise RuntimeError(
                "ADB tracking unavailable"
            )

        print("[ADB] Waiting for USB events...")

        while True:

            header = read_exact(sock, 4)

            length = int(
                header.decode("ascii"),
                16
            )

            payload = read_exact(
                sock,
                length
            ).decode(
                "utf-8",
                errors="replace"
            )

            yield payload


# ==========================================
# Connection manager
# ==========================================

def monitor():

    previous_serial = None

    for event in track_devices():

        devices = {}

        for line in event.splitlines():

            parts = line.split()

            if len(parts) >= 2:

                devices[parts[0]] = parts[1]

        ready = [
            serial
            for serial, status
            in devices.items()
            if status == "device"
        ]

        if len(ready) == 1:

            serial = ready[0]

            if serial != previous_serial:

                print()
                print("[USB] Device detected.")

                configure_usb(serial)

                previous_serial = serial

        else:

            if previous_serial is not None:

                print()
                print("[USB] Device disconnected.")

            previous_serial = None

            if len(ready) > 1:
                print(
                    "[USB] Multiple devices detected."
                )


# ==========================================
# Main
# ==========================================

def main():

    print()
    print("==============================")
    print("GALAXY TRACKPAD USB MANAGER")
    print("==============================")
    print()

    if not ADB.is_file():
        print("[ERROR] ADB not found.")
        return

    run_adb("start-server")

    try:

        while True:

            try:

                monitor()

            except (
                ConnectionError,
                OSError,
                RuntimeError,
                ValueError
            ) as error:

                print(
                    "[ADB] Connection error:",
                    error
                )

                print(
                    "[ADB] Retrying in 2 seconds..."
                )

                time.sleep(2)

                run_adb("start-server")

    except KeyboardInterrupt:

        print()
        print("USB manager stopped.")


if __name__ == "__main__":
    main()