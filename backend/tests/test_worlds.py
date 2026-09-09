"""Tests del servicio de mundos (formato 1.0 + legado)."""

import os
from pathlib import Path

from app.services.worlds import WorldService


def test_list_empty(tmp_path: Path):
    ws = WorldService(tmp_path)
    (tmp_path / "worlds_local").mkdir()
    assert ws.list() == []


def test_list_v10(tmp_path: Path):
    ws = WorldService(tmp_path)
    wl = tmp_path / "worlds_local"
    wl.mkdir()
    d = wl / "MiMundo"
    d.mkdir()
    (d / "_main.5.fwl2").write_text("x")
    (d / "_main.5.db2").write_text("y" * 100)
    (d / "_main.5.chunks").write_text("z")
    (d / "_main.5.ok").write_text("")
    worlds = ws.list()
    assert len(worlds) == 1
    w = worlds[0]
    assert w.name == "MiMundo"
    assert w.format == "v10"
    assert w.last_save_ok is True
    assert w.generation == 5


def test_list_empty_v10(tmp_path: Path):
    ws = WorldService(tmp_path)
    wl = tmp_path / "worlds_local"
    wl.mkdir()
    (wl / "Vacio").mkdir()
    worlds = ws.list()
    assert len(worlds) == 1
    assert worlds[0].empty is True


def test_list_legacy(tmp_path: Path):
    ws = WorldService(tmp_path)
    wl = tmp_path / "worlds_local"
    wl.mkdir()
    (wl / "Viejo.db").write_text("x" * 50)
    (wl / "Viejo.fwl").write_text("y")
    worlds = ws.list()
    assert len(worlds) == 1
    w = worlds[0]
    assert w.format == "legacy"
    assert w.name == "Viejo"


def test_create(tmp_path: Path):
    ws = WorldService(tmp_path)
    (tmp_path / "worlds_local").mkdir()
    w = ws.create("Nuevo")
    assert w.name == "Nuevo"
    assert w.empty is True
    assert (tmp_path / "worlds_local" / "Nuevo").is_dir()


def test_create_invalid_name(tmp_path: Path):
    ws = WorldService(tmp_path)
    (tmp_path / "worlds_local").mkdir()
    try:
        ws.create("../etc")
    except ValueError:
        return
    raise AssertionError("esperaba ValueError")
