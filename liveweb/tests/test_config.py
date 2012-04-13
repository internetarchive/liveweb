from .. import config

def test_parse_size():
    assert config._parse_size("123") == 123
    assert config._parse_size(123) == 123   
    
    assert config._parse_size("123KB") == 123 * 1024
    assert config._parse_size("123MB") == 123 * 1024 * 1024
    assert config._parse_size("123GB") == 123 * 1024 * 1024 * 1024

    