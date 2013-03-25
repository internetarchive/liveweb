"""Really simple implememtation of wayback machine web-interface. 

Written to test the liveweb proxy implementation.
"""

import sys
import httplib
import gzip
import urlparse
import cgi
from StringIO import StringIO

from BeautifulSoup import BeautifulSoup

import warc
from .wsgiapp import wsgiapp
# We expect that liveweb host:port is passed as argument to this script.
liveweb = sys.argv[1]
import re
import logging

logging.basicConfig(level=logging.DEBUG, )
logger = logging.getLogger('[wayback]')


class application(wsgiapp):
    """WSGI application for wayback machine prototype.
    """
    urls = [
        ("/", "index"),
        ("/get", "get"),
        ("/web/(.*)", "web")
    ]

    @property
    def home(self):
        return "http://" + self.environ['HTTP_HOST']

    def GET_index(self):
        self.header("content-type", "text/html")
        return [HEADER]
        #yield "<h1>Wayback Machine Prototype</h1>"

    def GET_get(self):
        fs = cgi.FieldStorage(environ=self.environ, keep_blank_values=1)
        if 'url' in fs:
            url = fs['url'].value
            self.status = "302 See Other"
            self.header("Location", self.home + "/web/" + url)
            return [""]
        else:
            self.status = "302 See Other"
            self.header("Location", self.home + "/")
            return [""]

    def GET_web(self, url):
        qs = self.environ.get("QUERY_STRING", "")
        if qs:
            url = url + "?" + qs
        record = self.fetch_arc_record(url)

        # fake socket to pass to httplib
        f = StringIO(record.payload)
        f.makefile = lambda *a: f

        response = httplib.HTTPResponse(f)
        response.begin()
        h = dict(response.getheaders())

        content_type = h.get("content-type", "text/plain")
        self.header("Content-Type", content_type)

        if 'content-length' in h:
            self.header('Content-Length', h['content-length'])

        content = response.read()
        if content_type.lower().startswith("text/html"):
            content = self.rewrite_page(url, content)
            self.header('Content-Length', str(len(content)))
        elif content_type.lower().startswith("text/css"):
            content = self.rewrite_css(url, content)
            self.header('Content-Length', str(len(content)))
        return [content]

    def rewrite_css(self, base_url, content):
        #base_url = base_url.replace(os.path.basename(base_url), '')
        for image_url in re.findall('url\(([^\)]+)', content):
            image_url = image_url.replace('"', '')
            image_url = image_url.replace("'", '')
            if not image_url.startswith('http://'):
                new_url = urlparse.urljoin(base_url, image_url)
            else:
                new_url = image_url
            new_url = new_url.replace('//', '/')
            url2 = urlparse.urljoin(base_url, new_url)
            url2 = self.home + "/web/" + url2
            logger.debug("rewrote %r => %r" % (image_url, url2))
            content = content.replace(image_url, url2, 1)
        return content

    def fetch_arc_record(self, url):
        """Fetchs the ARC record data from liveweb proxy.
        """
        conn = httplib.HTTPConnection(liveweb)
        conn.request("GET", url)
        content = conn.getresponse().read()

        gz = gzip.GzipFile(fileobj=StringIO(content), mode="rb")
        record = warc.ARCRecord.from_string(gz.read(), version=1)

        return record

    def rewrite_page(self, base_url, content):
        """Rewrites all the links the the HTML."""

        soup = BeautifulSoup(content)
        for tag in soup.findAll(["a", "link", "img", "script", "form"]):
            if tag.has_key('href'):
                tag['href'] = self.rewrite_url(base_url, tag['href'])
            elif tag.has_key("src"):
                tag['src'] = self.rewrite_url(base_url, tag['src'])
            elif tag.has_key("action"):
                tag['action'] = self.rewrite_url(base_url, tag['action'])

        self.inject_header(base_url, soup)
        return str(soup)

    def inject_header(self, base_url, soup):
        """Injects wayback machine header into the web page."""
        header_soup = BeautifulSoup(HEADER).find("div")
        header_soup.find("input", {"id": "wmtbURL"})['value'] = base_url
        soup.find("body").insert(0, header_soup)

    def rewrite_url(self, base_url, url):
        if url.strip().lower().startswith("javascript"):
            return url
        url2 = urlparse.urljoin(base_url, url)
        url2 = self.home + "/web/" + url2
        logger.debug("rewrote %r => %r" % (url, url2))
        return url2


HEADER = """
<div id="wm-ipp" style="position: relative; padding-top: 0px; padding-right: 5px; padding-bottom: 0px; padding-left: 5px; min-height: 70px; min-width: 800px; z-index: 9000; display: block; ">
<div id="wm-ipp-inside" style="position:fixed;padding:0!important;margin:0!important;width:97%;min-width:780px;border:5px solid #000;border-top:none;background-image:url(http://staticweb.archive.org/images/toolbar/wm_tb_bk_trns.png);text-align:center;-moz-box-shadow:1px 1px 3px #333;-webkit-box-shadow:1px 1px 3px #333;box-shadow:1px 1px 3px #333;font-size:11px!important;font-family:'Lucida Grande','Arial',sans-serif!important;">
   <table style="border-collapse:collapse;margin:0;padding:0;width:100%;"><tbody><tr>
   <td style="padding:10px;vertical-align:top;min-width:110px;">
   <a href="http://wayback.archive.org/web/" title="Wayback Machine home page" style="background-color:transparent;border:none;"><img src="http://staticweb.archive.org/images/toolbar/wayback-toolbar-logo.png" alt="Wayback Machine" width="110" height="39" border="0"></a>
   </td>
   <td style="padding:0!important;text-align:center;vertical-align:top;width:100%;">

       <table style="border-collapse:collapse;margin:0 auto;padding:0;width:570px;"><tbody><tr>
       <td style="padding:3px 0;" colspan="2">
       <form target="_top" method="get" action="/get" name="wmtb" id="wmtb" style="margin:0!important;padding:0!important;"><input type="text" name="url" id="wmtbURL" value="" style="width:400px;font-size:11px;font-family:'Lucida Grande','Arial',sans-serif;" onfocus="javascript:this.focus();this.select();"><input type="hidden" name="type" value="replay"><input type="hidden" name="date" value="20070607010239"><input type="submit" value="Go" style="font-size:11px;font-family:'Lucida Grande','Arial',sans-serif;margin-left:5px;"><span id="wm_tb_options" style="display:block;"></span></form>
       </td>
       <td style="vertical-align:bottom;padding:5px 0 0 0!important;" rowspan="2">
       </td>
   <td style="text-align:right;padding:5px;width:65px;font-size:11px!important;">
       <a href="javascript:;" onclick="document.getElementById('wm-ipp').style.display='none';" style="display:block;padding-right:18px;background:url(http://staticweb.archive.org/images/toolbar/wm_tb_close.png) no-repeat 100% 0;color:#33f;font-family:'Lucida Grande','Arial',sans-serif;margin-bottom:23px;background-color:transparent;border:none;" title="Close the toolbar">Close</a>
       <a href="http://faq.web.archive.org/" style="display:block;padding-right:18px;background:url(http://staticweb.archive.org/images/toolbar/wm_tb_help.png) no-repeat 100% 0;color:#33f;font-family:'Lucida Grande','Arial',sans-serif;background-color:transparent;border:none;" title="Get some help using the Wayback Machine">Help</a>
   </td>
   </tr></tbody></table>
</div>
</div>
"""
