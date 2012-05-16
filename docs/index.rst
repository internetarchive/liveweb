.. Liveweb Proxy documentation master file, created by
   sphinx-quickstart on Fri Apr 27 14:01:57 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Liveweb Proxy
=============

Liveweb proxy is a component of Internet Archive's `wayback machine
project <http://web.archive.org/>`_.

The liveweb proxy captures the content of a web page in real time,
archives it into a ARC or WARC file and returns the ARC/WARC record
back to the wayback machine to process. The recorded ARC/WARC file
becomes part of the wayback machine in due course of time.

.. note::

    The liveweb project is under active development, so this documentation may not be up-to-date.

Installation
------------

Liveweb proxy can be installed using `pip <http://www.pip-installer.org/>`_::

    $ pip install liveweb

or, with `easy_install <http://pypi.python.org/pypi/setuptools>`_ ::

    $ easy_install liveweb

See `Development Setup <devsetup>`_ if you want to work with source code.

Running liveweb-proxy
---------------------

Liveweb proxy can be run using::

     $ liveweb-proxy 

To start liveweb-proxy on a different port::

     $ liveweb-proxy -p 8080

To load settings from a config file::

     $ liveweb-proxy -c liveweb.ini

To see the available command-line options::

     $ liveweb-proxy --help

See :ref:`Configuration <config>` section for the available config settings and command line options.

Advanced Usage
--------------

Under the hood, liveweb proxy used `uwsgi <http://projects.unbit.it/uwsgi/>`_ as the http server.

If you want to tweak uwsgi parameters, you can start liveweb as::

    $ uwsgi --master --single-interpreter --lazy --wsgi liveweb.main --processes 1 --threads 10 --http localhost:7070

The values of ``--processes``, ``--threads`` and ``--http`` options can be changed as needed and more options can be added too.

You may have to specify `-H virtualenv_home` if you using a virtualenv.

Documentation
-------------

.. toctree::
   :maxdepth: 3

   devsetup
   config
   errors
