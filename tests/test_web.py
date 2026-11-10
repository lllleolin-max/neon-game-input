import time
import unittest
from unittest.mock import Mock

from neon_game_input import Sample

try:
    from aiohttp import WSServerHandshakeError
    from aiohttp.test_utils import TestClient, TestServer
    from neon_game_input.web import create_app
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Install the browser extra for bridge tests')
class WebTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(TestServer(create_app('mouse')))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_health_and_complete_offline_assets(self):
        result = await self.client.get('/health')
        self.assertEqual((await result.json())['game_workers'],0)
        for path in ('/', '/app.mjs', '/input.mjs', '/style.css', '/tag36h11_0.png', '/config'):
            response = await self.client.get(path)
            self.assertEqual(response.status,200,path)
            self.assertNotIn('Access-Control-Allow-Origin',response.headers)
        self.assertEqual((await (await self.client.get('/config')).json())['mode'],'mouse')

    async def test_source_files_and_parent_paths_are_not_served(self):
        for path in ('/pyproject.toml','/.env','/neon.py','/../LICENSE','/assets/../../LICENSE'):
            self.assertEqual((await self.client.get(path)).status,404)

    async def test_non_loopback_host_and_cross_origin_ws_rejected(self):
        self.assertEqual((await self.client.get('/config',headers={'Host':'evil.example'})).status,403)
        for origin in ('http://evil.example','null'):
            with self.assertRaises(WSServerHandshakeError) as error:
                await self.client.ws_connect('/samples',headers={'Origin':origin})
            self.assertEqual(error.exception.status,403)

    async def test_same_origin_ping_and_invalid_messages(self):
        origin = str(self.client.make_url('/')).rstrip('/')
        async with self.client.ws_connect('/samples',headers={'Origin':origin}) as ws:
            await ws.send_str('invalid-json')
            await ws.send_json([])
            await ws.send_json({'type':'ping','id':17})
            self.assertEqual(await ws.receive_json(timeout=2),{'type':'pong','id':17})

    async def test_only_sample_metadata_is_relayed_with_lifecycle_cleanup(self):
        adapter = Mock()
        adapter.poll.return_value = Sample('neon',1,(640,360),True,True,time.monotonic(),123,markers=(0,1,2,3))
        client = TestClient(TestServer(create_app('neon',adapter=adapter)))
        await client.start_server()
        try:
            origin = str(client.make_url('/')).rstrip('/')
            async with client.ws_connect('/samples',headers={'Origin':origin}) as ws:
                value = await ws.receive_json(timeout=2)
                self.assertEqual(value['source'],'neon')
                self.assertEqual(value['position'],[640,360])
                self.assertGreaterEqual(value['age'],0)
                self.assertEqual(set(value), {'type','source','sequence','position','valid','mapped','age','reason','markers'})
        finally:
            await client.close()
        adapter.start.assert_called_once()
        adapter.close.assert_called_once()
