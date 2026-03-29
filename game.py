#!/usr/bin/env python3
"""Vector Runner — Wireframe platformer with phosphor green aesthetic."""

import math
import random
import struct
import sys
import time
import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 960, 540
FPS = 60
GRAVITY = 0.6
JUMP_FORCE = -12
DOUBLE_JUMP_FORCE = -10
SCROLL_BASE = 3.0
SCROLL_ACCEL = 0.003  # Speed increase per frame

# Colors
BG = (10, 10, 15)
GREEN = (0, 255, 0)
GREEN_DIM = (0, 100, 0)
TEAL = (0, 212, 170)
TEAL_DIM = (0, 80, 64)
WHITE = (200, 200, 200)
RED = (255, 50, 50)
AMBER = (255, 180, 0)

# Player
PLAYER_X = 120
PLAYER_SIZE = 18

# Platform generation
PLAT_MIN_W = 80
PLAT_MAX_W = 200
PLAT_H = 8
GAP_MIN = 60
GAP_MAX = 180
PLAT_Y_MIN = 200
PLAT_Y_MAX = HEIGHT - 80


# ---------------------------------------------------------------------------
# Sound generation (numpy sine waves → pygame)
# ---------------------------------------------------------------------------
def gen_sound(freq, dur_ms, volume=0.3, sweep_to=None):
    """Generate a simple sine wave sound."""
    sr = 22050
    n = int(sr * dur_ms / 1000)
    t = np.linspace(0, dur_ms / 1000, n, dtype=np.float32)
    if sweep_to:
        freqs = np.linspace(freq, sweep_to, n)
        wave = np.sin(2 * np.pi * freqs * t)
    else:
        wave = np.sin(2 * np.pi * freq * t)
    # Fade out
    fade = np.linspace(1, 0, n, dtype=np.float32) ** 2
    wave = (wave * fade * volume * 32767).astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(stereo)


# ---------------------------------------------------------------------------
# Parallax layers
# ---------------------------------------------------------------------------
class StarField:
    def __init__(self, count, speed_factor, color, size_range=(1, 2)):
        self.stars = [
            [random.randint(0, WIDTH), random.randint(0, HEIGHT),
             random.randint(*size_range)]
            for _ in range(count)
        ]
        self.speed_factor = speed_factor
        self.color = color

    def update(self, scroll_speed):
        for s in self.stars:
            s[0] -= scroll_speed * self.speed_factor
            if s[0] < -5:
                s[0] = WIDTH + random.randint(0, 50)
                s[1] = random.randint(0, HEIGHT)

    def draw(self, surface):
        for x, y, sz in self.stars:
            pygame.draw.circle(surface, self.color, (int(x), int(y)), sz)


class GeometricDebris:
    def __init__(self, count, speed_factor):
        self.shapes = []
        for _ in range(count):
            self.shapes.append({
                "x": random.randint(0, WIDTH),
                "y": random.randint(50, HEIGHT - 50),
                "sides": random.choice([3, 4, 5, 6]),
                "size": random.randint(8, 25),
                "angle": random.uniform(0, math.pi * 2),
                "spin": random.uniform(-0.02, 0.02),
            })
        self.speed_factor = speed_factor

    def update(self, scroll_speed):
        for s in self.shapes:
            s["x"] -= scroll_speed * self.speed_factor
            s["angle"] += s["spin"]
            if s["x"] < -30:
                s["x"] = WIDTH + random.randint(10, 100)
                s["y"] = random.randint(50, HEIGHT - 50)

    def draw(self, surface):
        for s in self.shapes:
            points = []
            for i in range(s["sides"]):
                a = s["angle"] + (2 * math.pi * i / s["sides"])
                px = s["x"] + s["size"] * math.cos(a)
                py = s["y"] + s["size"] * math.sin(a)
                points.append((int(px), int(py)))
            if len(points) >= 3:
                pygame.draw.polygon(surface, TEAL_DIM, points, 1)


