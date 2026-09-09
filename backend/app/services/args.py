"""Generador de argumentos para ``valheim_server.x86_64``.

Orden obligatorio: ``-preset`` → ``-modifier`` → ``-setkey``. El preset pisa
lo anterior; los modificadores van siempre después. ``normal`` se omite
(equivale a no pasar el flag).
"""

from __future__ import annotations

from app.core.config import GameSettings, ModifiersSettings
from app.core.util import validate_password

PRESETS = {"normal", "casual", "easy", "hard", "hardcore", "immersive", "hammer"}
MODIFIER_VALUES: dict[str, set[str]] = {
    "combat": {"normal", "veryeasy", "easy", "hard", "veryhard"},
    "deathpenalty": {"normal", "casual", "veryeasy", "easy", "hard", "hardcore"},
    "resources": {"normal", "muchless", "less", "more", "muchmore", "most"},
    "raids": {"normal", "none", "muchless", "less", "more", "muchmore"},
    "portals": {"normal", "casual", "hard", "veryhard"},
}
SETKEYS = {"nobuildcost", "playerevents", "passivemobs", "nomap"}


def build_argv(game: GameSettings, mod: ModifiersSettings) -> list[str]:
    argv: list[str] = [
        "-nographics",
        "-batchmode",
        "-name", game.name,
        "-port", str(game.port),
        "-world", game.world,
        "-password", game.password,
        "-savedir", str(game.savedir),
        "-saveinterval", str(game.save_interval),
        "-instanceid", game.instance_id,
    ]
    if game.public:
        argv.append("-public")
        argv.append("1")
    else:
        argv.append("-public")
        argv.append("0")
    if game.crossplay:
        argv.append("-crossplay")
    argv.extend(game.extra_args)

    if mod.preset and mod.preset != "normal":
        argv.extend(["-preset", mod.preset])
    for name in ("combat", "deathpenalty", "resources", "raids", "portals"):
        value = getattr(mod, name, "normal")
        if value and value != "normal" and value in MODIFIER_VALUES[name]:
            argv.extend(["-modifier", name, value])
    seen: set[str] = set()
    for key in mod.setkeys:
        if key in SETKEYS and key not in seen:
            argv.extend(["-setkey", key])
            seen.add(key)
    return argv


def validate_modifiers(mod: ModifiersSettings) -> tuple[bool, str]:
    if mod.preset not in PRESETS:
        return False, f"preset no soportado: {mod.preset}"
    for name, allowed in MODIFIER_VALUES.items():
        value = getattr(mod, name, "normal")
        if value not in allowed:
            return False, f"{name}={value!r} no es válido"
    for key in mod.setkeys:
        if key not in SETKEYS:
            return False, f"setkey no soportado: {key}"
    return True, ""


def validate_game(game: GameSettings) -> tuple[bool, str]:
    ok, msg = validate_password(game.password, game.world)
    if not ok:
        return False, msg
    if not game.name or len(game.name) > 60:
        return False, "El nombre del servidor debe tener entre 1 y 60 caracteres"
    if not game.world or len(game.world) > 40:
        return False, "El nombre del mundo debe tener entre 1 y 40 caracteres"
    if not (1024 <= game.port <= 65535):
        return False, "Puerto fuera de rango"
    if not (60 <= game.save_interval <= 86400):
        return False, "saveinterval debe estar entre 60 y 86400 segundos"
    return True, ""


def diff(old: list[str], new: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    o, n = list(old), list(new)
    i = j = 0
    while i < len(o) and j < len(n):
        if o[i] == n[j]:
            i += 1
            j += 1
            continue
        if j + 1 < len(n) and o[i] == n[j + 1]:
            out.append({"kind": "add", "arg": n[j]})
            j += 1
            continue
        if i + 1 < len(o) and o[i + 1] == n[j]:
            out.append({"kind": "remove", "arg": o[i]})
            i += 1
            continue
        out.append({"kind": "remove", "arg": o[i]})
        out.append({"kind": "add", "arg": n[j]})
        i += 1
        j += 1
    while i < len(o):
        out.append({"kind": "remove", "arg": o[i]})
        i += 1
    while j < len(n):
        out.append({"kind": "add", "arg": n[j]})
        j += 1
    return out


def parse_env_argv(path) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith("ARGV="):
            return line[5:].strip()
    return ""
