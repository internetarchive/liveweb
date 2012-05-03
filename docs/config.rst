
Configuration
=============

.. _config_storage:

storage
-------

The ``storage`` paramater specifies where and how the records are
stored on disk. ::

    storage:
        directory: "records"
        pattern: "liveweb-%(timestamp)s-%(seq)s.arc.gz"
        max_files: 1
        max_file_size: 104857600 # 100 MB

The description of the properties:

**directory**

    The directory to store the files.

**pattern**

    The pattern of the filename. Python string formatting is used to
    substitute the ``timestamp`` and ``seq`` number.

**max_files** 

    Number of files to use. The application creates a file poll with
    the specified number of files and threads start writing to the
    first available file.

**max_file_size**

    Specifies the maximum size of the file. Once a file crosses this
    size, it is closed and a new file is created with incremented
    ``seq`` number.

Except ``directory``, all the other paramaters are optional with above
specified values as defaults.

.. _config_cache:

cache
-----

Liveweb proxy supports, caching the records on various backends.


Redis Backend
^^^^^^^^^^^^^

The redis cache backend stores the content of the records in redis. ::

    cache:
        type: redis
        host: localhost
        port: 6379
        db: 0
        expire_time: 3600
        max_record_size: 102400

Except ``type`` all other paramerters are optional with the above
specified values as defaults.

The ``max_record_size`` parameter specified the maximum record size
allowed to be cached. Records larger than this are not cached.

SQLite Backend
^^^^^^^^^^^^^^

The sqlite cache backend stores the filename, offset and length in
the database. It reads the record from disk the same URL is accessed
again. ::

    cache:
        type: sqlite
        database: liveweb.db

Memory Backend
^^^^^^^^^^^^^^

There is no support for in-memory backend, but it can be achieved by
using sqlite with in-memory database. ::

    cache:
        type: sqlite
        database: ":memory:"

No Cache
^^^^^^^^

This is the default behaviour. Can be specified in config as::

    cache: null

.. _config_user_agent:

user_agent
----------

Specifies the value of the ``User-Agent`` request header. Default
value is ``ia_archiver(OS-Wayback)``.

.. _config_timeout:

default_timeout
---------------

Specifies the default value for :ref:`connect_timeout`, :ref:`initial_data_timeout` and :ref:`read_timeout`.

.. _config_dns_timeout:

dns_timeout
-----------

Specifies the max amount of time can a DNS resolution can take.

Python doesn't support a way to specify DNS timeout. On Linux, the dns
timeout can be specified via the `RES_OPTIONS` environment
variable. This enviroment variable is set at the startup of the
application based on this config setting.

If unspecified, the system default behavior is used.

See `resolv.conf man page`_ for more details.

.. _resolv.conf man page: http://manpages.ubuntu.com/manpages/lucid/en/man5/resolv.conf.5.html

.. _config_connect_timeout:

connect_timeout
---------------

Specifies the connect timeout in seconds. Connections that take longer
to establish will be aborted.

.. _config_initial_data_timeout:

initial_data_timeout
--------------------

Specifies the maximum time allowed before receiving initial data (HTTP headers) from the remote server.

.. _config_read_timeout:

read_timeout
------------

Specifies the read timeout in seconds. This indicates the idle
time. If no data is received for more than this time, the request will
fail.

If unspecified, this will default to the ``connect_timeout``.

max_request_time
----------------

Specifies the total amout of time a HTTP request can take. If it takes
more than this, the current request will fail.

max_response_size
-----------------

Specifies the maximum allowed size of response.

archive_format
--------------

Specified the archive format. Can be either ``arc`` or ``warc``.

.. warning::

   As of now only ``arc`` is supported.

http_passthrough
----------------

This is a boolean parameter, setting it to ``true`` will make it work like a http proxy with archiving. Useful for testing and recording personal browsing.
