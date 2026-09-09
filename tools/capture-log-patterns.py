"""Lee un log del servidor de Valheim y vuelca los patrones conocidos y
desconocidos. Útil para extender el parser en el comisionado de 1.0.

Uso:
    python tools/capture-log-patterns.py /var/log/valheim/server.log
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "logparser",
    ROOT / "backend" / "app" / "services" / "logparser.py",
)
if SPEC is None or SPEC.loader is None:
    print("No se pudo cargar logparser desde backend/app/services/logparser.py", file=sys.stderr)
    sys.exit(1)
logparser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(logparser)

KNOWN = {p.name for p in logparser.RULES}


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: capture-log-patterns.py <log>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"No existe {path}", file=sys.stderr)
        return 2

    matched: Counter[str] = Counter()
    unmatched: Counter[str] = Counter()
    sample: dict[str, str] = {}

    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        found = False
        for rule in logparser.RULES:
            if rule.regex.search(line):
                matched[rule.name] += 1
                sample.setdefault(rule.name, line)
                found = True
                break
        if not found:
            stripped = re.sub(r"\d+", "0", line)
            stripped = re.sub(r"0+", "0", stripped)
            key = stripped[:140]
            unmatched[key] += 1
            sample.setdefault(f"??{key}", line)

    print(f"Reconocidas ({sum(matched.values())} líneas):")
    for name, n in matched.most_common():
        if name in KNOWN:
            print(f"  {name:20s} {n:6d}  {sample[name][:120]}")

    print(f"\nDesconocidas ({sum(unmatched.values())} líneas únicas={len(unmatched)}):")
    for key, n in unmatched.most_common(20):
        print(f"  {n:5d}  {sample[key][:140]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
