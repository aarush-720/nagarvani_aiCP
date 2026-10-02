"""Make printing safe on consoles that cannot show Devanagari (e.g. some Windows code pages)."""
import sys


def safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
