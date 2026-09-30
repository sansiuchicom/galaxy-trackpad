# touchpad_live_v01.py

import asyncio
import json
import time

from websockets.asyncio.server import serve

from touchpad_lab import (
    INPUT,
    POINT,
    PT_TOUCHPAD,
    device,
    send,
    destroy
)


# ==========================================
# Configuration
# ==========================================

ACTIVE = 0x4006
RELEASE = 0x4000

PAD_WIDTH = 10000
PAD_HEIGHT = 6000


# ==========================================
# Windows touchpad bridge
# ==========================================

class SingleFingerBridge:

    def __init__(self):

        self.handle = device(
            gesture_only=False
        )

        self.pressed = False
        self.source_id = None

        self.last_position = (
            PAD_WIDTH // 2,
            PAD_HEIGHT // 2
        )

        self.tick = 1
        self.last_clock = time.monotonic()
        self.last_log = 0.0

        print(
            "Windows virtual touchpad ready!"
        )


    def inject(self, x, y, flags):

        now = time.monotonic()

        elapsed_ms = max(
            1,
            min(
                50,
                round(
                    (now - self.last_clock) * 1000
                )
            )
        )

        self.tick += elapsed_ms
        self.last_clock = now

        frame = (INPUT * 1)()

        frame[0].type = PT_TOUCHPAD

        pointer = (
            frame[0]
            .data.touchInfo.pointerInfo
        )

        pointer.pointerId = 0
        pointer.pointerFlags = flags

        pointer.ptHimetricLocation = POINT(
            x,
            y
        )

        pointer.dwTime = self.tick

        send(
            self.handle,
            frame,
            1
        )


    def release(self):

        if self.pressed:

            self.inject(
                *self.last_position,
                RELEASE
            )

            self.pressed = False
            self.source_id = None

            print("Finger UP")


    def update(self, contacts):

        # Only finger input for version 0.1.

        fingers = [
            c for c in contacts
            if c.get("tool") == "touch"
        ]

        # Multitouch will be implemented later.

        if len(fingers) != 1:

            self.release()
            return

        finger = fingers[0]

        pointer_id = finger["id"]

        x = round(
            max(
                0.0,
                min(
                    1.0,
                    float(finger["x"])
                )
            ) * PAD_WIDTH
        )

        y = round(
            max(
                0.0,
                min(
                    1.0,
                    float(finger["y"])
                )
            ) * PAD_HEIGHT
        )

        if (
            self.pressed
            and pointer_id != self.source_id
        ):

            self.release()

        if not self.pressed:

            print(
                f"Finger DOWN: x={x} y={y}"
            )

            self.source_id = pointer_id
            self.pressed = True

        self.last_position = (x, y)

        self.inject(
            x,
            y,
            ACTIVE
        )

        now = time.monotonic()

        if now - self.last_log > 0.5:

            print(
                f"MOVE: x={x} y={y}"
            )

            self.last_log = now


    def close(self):

        try:

            self.release()

        finally:

            destroy(self.handle)

            print(
                "Virtual touchpad removed."
            )


# ==========================================
# WebSocket receiver
# ==========================================

async def main():

    bridge = SingleFingerBridge()


    async def handler(websocket):

        print(
            "Galaxy Tab connected!"
        )

        try:

            async for raw in websocket:

                try:

                    message = json.loads(raw)

                    bridge.update(
                        message.get(
                            "contacts",
                            []
                        )
                    )

                except (
                    KeyError,
                    TypeError,
                    ValueError
                ) as error:

                    print(
                        "Invalid packet:",
                        error
                    )

        finally:

            bridge.release()

            print(
                "Galaxy Tab disconnected."
            )


    try:

        async with serve(
            handler,
            "127.0.0.1",
            8766
        ):

            print(
                "Listening on port 8766"
            )

            print(
                "Touch the tablet "
                "with ONE finger."
            )

            await asyncio.Future()

    finally:

        bridge.close()


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print("Server stopped.")