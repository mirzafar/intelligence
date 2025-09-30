import json

import tornado.web
import tornado.websocket


class BaseHandler(tornado.web.RequestHandler):
    def success(self, data: dict = None):
        self.set_header('Content-Type', 'application/json')
        response = {
            '_success': True,
            **(data or {})
        }
        self.write(json.dumps(response, default=str))

    def error(self, message='Error'):
        self.set_header('Content-Type', 'application/json')
        response = {
            '_success': False,
            'message': message
        }
        self.write(json.dumps(response))
