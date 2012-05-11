from .. import config
import pytest

class TestConfigItem:
    def test_parse_int(self):
        c = config.ConfigItem("foo")
        assert c.parse_int("1") == 1
        with pytest.raises(ValueError):
            assert c.parse_int("bad")

    def test_parse_time(self):
        c = config.ConfigItem("foo")
        assert c.parse_time("1") == 1
        assert c.parse_time("1.5") == 1.5
        assert c.parse_time("2m") == 2 * 60
        assert c.parse_time("2h") == 2 * 3600

        with pytest.raises(ValueError):
            assert c.parse_time("2x")

    def test_parse_bytes(self):
        c = config.ConfigItem("foo")
        assert c.parse_bytes("1") == 1
        assert c.parse_bytes("2KB") == 2 * 1024
        assert c.parse_bytes("2MB") == 2 * 1024 * 1024
        assert c.parse_bytes("2GB") == 2 * 1024 * 1024 * 1024

    def test_default(self):
        c = config.ConfigItem("foo")
        assert c.value == None

        c = config.ConfigItem("foo", default="foo-default")
        assert c.value == "foo-default"

    def test_from_env(self):
        c = config.ConfigItem("foo", default="foo-default")
        c.load_from_env({})
        assert c.value == "foo-default"

        c.load_from_env({"LIVEWEB_FOO": "foo-env"})
        assert c.value == "foo-env"
