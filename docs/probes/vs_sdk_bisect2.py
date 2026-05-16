import ctypes
import os
import sys

dll_dir = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer"
os.add_dll_directory(dll_dir)
sdk = ctypes.CDLL(os.path.join(dll_dir, "VS_PC_SDK.dll"))
print("DLL loaded OK")
sys.stdout.flush()

step = sys.argv[1] if len(sys.argv) > 1 else "all"

if step in ("ip", "all"):
    print("VS_GetClientIP ...")
    sys.stdout.flush()
    fn = sdk.VS_GetClientIP
    fn.restype = ctypes.c_char_p
    try:
        print(f"  -> {fn()}")
    except Exception as e:
        print(f"  EXCEPTION: {e}")
    sys.stdout.flush()

if step in ("getp", "all"):
    print("VS_WVRGetParameters (PLAYER2_STEAMVR_ENABLE) ...")
    sys.stdout.flush()
    fn = sdk.VS_WVRGetParameters
    fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    fn.restype = ctypes.c_int
    buf = ctypes.create_string_buffer(256)
    r = fn(b"PLAYER2_STEAMVR_ENABLE", buf, 256)
    print(f"  -> r={r}  val={buf.value!r}")
    sys.stdout.flush()

if step in ("init", "all"):
    print("VS_Init ...")
    sys.stdout.flush()
    fn = sdk.VS_Init
    fn.restype = ctypes.c_int
    r = fn()
    print(f"  -> {r}")
    sys.stdout.flush()

print("DONE")
