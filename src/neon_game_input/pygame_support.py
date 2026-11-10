"""Optional Pygame drawing helpers; the input core does not import Pygame."""
from collections import deque
from importlib.resources import files
from math import hypot

from .geometry import Surface


class PygameOverlay:
    def __init__(self, surface: Surface):
        import pygame
        self.pg = pygame
        self.surface = surface
        self.history = deque(maxlen=40)
        self.tags = {}
        for tag in surface.marker_rects():
            path = files("neon_game_input").joinpath(f"assets/tag36h11_{tag}.png")
            with path.open("rb") as stream:
                texture = pygame.image.load(stream).convert()
            self.tags[tag] = pygame.transform.scale(texture, (surface.marker_size,)*2)

    def markers(self, canvas):
        """Draw last, in pure black/white. Do not cover the quiet zones."""
        for tag, rect in self.surface.marker_rects().items():
            canvas.blit(self.tags[tag], (rect.x, rect.y))

    def cursor(self, canvas, position, now):
        if position is None or not self.surface.contains(position):
            self.history.clear()
            return
        while self.history and now-self.history[0][1] > 0.25:
            self.history.popleft()
        if not self.history or hypot(position[0]-self.history[-1][0][0],
                                     position[1]-self.history[-1][0][1]) > 2:
            self.history.append((position, now))
        for point, stamp in self.history:
            fade = max(0, 1-(now-stamp)/0.25)
            self.pg.draw.circle(canvas, (int(60*fade), int(170*fade), int(150*fade)),
                                point, max(1, int(5*fade)))
        self.pg.draw.circle(canvas, (239, 255, 249), position, 7, 2)
        self.pg.draw.circle(canvas, (139, 244, 213), position, 2)
