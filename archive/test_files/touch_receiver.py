import asyncio
import json
import time

from websockets.asyncio.server import serve


async def handler(websocket):

    print("\nGalaxy Tab connected!")

    last_print = 0

    try:
        async for raw in websocket:

            data = json.loads(raw)

            event = data.get("event")
            contacts = data.get("contacts", [])

            now = time.monotonic()

            # Avoid flooding the terminal.
            if event != "move" or now - last_print >= 0.2:

                print(
                    f"\nEVENT: {event} "
                    f"| CONTACTS: {len(contacts)}"
                )

                for finger in contacts:

                    print(
                        f"ID={finger['id']} "
                        f"TYPE={finger['tool']} "
                        f"X={finger['x']:.3f} "
                        f"Y={finger['y']:.3f} "
                        f"PRESSURE={finger['pressure']:.3f}"
                    )

                last_print = now

    finally:

        print("\nGalaxy Tab disconnected.")


async def main():

    async with serve(
        handler,
        "127.0.0.1",
        8766
    ):

        print("Touch receiver running on port 8766")

        await asyncio.Future()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nServer stopped.")