"""Regenerate bundled tag36h11 PNGs with the official MIT-licensed generator."""
from pathlib import Path


def main():
    import cv2
    import numpy as np
    from pupil_labs.real_time_screen_gaze import marker_generator
    folder = Path(__file__).resolve().parents[1]/"src/neon_game_input/assets"
    folder.mkdir(parents=True, exist_ok=True)
    for tag in range(4):
        pixels = np.full((10, 10), 255, dtype=np.uint8)
        pixels[1:9, 1:9] = marker_generator.generate_marker(tag, side_pixels=8, flip_x=True, flip_y=True)
        image = cv2.resize(pixels, (160, 160), interpolation=cv2.INTER_NEAREST)
        ok, data = cv2.imencode(".png", image)
        if not ok:
            raise RuntimeError("PNG encoder unavailable")
        (folder/f"tag36h11_{tag}.png").write_bytes(data.tobytes())
    print("Generated four official tag36h11 markers (160px, 16px quiet zone).")


if __name__ == "__main__":
    main()
