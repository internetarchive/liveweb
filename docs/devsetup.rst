Development Setup
=================

Setting up
----------

Start with getting the source code from github. ::

    $ git clone git://github.com/internetarchive/liveweb.git
    $ cd liveweb

Setup a virtualenv. ::

    $ make venv

This will create the virtualenv in the current directory. Edit the
``Makefile`` if you want to setup virtualenv elsewhere.

Running the application
-----------------------

Run the application using::

    $ make run

This will start the liveweb proxy at ``localhost:7070``.

Testing using curl
------------------

Assuming the liveweb proxy is running on `localhost:7070`::

    $ curl -s -x localhost:7070 http://httpbin.org/get | zcat 
    http://httpbin.org/get 204.236.238.79 20120427110218 application/json 451
    HTTP/1.1 200 OK
    Content-Type: application/json
    Date: Fri, 27 Apr 2012 11:02:18 GMT
    Server: gunicorn/0.13.4
    Content-Length: 298
    Connection: Close

    {
      "url": "http://httpbin.org/get", 
      "headers": {
        "Content-Length": "", 
        "Accept-Encoding": "identity", 
        "Connection": "keep-alive", 
        "User-Agent": "ia_archiver(OS-Wayback)", 
        "Host": "httpbin.org", 
        "Content-Type": ""
      }, 
      "args": {}, 
      "origin": "207.241.237.193"
    }

Running in http-passthough mode
-------------------------------

Enable http-passthrough mode by adding the following to the config file. ::

    http_passthough: true

Make sure caching is disabled. The http-passthough mode doesn't work with caching.

Run the application and change the browser setting to use application
address (localhost:7070 by default) as http proxy.

Performance Testing
-------------------

Test performance using Apache-Bench::

    $ ab -X localhost:7070 -c 10 -n 100 http://www.archive.org/

The ``-X`` options is to specify the proxy server.

