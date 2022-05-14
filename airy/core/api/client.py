import ssl

from aiohttp import web


async def handle(request: web.Request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


class HttpServer:
    def __init__(self,):
        self.app = web.Application()
        self.runner = web.AppRunner(self.app)
        self.app.router.add_routes()

        self.app.add_routes([web.get('/', handle)])

    async def start(self):
        await self.runner.setup()
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.check_hostname = False
        ssl_context.load_cert_chain('cert.pem', 'key.pem')
        self.site = web.TCPSite(self.runner, '192.168.1.88', 8088, ssl_context=ssl_context)
        await self.site.start()
