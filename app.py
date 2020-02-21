import asyncio

from aiohttp import web

import source


async def index_handler(request):
    rates = await request.app['rate_source']._requester.get_rates()
    return web.Response(text=str(rates))


async def start_background(app):
    app['cleanupable'] = []
    rate_source = source.CurrencyRates()
    await rate_source.start()
    app['rate_source'] = rate_source


    app['cleanupable'].append(rate_source.stop)


async def cleanup_background(app):
    cleanupables = app['cleanupable']

    for cleanup in cleanupables:
        if asyncio.iscoroutinefunction(cleanup):
            await cleanup()
        else:
            cleanup()


# to start use aiohttp CLI:
# python -m aiohttp.web -H localhost -P 8080 app:main
def main(argv):
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.on_startup.append(start_background)
    app.on_cleanup.append(cleanup_background)
    return app
