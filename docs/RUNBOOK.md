# Runbook

## El servidor no arranca

1. `valheimctl status` o `sudo systemctl status valheim-server`.
2. `sudo journalctl -u valheim-server -n 200 --no-pager`.
3. Buscar `Error bad password:`, `Error loading world`, `Failed to start Steam
   Game Server`.
4. Si es por la password: ≥5 caracteres, sin `" @ !`, que no esté dentro del
   nombre del mundo.

## El mundo no carga: “Missing DB” o “[Old Format]”

Valheim 1.0 escribe cada mundo como un directorio (`_main.*.db2`, `.fwl2`,
`.chunks`, `.ok` + `*.chunk`). Si los `.db`/`.fwl` legados aparecen marcados:

- `Missing DB` = existe un `.fwl` sin `.db` válido. Mira en el backup más
  reciente: `cp <mundo>.db.backup <mundo>.db` o restaura desde el panel.
- `[Old Format]` = mundo legado. Se “mueve” desde el menú del juego a local
  o cloud y se convierte al guardar; no es corrupción.
- Un directorio 1.0 vacío es normal: el mundo aún no se ha guardado bajo el
  nuevo formato. No borrar.

## El servidor está caído y el panel no me deja arrancar

`valheimctl start` desde SSH. Si la unidad no responde:

```bash
sudo systemctl kill -s SIGINT valheim-server
sudo systemctl start valheim-server
```

## Restaurar un backup

En el panel: *Backups → Restaurar*. El servidor se para, se hace un snapshot
del estado actual (por si acaso), se aplica el `tar.zst` sobre el savedir y
se vuelve a arrancar. En LXC: `valheimctl restore <id>`.

## Reinicio de emergencia

```bash
valheimctl stop
valheimctl start
```

## Cambiar de modo Steam a crossplay (o al revés)

El panel: *Configuración → Modo de conexión* → cambiar *Crossplay* → “Aplicar y
reiniciar”. El aviso T-1 min llega a Telegram. El join code cambia en cada
reinicio, se publica de nuevo en la consola del panel y en el grupo.

## Actualizar el servidor a 1.0

En el panel: *Actualizaciones → Actualizar ahora*. Hace backup previo, para
el servidor, ejecuta `steamcmd +app_update 896660 validate` y vuelve a
arrancar. Verifica el arranque en 60-90 s y, si no se ve `DungeonDB Start`,
consulta este runbook.

## Reclamar el join code

Aparece al inicio en la consola del servidor y en el panel
(*Dashboard → Join code*). Se rota en cada reinicio.
