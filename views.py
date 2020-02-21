from aiohttp import web

from currency_pairs import Point, Assets
from watchdog import Second


class PointJsonSerializer(dict):
    def __init__(self, point: Point):
        super().__init__(**point._asdict())


async def index_handler(request):
    rates = await request.app['db'].get(Assets['EURUSD'], offset=Second(30*60))
    return web.json_response(tuple(map(PointJsonSerializer, rates)))

