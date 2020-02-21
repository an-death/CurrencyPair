import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable

import aiohttp

from storage.point import Point
from watchdog import Watchdog, Seconds

CancelFunc = Callable[[], None]


class ContentType:
    # I'm not use `mimetypes` package
    # because he depend on system files, like /etc/mime.types
    # which doesnt exist in some docker images (CI/CD for example)
    JSON = 'application/json'
    JAVASCRIPT = 'text/javascript'


class CurrencyRequestClient:
    _URL = 'https://ratesjson.fxcm.com/DataDisplayer'

    def __init__(self):
        self._session = aiohttp.ClientSession()

    async def get_rates(self):
        async with self._session.get(self._URL) as response:
            return await self._json(response)

    async def _json(self, response: aiohttp.ClientResponse):
        # it is actually return javascript for `ratesjson.com`
        if response.content_type == ContentType.JAVASCRIPT:
            data = await response.read()
            data = data[5:-3]                   # drop `null(` and `);`
            data = data.replace(b'",}', b'"}')  # drop ending `,` of js-obj
            return json.loads(data)

        if response.content_type == ContentType.JSON:
            return await response.json()

        raise Exception('Unsupported content type')

    async def stop(self):
        if self._session and not self._session.closed:
            await self._session.close()


class SubscribeEngine(ABC):
    @abstractmethod
    def subscribe(self, chan_name: str, callback) -> CancelFunc:
        pass

    @abstractmethod
    def notify(self, data: 'JsonConvertable'):
        pass


class SimpleSubscribeEngine(SubscribeEngine):
    # Here could be Redis pub/sub for example

    def __init__(self):
        self._channels = defaultdict(list)

    def subscribe(self, chan_name: str, callback) -> CancelFunc:
        self._channels[chan_name].append(callback)
        return lambda: self._channels[chan_name].remove(callback)

    async def notify(self, chan_name: str, data: 'JsonConvertable'):
        for callback in self._channels[chan_name]:
            try:
                await callback(data)

            except Exception as e:
                print(e)
                # TODO: log
                pass


class CurrencyRates:
    _SubscribeEngine = SimpleSubscribeEngine
    _CurrencyGetter = CurrencyRequestClient

    def __init__(self):
        self._watchdog = Watchdog(self._watchdog_fn, Seconds(1), logging.exception)
        self._requester = self._CurrencyGetter()
        self._notifier = self._SubscribeEngine()

    async def start(self):
        await self._watchdog.start()

    async def stop(self):
        self._watchdog.stop()
        await self._requester.stop()

    async def _watchdog_fn(self):
        rates = await self._requester.get_rates()
        await self._notify_subscribers(rates['Rates'])

    async def _notify_subscribers(self, rates: list):
        for rate in rates:
            point = Point.from_ratesjson(rate)
            await self._notifier.notify(point.assetName, point)

    def subscribe(self, rate_name: 'Currency', callback) -> CancelFunc:
        return self._notifier.subscribe(rate_name, callback)
