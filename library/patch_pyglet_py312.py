"""
11.18.26: added.

PsychoPy pins pyglet 1.4.11 on Windows. In Python 3.12 ctypes.wintypes.BYTE
became unsigned (c_ubyte), but pyglet 1.4.11 still hands a signed c_byte
buffer to GdipCreateBitmapFromScan0, whose argtypes use POINTER(BYTE). So
drawing any TextStim crashes with:

    ctypes.ArgumentError: argument 5: TypeError:
    expected LP_c_ubyte instance instead of c_byte_Array_...

This patches that one line in the installed pyglet/font/win32.py to build
the buffer from BYTE, which matches the argtypes on every Python version.
Safe to run more than once. Run it after `pip install -e .`, like
patch_python_vlc.py.
"""

import importlib.util
import sys
from pathlib import Path

OLD = "self._data = (ctypes.c_byte * (4 * width * height))()"
NEW = "self._data = (BYTE * (4 * width * height))()  # patched by rcp_task_acquisition (Python 3.12 BYTE is unsigned)"


def main():
    if sys.platform != "win32":
        print("Not Windows, skipping pyglet patch.")
        return 0
    if sys.version_info[:2] < (3, 12):
        print("Detected Python version < 3.12, skipping pyglet patch.")
        return 0

    spec = importlib.util.find_spec("pyglet")
    if spec is None or not spec.submodule_search_locations:
        print("pyglet is not installed. Have you `pip install -e .` the project?")
        return 1
    target = Path(list(spec.submodule_search_locations)[0]) / "font" / "win32.py"
    text = target.read_text(encoding="utf-8")

    if NEW in text:
        print(f"pyglet already patched: {target}")
        return 0
    if text.count(OLD) != 1:
        print(f"Unexpected pyglet version, line not found; nothing changed: {target}")
        return 1

    target.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print(f"pyglet patched: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
