# Ranking compartido — Worker de Cloudflare

El juego funciona sin esto. `index.html` guarda el ranking en `localStorage` y
sólo lo vuelve compartido si `CONFIG.leaderboard.apiUrl` apunta a este Worker.

## Desplegar

Hace falta Node (en esta máquina no está instalado; el juego no lo necesita,
sólo el despliegue).

```bash
cd cloudflare-worker
npx wrangler login

# 1. Crear el almacenamiento persistente
npx wrangler kv namespace create LEADERBOARD_KV
#    -> copia el id que imprime y descomenta el bloque [[kv_namespaces]]
#       de wrangler.toml con ese id

# 2. Definir el secreto que protege el reinicio del ranking
npx wrangler secret put ADMIN_SECRET

# 3. Publicar
npx wrangler deploy
```

Al terminar, `wrangler` imprime la URL (algo como
`https://fleet-sizing-leaderboard.<tu-subdominio>.workers.dev`). Pégala en
`index.html`:

```js
leaderboard: {
  maxEntries: 10,
  apiUrl: 'https://fleet-sizing-leaderboard.<tu-subdominio>.workers.dev',
  ...
}
```

Alternativa sin Node: crear el Worker desde el panel de Cloudflare, pegar el
contenido de `worker.js`, y enlazar a mano el namespace KV con binding
`LEADERBOARD_KV` y la variable de entorno `ADMIN_SECRET`.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/leaderboard` | Top 10 por balance descendente |
| `POST` | `/api/score` | Registra una partida y devuelve el Top 10 |
| `POST` | `/api/reset` | Vacía el ranking. Requiere `X-Admin-Secret` |

Orden: balance descendente; empates se rompen por nivel de servicio (mayor) y
luego por deuda final (menor). Es el mismo criterio que `lbOrdenar` en
`index.html`; si cambias uno, cambia el otro.

## Notas

- No hay botón público de borrado. `/api/reset` exige el header
  `X-Admin-Secret` y, si `ADMIN_SECRET` no está configurado, **rechaza
  siempre** — es preferible que el reinicio no funcione a dejarlo abierto.
- El Worker no confía en el cuerpo del POST: recorta y acota todos los campos.
  El nombre se guarda en crudo y se escapa al pintarlo en el cliente.
- Las partidas sólo son comparables con la misma semilla. La entrada guarda
  `semilla` y `modo` (`clasico` / `duro`) para poder detectar mezclas.

## Reiniciar el ranking

```bash
curl -X POST https://<tu-worker>.workers.dev/api/reset \
  -H "X-Admin-Secret: <tu-secreto>"
```
