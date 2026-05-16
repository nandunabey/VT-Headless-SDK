import ctypes
import ctypes.wintypes
import time
import os
import struct

dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)

# Try WinDLL (STDCALL) first — HTC SDKs typically use __stdcall
dll_path = os.path.join(dll_dir, "VS_PC_SDK.dll")
print(f"Loading {dll_path} ...")
try:
    sdk = ctypes.WinDLL(dll_path)
    print("  Loaded as WinDLL (STDCALL)")
except Exception as e:
    print(f"  WinDLL failed: {e}, trying CDLL ...")
    sdk = ctypes.CDLL(dll_path)
    print("  Loaded as CDLL")

# ---- VS_SDKVersion / VS_Version ----------------------------------------
try:
    ver_fn = sdk.VS_SDKVersion
    ver_fn.restype = ctypes.c_char_p
    v = ver_fn()
    print(f"VS_SDKVersion: {v}")
except Exception as e:
    print(f"VS_SDKVersion error: {e}")

try:
    ver_fn2 = sdk.VS_Version
    ver_fn2.restype = ctypes.c_char_p
    v2 = ver_fn2()
    print(f"VS_Version: {v2}")
except Exception as e:
    print(f"VS_Version error: {e}")

# ---- Step 1: Call VS_Init with various signatures -----------------------
import socket
my_ip = socket.gethostbyname(socket.gethostname())
print(f"\nThis machine IP: {my_ip}")

print("\n--- Trying VS_Init() variants ---")

# Variant A: no args
print("Variant A: VS_Init() no args ...")
try:
    fn = sdk.VS_Init
    fn.restype = ctypes.c_int
    fn.argtypes = []
    r = fn()
    print(f"  result: {r}")
except Exception as e:
    print(f"  EXCEPTION: {e}")

# Variant B: NULL hwnd
print("Variant B: VS_Init(NULL) ...")
try:
    fn2 = sdk.VS_Init
    fn2.restype = ctypes.c_int
    fn2.argtypes = [ctypes.c_void_p]
    r2 = fn2(None)
    print(f"  result: {r2}")
except Exception as e:
    print(f"  EXCEPTION: {e}")

# Variant C: license string
print("Variant C: VS_Init(b'') empty license ...")
try:
    fn3 = sdk.VS_Init
    fn3.restype = ctypes.c_int
    fn3.argtypes = [ctypes.c_char_p]
    r3 = fn3(b"")
    print(f"  result: {r3}")
except Exception as e:
    print(f"  EXCEPTION: {e}")

# ---- Step 2: WVR parameters (before and after Init) ---------------------
print("\n--- VS_WVRSetParameters ---")
set_param = sdk.VS_WVRSetParameters
set_param.restype = ctypes.c_int
set_param.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

get_param = sdk.VS_WVRGetParameters
get_param.restype = ctypes.c_int
get_param.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]

# Read current values first
buf = ctypes.create_string_buffer(256)
keys_to_read = [
    b"PLAYER2_STEAMVR_ENABLE",
    b"PLAYER2_STEAMVR_IP",
    b"PLAYER2_STEAMVR_PORT",
    b"persist.lambda.3rdhost",
    b"persist.tracking.mode.nonhmd",
    b"persist.horusd.wifi.only.mode",
]
print("Current values:")
for k in keys_to_read:
    buf = ctypes.create_string_buffer(256)
    r = get_param(k, buf, 256)
    print(f"  GET {k.decode()!r} -> r={r} val={buf.value!r}")

print("\nSetting parameters:")
r1 = set_param(b"PLAYER2_STEAMVR_ENABLE", b"1")
print(f"  PLAYER2_STEAMVR_ENABLE=1   -> r={r1}")
r2 = set_param(b"PLAYER2_STEAMVR_IP", my_ip.encode())
print(f"  PLAYER2_STEAMVR_IP={my_ip}  -> r={r2}")
r3 = set_param(b"PLAYER2_STEAMVR_PORT", b"5555")
print(f"  PLAYER2_STEAMVR_PORT=5555  -> r={r3}")

# Read back to confirm
print("\nRead-back after set:")
for k in [b"PLAYER2_STEAMVR_ENABLE", b"PLAYER2_STEAMVR_IP", b"PLAYER2_STEAMVR_PORT"]:
    buf = ctypes.create_string_buffer(256)
    r = get_param(k, buf, 256)
    print(f"  GET {k.decode()!r} -> r={r} val={buf.value!r}")

# ---- Step 3: Callback with various signatures --------------------------
print("\n--- VS_SetCallbackFunction ---")

packet_count = [0]
last_data = [None]

# Try signature: (data_ptr, data_len) — common for raw buffer callbacks
CB_A = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int)

def cb_raw(data_ptr, data_len):
    packet_count[0] += 1
    ts = time.strftime('%H:%M:%S')
    if data_ptr and data_len > 0 and data_len < 4096:
        try:
            buf = (ctypes.c_uint8 * data_len).from_address(data_ptr)
            raw = bytes(buf)
            last_data[0] = raw
            print(f"\n[{ts}] CALLBACK #{packet_count[0]} len={data_len}")
            print(f"  hex64: {raw[:64].hex()}")
            if data_len >= 4:
                u32s = struct.unpack_from(f'<{min(data_len//4,16)}I', raw)
                print(f"  u32LE: {list(u32s)}")
            if data_len >= 16:
                fls = struct.unpack_from(f'<{min(data_len//4,12)}f', raw)
                print(f"  floats: {[round(f,5) for f in fls]}")
        except Exception as ex:
            print(f"  callback decode error: {ex}")
    else:
        print(f"\n[{ts}] CALLBACK #{packet_count[0]} data_ptr={data_ptr} len={data_len}")

cb_a = CB_A(cb_raw)

set_cb = sdk.VS_SetCallbackFunction
set_cb.restype = ctypes.c_int
set_cb.argtypes = [ctypes.c_void_p]
r4 = set_cb(cb_a)
print(f"  VS_SetCallbackFunction(raw_cb) result: {r4}")

# ---- Step 4: wait for any callbacks ------------------------------------
print("\nWaiting 30s for pose callbacks. Move tracker now...")
for i in range(30):
    time.sleep(1)
    print(f"  [{i+1:2d}s] callbacks={packet_count[0]}", flush=True)
    if packet_count[0] > 3:
        print("  POSE DATA FLOWING!")
        break

print(f"\nTotal callbacks: {packet_count[0]}")
if last_data[0]:
    print(f"Last packet ({len(last_data[0])} bytes):")
    print(f"  hex: {last_data[0].hex()}")
