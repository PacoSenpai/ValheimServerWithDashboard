"""Schemas Pydantic de la API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GameMode = Literal["steam", "crossplay"]


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=8, max_length=128)


class GameConfigIn(BaseModel):
    name: str
    world: str
    password: str
    port: int
    public: bool
    crossplay: bool
    save_interval: int = 1800
    extra_args: list[str] = Field(default_factory=list)


class ModifiersIn(BaseModel):
    preset: str
    combat: str = "normal"
    deathpenalty: str = "normal"
    resources: str = "normal"
    raids: str = "normal"
    portals: str = "normal"
    setkeys: list[str] = Field(default_factory=list)


class ListIn(BaseModel):
    entries: list[str]


class WorldIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class ScheduleIn(BaseModel):
    restart_cron: str
    idle_shutdown_minutes: int
    warn_before_restart_minutes: int


class TelegramIn(BaseModel):
    token: str
    chat_id: str
    enabled: bool
    events: list[str] = Field(default_factory=list)


class NetworkIn(BaseModel):
    public_host: str
    use_a2s: bool
    a2s_probe_interval_seconds: int
