from aiohttp import web


def index_handler(request):
    return web.Response(text='asd')


# to start use aiohttp CLI:
# python -m aiohttp.web -H localhost -P 8080 app:main
def main(argv):
    app = web.Application()
    app.router.add_get('/', index_handler)
    return app
