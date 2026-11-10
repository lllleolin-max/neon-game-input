"""Copyable integration example. Install neon-game-input[demo] first.

Run with --mode mouse for labeled simulation, --mode neon for real hardware.
"""
import argparse
import time

import pygame
from neon_game_input import Dwell, InputMonitor, MouseInput, NeonInput, Rect, Surface
from neon_game_input.pygame_support import PygameOverlay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('mouse', 'neon'), default='mouse')
    parser.add_argument('--address')
    parser.add_argument('--frames', type=int, help='Exit after N frames for smoke checks')
    args = parser.parse_args()
    pygame.display.init()
    pygame.font.init()
    geometry = Surface()
    screen = pygame.display.set_mode((geometry.width, geometry.height))
    label = 'MOUSE SIMULATION' if args.mode == 'mouse' else 'REAL NEON'
    pygame.display.set_caption('Minimal integration | ' + label)
    overlay = PygameOverlay(geometry)
    adapter = (MouseInput() if args.mode == 'mouse' else NeonInput(geometry, address=args.address).start())
    monitor, dwell = InputMonitor(), Dwell()
    button = Rect(500, 280, 280, 160)
    font = pygame.font.Font(None, 30)
    clock, count, frames, running = pygame.time.Clock(), 0, 0, True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            now, focused = time.monotonic(), bool(pygame.key.get_focused())
            sample = (adapter.poll(pygame.mouse.get_pos(), focused=focused, now=now)
                      if args.mode == 'mouse' else adapter.poll(now, focused=focused))
            frame = monitor.step(sample, now)
            if dwell.update('button' if button.contains(frame.position) else None, frame):
                count += 1
            screen.fill((13, 25, 31))
            pygame.draw.rect(screen, (30, 76, 72), (button.x, button.y, button.width, button.height))
            for text, y in ((label, 220), (f'Dwell activations: {count}', 340),
                            ('Look away to rearm', 390), (frame.reason or 'Input ready', 470)):
                rendered = font.render(text, True, (235, 246, 241))
                screen.blit(rendered, rendered.get_rect(center=(640, y)))
            pygame.draw.rect(screen, (137, 239, 210), (500, 445, 280*dwell.progress, 5))
            overlay.cursor(screen, frame.position if frame.usable else None, now)
            if args.mode == 'neon':
                overlay.markers(screen)
            pygame.display.flip()
            frames += 1
            if args.frames and frames >= args.frames:
                running = False
            clock.tick(120)
    finally:
        if isinstance(adapter, NeonInput):
            adapter.close()
        pygame.quit()


if __name__ == '__main__':
    main()
