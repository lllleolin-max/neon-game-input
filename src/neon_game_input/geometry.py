"""Coordinates refer to the game canvas, never to the OS desktop."""
from dataclasses import dataclass
from math import hypot, isfinite

Point = tuple[float, float]


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def contains(self, point: Point | None) -> bool:
        return point is not None and (self.x <= point[0] < self.x + self.width
                                     and self.y <= point[1] < self.y + self.height)


@dataclass(frozen=True)
class Circle:
    x: float
    y: float
    radius: float

    def contains(self, point: Point | None) -> bool:
        return point is not None and hypot(point[0] - self.x, point[1] - self.y) <= self.radius


@dataclass(frozen=True)
class Surface:
    width: int = 1280
    height: int = 720
    marker_size: int = 160
    margin: int = 24

    def __post_init__(self):
        values = (self.width, self.height, self.marker_size, self.margin)
        if any(not isinstance(v, int) or isinstance(v, bool) for v in values):
            raise ValueError("Surface geometry must use integer pixels")
        if self.marker_size < 10 or self.marker_size % 10 or self.margin < 0:
            raise ValueError("marker_size must be a positive multiple of 10; margin >= 0")
        if min(self.width, self.height) <= 2 * (self.margin + self.marker_size):
            raise ValueError("Canvas is too small for four non-overlapping markers")

    def contains(self, point: Point | None) -> bool:
        return Rect(0, 0, self.width, self.height).contains(point)

    def marker_rects(self) -> dict[int, Rect]:
        m, s, w, h = self.margin, self.marker_size, self.width, self.height
        return {0: Rect(m, m, s, s), 1: Rect(w-m-s, m, s, s),
                2: Rect(w-m-s, h-m-s, s, s), 3: Rect(m, h-m-s, s, s)}

    def marker_vertices(self) -> dict[int, list[Point]]:
        # White quiet zone is one of ten cells; mapper takes BLACK corners only.
        border = self.marker_size / 10
        size = self.marker_size - 2 * border
        return {tag: [(r.x+border, r.y+border), (r.x+border+size, r.y+border),
                      (r.x+border+size, r.y+border+size), (r.x+border, r.y+border+size)]
                for tag, r in self.marker_rects().items()}

    def from_normalized(self, x: float, y: float) -> Point:
        """Official mapper: bottom-left origin. Games: top-left origin.

        Outside coordinates remain outside; clamping would turn a miss into a hit.
        """
        return x * self.width, (1-y) * self.height

    def from_viewport(self, point: Point, size: tuple[int, int]) -> Point | None:
        """Invert an aspect-preserving, centered canvas, including letterboxing."""
        if min(size) <= 0 or not all(isfinite(v) for v in (*point, *size)):
            return None
        scale = min(size[0]/self.width, size[1]/self.height)
        offset = ((size[0]-self.width*scale)/2, (size[1]-self.height*scale)/2)
        result = ((point[0]-offset[0])/scale, (point[1]-offset[1])/scale)
        return result if self.contains(result) else None
