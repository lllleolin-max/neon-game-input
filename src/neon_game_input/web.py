"""Loopback-only sample bridge. The browser runs and renders the entire game."""
import argparse
import asyncio
from importlib.resources import files
import json
import time

from . import NeonInput, Surface


def create_app(mode="mouse", *, address=None, port=8080, adapter=None):
    from aiohttp import web
    if mode not in {"mouse", "neon"}:
        raise ValueError("mode must be mouse or neon")
    surface = Surface()
    neon = adapter if adapter is not None else (NeonInput(surface, address=address, port=port) if mode == "neon" else None)
    sockets = set()

    @web.middleware
    async def local_only(request, handler):
        host = request.host.split(":")[0].lower()
        if host not in {"127.0.0.1", "localhost"}:
            raise web.HTTPForbidden(text="Loopback host required")
        response = await handler(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        return response

    app = web.Application(middlewares=[local_only])

    async def resource(request):
        name = request.match_info.get("name", "index.html")
        allowed = {"index.html": "text/html", "app.mjs": "text/javascript",
                   "input.mjs": "text/javascript", "style.css": "text/css"}
        if name in allowed:
            return web.Response(body=files("neon_game_input").joinpath("browser", name).read_bytes(),
                                content_type=allowed[name])
        if name in {f"tag36h11_{tag}.png" for tag in range(4)}:
            return web.Response(body=files("neon_game_input").joinpath("assets", name).read_bytes(),
                                content_type="image/png")
        raise web.HTTPNotFound()

    async def config(request):
        return web.json_response({"mode": mode, "width": surface.width, "height": surface.height,
                                  "marker_size": surface.marker_size, "margin": surface.margin})

    async def health(request):
        return web.json_response({"status": "ok", "game_workers": 0, "mode": mode})

    async def samples(request):
        # Prevent a remote website from reading local eye data via a WebSocket.
        if request.headers.get("Origin") != f"http://{request.host}":
            raise web.HTTPForbidden(text="Same-origin browser required")
        ws = web.WebSocketResponse(heartbeat=10, max_msg_size=2048)
        await ws.prepare(request)
        sockets.add(ws)

        async def publish():
            previous = None
            while not ws.closed:
                now = time.monotonic()
                sample = neon.poll(now) if neon else None
                if sample and sample.sequence != previous:
                    previous = sample.sequence
                    await ws.send_json({"type": "sample", "source": sample.source,
                                        "sequence": sample.sequence, "position": sample.position,
                                        "valid": sample.valid, "mapped": sample.mapped,
                                        "age": max(0, now-sample.received_at), "reason": sample.reason,
                                        "markers": sample.markers})
                await asyncio.sleep(1/60)

        sender = asyncio.create_task(publish())
        try:
            async for message in ws:
                if message.type == web.WSMsgType.TEXT:
                    try:
                        value = json.loads(message.data)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(value, dict) and value.get("type") == "ping" and isinstance(value.get("id"), int):
                        await ws.send_json({"type": "pong", "id": value["id"]})
        finally:
            sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)
            sockets.discard(ws)
        return ws

    async def shutdown(app):
        for ws in tuple(sockets):
            await ws.close(code=1001, message=b"Server shutting down")

    async def lifecycle(app):
        if neon:
            neon.start()
        yield
        if neon:
            neon.close()

    app.cleanup_ctx.append(lifecycle)
    app.on_shutdown.append(shutdown)
    app.router.add_get("/", resource)
    app.router.add_get("/config", config)
    app.router.add_get("/health", health)
    app.router.add_get("/samples", samples)
    app.router.add_get("/{name}", resource)
    return app


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("mouse", "neon"), default="mouse")
    parser.add_argument("--address", help="Companion address; omitted = mDNS discovery")
    parser.add_argument("--companion-port", type=int, default=8080)
    parser.add_argument("--port", type=int, default=8765, help="Local HTTP port")
    args = parser.parse_args(argv)
    try:
        from aiohttp import web
    except ImportError:
        parser.exit(1, "Install the browser extra: python -m pip install -e '.[browser]'\n")
    print(f"Open http://127.0.0.1:{args.port} | " + ("MOUSE SIMULATION" if args.mode == "mouse" else "REAL NEON"))
    web.run_app(create_app(args.mode, address=args.address, port=args.companion_port),
                host="127.0.0.1", port=args.port, access_log=None)


if __name__ == "__main__":
    main()
