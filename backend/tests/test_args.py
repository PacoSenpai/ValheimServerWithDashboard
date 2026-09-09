"""Tests del generador de argumentos."""

from app.core.config import GameSettings, ModifiersSettings
from app.services.args import build_argv, diff, validate_game, validate_modifiers


def _game(**over):
    base = dict(
        name="X", world="W", password="secreto123",
        port=2456, public=True, crossplay=False,
        save_interval=1800, instance_id="1",
    )
    base.update(over)
    return GameSettings(**base)


def _mod(**over):
    base = dict(preset="normal", combat="normal", deathpenalty="normal",
                resources="normal", raids="normal", portals="normal", setkeys=[])
    base.update(over)
    return ModifiersSettings(**base)


def test_argv_basico():
    argv = build_argv(_game(), _mod())
    assert "-name" in argv and "X" in argv
    assert "-world" in argv and "W" in argv
    assert "-public" in argv and "1" in argv
    assert "-nographics" in argv and "-batchmode" in argv
    assert "-crossplay" not in argv


def test_argv_crossplay_y_modificadores():
    argv = build_argv(_game(crossplay=True),
                      _mod(preset="hard", combat="veryhard", setkeys=["nomap"]))
    assert "-crossplay" in argv
    assert "-preset" in argv and "hard" in argv
    assert "-modifier" in argv and "combat" in argv and "veryhard" in argv
    assert "-setkey" in argv and "nomap" in argv
    idx_preset = argv.index("-preset")
    idx_mod = argv.index("-modifier")
    idx_setkey = argv.index("-setkey")
    assert idx_preset < idx_mod < idx_setkey


def test_normal_se_omite():
    argv = build_argv(_game(), _mod(preset="normal", combat="normal", resources="normal"))
    assert "-preset" not in argv
    assert "-modifier" not in argv
    assert "-setkey" not in argv


def test_password_corta():
    ok, msg = validate_game(_game(password="123"))
    assert not ok
    assert "5" in msg


def test_password_caracteres_invalidos():
    ok, _ = validate_game(_game(password='abc"@!'))
    assert not ok


def test_password_contiene_nombre_mundo():
    ok, _ = validate_game(_game(world="mimundo", password="secreto_mimundo"))
    assert not ok


def test_preset_invalido():
    m = _mod()
    m.preset = "nuclear"
    ok, msg = validate_modifiers(m)
    assert not ok


def test_modifier_invalido():
    m = _mod()
    m.combat = "facil"
    ok, _ = validate_modifiers(m)
    assert not ok


def test_diff_agrega():
    d = diff(["-name", "A"], ["-name", "A", "-crossplay"])
    assert any(x["kind"] == "add" and x["arg"] == "-crossplay" for x in d)


def test_diff_quita():
    d = diff(["-name", "A", "-crossplay"], ["-name", "A"])
    assert any(x["kind"] == "remove" and x["arg"] == "-crossplay" for x in d)
