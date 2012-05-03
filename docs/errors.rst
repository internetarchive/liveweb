Error Codes
===========

The application writes the errors with following codes when something fails when trying to fetch the given URL.

1X - Bad Input
--------------

**E10 - Invalid URL**

    The given URL is invalid. For example::

        http://example.com:bad-port/

2X - DNS errors
---------------

**E20 - Invalid Domain**

    The URL has non existant domain.

**E21 - DNS Timeout**

    The hostname couldn't be resolved within :ref:`config_dns_timeout` seconds.

3X - Connection Errors
----------------------

**E30 - Connection Refused**

    Connection refused by the server.

**E31 - Connect Timeout**

    Connection couldn't be established within :ref:`config_connect_timeout` seconds.

**E32 - Initial Data Timeout**

    Initial data (HTTP headers) couldn't be obtained within :ref:`config_initial_data_timeout` seconds.

**E33 - Read Timeout**

    When reading data from the remote server, no data was received for :ref:`config_read_timeout` seconds.

**E34 - Connection Dropped**

   The remote server dropped the connection before all the data was received.

**E39 - Unexpected Connection Error**

   Unexpected connection error when receiving data from the remote server.

4X - Resource Limits
--------------------

**E40 - Response Too Big**

    The response length is bigger than :ref:`config_max_response_size` bytes.

**E41 - Request Took Too Long**

   The request was not completed within :ref:`config_max_request_time` seconds.

In all these cases, the application responds back with status ``200 OK``
with a record contain status ``302 Bad Gateway``.


