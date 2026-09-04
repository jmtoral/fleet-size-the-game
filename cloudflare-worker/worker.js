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
 */

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Accept, X-Admin-Secret',
  'Access-Control-Max-Age': '86400',
  'Content-Type': 'application/json;charset=UTF-8'
};

const CLAVE_KV = 'fleet_sizing_leaderboard';
const TOPE_GUARDADO = 50;   // se conserva más de lo que se muestra, para el histórico
const TOPE_PUBLICO = 10;

// Respaldo en memoria por si el KV todavía no está enlazado. Ojo: es por
// isolate y se pierde solo, sirve para probar, no para producción.
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
      return json(await leer(env, TOPE_PUBLICO));
    }

    if (request.method === 'POST' && url.pathname === '/api/reset') {
      const secreto = request.headers.get('X-Admin-Secret');
      // Sin ADMIN_SECRET configurado se rechaza siempre: es preferible que el
      // reinicio no funcione a que quede abierto a cualquiera.
      if (!env.ADMIN_SECRET || secreto !== env.ADMIN_SECRET) {
        return json({ error: 'No autorizado.' }, 403);
      }
      await escribir(env, []);
      return json({ ok: true, mensaje: 'Ranking reiniciado.' });
    }

    if (request.method === 'POST' && url.pathname === '/api/score') {
      try {
        const body = await request.json();
        const entrada = sanitizar(body);
        if (!entrada) return json({ error: 'Payload inválido.' }, 400);

        const ranking = await leer(env, TOPE_GUARDADO);
        ranking.push(entrada);
        ranking.sort(ordenar);

        const top = ranking.slice(0, TOPE_GUARDADO);
        await escribir(env, top);
        return json(top.slice(0, TOPE_PUBLICO));
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

async function leer(env, limite) {
  if (env && env.LEADERBOARD_KV) {
    try {
      const data = await env.LEADERBOARD_KV.get(CLAVE_KV, 'json');
      if (Array.isArray(data)) return data.slice(0, limite);
    } catch (e) {
      console.error('Error leyendo de KV:', e);
    }
  }
  return enMemoria.slice(0, limite);
}

async function escribir(env, data) {
  if (env && env.LEADERBOARD_KV) {
    try {
      await env.LEADERBOARD_KV.put(CLAVE_KV, JSON.stringify(data));
      return;
    } catch (e) {
      console.error('Error escribiendo en KV:', e);
    }
  }
  enMemoria = data;
}
