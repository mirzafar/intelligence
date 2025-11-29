import os

import motor.motor_tornado
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.platform.asyncio import AsyncIOMainLoop

from core.ai_client import ai_client
from settings import settings as stg
from views import (
    MainHandler,
    ChatsHandler,
    ResponseHandler,
    ChatHandler,
    FilesHandler,
    FileHandler,
    FileDownloadHandler,
    DiagramsHandler,
    DiagramHandler,
    DesignsHandler,
    ModelsHandler, ModelHandler
)


def make_app():
    print('initializing mongodb ->>')
    client = motor.motor_tornado.MotorClient(stg['mongo']['db_url'])
    print('initializing mongodb <<-')
    print('initializing ai client vector store ->>')
    tornado.ioloop.IOLoop.current().add_callback(ai_client.initialize_vector_store)
    print('initializing ai client vector store <<-')

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
        (r'/api/files/([a-fA-F0-9]{24})/download', FileDownloadHandler),

        (r'/api/diagrams', DiagramsHandler),
        (r'/api/diagrams/([a-fA-F0-9-]{36})', DiagramHandler),

        (r'/api/designs/([a-fA-F0-9-]{36})', DesignsHandler),

        (r'/api/models', ModelsHandler),
        (r'/api/models/([a-fA-F0-9]{24})/', ModelHandler),
    ], **settings, autoreload=True, debug=True)


if __name__ == '__main__':
    AsyncIOMainLoop().install()
    app = make_app()
    app.listen(8784)
    print('Server started on port http://127.0.0.1:8784')
    tornado.ioloop.IOLoop.current().start()
