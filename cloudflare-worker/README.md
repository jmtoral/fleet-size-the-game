# Ranking compartido — Worker de Cloudflare

**Ya está desplegado y en uso:**
`https://fleet-sizing-leaderboard.jmtoralcruz.workers.dev`

El juego funciona sin esto: `index.html` guarda el ranking en `localStorage` y
sólo lo vuelve compartido porque `CONFIG.leaderboard.apiUrl` apunta a este
Worker. Si el Worker se cae, el juego sigue jugándose con ranking local.

| Recurso | Valor |
|---|---|
| Worker | `fleet-sizing-leaderboard` |
| Namespace KV | `FLEET_SIZING_KV` (`cb31638b51264b74943b18fd60997339`) |
| Binding en el código | `env.LEADERBOARD_KV` |

El namespace es **propio de este juego**. La cuenta ya tenía un `LEADERBOARD_KV`
que es el de Stay Time, con partidas reales; se mantienen separados para poder
vaciar uno sin tocar el otro.

## Volver a desplegar

```bash
cd cloudflare-worker
npx wrangler deploy
```

Si es una cuenta nueva, primero `npx wrangler login` y crear el namespace con
`npx wrangler kv namespace create FLEET_SIZING_KV`, pegando el id en
`wrangler.toml`.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/api/leaderboard` | Top 10 por balance descendente |
| `POST` | `/api/score` | Registra una partida y devuelve el Top 10 |
| `POST` | `/api/reset` | Vacía el ranking. Requiere `X-Admin-Secret` |

Orden: balance descendente; empates se rompen por nivel de servicio (mayor) y
luego por deuda final (menor). Es el mismo criterio que `lbOrdenar` en
`index.html`; si cambias uno, cambia el otro.

## Cómo se guarda: una llave por partida

Cada partida se escribe en su propia llave `score:<id>` y el ranking se arma al
leer, con un `list()` que trae las entradas en la metadata.

La versión obvia —guardar la lista completa en una sola llave y hacer
leer/ordenar/escribir en cada POST— **pierde partidas**, porque las lecturas de
KV son de consistencia eventual: dos jugadores que guardan casi al mismo tiempo
leen la misma foto vieja y el segundo sobrescribe al primero. Se reprodujo en
pruebas: de 4 partidas guardadas seguidas sobrevivieron 2. Con una llave por
partida, 5 escrituras en paralelo sobreviven las 5.

**Consecuencia a tener presente:** `list()` tarda unos 15 s (medido) en ver una
llave nueva, y lo mismo al borrar. Por eso:

- La respuesta del `POST /api/score` mezcla el `list()` con la entrada recién
  guardada, para que quien acaba de jugar se vea al instante.
- El cliente **fusiona** en vez de reemplazar su ranking local con lo que
  responde el servidor. Si reemplazara, una respuesta todavía incompleta le
  borraría sus partidas anteriores.
- Tras un `/api/reset`, el ranking puede seguir apareciendo unos segundos.

## Notas

- No hay botón público de borrado. `/api/reset` exige el header
  `X-Admin-Secret` y, si `ADMIN_SECRET` no está configurado, **rechaza
  siempre** — es preferible que el reinicio no funcione a dejarlo abierto.
  Hoy **no está configurado**; para habilitarlo:
  `npx wrangler secret put ADMIN_SECRET`.
- El Worker no confía en el cuerpo del POST: recorta y acota todos los campos.
  El nombre se guarda en crudo y se escapa al pintarlo en el cliente.
- Las partidas sólo son comparables con la misma semilla. La entrada guarda
  `semilla` y `modo` (`clasico` / `duro`) para poder detectar mezclas.
- Para vaciar el ranking sin `ADMIN_SECRET`, se pueden borrar las llaves
  directo: `npx wrangler kv key list --namespace-id=<id> --remote --prefix=score:`
  y luego `npx wrangler kv bulk delete`.

## Reiniciar el ranking

```bash
curl -X POST https://<tu-worker>.workers.dev/api/reset \
  -H "X-Admin-Secret: <tu-secreto>"
```
