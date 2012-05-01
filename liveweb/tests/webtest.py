"""Web app to simulate various error conditions.
"""

from liveweb.tools.wsgiapp import wsgiapp
import time

class application(wsgiapp):
    urls = [
        ("/", "index"),
        ("/echo/(.*)", "echo"),
        ("/delay-headers/([0-9\.]+)", "delay_headers"),
        ("/delay/([0-9\.]+)", "delay"),
        ("/drop", "drop"),
    ]

    def GET_index(self):
        self.header("Content-Type", "text/plain")
        return ["hello, world!\n"]

    def GET_echo(self, name):
        self.header("Content-Type", "text/plain")
        return [name]

    def GET_drop(self):
        self.header("Content-Type", "text/plain")
        self.header("Content-Length", "10000")
        return ["dropped!"]

    def GET_delay_headers(self, delay):
        self.header("Content-Type", "text/plain")
        delay = float(delay)
        time.sleep(delay)
        return ["delayed"]

    def GET_delay(self, delay):
        """Emits 10 numbers with delay seconds between each.
        """
        delay = float(delay)
        for i in range(10):
            yield str(i) + "\n"
            time.sleep(delay)

if __name__ == "__main__":
    import sys

    try:
        port = int(sys.argv[1])
    except IndexError:
        port = 8080

    from wsgiref.simple_server import make_server
    httpd = make_server('127.0.0.1', port, application)
    print "http://127.0.0.1:%d/" % port
    httpd.serve_forever()
