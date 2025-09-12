import os

import motor.motor_tornado
import tornado.ioloop
import tornado.web
import tornado.websocket

from core.ai_client import ai_client
from core.views import MainHandler, ChatsHandler, ResponseHandler, ChatHandler, FilesHandler, FileHandler
from settings import settings as stg


def make_app():
    client = motor.motor_tornado.MotorClient(stg['mongo']['db_url'])
    ai_client.initialize()
    settings = {
        'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
        'db': client[stg['mongo']['db_database']]
    }

    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/api/chats', ChatsHandler),
        (r'/api/chats/([a-fA-F0-9]{24})', ChatHandler),
        (r'/api/response', ResponseHandler),
        (r'/api/files', FilesHandler),
        (r'/api/files/([a-fA-F0-9]{24})', FileHandler),
    ], **settings, autoreload=True)


if __name__ == '__main__':
    app = make_app()
    app.listen(8784)
    print('Server started on port http://127.0.0.1:8784')
    tornado.ioloop.IOLoop.current().start()
