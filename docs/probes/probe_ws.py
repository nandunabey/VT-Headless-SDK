import asyncio, json
import websockets

async def probe():
    async with websockets.connect('ws://localhost:8765') as ws:
        for _ in range(6):
            msg = await ws.recv()
            d = json.loads(msg)
            if d['type'] == 'pose_multi':
                tc = d['stats']['tracker_count']
                print(f'pose_multi  tracker_count={tc}  frame={d["frame_id"]}')
                for t in d['trackers']:
                    print(f'  id={t["id"]}  valid={t["valid"]}  pos={t["pos"]}')
                return

asyncio.run(probe())
