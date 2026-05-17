"""
VUT Headless SDK — Record to CSV
Records pose stream to a CSV file for a given duration.
Run: python record_to_csv.py --duration 30 --output session.csv
Requires: pip install websockets
"""
import asyncio, websockets, json, csv, argparse
from datetime import datetime

WS_URL = "ws://localhost:8765"

async def record(duration: int, output: str):
    rows = []
    print(f"Recording for {duration}s -> {output}")
    start = asyncio.get_event_loop().time()

    async with websockets.connect(WS_URL) as ws:
        async for message in ws:
            if asyncio.get_event_loop().time() - start > duration:
                break
            data = json.loads(message)
            ts = data.get("meta", {}).get("timestamp",
                 __import__("time").time())
            for serial, pose in data.items():
                if serial == "meta":
                    continue
                pos = pose["position"]
                rot = pose["rotation"]
                rows.append({
                    "timestamp": ts,
                    "serial": serial,
                    "x": pos["x"], "y": pos["y"], "z": pos["z"],
                    "qw": rot["w"], "qx": rot["x"],
                    "qy": rot["y"], "qz": rot["z"],
                    "battery_pct": pose.get("battery_pct", ""),
                    "status": pose.get("status", "")
                })

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {output}")

parser = argparse.ArgumentParser()
parser.add_argument("--duration", type=int, default=30)
parser.add_argument("--output", default=
    f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
args = parser.parse_args()
asyncio.run(record(args.duration, args.output))
