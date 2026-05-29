# Vector Runner

A small auto-scrolling platformer with a vector-wireframe, phosphor-green aesthetic. Written in Python with pygame in a single file.

## What it does

You control a diamond-shaped player on an endlessly auto-scrolling course made of procedurally generated platforms. Jump (and double-jump) across gaps while avoiding spinning polygon obstacles. The scroll speed ramps up over time, so the score climbs and the difficulty rises the longer you survive. Falling off the screen or hitting an obstacle ends the run.

Visuals and audio are generated entirely in code:

- Wireframe rendering (diamonds, polygons, pulsing platform outlines) on a near-black background in green/teal "phosphor" tones.
- A motion trail / afterimage behind the player.
- Parallax background layers: two star fields and rotating geometric debris scrolling at different speeds.
- Particle bursts on jump, landing, milestones, and death.
- Sound effects synthesized at runtime as sine waves via numpy (jump, land, death sweep, milestone chime) — no audio asset files.

A score, current speed, and high score are shown in the HUD. The high score is kept in memory for the session only (not saved to disk).

## Status

Complete and runnable as a self-contained mini-game. It is a single-file hobby project (`game.py`, ~450 lines); there is no menu system, no persistence, and no test suite.

## Requirements

- Python 3
- [pygame](https://www.pygame.org/)
- [numpy](https://numpy.org/) (used to synthesize the sound effects)

```bash
pip install pygame numpy
```

## Run

```bash
python3 game.py
```

A 960x540 window opens.

## Controls

- **Space / Up / W** — jump (press again in the air for a double jump); also restarts after game over
- **Esc** — quit

## Notes / limitations

- Window size, frame rate, gravity, jump force, scroll speed, and generation parameters are hard-coded constants near the top of `game.py` — edit there to tweak.
- High score resets when you close the window; nothing is written to disk.
- Requires a display and audio device (uses pygame's display and mixer); it won't run headless.
