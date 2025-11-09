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
