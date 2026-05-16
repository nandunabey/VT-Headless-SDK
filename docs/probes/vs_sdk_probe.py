import ctypes
import os

dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)
sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
print("DLL loaded OK\n")

# --- VS_Version / VS_SDKVersion ---
for sym in ("VS_Version", "VS_SDKVersion"):
    fn = getattr(sdk, sym)
    fn.restype = ctypes.c_char_p
    try:
        val = fn()
        print(f"{sym}() -> {val}")
    except Exception as e:
        print(f"{sym}() -> EXCEPTION: {e}")

# --- VS_GetClientIP ---
print()
get_ip = sdk.VS_GetClientIP
get_ip.restype = ctypes.c_char_p
try:
    val = get_ip()
    print(f"VS_GetClientIP() -> {val}")
except Exception as e:
    print(f"VS_GetClientIP() -> EXCEPTION: {e}")

# --- VS_WVRGetParameters for known and guessed keys ---
print()
get_p = sdk.VS_WVRGetParameters
get_p.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
get_p.restype  = ctypes.c_int

BUF = 256
keys = [
    b"PLAYER2_STEAMVR_ENABLE",
    b"PLAYER2_STEAMVR_IP",
    b"PLAYER2_STEAMVR_PORT",
    b"TRACKER_IP",
    b"TRACKER_PORT",
    b"TRACKER_ADDR",
    b"DEVICE_IP",
    b"LICENSE_KEY",
    b"LICENSE",
    b"SERVER_IP",
    b"SERVER_PORT",
    b"CLIENT_IP",
    b"UDP_PORT",
    b"UDP_IP",
    b"MODE",
    b"ENABLE",
    b"VERSION",
]
for key in keys:
    buf = ctypes.create_string_buffer(BUF)
    r = get_p(key, buf, BUF)
    val = buf.value.decode(errors="replace") if buf.value else "(empty)"
    print(f"  GetParam {key.decode():<30} -> r={r}  val={val!r}")

# --- try VS_Init alone (server should be running) ---
print("\nCalling VS_Init ...")
init_fn = sdk.VS_Init
init_fn.restype = ctypes.c_int
r = init_fn()
print(f"  VS_Init -> {r}")
