import time
from abc import ABC, abstractmethod
from collections import namedtuple
from decimal import Decimal

# That actually could be in database
from operator import itemgetter
from typing import Any


class Currency:
    EURUSD = 'EURUSD'
    USDJPY = 'USDJPY'
    GBPUSD = 'GBPUSD'
    AUDUSD = 'AUDUSD'
    USDCAD = 'USDCAD'


Assets = {
    Currency.EURUSD: 1,
    Currency.USDJPY: 2,
    Currency.GBPUSD: 3,
    Currency.AUDUSD: 4,
    Currency.USDCAD: 5,
}


class Point(
    namedtuple('Point', 'assetName, assetId, value, time')
):
    @classmethod
    def from_ratesjson(cls, data: dict) -> 'Point':
        return RatesJSONConverter(data).convert()

    def json(self):
        return self._asdict()


class UnknownAsset(Exception):
    def __init__(self, asset_name: str):
        self._name = asset_name

    def __str__(self):
        return f'{self.__class__.__name__}: {self._name}'


class PointConverter(ABC):
    __slots__ = ('_data',)

    def __init__(self, data: Any):
        self._data = data

    @abstractmethod
    def convert(self) -> Point:
        pass


class RatesJSONConverter(PointConverter):
    _data: dict
    __bid_ask_extractor = itemgetter('Bid', 'Ask')

    def _get_value(self, data: dict):
        bid_ask_sum = sum(map(Decimal, self.__bid_ask_extractor(data)))
        return bid_ask_sum / 2

    @staticmethod
    def _get_current_unixtime():
        return int(time.time())

    def convert(self) -> Point:
        data = self._data
        name = data['Symbol']
        value = self._get_value(data)
        time = self._get_current_unixtime()
        return Point(name, Assets.get(name, None), float(value), time)
