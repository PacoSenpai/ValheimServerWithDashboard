# World Modifiers — Verificación empírica (Valheim 1.0)

> **Pendiente de rellenar durante la fase de comisionado.**
> La documentación oficial (FAQ y manual del servidor dedicado) no cubre los
> cambios del binario del servidor en 1.0, así que nada de lo que está abajo
> debe darse por definitivo hasta verificarlo contra el build real.

## Procedimiento

1. Arrancar el servidor con `-logFile /var/log/valheim/server.log` y capturar
   el log entero del primer arranque.
2. Ejecutar `tools/capture-log-patterns.py /var/log/valheim/server.log` y revisar
   las líneas que el parser no reconoce.
3. Probar cada valor de `-preset`, `-modifier` y `-setkey` y comprobar el
   arranque y el resultado.
4. Con y sin `-crossplay`, sondear A2S en UDP 2457 y 2458 y registrar la
   respuesta.

## Flags confirmados del manual oficial (abril 2024)

Aplicables hoy; en 1.0 se verifican:

- `-name`, `-port`, `-world`, `-password`, `-public`, `-savedir`, `-saveinterval`,
  `-instanceid`, `-crossplay`.
- `-preset <normal|casual|easy|hard|hardcore|immersive|hammer>`.
- `-modifier combat <veryeasy|easy|hard|veryhard>`.
- `-modifier deathpenalty <casual|veryeasy|easy|hard|hardcore>`.
- `-modifier resources <muchless|less|more|muchmore|most>`.
- `-modifier raids <none|muchless|less|more|muchmore>`.
- `-modifier portals <casual|hard|veryhard>`.
- `-setkey <nobuildcost|playerevents|passivemobs|nomap>` (repetible).

## Cambios conocidos a verificar en 1.0

- ¿Aparecen flags nuevos por Deep North / crossplay? (ej. `-players`).
- ¿`-setkey` persiste en el `.fwl` o se pierde entre reinicios?
- ¿El orden `preset → modifier → setkey` se sigue aplicando?
- ¿A2S responde con `-crossplay`?

## Líneas de log base a verificar (parser)

| Evento | Patrón a comprobar |
|---|---|
| Servidor listo | `DungeonDB Start` |
| Conexión | `Got handshake from client (\d+)` / `Got connection SteamID (\d+)` |
| Personaje en juego | `Got character ZDOID from (.+?) : ([\w-]+):` |
| Muerte | `Got character ZDOID from (.+?) : 0:0` |
| Desconexión | `Closing socket (\d+)` |
| Contraseña errónea | `Peer (\d+) has wrong password` / `Failed to authenticate user` |
| Join code | `join code (\w{6})` / `New session server "..."` |
| Registro PlayFab | `Register PlayFab server` / `Joined PlayFab party network` |

## Resultados de la verificación

> (Rellenar tras el primer arranque de 1.0.)
