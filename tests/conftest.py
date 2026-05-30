"""Test configuration for Vector Runner.

These tests exercise only pure game logic (state machines, collision math,
position updates, geometry/parameter invariants). They never open a window or
audio device. We still set SDL's dummy drivers so that importing ``game`` —
which imports ``pygame`` at module load — works on headless CI runners.

Nothing here touches ``game.main()``, ``gen_sound`` (needs the mixer), or any
``draw`` method (needs a display surface).
"""

import os

# Must be set before pygame is imported anywhere.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