# ---------------------------------------------------------------------------
# Game objects
# ---------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.x = PLAYER_X
        self.y = HEIGHT // 2
        self.vy = 0
        self.on_ground = False
        self.jumps_left = 2
        self.alive = True
        self.trail = []

    def jump(self):
        if self.jumps_left > 0:
            self.vy = JUMP_FORCE if self.jumps_left == 2 else DOUBLE_JUMP_FORCE
            self.jumps_left -= 1
            self.on_ground = False
            return True
        return False

    def update(self, platforms):
        self.vy += GRAVITY
        self.y += self.vy

        self.on_ground = False
        for p in platforms:
            if (self.vy >= 0 and
                    p.x < self.x + PLAYER_SIZE and
                    p.x + p.w > self.x - PLAYER_SIZE and
                    p.y <= self.y + PLAYER_SIZE <= p.y + PLAT_H + self.vy + 2):
                self.y = p.y - PLAYER_SIZE
                self.vy = 0
                self.on_ground = True
                self.jumps_left = 2

        # Trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12:
            self.trail.pop(0)

        # Death check
        if self.y > HEIGHT + 50 or self.y < -100:
            self.alive = False

    def draw(self, surface):
        # Trail (afterimage)
        for i, (tx, ty) in enumerate(self.trail):
            alpha = i / len(self.trail) if self.trail else 0
            c = (0, int(255 * alpha * 0.3), 0)
            sz = int(PLAYER_SIZE * (0.5 + 0.5 * alpha))
            self._draw_diamond(surface, tx, ty, sz, c)

        # Main player (bright + glow)
        self._draw_diamond(surface, self.x, self.y, PLAYER_SIZE + 3, GREEN_DIM)
        self._draw_diamond(surface, self.x, self.y, PLAYER_SIZE, GREEN)

    @staticmethod
    def _draw_diamond(surface, x, y, size, color):
        points = [
            (x, y - size),
            (x + size * 0.7, y),
            (x, y + size * 0.6),
            (x - size * 0.7, y),
        ]
        pygame.draw.polygon(surface, color, [(int(px), int(py)) for px, py in points], 2)


class Platform:
    def __init__(self, x, y, w):
        self.x = x
        self.y = y
        self.w = w
        self.pulse_phase = random.uniform(0, math.pi * 2)

    def update(self, scroll_speed):
        self.x -= scroll_speed
        self.pulse_phase += 0.03

    def draw(self, surface):
        pulse = 0.5 + 0.5 * math.sin(self.pulse_phase)
        c = (0, int(180 + 75 * pulse), int(140 + 30 * pulse))
        # Glow
        r_glow = pygame.Rect(int(self.x) - 1, int(self.y) - 1, int(self.w) + 2, PLAT_H + 2)
        c_glow = (0, int(60 + 30 * pulse), int(40 + 20 * pulse))
        pygame.draw.rect(surface, c_glow, r_glow, 1)
        # Main
        r = pygame.Rect(int(self.x), int(self.y), int(self.w), PLAT_H)
        pygame.draw.rect(surface, c, r, 2)


class Obstacle:
    def __init__(self, x, y, size=20, sides=6):
        self.x = x
        self.y = y
        self.size = size
        self.sides = sides
        self.angle = 0
        self.spin = random.choice([-1, 1]) * random.uniform(0.02, 0.05)

    def update(self, scroll_speed):
        self.x -= scroll_speed
        self.angle += self.spin

    def draw(self, surface):
        points = []
        for i in range(self.sides):
            a = self.angle + (2 * math.pi * i / self.sides)
            px = self.x + self.size * math.cos(a)
            py = self.y + self.size * math.sin(a)
            points.append((int(px), int(py)))
        # Glow
        pygame.draw.polygon(surface, (80, 0, 0), points, 1)
        # Inner
        inner = []
        for i in range(self.sides):
            a = self.angle + (2 * math.pi * i / self.sides)
            px = self.x + self.size * 0.7 * math.cos(a)
            py = self.y + self.size * 0.7 * math.sin(a)
            inner.append((int(px), int(py)))
        pygame.draw.polygon(surface, RED, inner, 2)

    def collides(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        return (dx * dx + dy * dy) < (self.size + PLAYER_SIZE * 0.5) ** 2


class Particle:
    def __init__(self, x, y, color=GREEN):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-4, 1)
        self.life = random.uniform(0.3, 0.8)
        self.max_life = self.life
        self.color = color

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.life -= dt

    def draw(self, surface):
        alpha = max(0, self.life / self.max_life)
        c = tuple(int(v * alpha) for v in self.color)
        pygame.draw.circle(surface, c, (int(self.x), int(self.y)), max(1, int(2 * alpha)))


