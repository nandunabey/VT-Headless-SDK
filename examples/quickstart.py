"""
VUT Headless SDK — Quickstart
Connects to the tracker daemon and prints live poses.
Run: python quickstart.py
Requires: pip install websockets
"""
import asyncio, websockets, json

WS_URL = "ws://localhost:8765"

async def main():
    print(f"Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL) as ws:
        print("Connected. Receiving poses...\n")
        async for message in ws:
            data = json.loads(message)
            for serial, pose in data.items():
                if serial == "meta":
                    continue
                pos = pose["position"]
                bat = pose.get("battery_pct", "?")
                print(f"{serial} [{pose['status']}] "
                      f"x={pos['x']:+.3f} "
                      f"y={pos['y']:+.3f} "
                      f"z={pos['z']:+.3f} "
                      f"battery={bat}%")

asyncio.run(main())
