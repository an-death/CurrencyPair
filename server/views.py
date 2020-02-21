import json
import logging
from typing import Iterable

import aiohttp
from aiohttp import web

from server.ws_actions import Action, AssetsAction, SubscribeAction


async def index_handler(request: web.Request):
    return web.FileResponse('server/html/index.html')


async def ws_handle(request):
    client = WSClientHandler(request)
    try:
        await client.run()
    finally:
        await client.stop()


class WSClientHandler:
    _ACTIONS: Iterable[Action] = (
        AssetsAction,
        SubscribeAction,
    )

    def __init__(self, request: web.Request):
        self._request = request
        self._ws: web.WebSocketResponse = web.WebSocketResponse()
        self._cancel_subscribe = None
        self.logger = logging.getLogger(str(self.__class__))
        self._actions = {
            a.NAME: a(request.app, self._ws)
            for a in self._ACTIONS
        }

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
            if self._ws.closed:
                return

            msg = await self._ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                yield msg

            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.logger.error(msg.excepton())

    async def _handle_message(self, msg: aiohttp.WSMessage):
        data = msg.json()
        action, message = data['action'], data['message']
        await self._actions[action].response(message)
