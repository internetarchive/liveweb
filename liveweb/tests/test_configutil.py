from ..configutil import ConfigOption, Config, parse_bytes, parse_time

class TestConfigOption:
    def test_add_option(self):
        opt = ConfigOption("--threads", help="Number of threads")
        assert opt.dest == "threads"

    def test_help(self):
        opt = ConfigOption("--threads", help="Number of threads")
        assert opt.option.help == "Number of threads"

        opt = ConfigOption("--threads", default="10", help="Number of threads (default: %default)")
        assert opt.option.help == "Number of threads (default: 10)"

    def test_default(self):
        c = ConfigOption("--foo")
        assert c.value == None

        c = ConfigOption("--foo", default="foo-default")
        assert c.value == "foo-default"

    def test_from_env(self):
        c = ConfigOption("--foo", default="foo-default")
        c.load_from_env({})
        assert c.value == "foo-default"

        c.load_from_env({"LIVEWEB_FOO": "foo-env"})
        assert c.value == "foo-env"

    def test_putenv(self, monkeypatch):
        import os

        environ = {}
        monkeypatch.setattr(os, "environ", environ)
        monkeypatch.setattr(os, "getenv", environ.__getitem__)
        monkeypatch.setattr(os, "putenv", environ.__setitem__)

        c = ConfigOption("--foo", default="foo-default")

        c.putenv()
        assert environ == {}

        c.set("new-value")
        c.putenv()
        assert environ == {"LIVEWEB_FOO": "new-value"}

def test_parse_bytes():
    assert parse_bytes("5") == 5
    assert parse_bytes("5KB") == 5 * 1024
    assert parse_bytes("5MB") == 5 * 1024 * 1024
    assert parse_bytes("5GB") == 5 * 1024 * 1024 * 1024

def test_parse_time():
    assert parse_time("5") == 5.0
    assert parse_time("5s") == 5.0
    assert parse_time("5m") == 5.0 * 60
    assert parse_time("5h") == 5.0 * 3600

    

