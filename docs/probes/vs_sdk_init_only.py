import ctypes
import os
import socket
import select
import time

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())

my_ip = get_lan_ip()
print(f"LAN IP: {my_ip}")

dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)
sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
print("DLL loaded OK")

set_param = sdk.VS_WVRSetParameters
set_param.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
set_param.restype  = ctypes.c_int

for key, val in [
    (b"PLAYER2_STEAMVR_ENABLE", b"1"),
    (b"PLAYER2_STEAMVR_IP",     my_ip.encode()),
    (b"PLAYER2_STEAMVR_PORT",   b"5555"),
]:
    r = set_param(key, val)
    print(f"  SetParam {key.decode()} = {val.decode()}  -> {r}")

# NO callback registration — just call VS_Init
print("\nCalling VS_Init (no callback) ...")
init_fn = sdk.VS_Init
init_fn.restype = ctypes.c_int
r = init_fn()
print(f"  VS_Init result: {r}")

print("\nListening on UDP 0.0.0.0:5555 for 20 seconds ...")

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
udp.bind(("0.0.0.0", 5555))
udp.setblocking(False)

import struct
packets = 0
deadline = time.time() + 20
last_print = 0

while time.time() < deadline:
    r2, _, _ = select.select([udp], [], [], 0.25)
    if r2:
        data, addr = udp.recvfrom(4096)
        packets += 1
        print(f"  PKT #{packets} from {addr}  len={len(data)}")
        print(f"    hex[0:32]: {data[:32].hex()}")
        if len(data) >= 28:
            floats = struct.unpack_from('<7f', data, 0)
            print(f"    as 7 floats: {[round(f,4) for f in floats]}")
        if packets >= 10:
            print("\n  Data flowing!")
            break
    else:
        now = time.time()
        if now - last_print >= 5:
            print(f"  [{int(deadline - now):2d}s left] packets: {packets}")
            last_print = now

udp.close()
print(f"\nDone. Total UDP packets: {packets}")
