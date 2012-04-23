Liveweb Proxy for Wayback Machine
=================================

[![Build Status](https://secure.travis-ci.org/internetarchive/liveweb.png?branch=master)](http://travis-ci.org/internetarchive/liveweb)

Liveweb proxy is component of Internet Archive's [wayback machine][]
project.

[wayback machine]: http://web.archive.org/

The liveweb proxy captures the content of a web page in real time, archives it 
into a ARC or WARC file and returns the ARC/WARC record back to the wayback 
machine to process. The recorded ARC/WARC file becomes part of the wayback 
machine in due course of time.

How to setup
============

* `make venv`

	This setup a new virtual env in the project directory and instals all the dependencies.
	
* `make run`

	This starts running the liveweb proxy.
	
* `make test`

	Runs all the test cases.
	
