import ctypes
import os
import socket

dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)

print("Loading VS_PC_SDK.dll ...")
try:
    sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
    print("  DLL loaded OK")
except Exception as e:
    print(f"  LOAD ERROR: {e}")
    raise SystemExit(1)

# Wire up VS_WVRSetParameters only
try:
    set_param = sdk.VS_WVRSetParameters
    set_param.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    set_param.restype = ctypes.c_int
    print("  VS_WVRSetParameters symbol resolved OK")
except AttributeError as e:
    print(f"  SYMBOL ERROR: {e}")
    raise SystemExit(1)

my_ip = socket.gethostbyname(socket.gethostname())
print(f"\nLocal IP: {my_ip}")

calls = [
    (b"PLAYER2_STEAMVR_ENABLE", b"1"),
    (b"PLAYER2_STEAMVR_IP",     my_ip.encode()),
    (b"PLAYER2_STEAMVR_PORT",   b"5555"),
]

for key, val in calls:
    print(f"\nVS_WVRSetParameters({key.decode()!r}, {val.decode()!r})")
    try:
        r = set_param(key, val)
        print(f"  -> result: {r}")
    except Exception as e:
        print(f"  -> EXCEPTION: {e}")

print("\nParameter writes done. Now listening on UDP 0.0.0.0:5555 for 15 seconds ...")
print("(ViveTrackerServer is NOT running — this checks if DLL itself emits anything)\n")

import socket as sock_mod
import select

udp = sock_mod.socket(sock_mod.AF_INET, sock_mod.SOCK_DGRAM)
udp.bind(("0.0.0.0", 5555))
udp.setblocking(False)

import time
deadline = time.time() + 15
packets = 0
while time.time() < deadline:
    r, _, _ = select.select([udp], [], [], 0.5)
    if r:
        data, addr = udp.recvfrom(4096)
        packets += 1
        print(f"  UDP packet from {addr}: {len(data)} bytes | hex: {data[:32].hex()}")
    else:
        remaining = int(deadline - time.time())
        print(f"  waiting... {remaining}s left, packets so far: {packets}", end="\r")

udp.close()
print(f"\n\nDone. Total UDP packets received (no server running): {packets}")
