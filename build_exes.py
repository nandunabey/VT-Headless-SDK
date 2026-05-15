"""
build_exes.py — VUT Robotics SDK PyInstaller build script
==========================================================
Builds three standalone Windows executables using the
PyInstaller programmatic API (no subprocess calls).

Usage:
    python build_exes.py

Output: dist/vut-status.exe, dist/vut-daemon.exe, dist/vut-pose.exe
"""

import sys
import time
from pathlib import Path

try:
    import PyInstaller.__main__ as _pyi
except ImportError:
    sys.exit("PyInstaller not found — run: pip install pyinstaller")

SPECS = [
    ('vut-status.spec',  'vut-status.exe'),
    ('vut-daemon.spec',  'vut-daemon.exe'),
    ('vut-pose.spec',    'vut-pose.exe'),
]

DIST_DIR  = Path('dist')
BUILD_DIR = Path('build')


def build_spec(spec_file: str, exe_name: str) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  Building {exe_name}")
    print(f"  Spec:    {spec_file}")
    print(f"{'=' * 60}")
    t0 = time.time()

    try:
        _pyi.run([
            spec_file,
            '--distpath', str(DIST_DIR),
            '--workpath',  str(BUILD_DIR),
            '--noconfirm',
            '--clean',
        ])
    except SystemExit as e:
        if e.code != 0:
            print(f"\n  FAILED: {exe_name} (exit code {e.code})", file=sys.stderr)
            return False

    elapsed = time.time() - t0
    out = DIST_DIR / exe_name
    if out.exists():
        size_mb = out.stat().st_size / (1024 * 1024)
        print(f"\n  OK  {exe_name}  ({size_mb:.1f} MB)  built in {elapsed:.0f}s")
        return True
    else:
        print(f"\n  FAILED: {exe_name} not found in {DIST_DIR}", file=sys.stderr)
        return False


def main() -> None:
    print("VUT Robotics SDK — PyInstaller build")
    print(f"Python      : {sys.version.split()[0]}")
    print(f"Output dir  : {DIST_DIR.resolve()}")

    DIST_DIR.mkdir(exist_ok=True)
    BUILD_DIR.mkdir(exist_ok=True)

    results = {}
    for spec, exe in SPECS:
        results[exe] = build_spec(spec, exe)

    print(f"\n{'=' * 60}")
    print("  Build summary")
    print(f"{'=' * 60}")
    all_ok = True
    for exe, ok in results.items():
        status = "OK " if ok else "FAIL"
        print(f"  [{status}]  {exe}")
        if not ok:
            all_ok = False

    if not all_ok:
        sys.exit(1)

    print("\n  All executables built successfully.")
    print(f"  Location: {DIST_DIR.resolve()}")


if __name__ == '__main__':
    main()
