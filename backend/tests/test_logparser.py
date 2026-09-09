"""Tests del parser de log."""

from app.services.logparser import parse_line


def test_handshake():
    e = parse_line("05/10/2024 12:00:00: Got handshake from client 76561198000000001")
    assert e is not None
    assert e.event == "steam_handshake"
    assert e.data["steam_id"] == "76561198000000001"


def test_join():
    e = parse_line("05/10/2024 12:00:00: Got character ZDOID from Bjorn : abc-12:3")
    assert e is not None
    assert e.event == "join"
    assert e.data["name"] == "Bjorn"


def test_death():
    e = parse_line("05/10/2024 12:00:00: Got character ZDOID from Astrid : abc-12:0:0")
    assert e is not None
    assert e.event == "death"
    assert e.data["name"] == "Astrid"


def test_bad_password():
    e = parse_line("Peer 76561198000000099 has wrong password")
    assert e is not None
    assert e.event == "bad_password"


def test_login_fail():
    e = parse_line("Failed to authenticate user 76561198000000050, password mismatch")
    assert e is not None
    assert e.event == "login_fail"
    assert e.data["steam_id"] == "76561198000000050"


def test_join_code_v1():
    e = parse_line('05/10/2024 12:00:00: New session server "My server" that has join code ABC123, now 0 player(s)')
    assert e is not None
    assert e.event == "join_code"
    assert e.data["join_code"] == "ABC123"


def test_join_code_v2():
    e = parse_line('05/10/2024 12:00:00: Session "My server" with join code XYZ789 and IP 1.2.3.4:2456 is active with 2 player(s)')
    assert e is not None
    assert e.event == "join_code"
    assert e.data["join_code"] == "XYZ789"


def test_ready_dungeon():
    e = parse_line("05/10/2024 12:00:00: DungeonDB Start")
    assert e is not None
    assert e.event == "ready"


def test_ready_game():
    e = parse_line("05/10/2024 12:00:00: Game server connected")
    assert e is not None
    assert e.event == "ready"


def test_world_save():
    e = parse_line("05/10/2024 12:00:00: World saved")
    assert e is not None
    assert e.event == "world_save"


def test_version():
    e = parse_line("Game version: 1.0.0")
    assert e is not None
    assert e.event == "version"
    assert e.data["version"] == "1.0.0"


def test_unmatched():
    e = parse_line("This line is unknown to the parser")
    assert e is not None
    assert e.event == "unknown"
    assert e.rule == "unmatched"


def test_empty_line():
    assert parse_line("") is None
