"""Configuración tipada con pydantic-settings.

Fuentes de configuración, en orden de precedencia:
1. Variables de entorno (prefijo ``VALHEIM_DASHBOARD_``).
2. Fichero ``/etc/valheim-dashboard/config.toml`` o el que apunte ``CONFIG``.
3. Valores por defecto.
"""

from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PanelSettings(BaseModel):
    bind: str = "0.0.0.0"
    port: int = 8080
    secret_key_file: Path = Path("/etc/valheim-dashboard/secret.key")
    admin_password_hash_file: Path = Path("/etc/valheim-dashboard/admin_password_hash")
    session_ttl_hours: int = 24
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8080"])
    login_rate_limit_per_min: int = 5


class GameSettings(BaseModel):
    service_name: str = "valheim-server"
    install_dir: Path = Path("/opt/valheim/server")
    savedir: Path = Path("/var/lib/valheim/saves")
    backups_dir: Path = Path("/var/lib/valheim/backups")
    log_file: Path = Path("/var/log/valheim/server.log")
    env_file: Path = Path("/etc/valheim-dashboard/valheim.env")
    name: str = "Mi Valheim Server"
    world: str = "Dedicated"
    password: str = "changeme"
    port: int = 2456
    public: bool = True
    crossplay: bool = False
    save_interval: int = 1800
    instance_id: str = "1"
    extra_args: list[str] = Field(default_factory=list)


class ModifiersSettings(BaseModel):
    preset: str = "normal"
    combat: str = "normal"
    deathpenalty: str = "normal"
    resources: str = "normal"
    raids: str = "normal"
    portals: str = "normal"
    setkeys: list[str] = Field(default_factory=list)

    @field_validator("preset")
    @classmethod
    def _v_preset(cls, v: str) -> str:
        allowed = {"normal", "casual", "easy", "hard", "hardcore", "immersive", "hammer"}
        if v not in allowed:
            raise ValueError(f"preset debe ser uno de {sorted(allowed)}")
        return v

    @field_validator("setkeys")
    @classmethod
    def _v_setkeys(cls, v: list[str]) -> list[str]:
        allowed = {"nobuildcost", "playerevents", "passivemobs", "nomap"}
        for k in v:
            if k not in allowed:
                raise ValueError(f"setkey no soportado: {k}")
        return v


class NetworkSettings(BaseModel):
    public_host: str = ""
    query_port_offset: int = 1
    a2s_probe_interval_seconds: int = 10
    use_a2s: bool = True


class TelegramSettings(BaseModel):
    token: str = ""
    chat_id: str = ""
    enabled: bool = False
    events: list[str] = Field(
        default_factory=lambda: [
            "down", "resources", "maintenance", "update", "backup",
        ]
    )
    cooldown_seconds: int = 60
    rate_limit_per_minute: int = 18
    max_retries: int = 3
    timeout_seconds: float = 5.0
    notify_recovery: bool = True


class BackupSettings(BaseModel):
    max_keep: int = 2
    pre_update: bool = True
    pre_modifier_change: bool = True
    pre_restore: bool = True


class ScheduleSettings(BaseModel):
    restart_cron: str = ""
    idle_shutdown_minutes: int = 0
    warn_before_restart_minutes: int = 10
    maintenance_warnings: list[int] = Field(default_factory=lambda: [10, 1])


class MetricsSettings(BaseModel):
    interval_seconds: float = 1.0
    retention_days: int = 30
    downsample_after_hours: int = 24
    cpu_alert_percent: float = 90.0
    cpu_alert_window_minutes: int = 5
    ram_alert_percent: float = 85.0
    disk_alert_percent: float = 80.0
    disk_alert_critical_percent: float = 90.0
    crash_loop_threshold: int = 3
    crash_loop_window_minutes: int = 10


class StorageSettings(BaseModel):
    data_dir: Path = Path("/var/lib/valheim-dashboard")
    db_path: Path = Path("/var/lib/valheim-dashboard/app.sqlite")
    work_in_process: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VALHEIM_DASHBOARD_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    panel: PanelSettings = Field(default_factory=PanelSettings)
    game: GameSettings = Field(default_factory=GameSettings)
    modifiers: ModifiersSettings = Field(default_factory=ModifiersSettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    backup: BackupSettings = Field(default_factory=BackupSettings)
    schedule: ScheduleSettings = Field(default_factory=ScheduleSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)

    @classmethod
    def from_toml(cls, path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        with path.open("rb") as fh:
            return tomllib.load(fh)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    path = Path(os.environ.get("VALHEIM_DASHBOARD_CONFIG", "/etc/valheim-dashboard/config.toml"))
    overrides = Settings.from_toml(path)
    return Settings(**overrides)


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
