Error Codes
===========

The application writes the errors with following codes when something fails when trying to fetch the given URL.

**E10 - Invalid URL**

    When the URL is invalid. For example::

        http://example.com:bad-port/

**E20 - Invalid Domain**

    When the URL has non existant domain. ::

        http://no-such-domain.com/

**E21 - DNS Timeout**

    When DNS resolution is timed out.

**E30 - Connection Refused**


**E31 - Connection Dropped**

**E40 - Connection Timeout**

**E41 - Read Timeout**

In all these cases, the application responds back with status ``200 OK``
with a record contain status ``302 Bad Gateway``.


