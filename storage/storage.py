from abc import ABC, abstractmethod
from collections import defaultdict, deque
from functools import partial
from operator import methodcaller
from typing import Any, Iterable

from storage.asset import Assets
from storage.point import Point
from watchdog import Time, Seconds


class Storage(ABC):

    @abstractmethod
    async def add(self, asset: int, data: Any):
        pass

    @abstractmethod
    async def get(self, asset: int, offset: Time = Seconds(1)):
        pass

    @abstractmethod
    async def add_by_name(self, asset_name, data: Any):
        pass

    @abstractmethod
    async def get_by_name(self, asset_name: str, offset: Time = Seconds(1)):
        pass


class InMemoryStorage(Storage):
    # could be replaced with Redis or SQL
    # main point it should have only what's we need

    def __init__(self):
        self._storage = defaultdict(partial(deque, maxlen=30*60))

    async def add(self, asset: int, point: Point):
        self._storage[asset].appendleft(point)

    async def get(self, asset: int, offset: Time = Seconds(1)):
        return tuple(self._storage[asset])[0:int(offset)]

    async def add_by_name(self, asset_name, point: Point):
        return await self.add(Assets[asset_name], point)

    async def get_by_name(self, asset_name: str, offset: Time = Seconds(1)):
        return await self.get(Assets[asset_name], offset=offset)


class DBUpdater:
    def __init__(self, storage: Storage, subscribe, assets: Iterable[str]):
        self._storage = storage
        self._assets = assets
        self._subscribe = subscribe

        self._closable = []

    async def start(self):
        for a in self._assets:
            self._closable.append(
                self._subscribe.subscribe(
                    a,
                    partial(self._storage.add_by_name, a)
                )
            )

    def stop(self):
        tuple(
            map(methodcaller('__call__'), self._closable)
        )
