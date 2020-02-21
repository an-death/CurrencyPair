import asyncio

from aiohttp import web

import source
from currency_pairs import Assets
from storage import InMemoryStorage, DBUpdater
from views import index_handler


async def start_background(app):
    app['closable'] = []

    rate_source = source.CurrencyRates()
    await rate_source.start()
    app['rate_source'] = rate_source
    app['db'] = InMemoryStorage()
    db_updater = DBUpdater(app['db'], rate_source, Assets.keys())
    await db_updater.start()

    app['closable'].extend(
        (rate_source.stop, db_updater.stop)
    )


async def cleanup_background(app):
    closes = app['closable']

    for close in closes:
        if asyncio.iscoroutinefunction(close):
            await close()
        else:
            close()


# to start use aiohttp CLI:
# python -m aiohttp.web -H localhost -P 8080 app:main
def main(argv):
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.on_startup.append(start_background)
    app.on_cleanup.append(cleanup_background)
    return app
