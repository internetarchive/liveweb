from ..webapp import application

class Test_application:
    def test_parse_request_url(self):
        environ = {
            'REQUEST_METHOD': "GET",
            'REQUEST_URI': 'http://www.example.com/foo/bar',
            'PATH_INFO': 'http://www.example.com/foo/bar',
            'HTTP_HOST': 'www.example.com'
        }
        app = application(environ, None)
        app.parse_request()
        assert app.url == "http://www.example.com/foo/bar"
        
    def test_nginx_work_around(self):
        # nginx is stripping the http://host in the URL, which is of the form http://host/path
        # and passing just /path to the app. 
        # Test the work-around that reconstructs the full path using the host.
        environ = {
            'REQUEST_METHOD': "GET",
            'REQUEST_URI': '/foo/bar',
            'PATH_INFO': '/foo/bar',
            'HTTP_HOST': 'www.example.com'
        }
        app = application(environ, None)
        app.parse_request()
        assert app.url == "http://www.example.com/foo/bar"