# ---------------------------------------------------------------------------
# Main game
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    pygame.mixer.init(22050, -16, 2, 512)
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Vector Runner")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 20, bold=True)
    font_big = pygame.font.SysFont("monospace", 36, bold=True)

    # Generate sounds
    snd_jump = gen_sound(440, 80, 0.2)
    snd_land = gen_sound(220, 60, 0.15)
    snd_die = gen_sound(880, 400, 0.25, sweep_to=110)
    snd_milestone = gen_sound(523, 50, 0.15)

    def new_game():
        player = Player()
        platforms = [Platform(50, HEIGHT - 120, 300)]
        obstacles = []
        particles = []
        # Parallax
        stars_far = StarField(40, 0.2, (40, 40, 60))
        stars_mid = StarField(20, 0.4, (60, 60, 80), (1, 3))
        debris = GeometricDebris(8, 0.6)
        return player, platforms, obstacles, particles, stars_far, stars_mid, debris

    player, platforms, obstacles, particles, stars_far, stars_mid, debris = new_game()
    scroll_speed = SCROLL_BASE
    score = 0
    high_score = 0
    last_milestone = 0
    game_over = False
    game_over_time = 0
    next_plat_x = platforms[-1].x + platforms[-1].w + random.randint(GAP_MIN, GAP_MAX)
    next_obs_score = 500

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    if game_over:
                        if time.time() - game_over_time > 0.5:
                            player, platforms, obstacles, particles, stars_far, stars_mid, debris = new_game()
                            scroll_speed = SCROLL_BASE
                            score = 0
                            last_milestone = 0
                            game_over = False
                            next_plat_x = platforms[-1].x + platforms[-1].w + GAP_MIN
                            next_obs_score = 500
                    elif player.jump():
                        snd_jump.play()
                        for _ in range(6):
                            particles.append(Particle(player.x, player.y + PLAYER_SIZE))
                if event.key == pygame.K_ESCAPE:
                    running = False

        if not game_over:
            # Update
            scroll_speed += SCROLL_ACCEL
            score += int(scroll_speed)

            # Milestones
            if score // 1000 > last_milestone:
                last_milestone = score // 1000
                snd_milestone.play()
                for _ in range(15):
                    particles.append(Particle(
                        random.randint(100, WIDTH - 100),
                        random.randint(100, HEIGHT - 100),
                        random.choice([GREEN, TEAL, AMBER])
                    ))

            # Parallax
            stars_far.update(scroll_speed)
            stars_mid.update(scroll_speed)
            debris.update(scroll_speed)

            # Platforms
            while next_plat_x < WIDTH + 200:
                w = random.randint(PLAT_MIN_W, PLAT_MAX_W)
                y = random.randint(PLAT_Y_MIN, PLAT_Y_MAX)
                platforms.append(Platform(next_plat_x, y, w))
                next_plat_x += w + random.randint(GAP_MIN, GAP_MAX)

            for p in platforms:
                p.update(scroll_speed)
            platforms = [p for p in platforms if p.x + p.w > -50]

            # Obstacles
            if score > next_obs_score:
                # Place obstacle above a platform
                if platforms:
                    ref = random.choice([p for p in platforms if p.x > WIDTH * 0.3] or platforms)
                    sides = random.choice([5, 6, 6, 8])
                    obstacles.append(Obstacle(
                        ref.x + ref.w * random.uniform(0.2, 0.8),
                        ref.y - random.randint(30, 60),
                        random.randint(15, 25), sides
                    ))
                next_obs_score += random.randint(400, 800)

            for o in obstacles:
                o.update(scroll_speed)
            obstacles = [o for o in obstacles if o.x > -50]

            # Player
            was_airborne = not player.on_ground
            player.update(platforms)
            if was_airborne and player.on_ground:
                snd_land.play()
                for _ in range(4):
                    particles.append(Particle(player.x, player.y + PLAYER_SIZE, TEAL))

            # Collision
            for o in obstacles:
                if o.collides(player):
                    player.alive = False

            if not player.alive:
                game_over = True
                game_over_time = time.time()
                high_score = max(high_score, score)
                snd_die.play()
                for _ in range(30):
                    particles.append(Particle(player.x, player.y,
                                              random.choice([GREEN, RED, AMBER])))

            # Particles
            for p in particles:
                p.update(dt)
            particles = [p for p in particles if p.life > 0]

        # Draw
        screen.fill(BG)
        stars_far.draw(screen)
        stars_mid.draw(screen)
        debris.draw(screen)

        for p in platforms:
            p.draw(screen)
        for o in obstacles:
            o.draw(screen)
        for p in particles:
            p.draw(screen)
        if player.alive:
            player.draw(screen)

        # HUD
        score_text = font.render(f"SCORE {score:,}", True, GREEN)
        screen.blit(score_text, (WIDTH - score_text.get_width() - 15, 15))

        speed_text = font.render(f"SPD {scroll_speed:.1f}", True, TEAL_DIM)
        screen.blit(speed_text, (WIDTH - speed_text.get_width() - 15, 40))

        if high_score > 0:
            hi_text = font.render(f"HI {high_score:,}", True, GREEN_DIM)
            screen.blit(hi_text, (WIDTH - hi_text.get_width() - 15, 65))

        if game_over:
            go_text = font_big.render("GAME OVER", True, RED)
            screen.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 40))
            hint = font.render("SPACE to restart", True, WHITE)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 10))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
