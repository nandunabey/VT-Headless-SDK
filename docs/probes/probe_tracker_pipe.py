"""
Connect directly to \\.\pipe\TrackerNamedPipe and dump what the server sends.
"""
import ctypes, ctypes.wintypes, time

GENERIC_READ  = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000

k32 = ctypes.windll.kernel32

pipe_name = r"\\.\pipe\TrackerNamedPipe"
print(f"Connecting to {pipe_name} ...")

handle = k32.CreateFileW(
    pipe_name,
    GENERIC_READ | GENERIC_WRITE,
    0, None,
    OPEN_EXISTING,
    0, None
)
INVALID = ctypes.c_void_p(-1).value
if handle == INVALID:
    err = k32.GetLastError()
    print(f"  FAILED to open pipe. GetLastError={err}")
    raise SystemExit(1)

print(f"  Pipe opened! handle=0x{handle:x}")

# Set pipe to message mode
PIPE_READMODE_MESSAGE = 2
mode = ctypes.c_ulong(PIPE_READMODE_MESSAGE)
k32.SetNamedPipeHandleState(handle, ctypes.byref(mode), None, None)

# Try reading for 10 seconds
buf = ctypes.create_string_buffer(4096)
bytes_read = ctypes.c_ulong(0)
print("Reading messages from pipe (10s)...")
deadline = time.time() + 10
msg_count = 0

while time.time() < deadline:
    ok = k32.ReadFile(handle, buf, 4096, ctypes.byref(bytes_read), None)
    if ok and bytes_read.value > 0:
        data = bytes(buf.raw[:bytes_read.value])
        msg_count += 1
        print(f"\n  MSG #{msg_count}  len={bytes_read.value}")
        print(f"  hex: {data[:64].hex()}")
        try:
            print(f"  ascii: {data[:64].decode('ascii', errors='replace')}")
        except Exception:
            pass
    else:
        err = k32.GetLastError()
        if err == 109:  # ERROR_BROKEN_PIPE
            print("  Pipe closed by server.")
            break
        elif err == 0:
            continue
        else:
            print(f"  ReadFile error: {err}")
            time.sleep(0.1)

k32.CloseHandle(handle)
print(f"\nDone. Messages received: {msg_count}")
