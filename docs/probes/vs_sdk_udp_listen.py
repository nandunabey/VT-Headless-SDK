import ctypes
import os
import socket
import select
import time

# --- find real LAN IP (not CGN 100.x or loopback) ---
def get_lan_ip():
    candidates = []
    hostname = socket.gethostname()
    for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
        ip = info[4][0]
        if ip.startswith("127.") or ip.startswith("100."):
            continue
        candidates.append(ip)
    if candidates:
        return candidates[0]
    # fallback: connect to external and read local side
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(hostname)

my_ip = get_lan_ip()
print(f"Using LAN IP: {my_ip}")

# --- load DLL ---
dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)
sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
print("DLL loaded OK")

set_param = sdk.VS_WVRSetParameters
set_param.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
set_param.restype  = ctypes.c_int

calls = [
    (b"PLAYER2_STEAMVR_ENABLE", b"1"),
    (b"PLAYER2_STEAMVR_IP",     my_ip.encode()),
    (b"PLAYER2_STEAMVR_PORT",   b"5555"),
]
for key, val in calls:
    r = set_param(key, val)
    print(f"  SetParam {key.decode()} = {val.decode()}  -> {r}")

# --- listen for UDP ---
print("\nListening on UDP 0.0.0.0:5555 for 30 seconds ...")
print("(ViveTrackerServer should already be running)\n")

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
udp.bind(("0.0.0.0", 5555))
udp.setblocking(False)

packets = 0
deadline = time.time() + 30
last_print = 0

while time.time() < deadline:
    r, _, _ = select.select([udp], [], [], 0.25)
    if r:
        data, addr = udp.recvfrom(4096)
        packets += 1
        print(f"  PKT #{packets} from {addr}  len={len(data)}")
        print(f"    hex[0:32]: {data[:32].hex()}")
        import struct
        if len(data) >= 28:
            floats = struct.unpack_from('<7f', data, 0)
            print(f"    as 7 floats: {[round(f,4) for f in floats]}")
        if packets >= 10:
            print("\n  10 packets received — data is flowing!")
            break
    else:
        now = time.time()
        if now - last_print >= 5:
            print(f"  [{int(deadline - now):2d}s left]  packets so far: {packets}")
            last_print = now

udp.close()
print(f"\nDone. Total UDP packets: {packets}")
