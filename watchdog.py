import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Optional


class Time(ABC):
    def __init__(self, value: int):
        self._value = value

    def __int__(self):
        return self._value

    @abstractmethod
    def _to_second(self, value: int):
        pass


class Seconds(Time):
    def _to_second(self, value: int):
        return value


class Minutes(Time):
    def _to_second(self, value: int):
        return value * 60


class Watchdog:
    _watchdog_fn: Callable[[], Awaitable] = None
    _watchdog_period: int = None
    _task: asyncio.Task = None

    def __init__(self,
                 watchdog_fn: Callable[[], Awaitable],
                 period: Time,
                 err_handler: Optional[Callable[[Exception], None]] = None):
        self._watchdog_fn = watchdog_fn
        self._watchdog_period = period
        self._error_handler = err_handler

    async def start(self):
        self._task = asyncio.create_task(self._watchdog())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()

    async def _watchdog(self):
        while True:
            await asyncio.sleep(int(self._watchdog_period))
            try:
                await self._watchdog_fn()

            except asyncio.CancelledError:
                break

            except Exception as e:
                if self._error_handler:
                    self._error_handler(e)
