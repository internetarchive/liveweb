from .. import proxy
from cStringIO import StringIO
import datetime

class TestRecord:
    def test_read_all(self):
        content = "helloworld" * 100
        record = proxy.Record(None, 0, len(content), iter([content]))

        # read_all should return all the content
        assert record.read_all() == content

        # after calling read_all, the content should still be available
        assert record.read_all() == content
        assert record.read_all() == content

        # after read_all, the content_iter should still have the content
        assert "".join(record.content_iter) == content

    def test_init(self, tmpdir):
        path = tmpdir.join("foo.txt")
        path.write("helloworld" * 100)

        record = proxy.Record(path.strpath, 0, 1000, None)
        assert record.read_all() == "helloworld" * 100

        record = proxy.Record(path.strpath, 800, 100, None)
        assert record.read_all() == "helloworld" * 10


def test_split_type_host():
    assert proxy.split_type_host("http://www.archive.org/details/test") == ("http", "www.archive.org", "/details/test")


def test_FakeSocket():
    s = proxy._FakeSocket()
    assert s.makefile(mode="rb").read() == ""

    s = proxy._FakeSocket(StringIO("helloworld"))
    assert s.makefile(mode="rb").read() == "helloworld"


SAMPLE_RESPONSE = """\
HTTP/1.1 200 OK
Content-type: text/plain
Server: Apache/2.2.20
Content-Length: 10

helloworld""".replace("\n", "\r\n")

SAMPLE_RESPONSE_CHUNKED = """\
HTTP/1.1 200 OK
Content-Type: text/plain
Server: Apache/2.2.20
Transfer-Encoding: chunked

5
hello
5
world
0
""".replace("\n", "\r\n")

class TestProxyResponse:
    def make_response(self, content):
        sock = proxy._FakeSocket(StringIO(content))
        response = proxy.ProxyHTTPResponse("http://example.com/hello", sock)
        response.begin()
        return response

    def test_headers(self):
        response = self.make_response(SAMPLE_RESPONSE)
        assert sorted(response.getheaders()) == [
            ("content-length", "10"), 
            ("content-type", "text/plain"), 
            ("server", "Apache/2.2.20"),
        ]

    def test_buf(self):
        response = self.make_response(SAMPLE_RESPONSE)
        assert response.buf.getvalue() == SAMPLE_RESPONSE

    def test_buf_chunked(self):
        response = self.make_response(SAMPLE_RESPONSE_CHUNKED)
        assert response.buf.getvalue() == SAMPLE_RESPONSE_CHUNKED

    def test_get_payload(self):
        response = self.make_response(SAMPLE_RESPONSE)
        payload = response.get_payload()
        assert "".join(payload) == "helloworld"

    def test_get_payload_chunked(self):
        response = self.make_response(SAMPLE_RESPONSE_CHUNKED)
        payload = response.get_payload()
        assert "".join(payload) == "5\r\nhello\r\n5\r\nworld\r\n0\r\n"
    
    def test_arc_record(self, monkeypatch):
        # monkey patch _utcnow so that the time is deterministic
        monkeypatch.setattr(proxy.ProxyHTTPResponse, "_utcnow", lambda self: datetime.datetime(2010, 9, 8, 7, 6, 5))

        self._test_arc_record(SAMPLE_RESPONSE)
        self._test_arc_record(SAMPLE_RESPONSE_CHUNKED)

    def _test_arc_record(self, http_payload):
        response = self.make_response(http_payload)
        arc = response._make_arc_record()
        assert str(arc.header) == "http://example.com/hello 0.0.0.0 20100908070605 text/plain %d" % len(http_payload)
