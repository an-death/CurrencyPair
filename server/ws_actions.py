from abc import ABC, abstractmethod
from itertools import starmap

from currency_pairs import Assets


class Action(ABC):
    _name: str = None
    _message: 'JsonSerializable' = None

    @classmethod
    def from_raw(cls, data: dict):
        pass

    @abstractmethod
    def response(self):
        pass


class AssetsSerializer:
    @staticmethod
    def serialize():
        data = starmap(lambda name, id: {'id': id, 'name': name}, Assets.items())
        return tuple(data)


class AssetsAction(Action):
    _name = 'assets'
    _serializer = AssetsSerializer

    def __init__(self, data: dict):
        pass

    def response(self):
        return {'action': self._name, 'message': self._serializer().serialize()}


class AssetAction(Action):
    _name = 'asset'

    def __init__(self, data: dict):
        self._message = data['message']
        self._asset_id = data['message']['assetId']

    def response(self):
        return {'action': self._name, 'message': self.serializer(self._asset_id).serialize()}

