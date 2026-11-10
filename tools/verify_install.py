"""Run with an isolated wheel environment: python -I tools/verify_install.py."""
import asyncio
from importlib.resources import files
import json
import os
import subprocess
import sys

import neon_game_input


async def verify_web():
    from aiohttp.test_utils import TestClient, TestServer
    from neon_game_input.web import create_app
    async with TestClient(TestServer(create_app('mouse'))) as client:
        health = await (await client.get('/health')).json()
        assert health['game_workers'] == 0
        for name in ('/', '/app.mjs', '/input.mjs', '/style.css', '/tag36h11_0.png'):
            response = await client.get(name)
            assert response.status == 200, name
            assert await response.read(), name
    return health


def main():
    package = files('neon_game_input')
    assert package.joinpath('assets/tag36h11_3.png').read_bytes().startswith(b'\x89PNG')
    assert package.joinpath('browser/app.mjs').is_file()
    env = dict(os.environ, SDL_VIDEODRIVER='dummy')
    desktop = subprocess.run([sys.executable, '-I', '-m', 'neon_game_input.demo', '--frames', '3'],
                             env=env, capture_output=True, text=True)
    if desktop.returncode:
        raise RuntimeError(desktop.stderr)
    print(json.dumps({'version': neon_game_input.__version__, 'imported_from': neon_game_input.__file__,
                      'desktop_smoke': 'passed', 'web_health': asyncio.run(verify_web()),
                      'bundled_markers_and_browser_assets': 'passed'}, indent=2))


if __name__ == '__main__':
    main()
