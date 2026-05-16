import pefile
import sys

dll_path = r"C:\Users\vive_\Downloads\VBPConsole.2.6.0.40.PUBLIC.WW\ViveTrackerServer\VS_PC_SDK.dll"

try:
    import pefile
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pefile", "-q"])
    import pefile

pe = pefile.PE(dll_path)
print(f"Machine: {hex(pe.FILE_HEADER.Machine)}  ({'x64' if pe.FILE_HEADER.Machine == 0x8664 else 'x86'})")
print(f"\nExported functions:")
if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
    exports = sorted(
        [e.name.decode() for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name],
        key=lambda s: s.lower()
    )
    for name in exports:
        print(f"  {name}")
    print(f"\nTotal: {len(exports)} exports")
else:
    print("  No export table found")
