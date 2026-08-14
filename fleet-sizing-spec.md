Rol: Actúa como Lead Game Developer y diseñador de serious games. El objetivo
pedagógico manda sobre el espectáculo visual.

## OBJETIVO DE APRENDIZAJE

El jugador debe salir entendiendo tres cosas:

1. El costo de flota es fijo y diario: un camión ocioso cuesta exactamente
   igual que uno que reparte toda su capacidad. La decisión de cuántos
   camiones mantener se paga todos los días, se use o no.
2. La carga suspendida es deuda que se arrastra, no una pérdida puntual: lo
   que no se resuelve hoy compite mañana con la demanda nueva por la misma
   capacidad, y si la flota es crónicamente insuficiente, la deuda crece sin
   límite mientras la flota pequeña sigue pareciendo "barata".
3. No existe una flota fija ganadora. Por diseño, tanto una flota mínima
   (deuda impagable que nunca se cobra explícitamente pero drena ingreso
   futuro) como una flota máxima (costo fijo que no se recupera en
   temporada baja) pierden contra una política que ajusta el tamaño de
   flota según la demanda reciente.

Audiencia: cualquier persona con contexto básico de logística/operaciones.
Partida activa de 5 minutos (1 año simulado).

## STACK Y ENTREGA

- Un único archivo `index.html` autocontenido, sin build step.
- Todo en 2D: HTML/CSS para el HUD, Canvas 2D nativo para la gráfica de
  líneas. NO se necesita Three.js ni cámara isométrica: no hay mapa, no hay
  rutas ni geografía que renderizar (decisión de diseño explícita, ver
  sección "Animación CEDIS-Ciudad" más abajo).
- Geometría/visuales 100% procedurales (SVG inline o CSS). Prohibido cargar
  imágenes, modelos, texturas o fuentes externas. Tipografía: pila de
  sistema (`system-ui`, `ui-monospace`), para que el archivo funcione sin
  conexión a internet.
- HUD en HTML y CSS plano superpuesto. NO uses Tailwind ni frameworks.

## ESTRUCTURA DEL CÓDIGO

- Objeto `CONFIG` al inicio con TODAS las constantes: capacidades, costos,
  probabilidades, parámetros de demanda, duración, semilla. Ningún número
  mágico fuera de `CONFIG`.
- RNG con semilla (`mulberry32`) desde `CONFIG.seed`, para partidas
  reproducibles en modo de prueba. Implementación exacta a usar:

```js
function mulberry32(a) {
  return function() {
    var t = a += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
}
```

- Máquina de estados: `MENU -> JUGANDO -> PAUSA -> RESULTADOS`. Una función
  por estado.
- Comentarios en español que expliquen la lógica de negocio, no la sintaxis
  de JS.

## RELOJ DE AÑO (elemento central del HUD)

- 365 días simulados en 300 s reales a velocidad 1x (`CONFIG.gameMs`,
  `CONFIG.yearDays`). Multiplicador de velocidad (1x/4x/10x) disponible
  como ayuda de prueba, etiquetado claramente como control de testing, NO
  como parte de la mecánica del juego (la única palanca de juego real es el
  tamaño de flota).
- Muestra SIEMPRE el día y mes simulado actual, nunca una cuenta regresiva
  pura.
- Usa `performance.now()` para el acumulador y pausa en `visibilitychange`.

## MODELO DE DEMANDA (en CONFIG, editable)

```
seasonal(dia) = CONFIG.demandBase + CONFIG.demandAmp * cos(2π*(dia - CONFIG.peakDay)/365)
demanda(dia)  = seasonal(dia) + (rng() - 0.5) * CONFIG.noiseRange
si rng() < CONFIG.shockProb:
    si rng() < 0.5:  demanda *= (CONFIG.shockDownMin + rng()*CONFIG.shockDownRange)
    si_no:            demanda *= (CONFIG.shockUpMin   + rng()*CONFIG.shockUpRange)
demanda = max(0, round(demanda))
```

