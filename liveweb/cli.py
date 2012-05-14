"""Command-line interface to the Liveweb Proxy.
"""
import sys
import os
from optparse import OptionParser, OptionGroup
from .configutil import Config

def make_config():
    c = Config("liveweb")

    c.add_option("-c", "--config",
                 help="specifies the liveweb-proxy config file")

    c.add_option("--archive-format",
                 type="choice",
                 choices=["none", "arc", "warc"],
                 default="arc",
                 help="specifies the archiving format")

    c.add_option("--http-passthrough",
                 type="bool",
                 default="false",
                 help="enables the http-passthrough mode")

    c.add_option("--user-agent", 
                 default="ia_archiver(OS-Wayback)",
                 help="the user-agent string used by liveweb-proxy")

    # server options
    c.add_option("-l", "--listen", 
                 metavar="IP_ADDRESS", 
                 default="127.0.0.1",
                 help="the IP-address on which the liveweb-proxy will listen on (default: %default).")

    c.add_option("-p", "--port",
                 type="int",
                 default="7070",
                 help="the port on which the liveweb-proxy will listen on (default: %default).")

    c.add_option("-w", "--workers", 
                 type="int", 
                 default="1",
                 help="the number of worker processes (default: %default)")

    c.add_option("-t", "--threads",
                 type="int",
                 default="10",
                 help="the number of threads/process (default: %default)")

    # storage options
    c.add_option("-o", "--output-directory", 
                 metavar="DIR", 
                 default="records",
                 help="the directory to store the arc/warc files (default: %default)")

    c.add_option("--filename-pattern", 
                 type="string", 
                 default="live-%(timestamp)s-%(serial)05d.arc.gz",
                 help="specifies the format of the filename to store the arc/warc files.")

    c.add_option("--num-writers", 
                 type="int", 
                 default="1",
                 help="specifies the number of concurrent writers")

    c.add_option("--filesize-limit",
                 type="bytes", 
                 default="100MB",
                 help="specifies the recommended size limit for each file.")

    # timeouts and limits

    c.add_option("--default-timeout", 
                 type="time", 
                 default="10s",
                 help="the default timeout value to use if a timeout option is not specified."),

    c.add_option("--dns-timeout", 
                 type="time",
                 help="maximum allowed time for domain name resolution")

    c.add_option("--connect-timeout", 
                 type="time",
                 help="maximum allowed time for establishing connection")

    c.add_option("--initial-data-timeout",
                 type="time",
                 help="maximum wait time to receive status and headers from the remove server")

    c.add_option("--read-timeout",
                 type="time",
                 help="the read timeout")

    c.add_option("--max-request-time",
                 type="time",
                 default="5m",
                 help="the total amout of time a HTTP request can take")

    c.add_option("--max-response-size",
                 type="bytes",
                 default="100MB",
                 help="the maximum allowed size of response")

    # cache options
    c.add_option("--cache", 
                 type="choice", 
                 choices=["none", "redis", "sqlite"], 
                 default="none", 
                 help="specifies the type of cache to use")

    c.add_option("--redis-host", 
                 type="string", 
                 default="localhost")

    c.add_option("--redis-port", 
                 type="int", 
                 default="6379")

    c.add_option("--redis-db", 
                 type="int", 
                 default="0")

    c.add_option("--redis-expire-time", 
                 type="time", 
                 default="1h")

    c.add_option("--redis-max-record-size", 
                 type="bytes", 
                 default="100KB")

    c.add_option("--sqlite-db",
                 type="string",
                 default="liveweb.db")

    return c

def find_python_home():
    # Python will be installed in bin/ or Scripts/ directory. Parent
    # of that will be the Python home.
    bindir = os.path.abspath(os.path.dirname(sys.executable))
    home = os.path.dirname(bindir)
    return home

def run_uwsgi(config):
    python_home = os.getenv("VIRTUAL_ENV") or find_python_home()
    bind = "%s:%s" % (config['listen'], config['port'])

    # Set the UWSGI parameters in the env so that these details are
    # not shown in ps and top commands.
    os.putenv("UWSGI_MASTER", "1")
    os.putenv("UWSGI_SINGLE_INTERPRETER", "1")
    os.putenv("UWSGI_WSGI", "liveweb.main")
    os.putenv("UWSGI_PROCNAME_PREFIX", " liveweb-proxy ")
    os.putenv("UWSGI_HOME", python_home)

    os.putenv("UWSGI_PROCESSES", str(config['workers']))
    os.putenv("UWSGI_THREADS", str(config['threads']))
    os.putenv("UWSGI_HTTP", bind)
    os.putenv("UWSGI_LISTEN", "1024") # socket listen backlog. TODO support customizing this

    args = ["liveweb-proxy"]

    os.execvp("uwsgi", args)

def set_dns_timeout(timeout):
    os.putenv("RES_OPTIONS", "timeout:%d attempts:1" % timeout)

def main():
    c = make_config()

    # load configuration from env, config file and command line arguments.
    c.load()

    # update current env with new values so that the exec'ed process can take these settings
    c.putenv()

    set_dns_timeout(c.get('dns_timeout') or c.get('default_timeout'))

    run_uwsgi(c.dict())
    
if __name__ == "__main__":
    main()
