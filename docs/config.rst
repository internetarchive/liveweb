
Configuration
=============

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

user_agent
----------

Specifies the value of the ``User-Agent`` request header. Default
value is ``ia_archiver(OS-Wayback)``.

timeout
-------

Specifies the connection and read timeout in seconds.

archive_format
--------------

Specified the archive format. Can be either ``arc`` or ``warc``.

.. note::

   As of now only ``arc`` is supported.

http_passthrough
----------------

This is a boolean parameter, setting it to ``true`` will make it work like a http proxy with archiving. Useful for testing and recording personal browsing.

.. note::

   As of now, ``http_passthrough`` works only when no caching is used.

Other Settings
--------------

The application depends on the system for DNS resolution and it is not
possible to specify dns timeouts in the configuration. However, it can
be achieved by specifying appropriate timeout value in ``RES_OPTIONS``
environment variable. ::

    export RES_OPTIONS="timeout:1 attempts:1"

See `resolv.conf man page`_ for more details.

.. _resolv.conf man page: http://manpages.ubuntu.com/manpages/lucid/en/man5/resolv.conf.5.html