Defaults: `demandBase=480, demandAmp=300, peakDay=350, noiseRange=50,
shockProb=0.05, shockDownMin=0.3, shockDownRange=0.3, shockUpMin=1.5,
shockUpRange=0.7`.

**Orden de llamadas a `rng()` por día (crítico para reproducibilidad, no
reordenar):** 1) ruido, 2) chequeo de shock, 3) si hay shock: dirección,
4) si hay shock: magnitud, 5) por cada camión despachado, en orden
`i=0..N-1`: chequeo de incidente y, si aplica, fracción entregada.

## MODELO DE FLOTA Y CARGA SUSPENDIDA (implementar tal cual)

```
diaSimulado(dia, N, backlog):
  demanda = demandaDelDia(dia)                  // ver arriba, consume rng()
  capacidad = N * CONFIG.K
  backlogAsignado = min(backlog, capacidad)
  restante = capacidad - backlogAsignado
  demandaAsignada = min(demanda, restante)
  noAtendidoEstructural = demanda - demandaAsignada
  backlogViejoNoAtendido = backlog - backlogAsignado   // IMPORTANTE, ver nota
  totalAsignado = backlogAsignado + demandaAsignada
  camionesUsados = totalAsignado > 0 ? min(N, ceil(totalAsignado / CONFIG.K)) : 0

  cargaRestante = totalAsignado
  entregado = 0
  perdidoPorIncidentes = 0
  para i en 0..N-1:
    si i < camionesUsados:
      carga_i = min(CONFIG.K, cargaRestante); cargaRestante -= carga_i
      si rng() < CONFIG.incidentP:
        fraccion = rng() * CONFIG.incidentMaxFrac      // default 0.6
        entregado += carga_i * fraccion
        perdidoPorIncidentes += carga_i * (1 - fraccion)
        estadoCamion[i] = 'incidente'
      si_no:
        entregado += carga_i
        estadoCamion[i] = 'ok'
    si_no:
      estadoCamion[i] = 'inactivo'

  nuevoBacklogGenerado = noAtendidoEstructural + perdidoPorIncidentes
  backlogManana = backlogViejoNoAtendido + nuevoBacklogGenerado
  ingreso = entregado * CONFIG.profitPerBox
  costo   = N * CONFIG.fixedCostPerTruck
  return {backlogManana, ingreso, costo, entregado, demanda, estadoCamion}
```

**Nota de diseño, no te saltes esto:** en una primera versión del
prototipo, `backlogManana` se calculaba como `noAtendidoEstructural +
perdidoPorIncidentes` únicamente, sin sumar `backlogViejoNoAtendido`. Eso
hace que cualquier backlog que supere la capacidad del día simplemente
desaparezca de la contabilidad en vez de arrastrarse, lo cual vuelve
trivial el juego (una flota mínima siempre gana porque la deuda nunca se
acumula de verdad). La fórmula de arriba, con `backlogViejoNoAtendido`
incluido, es la correcta y la que debes implementar.

**Invariante de conservación (impleméntala como aserción de prueba):**

```
suma(demanda de todos los días) - suma(entregado de todos los días) - backlogFinal ≈ 0
```

Si esta invariante no se cumple (con tolerancia de redondeo), hay un bug en
la contabilidad de backlog.

## ANIMACIÓN CEDIS-CIUDAD

No hay mapa ni rutas reales: la ubicación de las tiendas no importa para la
economía del juego (ver decisión de diseño previa). Pero el juego necesita
señal visual de actividad, así que:

- Una franja horizontal con un ícono de CEDIS a la izquierda y un ícono de
  ciudad a la derecha.
- Cada día simulado, cada camión despachado (`estadoCamion[i] != 'inactivo'`)
  anima un viaje de ida y vuelta a lo largo de la franja, con duración
  sincronizada a la duración real del tick del día (`CONFIG.gameMs /
  CONFIG.yearDays / velocidadActual`). Color verde si `'ok'`, ámbar si
  `'incidente'`.
