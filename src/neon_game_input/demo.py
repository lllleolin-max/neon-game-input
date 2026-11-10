"""Playable Pygame demo: collect circles by looking at them, without clicking."""
import argparse
from pathlib import Path
import time
import math

from . import InputMonitor, MouseInput, NeonInput, Surface
from .example_game import TargetGame, status_text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mouse", "neon"), default="mouse")
    parser.add_argument("--address", help="Companion host/IP; omit for mDNS discovery")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--frames", type=int, help="Exit after N frames (smoke checks)")
    parser.add_argument("--screenshot", type=Path, help="Save the last rendered frame on exit")
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("duration must be positive and finite")
    try:
        import pygame
    except ImportError:
        parser.exit(1, "Install the demo extra: python -m pip install -e '.[demo]'\n")
    from .pygame_support import PygameOverlay
    pygame.display.init()
    pygame.font.init()
    surface = Surface()
    size = (surface.width, surface.height)
    screen = pygame.display.set_mode((0, 0) if args.fullscreen else size,
                                    pygame.FULLSCREEN if args.fullscreen else 0)
    pygame.display.set_caption("Neon Game Input | " + ("MOUSE SIMULATION" if args.mode == "mouse" else "REAL NEON"))
    canvas = pygame.Surface(size)
    overlay = PygameOverlay(surface)
    fonts = {n: pygame.font.Font(None, n) for n in (22, 26, 32, 58)}
    adapter = NeonInput(surface, address=args.address, port=args.port).start() if args.mode == "neon" else MouseInput()
    monitor, game, clock = InputMonitor(), TargetGame(surface, args.duration), pygame.time.Clock()
    frames, running = 0, True

    def text(value, position, size=26, color=(172, 188, 190)):
        label = fonts[size].render(value, True, color)
        canvas.blit(label, label.get_rect(center=position))

    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            now = time.monotonic()
            focused = bool(pygame.key.get_focused())
            if args.mode == "mouse":
                position = surface.from_viewport(pygame.mouse.get_pos(), screen.get_size())
                sample = adapter.poll(position, focused=focused, now=now)
            else:
                sample = adapter.poll(now, focused=focused)
            frame = monitor.step(sample, now)
            game.update(frame)
            canvas.fill((13, 25, 31))
            # Restrained grid gives a stable background without competing with the tags.
            for x in range(40, surface.width, 40):
                for y in range(40, surface.height, 40):
                    pygame.draw.circle(canvas, (24, 40, 45), (x, y), 1)
            text("NEON / GAME INPUT", (640, 66), 26, (137, 239, 210))
            mode_label = "MOUSE SIMULATION - NO NEON CONNECTED" if args.mode == "mouse" else "REAL NEON - COMPANION REQUIRED"
            text(mode_label, (640, 101), 22)
            headline = {"ready": "Look. Hold. Collect.", "playing": f"{game.score:02d}  collected",
                        "result": f"Round complete - {game.score} collected"}[game.state]
            text(headline, (640, 163), 58, (235, 246, 241))
            target = game.target
            point = (target.x, target.y)
            pygame.draw.circle(canvas, (30, 76, 72), point, target.radius)
            pygame.draw.circle(canvas, (137, 239, 210), point, target.radius, 2)
            if game.dwell.progress:
                bounds = pygame.Rect(0, 0, 2*(target.radius+10), 2*(target.radius+10))
                bounds.center = point
                pygame.draw.arc(canvas, (242, 211, 134), bounds,
                                math.pi/2-2*math.pi*game.dwell.progress, math.pi/2, 5)
            text({"ready": "START", "playing": "+1", "result": "AGAIN"}[game.state], point, 26, (235, 246, 241))
            text(f"{math.ceil(game.remaining):02d}s active time  /  ESC to exit", (640, 580), 32)
            text(status_text(frame, args.mode), (640, 625), 22)
            if not game.dwell.armed:
                text("Look away from the target to rearm", (640, 652), 22, (242, 211, 134))
            overlay.cursor(canvas, frame.position if frame.usable else None, now)
            if args.mode == "neon":
                overlay.markers(canvas)
            # Nearest-neighbor scaling preserves the pure black/white marker patterns.
            scale = min(screen.get_width()/surface.width, screen.get_height()/surface.height)
            drawn_size = (round(surface.width*scale), round(surface.height*scale))
            screen.fill((5, 10, 13))
            screen.blit(pygame.transform.scale(canvas, drawn_size),
                        ((screen.get_width()-drawn_size[0])//2, (screen.get_height()-drawn_size[1])//2))
            pygame.display.flip()
            frames += 1
            if args.frames and frames >= args.frames:
                running = False
            clock.tick(120)
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(screen, str(args.screenshot))
    finally:
        if isinstance(adapter, NeonInput):
            adapter.close()
        pygame.quit()


if __name__ == "__main__":
    main()
