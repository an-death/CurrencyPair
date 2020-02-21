import asyncio

from aiohttp import web

import source
from storage.asset import Assets
from storage.storage import InMemoryStorage, DBUpdater
from server.views import index_handler, ws_handle


async def start_background(app):
    app['closable'] = []

    rate_source = source.CurrencyRates()
    await rate_source.start()
    app['rates'] = rate_source
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



def app_factory():
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', ws_handle)
    app.on_startup.append(start_background)
    app.on_cleanup.append(cleanup_background)
    return app
