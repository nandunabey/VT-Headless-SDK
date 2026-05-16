"""
Try VS_Init with NO parameters set first.
The PLAYER2_STEAMVR_* params may require SteamVR running — skip them.
"""
import ctypes, os, socket, select, time

dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)
sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
print("DLL loaded OK")

# Check SDK version first
fn = sdk.VS_SDKVersion
fn.restype = ctypes.c_char_p
print(f"VS_SDKVersion: {fn()}")

# Call VS_Init with no setup at all
print("\nCalling VS_Init (bare, no params) ...")
import sys; sys.stdout.flush()
init_fn = sdk.VS_Init
init_fn.restype = ctypes.c_int
r = init_fn()
print(f"  VS_Init result: {r}")
sys.stdout.flush()

if r == 0:
    fn2 = sdk.VS_GetClientIP
    fn2.restype = ctypes.c_char_p
    print(f"  VS_GetClientIP: {fn2()}")

    print("\nListening on UDP 0.0.0.0:5555 for 15 seconds ...")
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(("0.0.0.0", 5555))
    udp.setblocking(False)
    packets = 0
    deadline = time.time() + 15
    while time.time() < deadline:
        r2, _, _ = select.select([udp], [], [], 0.5)
        if r2:
            data, addr = udp.recvfrom(4096)
            packets += 1
            print(f"  PKT #{packets} from {addr}  len={len(data)}  hex: {data[:32].hex()}")
        else:
            print(f"  [{int(deadline-time.time()):2d}s] pkts: {packets}", end="\r")
    udp.close()
    print(f"\nTotal UDP packets: {packets}")
else:
    print(f"\nVS_Init failed ({r}) — trying to read error meaning via GetParameters ...")
    get_p = sdk.VS_WVRGetParameters
    get_p.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    get_p.restype = ctypes.c_int
    for key in [b"ERROR", b"LAST_ERROR", b"STATUS", b"STATE", b"INIT_ERROR",
                b"DEVICE_STATUS", b"TRACKER_STATUS", b"CONNECTED"]:
        buf = ctypes.create_string_buffer(256)
        ret = get_p(key, buf, 256)
        if buf.value:
            print(f"  {key.decode()}: r={ret} val={buf.value!r}")
