"""
Use the system VIVE Hub VS_PC_SDK.dll (not VBPConsole copy).
"""
import ctypes, os, socket, select, time, sys

dll_dir = r"C:\Program Files\VIVE Hub\VIVE Ultimate Tracker\ViveUTServer"
os.add_dll_directory(dll_dir)
sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
print(f"DLL loaded from: {dll_dir}")

fn = sdk.VS_SDKVersion; fn.restype = ctypes.c_char_p
print(f"VS_SDKVersion: {fn()}")
sys.stdout.flush()

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return socket.gethostbyname(socket.gethostname())

my_ip = get_lan_ip()
print(f"LAN IP: {my_ip}")

set_param = sdk.VS_WVRSetParameters
set_param.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
set_param.restype  = ctypes.c_int
for k, v in [(b"PLAYER2_STEAMVR_ENABLE", b"1"),
             (b"PLAYER2_STEAMVR_IP",     my_ip.encode()),
             (b"PLAYER2_STEAMVR_PORT",   b"5555")]:
    print(f"  SetParam {k.decode()} -> {set_param(k, v)}")
sys.stdout.flush()

print("\nCalling VS_Init ...")
sys.stdout.flush()
init_fn = sdk.VS_Init; init_fn.restype = ctypes.c_int
r = init_fn()
print(f"  VS_Init result: {r}")
sys.stdout.flush()

if r == 0:
    fn2 = sdk.VS_GetClientIP; fn2.restype = ctypes.c_char_p
    print(f"  VS_GetClientIP: {fn2()}")
    print("\nListening for UDP pose data on 0.0.0.0:5555 (30s) ...")
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(("0.0.0.0", 5555)); udp.setblocking(False)
    pkts = 0; deadline = time.time() + 30
    while time.time() < deadline:
        if select.select([udp],[],[],0.5)[0]:
            data, addr = udp.recvfrom(4096)
            pkts += 1
            print(f"  PKT #{pkts} {addr} len={len(data)} hex={data[:32].hex()}")
            import struct
            if len(data) >= 28:
                print(f"  floats: {[round(f,4) for f in struct.unpack_from('<7f',data)]}")
        else:
            print(f"  [{int(deadline-time.time()):2d}s] pkts={pkts}", end="\r")
    udp.close()
    print(f"\nTotal packets: {pkts}")
else:
    print(f"\nVS_Init still failed ({r})")
