import asyncio
import json
import logging

import aiohttp
from aiohttp import web

from currency_pairs import Point, Assets
from watchdog import Seconds, Minutes


class PointJsonSerializer(dict):
    def __init__(self, point: Point):
        super().__init__(**point._asdict())


async def index_handler(request):
    rates = await request.app['db'].get(Assets['EURUSD'], offset=Seconds(30 * 60))
    return web.json_response(tuple(map(PointJsonSerializer, rates)))


async def ws_handle(request):
    client = WSClientHandler(request)
    try:
        await client.run()
    except asyncio.CancelledError:
        await client.stop()


class WSClientHandler:
    def __init__(self, request: web.Request):
        self._request = request
        self._ws: web.WebSocketResponse = web.WebSocketResponse()
        self._cancel_subscribe = None
        self.logger = logging.getLogger(str(self.__class__))

    async def run(self):
        await self._ws.prepare(self._request)
        async for msg in self._ws_listen():
            try:
                await self._handle_message(msg)

            except (ValueError, json.JSONDecodeError) as e:
                self.logger.exception(e)
                print(msg)
                await self._ws.send_json({'error': 'unsupported message format'})

            except KeyError as e:
                self.logger.exception(e)
                await self._ws.send_json({'error': 'unsupported action'})

    async def stop(self):
        if self._ws and not self._ws.closed:
            await self._ws.close()

    async def _ws_listen(self):
        while True:
            msg = await self._ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                yield msg

            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.logger.error(msg.excepton())

    async def _handle_message(self, msg: aiohttp.WSMessage):
        data = msg.json()
        action, message = data['action'], data['message']
        await self._route_action(action, message)

    async def _route_action(self, action: str, message):
        if action == 'assets':
            return await self._assets(message)
        if action == 'subscribe':
            return await self._subscribe(message)

        raise KeyError(f'unsupported action {action.upper()}')

    async def _assets(self, _):
        await self._ws.send_json({'action': 'assets', 'message':{'1':1}})

    async def _subscribe(self, message: dict):
        self._subscribe_rates(message['assetId'])
        points = await self._request.app['db'].get(message['assetId'], offset=Minutes(30))
        await self._ws.send_json(
            {'action': 'asset_history', 'message': {
                'points': points
            }}
        )

    def _subscribe_rates(self, asset_id: int):
        if self._cancel_subscribe:
            self._cancel_subscribe()

        async def f(point):
            await self._ws.send_json({'action': 'point', 'message': point})
        asset_name = next(filter(lambda x: x[1] == asset_id, Assets.items()))
        cancel_subscribe = self._request.app['rates'].subscribe(asset_name[0], f)
        self._cancel_subscribe = cancel_subscribe
