import json

import tornado.web
import tornado.websocket


class BaseHandler(tornado.web.RequestHandler):
    @property
    def json(self):
        return json.loads(self.request.body or '{}')

    def success(self, data: dict = None):
        self.set_header('Content-Type', 'application/json')
        return self.write(json.dumps({
            '_success': True,
            **(data or {})
        }, default=str))

    def error(self, message: str = 'Error'):
        self.set_header('Content-Type', 'application/json')
        return self.write(json.dumps({
            '_success': False,
            'message': message
        }))


class BaseStreamHandler(tornado.web.RequestHandler):
    def set_street_headers(self):
        self.set_header('Content-Type', 'text/plain')
        if self.request.connection.stream.closed():
            raise tornado.web.HTTPError(404)

    def success(self, data: dict = None):
        self.set_header('Content-Type', 'application/json')
        return self.write(json.dumps({
            '_success': True,
            **(data or {})
        }, default=str))

    @property
    def json(self):
        return json.loads(self.request.body or '{}')

    async def dispatch_data(self, data: dict):
        self.write(json.dumps(data, ensure_ascii=False))
        return await self.flush()

    async def dispatch_error(self, text: str = 'Error'):
        self.write(text)
        return await self.flush()
