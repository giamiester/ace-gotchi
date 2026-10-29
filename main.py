"""Ace Gotchi - an Ace Combat themed pocket aircraft.

Double-click "Ace Gotchi.vbs" to launch without a console window.
"""

import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from acegotchi.app import run  # noqa: E402

if __name__ == "__main__":
    run(BASE)
