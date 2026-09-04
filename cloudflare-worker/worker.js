/**
 * Fleet Sizing — Worker de Cloudflare para el ranking compartido.
 *
 * Endpoints:
 *   GET  /api/leaderboard  -> Top 10 ordenado por balance descendente.
 *   POST /api/score        -> Registra una partida y devuelve el Top 10 actualizado.
 *   POST /api/reset        -> Vacía el ranking. Protegido por ADMIN_SECRET.
 *
 * El juego funciona sin este Worker: `index.html` guarda en localStorage y sólo
 * sincroniza si `CONFIG.leaderboard.apiUrl` apunta aquí. Ver README.md.
 *
 * ---------------------------------------------------------------------------
 * UNA LLAVE POR PARTIDA, no una lista en una sola llave.
 *
 * La versión anterior guardaba el ranking completo en la llave
 * `fleet_sizing_leaderboard` y en cada POST hacía leer -> ordenar -> escribir.
 * Con KV eso pierde partidas: las lecturas son de consistencia eventual, así
 * que dos jugadores que guardan casi al mismo tiempo leen la misma foto vieja
 * y el segundo sobrescribe al primero. Se reprodujo en pruebas: de 4 partidas
 * guardadas seguidas sobrevivieron 2, y reapareció una entrada ya borrada.
 *
 * Ahora cada partida se escribe en su propia llave `score:<id>`, así que dos
 * escrituras simultáneas no compiten. El ranking se arma al leer, con un
 * `list()` que devuelve las entradas en la metadata de cada llave — una sola
 * llamada, sin un `get()` por partida.
 *
 * El costo de esto es que `list()` también es de consistencia eventual: una
 * llave recién escrita tarda ~15 s en aparecer (medido). Para que el jugador
 * se vea a sí mismo de inmediato, la respuesta del POST mezcla lo que devuelve
 * `list()` con la entrada recién guardada. El resto de jugadores la ven en la
 * siguiente lectura, unos segundos después.
 * ---------------------------------------------------------------------------
 */

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Accept, X-Admin-Secret',
  'Access-Control-Max-Age': '86400',
  'Content-Type': 'application/json;charset=UTF-8'
};

const PREFIJO = 'score:';
const TOPE_PUBLICO = 10;
const TOPE_LISTA = 1000;   // máximo que devuelve un list() de KV por página

// Respaldo en memoria por si el KV no está enlazado. Ojo: es por isolate y se
// pierde solo, sirve para probar, no para producción.
let enMemoria = [];

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: CORS });

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

    if (request.method === 'GET' &&
        (url.pathname === '/api/leaderboard' || url.pathname === '/')) {
      return json((await leerTodo(env)).slice(0, TOPE_PUBLICO));
    }

    if (request.method === 'POST' && url.pathname === '/api/reset') {
      const secreto = request.headers.get('X-Admin-Secret');
      // Sin ADMIN_SECRET configurado se rechaza siempre: es preferible que el
      // reinicio no funcione a que quede abierto a cualquiera.
      if (!env.ADMIN_SECRET || secreto !== env.ADMIN_SECRET) {
        return json({ error: 'No autorizado.' }, 403);
      }
      const borradas = await borrarTodo(env);
      return json({ ok: true, borradas });
    }

    if (request.method === 'POST' && url.pathname === '/api/score') {
      try {
        const entrada = sanitizar(await request.json());
        if (!entrada) return json({ error: 'Payload inválido.' }, 400);

        await guardar(env, entrada);

        // `list()` todavía no ve la llave recién escrita, así que se mezcla a
        // mano para que quien acaba de jugar se vea en el ranking al instante.
        const lista = await leerTodo(env);
        if (!lista.some(e => e.id === entrada.id)) lista.push(entrada);
        lista.sort(ordenar);
        return json(lista.slice(0, TOPE_PUBLICO));
      } catch (err) {
        return json({ error: 'Error procesando la solicitud.', detalle: err.message }, 500);
      }
    }

    return json({ error: 'Ruta no encontrada.' }, 404);
  }
};

/* El balance es el marcador del juego; los desempates premian mejor servicio y
   menos deuda. Debe coincidir con `lbOrdenar` de index.html. */
function ordenar(a, b) {
  return (b.balance - a.balance)
      || (b.servicio - a.servicio)
      || (a.deudaFinal - b.deudaFinal);
}

/* Nunca se confía en el cuerpo del POST: todo se recorta y se acota. El nombre
   se guarda en crudo y se escapa al pintarlo en el cliente. */
function sanitizar(b) {
  if (!b || typeof b.nombre !== 'string' || typeof b.balance !== 'number') return null;
  const num = (v, def = 0) => (Number.isFinite(Number(v)) ? Number(v) : def);
  const acotar = (v, min, max) => Math.min(max, Math.max(min, v));

  return {
    // Identificador propio: permite mezclar sin duplicar la entrada recién
    // escrita con la que devuelve `list()` cuando ya alcanzó a propagarse.
    id: Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10),
    nombre: b.nombre.trim().slice(0, 24) || 'Anónimo',
    balance: Math.round(acotar(num(b.balance), -10000000, 10000000)),
    servicio: +acotar(num(b.servicio), 0, 100).toFixed(1),
    flotaPromedio: +acotar(num(b.flotaPromedio), 0, 1000).toFixed(2),
    eficiencia: +acotar(num(b.eficiencia), 0, 100000).toFixed(1),
    deudaFinal: Math.round(acotar(num(b.deudaFinal), 0, 100000000)),
    dias: Math.round(acotar(num(b.dias), 0, 100000)),
    fin: ['caja', 'contrato'].includes(b.fin) ? b.fin : null,
    modo: b.modo === 'duro' ? 'duro' : 'clasico',
    semilla: Math.round(num(b.semilla, 42)),
    fecha: typeof b.fecha === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(b.fecha)
      ? b.fecha
      : new Date().toISOString().slice(0, 10)
  };
}

async function guardar(env, entrada) {
  if (env && env.LEADERBOARD_KV) {
    // La llave lleva el id de la entrada: única por partida y sin coordinación
    // entre peticiones, que es justo lo que evita que dos jugadores se pisen.
    // La entrada va también en la metadata para que `list()` la devuelva sin
    // tener que hacer un get() por partida.
    await env.LEADERBOARD_KV.put(PREFIJO + entrada.id, JSON.stringify(entrada), { metadata: entrada });
    return;
  }
  enMemoria.push(entrada);
}

async function leerTodo(env) {
  if (env && env.LEADERBOARD_KV) {
    try {
      const entradas = [];
      let cursor;
      do {
        const r = await env.LEADERBOARD_KV.list({ prefix: PREFIJO, limit: TOPE_LISTA, cursor });
        for (const k of r.keys) if (k.metadata) entradas.push(k.metadata);
        cursor = r.list_complete ? null : r.cursor;
      } while (cursor);
      return entradas.sort(ordenar);
    } catch (e) {
      console.error('Error leyendo de KV:', e);
    }
  }
  return enMemoria.slice().sort(ordenar);
}

async function borrarTodo(env) {
  if (env && env.LEADERBOARD_KV) {
    let n = 0, cursor;
    do {
      const r = await env.LEADERBOARD_KV.list({ prefix: PREFIJO, limit: TOPE_LISTA, cursor });
      for (const k of r.keys) { await env.LEADERBOARD_KV.delete(k.name); n++; }
      cursor = r.list_complete ? null : r.cursor;
    } while (cursor);
    return n;
  }
  const n = enMemoria.length;
  enMemoria = [];
  return n;
}