- Los camiones inactivos ese día se quedan quietos junto al CEDIS.
- Esto es decoración con propósito (comunica "hoy salieron X camiones y Y
  tuvieron problemas" de un vistazo), no una simulación de tráfico.

## ECONOMÍA DESAGREGADA (HUD, siempre visible)

Además del balance acumulado (grande, verde si ≥0, rojo si <0), muestra
como números separados, con color consistente con la gráfica:

- Ingreso acumulado (verde).
- Costo acumulado (rojo).
- Utilidad acumulada = ingreso - costo (debe coincidir exactamente con el
  balance; útil como segundo chequeo de conservación).

Gráfica de líneas por día (Canvas 2D): demanda, ingreso, costo, backlog,
cada una con su color. Medidor tipo velocímetro para el nivel de backlog
actual.

## PANTALLA DE RESULTADOS (día 365)

- Balance final, en grande, con veredicto (ganaste / perdiste).
- Nivel de servicio: % de cajas entregadas vs. demandadas en el año.
- Eficiencia de flota: cajas entregadas por camión-día activo.
- Gráfica final: flota (N) del jugador vs. demanda a lo largo del año.
- **Contrafactual obligatorio:** recalcula, con la misma semilla y el mismo
  historial de demanda que ya se generó, qué balance habría dado una flota
  FIJA igual al promedio de la flota que usó el jugador durante la partida.
  Muestra los dos balances lado a lado. Esto le muestra al jugador
  numéricamente cuánto ganó (o perdió) por ajustar la flota activamente en
  vez de fijarla una vez y olvidarse.

## CRITERIOS DE ACEPTACIÓN (verifica cada uno antes de entregar)

Todos calculados con `CONFIG.seed = 42` y los defaults de este documento
(`K=40, incidentP=0.08, incidentMaxFrac=0.6, fixedCostPerTruck=60,
profitPerBox=2.2`), corriendo una flota FIJA (sin que el jugador la mueva)
durante los 365 días completos:

- [ ] Abre en el navegador sin errores en consola.
- [ ] Flota fija N=10 todo el año: balance final = **$83,925**, nivel de
      servicio = **78.3%**, backlog final = **38,097** cajas.
- [ ] Flota fija N=9: balance = **$76,325** (menor que N=10).
- [ ] Flota fija N=11: balance = **$82,504** (menor que N=10). Junto con el
      punto anterior confirma que N=10 es un óptimo local entre flotas
      fijas: la curva de balance contra tamaño de flota es cóncava, no
      monótona.
- [ ] Flota fija N=6: balance = **$49,943** (subflota, castigo por deuda
      creciente).
- [ ] Flota fija N=20: balance = **-$50,714** (sobreflota, castigo por
      costo fijo).
- [ ] La invariante de conservación (`demanda - entregado - backlogFinal ≈
      0`) se cumple en todos los casos anteriores.
- [ ] Una política adaptativa simple (recalcular `N` cada día como
      `ceil(promedio móvil de los últimos 14 días de demanda / K)`, con
      `N=10` mientras no haya 14 días de historia) da balance = **$102,250**,
      nivel de servicio = **96.3%**, flota promedio ≈ **13.0** camiones.
      Este resultado debe ser MAYOR que el mejor resultado de cualquier
      flota fija de la lista anterior. Es la prueba de que el juego premia
      adaptarse, no solo elegir bien una vez.
- [ ] El multiplicador de velocidad (1x/4x/10x) no cambia ninguno de los
      números anteriores, solo la velocidad a la que se generan.
- [ ] Ningún reloj avanza con la pestaña en segundo plano.
- [ ] Todos los números tuneables viven en `CONFIG`.
- [ ] Funciona con tap en un viewport de 375px de ancho.

## ENTREGA

El archivo `index.html` completo, seguido de una nota breve sobre qué
constantes de `CONFIG` tocar para recalibrar dificultad (principalmente
`fixedCostPerTruck`, `profitPerBox`, `incidentP` y `demandAmp`) y un
recordatorio de correr el script de calibración offline (ver skill
`offline-balance-simulation`) antes de tocar esos números, para no
reintroducir un óptimo trivial en un extremo.
