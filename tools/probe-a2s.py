"""Sondea A2S_INFO y A2S_PLAYERS en una dirección y puerto. Útil para
comisionar el panel y verificar si A2S responde con/sin crossplay.

Uso:
    python tools/probe-a2s.py <ip> <puerto>
"""

from __future__ import annotations

import asyncio
import sys

import a2s


async def probe(addr: tuple[str, int]) -> int:
    info = await asyncio.to_thread(a2s.info, addr, timeout=3.0)
    print("A2S_INFO:")
    for f in info._fields:
        print(f"  {f} = {getattr(info, f)!r}")
    try:
        players = await asyncio.to_thread(a2s.players, addr, timeout=3.0)
    except Exception as exc:
        print(f"A2S_PLAYERS: error {exc!r}")
        return 0
    print(f"A2S_PLAYERS ({len(players)}):")
    for p in players:
        print(f"  - {p.name} score={p.score} dur={p.duration:.1f}s")
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print("Uso: probe-a2s.py <ip> <puerto>", file=sys.stderr)
        return 2
    addr = (sys.argv[1], int(sys.argv[2]))
    try:
        asyncio.run(probe(addr))
    except Exception as exc:
        print(f"Error: {exc!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
