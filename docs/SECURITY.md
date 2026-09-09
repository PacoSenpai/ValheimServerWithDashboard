# Seguridad

## Usuarios y permisos

- El servidor de juego y el panel corren como `valheim` (no `root`).
- El panel hace `sudo` NOPASSWD **solo** a:
  - `systemctl start|stop|restart|status|is-active|kill -s SIGINT valheim-server`
  - `systemctl daemon-reload valheim-server`
- No se expone ningún puerto a Internet para el panel.

## Secretos

| Secreto | Dónde | Permisos |
|---|---|---|
| JWT del panel | `/etc/valheim-dashboard/secret.key` | 0600 `valheim:valheim` |
| Password admin (hash) | `config.toml` | 0600 `valheim:valheim` |
| Token Telegram | `config.toml` (override `VALHEIM_DASHBOARD_TELEGRAM_TOKEN`) | 0600 |
| `chat_id` | `config.toml` | 0600 |
| `admin_password_hash` | `config.toml` (campo; nunca el password en claro) | 0600 |

**Regla**: ningún secreto en el repositorio, ni siquiera en ejemplos. Los
ficheros de configuración de ejemplo (`*.example`) contienen solo placeholders.

## Red

- UFW: `allow 22/tcp from <tu-LAN>` y `allow 8080/tcp from <tu-LAN>` para el
  panel, `allow 2456:2458/udp` para el juego (en modo Steam).
- En modo crossplay no se abren los puertos del juego (PlayFab hace relay).
- La cookie de sesión es `httpOnly`, `SameSite=Strict`, y se renueva al
  iniciar sesión.
- Rate limit: 5 intentos/min en `/api/auth/login`.

## Auditoría

Todas las acciones de cambio (configuración, modificadores, mundos, listas,
backups, actualizaciones, programaciones) se registran en `audit_log` con
timestamp, usuario y payload. Se muestran en el panel y se exponen por API.

## Actualizaciones

`steamcmd +app_update 896660 validate` es la única fuente de binarios. No
mezclar binarios de fuera de Steam. Los mods (BepInEx) no están soportados en
la v1; se añadirá un adaptador de comandos en caliente cuando exista build
compatible con 1.0.
