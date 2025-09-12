import tornado.websocket


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("resr.html")
