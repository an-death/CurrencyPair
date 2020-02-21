from abc import ABC, abstractmethod
from functools import partial
from typing import Callable, Any

from aiohttp import web

from server.serializers import AssetsSerializer, PointSetSerializer, PointSerializer
from storage.asset import Assets
from watchdog import Minutes

DEFAULT_HISTORY_OFFSET = Minutes(30)


class Action(ABC):
    NAME: str = None

    def __init__(self,
                 context: web.Application,
                 ws: web.WebSocketResponse):
        self._context = context
        self._ws = ws

    @abstractmethod
    async def response(self, message: Any):
        pass

    async def _send_response(self, data: dict):
        await self._ws.send_json(data)


class AssetsAction(Action):
    NAME = 'assets'

    async def response(self, _):
        data = {
            'action': self.NAME,
            'message': AssetsSerializer(Assets)
        }
        return await self._send_response(data)


class SubscribeAction(Action):
    NAME = 'subscribe'

    def __init__(self, context, send):
        super().__init__(context, send)
        self._subscribe = PointAction(context, send).response
        self._history = PointHistoryAction(context, send).response

    async def response(self, message: dict):
        await self._subscribe(message)
        await self._history(message)


class PointHistoryAction(Action):
    NAME = 'asset_history'
    _DEFAULT_OFFSET = DEFAULT_HISTORY_OFFSET

    def __init__(self, context, send):
        super().__init__(context, send)
        self._get_history = partial(
            context['db'].get, offset=self._DEFAULT_OFFSET
        )

    async def response(self, message: Any):
        points = await self._get_history(message['assetId'])
        await self._send_response(
            {'action': self.NAME,
             'message': {'points': PointSetSerializer(points)}
             }
        )


class PointAction(Action):
    NAME = 'point'
    _cancel_subscribe: Callable[[], None] = None

    def __init__(self, context, send):
        super().__init__(context, send)
        self._subscribe = partial(
            context['rates'].subscribe,
            callback=self._point
        )

    async def response(self, message: Any):
        self._subscribe_rates(message['assetId'])

    async def _point(self, point):
        if self._ws.closed:
            self._cancel_subscribe()
            return

        await self._send_response(
            {'action': self.NAME,
             'message': PointSerializer(point)}
        )

    def _subscribe_rates(self, asset_id: int):
        if self._cancel_subscribe:
            self._cancel_subscribe()
        if asset_id not in Assets.values():
            raise KeyError(f'unsupported asset id {asset_id}')

        asset_name = next(filter(lambda x: x[1] == asset_id, Assets.items()))
        cancel_subscribe = self._subscribe(asset_name[0])
        self._cancel_subscribe = cancel_subscribe
