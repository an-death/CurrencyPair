
from server.app import app_factory


# to start use aiohttp CLI:
# python -m aiohttp.web -H localhost -P 8080 main:main
def main(argv):
    return app_factory()
