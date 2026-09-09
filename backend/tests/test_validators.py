"""Tests del validador de IDs y password."""

from app.core.util import is_platform_id, is_steamid64, is_world_name, validate_password


def test_steamid64():
    assert is_steamid64("76561198000000001")
    assert not is_steamid64("12345")
    assert not is_steamid64("76561198X00000001")


def test_platform_id():
    assert is_platform_id("[Steam]_76561198000000001")
    assert not is_platform_id("76561198000000001")
    assert not is_platform_id("steam_123")


def test_world_name():
    assert is_world_name("MiMundo")
    assert is_world_name("Mi-Mundo 2")
    assert not is_world_name("a" * 50)
    assert not is_world_name("foo/bar")


def test_password():
    ok, _ = validate_password("secreto123", "W")
    assert ok
    ok, _ = validate_password("123", "W")
    assert not ok
    ok, _ = validate_password('a"b@c!d', "W")
    assert not ok
    ok, _ = validate_password("secreto_mundo", "mundo")
    assert not ok
