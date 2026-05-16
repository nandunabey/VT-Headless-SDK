import ctypes
import os
import sys

dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)
sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
print("DLL loaded OK")
sys.stdout.flush()

step = int(sys.argv[1]) if len(sys.argv) > 1 else 99

if step >= 1:
    print("Step 1: VS_SDKVersion ...")
    sys.stdout.flush()
    fn = sdk.VS_SDKVersion
    fn.restype = ctypes.c_char_p
    print(f"  -> {fn()}")
    sys.stdout.flush()

if step >= 2:
    print("Step 2: VS_Version ...")
    sys.stdout.flush()
    fn = sdk.VS_Version
    fn.restype = ctypes.c_char_p
    print(f"  -> {fn()}")
    sys.stdout.flush()

if step >= 3:
    print("Step 3: VS_GetClientIP ...")
    sys.stdout.flush()
    fn = sdk.VS_GetClientIP
    fn.restype = ctypes.c_char_p
    print(f"  -> {fn()}")
    sys.stdout.flush()

if step >= 4:
    print("Step 4: VS_WVRGetParameters (first key) ...")
    sys.stdout.flush()
    fn = sdk.VS_WVRGetParameters
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    fn.restype = ctypes.c_int
    buf = ctypes.create_string_buffer(256)
    r = fn(b"PLAYER2_STEAMVR_ENABLE", buf, 256)
    print(f"  -> r={r}  val={buf.value!r}")
    sys.stdout.flush()

if step >= 5:
    print("Step 5: VS_Init ...")
    sys.stdout.flush()
    fn = sdk.VS_Init
    fn.restype = ctypes.c_int
    r = fn()
    print(f"  -> {r}")
    sys.stdout.flush()

print("ALL DONE")
