"""Servidor falso de Valheim para desarrollar y probar el panel.

Emite por stdout líneas idénticas a las que produce el binario real, con una
secuencia de jugadores conectando y desconectando. Útil para iterar la UI sin
instalar el juego y para los tests de integración del parser.

Uso:
    python tools/fake-valheim-server.py [--log PATH] [--interval 8]
"""

from __future__ import annotations

import argparse
import os
import random
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

PLAYERS = [
    ("76561198000000001", "Bjorn", "viking"),
    ("76561198000000002", "Astrid", "explorer"),
    ("76561198000000003", "Eirik", "builder"),
    ("76561198000000004", "Sigrid", "hunter"),
    ("76561198000000005", "Ragnar", "wanderer"),
    ("76561198000000006", "Helga", "miner"),
    ("76561198000000007", "Olaf", "cook"),
    ("76561198000000008", "Freya", "mage"),
]

STAGES = [
    (1.0, "Game version: 1.0.0"),
    (0.5, "Steam: bound to UDP 2456"),
    (0.5, "Steam: bound to UDP 2457 (query)"),
    (0.5, "Steam: bound to UDP 2458"),
    (0.5, 'New session server "Mi Server" that has join code ABC123, now 0 player(s)'),
    (0.5, "DungeonDB Start"),
    (0.3, "Game server connected"),
    (0.2, "World: MiMundo (seed=abc123)"),
    (0.2, "World saved"),
    (3.0, None),
    (0.3, "Got handshake from client 76561198000000001"),
    (0.3, "Got character ZDOID from Bjorn : abcdef-12:0"),
    (4.0, "Got character ZDOID from Bjorn : abcdef-12:0:0"),
    (3.0, "Closing socket 77001"),
    (2.0, "Got handshake from client 76561198000000002"),
    (0.3, "Got character ZDOID from Astrid : aaaaaa-99:0"),
    (5.0, "Got handshake from client 76561198000000099"),
    (0.2, "Peer 76561198000000099 has wrong password"),
    (0.3, "Closing socket 77099"),
    (4.0, "Got character ZDOID from Astrid : aaaaaa-99:0:0"),
    (3.0, "World saved"),
    (4.0, "Got character ZDOID from Bjorn : abcdef-12:0"),
    (10.0, None),
    (0.3, "Got handshake from client 76561198000000003"),
    (0.3, "Got character ZDOID from Eirik : bbbbbb-77:0"),
    (15.0, None),
    (0.3, "Failed to authenticate user 76561198000000050, password mismatch"),
    (0.2, "Closing socket 77100"),
    (20.0, "World saved"),
    (40.0, "Steam: warning network congestion region: 3 players"),
    (60.0, "World saved"),
    (60.0, None),
    (60.0, None),
]


def ts() -> str:
    return datetime.now().strftime("%m/%d/%Y %H:%M:%S")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fake Valheim server for development.")
    parser.add_argument("--log", default=None, help="Ruta al fichero de log (opcional).")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Factor de velocidad del tiempo (1.0 = real, 0.1 = 10x).")
    args = parser.parse_args()

    log_path = Path(args.log) if args.log else None
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", buffering=1)
    else:
        log_handle = None

    def emit(line: str) -> None:
        msg = f"{ts()}: {line}"
        print(msg, flush=True)
        if log_handle is not None:
            log_handle.write(msg + "\n")

    stop = False

    def handle(signum, frame):
        nonlocal stop
        stop = True
        emit("Got signal, saving world")
        emit("World saved")
        emit("Server has been shutdown.")

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)

    emit("Starting Valheim Dedicated Server (fake)")
    emit("Server PID: " + str(os.getpid()))

    rng = random.Random(42)
    idx = 0
    while not stop and idx < len(STAGES):
        delay, line = STAGES[idx]
        idx += 1
        time.sleep(max(0.05, delay * args.interval))
        if stop:
            break
        if line is None:
            if rng.random() < 0.2:
                pid = rng.choice([p for p, _, _ in PLAYERS if rng.random() < 0.6])
                name = next(n for s, n, _ in PLAYERS if s == pid)
                emit(f"Got handshake from client {pid}")
                emit(f"Got character ZDOID from {name} : {rng.randint(0, 0xffffff):x}-{rng.randint(0, 99)}:0")
            continue
        emit(line)

    while not stop:
        time.sleep(1.0)
        if rng.random() < 0.05:
            emit("World saved")

    if log_handle is not None:
        log_handle.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
