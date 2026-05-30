"""Pure-logic unit tests for Vector Runner.

Scope: only deterministic, display-free game logic — the jump state machine,
obstacle collision math, position/scroll updates, death detection, particle
physics, and a few generation-parameter invariants.

Explicitly out of scope (and untested here): rendering (any ``draw`` method),
audio synthesis (``gen_sound`` needs the pygame mixer), and the ``main`` loop.
Those require a real display/audio device and live model/runtime state.
"""

import math

import game


# ---------------------------------------------------------------------------
# Player.jump — state machine
# ---------------------------------------------------------------------------
def test_player_starts_with_two_jumps():
    assert game.Player().jumps_left == 2


def test_jump_consumes_jumps_and_returns_true_until_exhausted():
    p = game.Player()
    assert p.jump() is True
    assert p.jumps_left == 1
    assert p.jump() is True
    assert p.jumps_left == 0
    # No jumps left -> returns False and does not go negative.
    assert p.jump() is False
    assert p.jumps_left == 0


def test_first_jump_uses_full_force_second_uses_double_jump_force():
    p = game.Player()
    p.jump()
    assert p.vy == game.JUMP_FORCE
    p.jump()
    assert p.vy == game.DOUBLE_JUMP_FORCE


def test_jump_clears_on_ground():
    p = game.Player()
    p.on_ground = True
    p.jump()
    assert p.on_ground is False


# ---------------------------------------------------------------------------
# Obstacle.collides — circle-vs-point distance math
# ---------------------------------------------------------------------------
def test_collides_true_when_overlapping():
    o = game.Obstacle(100, 100, size=20)
    p = game.Player()
    p.x, p.y = 100, 100
    assert o.collides(p) is True


def test_collides_false_when_far_away():
    o = game.Obstacle(100, 100, size=20)
    p = game.Player()
    p.x, p.y = 1000, 1000
    assert o.collides(p) is False


def test_collides_boundary_just_inside_and_just_outside():
    o = game.Obstacle(0, 0, size=20)
    p = game.Player()
    radius = o.size + game.PLAYER_SIZE * 0.5  # collision threshold distance
    # Just inside the threshold collides; just outside does not.
    p.x, p.y = radius - 1, 0
    assert o.collides(p) is True
    p.x, p.y = radius + 1, 0
    assert o.collides(p) is False


# ---------------------------------------------------------------------------
# Player.update — gravity, landing, death
# ---------------------------------------------------------------------------
def test_update_applies_gravity_when_airborne():
    p = game.Player()
    p.y = game.HEIGHT // 2
    p.vy = 0.0
    p.update([])  # no platforms underneath
    assert p.vy == game.GRAVITY
    assert p.on_ground is False


def test_update_lands_on_platform_and_resets_state():
    p = game.Player()
    plat = game.Platform(0, 300, 400)
    p.x = 100
    p.y = plat.y - game.PLAYER_SIZE - 1  # just above the platform top
    p.vy = 5.0
    p.jumps_left = 0
    p.update([plat])
    assert p.on_ground is True
    assert p.vy == 0
    assert p.jumps_left == 2
    assert p.y == plat.y - game.PLAYER_SIZE


def test_update_no_landing_when_moving_upward():
    p = game.Player()
    plat = game.Platform(0, 300, 400)
    p.x = 100
    p.y = plat.y - game.PLAYER_SIZE - 1
    p.vy = -5.0  # moving up: collision check requires vy >= 0
    p.update([plat])
    assert p.on_ground is False


def test_update_marks_dead_when_below_screen():
    p = game.Player()
    p.y = game.HEIGHT + 100
    p.update([])
    assert p.alive is False


def test_update_marks_dead_when_above_screen():
    p = game.Player()
    p.y = -200
    p.vy = -5.0
    p.update([])
    assert p.alive is False


def test_trail_is_capped_at_twelve_points():
    p = game.Player()
    for _ in range(50):
        p.update([])
    assert len(p.trail) <= 12


# ---------------------------------------------------------------------------
# Scrolling updates — Platform / Obstacle move left by scroll speed
# ---------------------------------------------------------------------------
def test_platform_update_scrolls_left():
    plat = game.Platform(500, 300, 100)
    x0 = plat.x
    plat.update(3.0)
    assert plat.x == x0 - 3.0


def test_obstacle_update_scrolls_left_and_spins():
    o = game.Obstacle(500, 300, size=20)
    x0, a0 = o.x, o.angle
    o.update(4.0)
    assert o.x == x0 - 4.0
    assert o.angle == a0 + o.spin


# ---------------------------------------------------------------------------
# Particle.update — physics
# ---------------------------------------------------------------------------
def test_particle_update_integrates_position_and_gravity():
    p = game.Particle(10, 20)
    vx0, vy0 = p.vx, p.vy
    p.update(0.1)
    assert p.x == 10 + vx0
    # y advanced by the pre-update vy; vy then gains the per-frame 0.1.
    assert p.y == 20 + vy0
    assert p.vy == vy0 + 0.1


def test_particle_life_decreases_by_dt():
    p = game.Particle(0, 0)
    life0 = p.life
    p.update(0.25)
    assert p.life == life0 - 0.25


# ---------------------------------------------------------------------------
# Generation-parameter invariants (catch accidental constant edits)
# ---------------------------------------------------------------------------
def test_platform_generation_bounds_are_sane():
    assert game.PLAT_MIN_W <= game.PLAT_MAX_W
    assert game.GAP_MIN <= game.GAP_MAX
    assert game.PLAT_Y_MIN < game.PLAT_Y_MAX
    assert game.PLAT_Y_MAX <= game.HEIGHT


def test_double_jump_force_is_weaker_than_first_jump():
    # Both are negative (upward); the double jump should be a smaller impulse.
    assert game.JUMP_FORCE < 0
    assert game.DOUBLE_JUMP_FORCE < 0
    assert abs(game.DOUBLE_JUMP_FORCE) < abs(game.JUMP_FORCE)


def test_obstacle_vertices_form_a_closed_regular_polygon():
    # Re-derive a vertex the way Obstacle.draw does and check the radius.
    o = game.Obstacle(50, 60, size=20, sides=6)
    for i in range(o.sides):
        a = o.angle + (2 * math.pi * i / o.sides)
        px = o.x + o.size * math.cos(a)
        py = o.y + o.size * math.sin(a)
        dist = math.hypot(px - o.x, py - o.y)
        assert math.isclose(dist, o.size, rel_tol=1e-9)
