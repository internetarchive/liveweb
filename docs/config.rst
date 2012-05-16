.. _config:


Liveweb Proxy Configuration
===========================

The ``liveweb-proxy`` can be configured using various command-line options and/or a config file.

Config file can be specified as::

    $ liveweb-proxy -c liveweb.ini

or::
 
    $ liveweb-proxy --config liveweb.ini

This section describes the available config settings. For each config setting, there is a command line option with the same name.

For example, config setting ``archive-format`` is available as command line argument `--archive-format`. 

The config file is specified in INI format. Here is a sample config file. ::

    [liveweb]

    archive-format = arc

    output-directory = /tmp/records

    dns-timeout = 2s
    

Archive Settings
----------------

**archive-format**

    Specifies the archive format. Should be one if ``arc`` or ``warc``.

    The default value is ``arc``.

.. warning::

   As of now only ``arc`` is supported.


**output-directory**

    Output directory to write ARC/WRC files. Default value is "records".


**filename-pattern**

    The pattern of the filename specified as Python string formatting
    template. The default value is
    ``live-%(timestamp)s-%(serial)05d-%(fqdn)s-%(port)s.arc.gz``.

    Available substitutions are ``timestamp``, ``serial``, ``pid``,
    ``fqdn`` (fully qualified domain name) and ``port``.

**filesize-limit**

    The limit on the size of file. If a file crosses this size, it
    will be closed a new file will be created to write new records.

**num-writers**

    The number of concurrent writers. 

    The default value is ``1``.


Cache Settings
--------------

.. _config_cache:

**cache**

    Type of cache to use. Available options are ``redis``, ``sqlite`` and ``none``.

    The default value is ``none``.

**redis-host**

**redis-port**

**redis-db**

    Redis host, port and db number. Used only when ``cache=redis``.

**redis-expire-time**

    Expire time to set in redis. Used only when ``cache=redis``.

    The default value is ``1h`` (1 hour).

**redis-max-record-size**

    Maximum allowed size of a record that can be cached. Used only when ``cache=redis``.

    The default value is ``100KB``.

**sqlite-db**

    Path to the sqlite database to use. This option is valid only when ``cache=sqlite``.

    The default value is ``liveweb.db``.

Timeouts and Resource Limits
----------------------------

**default-timeout**

    This is the default timeout value for ``connect-timeout``, ``initial-data-timeout`` and ``read-timeout``. 

    The default value is ``10s``.

.. _config_dns_timeout:

**dns-timeout**

    Specifies the max amount of time can a DNS resolution can take.

    Python doesn't support a way to specify DNS timeout. On Linux, the
    dns timeout can be specified via the ``RES_OPTIONS`` environment
    variable. This enviroment variable is set at the startup of the
    application based on this config setting.

    If unspecified, the DNS timeout is decided by the system default behavior.

    See `resolv.conf man page`_ for more details.

    .. _resolv.conf man page: http://manpages.ubuntu.com/manpages/lucid/en/man5/resolv.conf.5.html

.. _config_connect_timeout:

**connect-timeout**

    Specifies the connect timeout in seconds. Connections that take
    longer to establish will be aborted.

.. _config_initial_data_timeout:

**initial-data-timeout**

    Specifies the maximum time allowed before receiving initial data
    (HTTP headers) from the remote server.

.. _config_read_timeout:

**read-timeout**

    Specifies the read timeout in seconds. This indicates the idle time. If no data is received for more than this time, the request will fail.


**max-request-time**

    Specifies the total amout of time a HTTP request can take. If it takes
    more than this, the current request will fail.

    The default value is ``2m``.

**max-response-size**

    Specifies the maximum allowed size of response.

    The default value is ``100MB``.

Other Settings
--------------

.. _config_user_agent:

**user-agent**

    Specifies the value of the ``User-Agent`` request header. 

    The default value is ``ia_archiver(OS-Wayback)``.


**http-passthrough**

    This is a boolean parameter, setting it to ``true`` will make it
    work like a http proxy with archiving. Useful for testing and
    recording personal browsing.
