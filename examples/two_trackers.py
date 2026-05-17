"""
VUT Headless SDK — Two Tracker Distance
Prints live distance between two trackers by serial.
Edit SERIAL_A and SERIAL_B to match your trackers.
Run: python two_trackers.py
Requires: pip install websockets
"""
import asyncio, websockets, json, math

WS_URL = "ws://localhost:8765"
SERIAL_A = "YOUR_SERIAL_A"  # e.g. "41-A33204726"
SERIAL_B = "YOUR_SERIAL_B"  # e.g. "41-A33P02882"

def distance(a, b):
    return math.sqrt(
        (a['x']-b['x'])**2 +
        (a['y']-b['y'])**2 +
        (a['z']-b['z'])**2
    )

async def main():
    async with websockets.connect(WS_URL) as ws:
        print(f"Measuring distance: {SERIAL_A} <-> {SERIAL_B}\n")
        async for message in ws:
            data = json.loads(message)
            if SERIAL_A in data and SERIAL_B in data:
                d = distance(
                    data[SERIAL_A]["position"],
                    data[SERIAL_B]["position"]
                )
                print(f"Distance: {d:.3f}m  ({d*100:.1f}cm)")

asyncio.run(main())
