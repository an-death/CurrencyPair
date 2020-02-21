from itertools import starmap
from typing import Iterable

from storage.point import Point


class PointSerializer(dict):
    def __init__(self, point: Point):
        super().__init__(**point._asdict())


class AssetsSerializer(list):
    def __init__(self, assets: dict):
        super().__init__(starmap(lambda name, id: {'id': id, 'name': name}, assets.items()))


class PointSetSerializer(list):
    def __init__(self, points: Iterable[Point]):
        super().__init__(map(PointSerializer, points))
