Rol: Actúa como Lead Game Developer y diseñador de serious games. El objetivo
pedagógico manda sobre el espectáculo visual.

> **ESTADO: actualizado 2026-09-04.** Este documento ya refleja el modelo
> vigente. Los cambios grandes respecto de la primera versión van marcados con
> «CAMBIO» y razonados en `HANDOFF.md`. El punto de retorno al modelo original
> es el tag de git `v1-modelo-original`.

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
demanda(dia)  = seasonal(dia) + (rngRuido() - 0.5) * CONFIG.noiseRange
si quedan días de un régimen en curso:
    demanda *= multiplicadorVigente;  díasRestantes -= 1
si_no si rngShock() < CONFIG.shockStartProb:
    si rngShock() < 0.5:  mult = CONFIG.shockDownMin + rngShock()*CONFIG.shockDownRange
    si_no:                mult = CONFIG.shockUpMin   + rngShock()*CONFIG.shockUpRange
    dur = CONFIG.shockMinDays + floor(rngShock()*(shockMaxDays - shockMinDays + 1))
    demanda *= mult;  díasRestantes = dur - 1
demanda = max(0, round(demanda))
```

**CAMBIO (2026-09-04): `dia` es índice base 0** (0 = 1 de enero). La primera
versión no lo definía, y sólo base 0 reproduce los números.

**CAMBIO (2026-09-04): los shocks son REGÍMENES de varios días**, no picos de
un día. Con un día de duración y 7 de espera para contratar, la respuesta óptima
a cualquier shock era siempre ignorarlo: no había decisión bajo incertidumbre.

**CAMBIO (2026-09-04): tres flujos de `rng()` independientes**, derivados de la
semilla: `rngRuido = mulberry32(seed)`,
`rngShock = mulberry32(seed ^ shockSeedXor)`,
`rngIncidentes = mulberry32(seed ^ incidentSeedXor)`.
Antes todo salía de un solo generador, así que el lazo de incidentes —cuyo
número de llamadas depende del tamaño de la flota— corría el ruido y los shocks
de todos los días siguientes: **dos jugadores con decisiones distintas
enfrentaban años distintos**, lo que hacía incomparable cualquier ranking.

Defaults: `demandBase=480, demandAmp=300, peakDay=350, noiseRange=50,
shockStartProb=0.022, shockMinDays=3, shockMaxDays=12, shockDownMin=0.3,
shockDownRange=0.3, shockUpMin=1.5, shockUpRange=0.7`.

**Orden de llamadas por día (crítico, no reordenar):** `rngRuido` 1 vez;
`rngShock` 1 vez para el chequeo y, si arranca un régimen, 3 más (dirección,
magnitud, duración); `rngIncidentes` por cada camión despachado, en orden
`i=0..N-1`: chequeo de incidente y, si aplica, fracción entregada.

**La serie de demanda depende SÓLO de la semilla**, nunca de las decisiones del
jugador. Eso es lo que hace comparable el ranking.

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

## CIUDAD — CAMBIO (2026-09-04): vista aérea, no franja lateral

Sigue sin haber geografía en la ECONOMÍA: `ejecutarDia` no sabe que existen
colonias. El plano es una lectura de los agregados del día puesta en forma de
mapa, no una simulación espacial.

- Canvas de 320×96 «píxeles de arte» escalado con `image-rendering: pixelated`,
  todo procedural con `fillRect` en coordenadas enteras.
- Vista desde arriba: CEDIS a la izquierda y 18 colonias (6×3) separadas por
  avenidas. Cada camión tiene una colonia asignada: sale, recorre su avenida,
  se detiene a descargar y regresa.
- Las colonias surtidas se ven claras; las que esperan se pintan de rojo, y la
  fracción en rojo es `min(1, díasDeDeuda / deudaCiudadMax)`.
- **El viaje corre en TIEMPO REAL** (`CONFIG.pixel.viajeMs`), NO sincronizado al
  tick del día: un día dura 822 ms a 1x y sólo 82 ms a 10x, y a esa velocidad
  los camiones eran un borrón.
- El trazado se genera con un PRNG propio (`CONFIG.pixel.seed`), nunca con el de
  la partida: la decoración no debe mover los números.

## REGLAS DE OPERACIÓN — CAMBIO (2026-09-04): son el juego, no un modo opcional

Sin ellas la palanca es gratis e instantánea y no hay ninguna decisión que
tomar: basta leer la demanda y copiarla. Viven en `CONFIG.duro`:

- Contratar cuesta `hireCost=400` y **tarda `leadTimeDays=7` días** en llegar.
- Despedir cuesta `fireCost=200`.
- Si la caja baja de `pisoCaja=-25000`, **quiebras** y termina la partida.
- Si la deuda supera `deudaMaxDias=30` días de tu capacidad durante
  `graciaDias=5` días seguidos, **pierdes el contrato**.

Los criterios de aceptación corren el modelo económico puro, SIN esta capa.

## SEMILLA SEMANAL Y PUNTAJE — CAMBIO (2026-09-04)

- La partida usa una **semilla derivada de la semana ISO**: el año cambia cada
  semana pero es el mismo para todos los que juegan esa semana. Con semilla fija
  el jugador memoriza dónde caen los regímenes a la tercera partida.
- La semilla se **cura**: se prueban candidatas de la misma semana hasta
  encontrar una donde al menos una flota fija sobreviva el año con balance
  positivo. Sin eso no hay contra qué medir al jugador.
- El **puntaje es relativo**: `balance − (mejor flota fija posible de esa
  semilla, jugada con las MISMAS reglas)`. Compararlo contra una flota fija del
  modelo puro sería injusto, porque ésa no paga el arranque ni las
  contrataciones. Ese número es el objetivo de aprendizaje 3 convertido en
  marcador, y es comparable entre semanas distintas.
- El veredicto ya no usa una cifra fija: **ganas si el puntaje es positivo** y
  terminaste el año.

## CIERRE DE MES — CAMBIO (2026-09-04)

Al terminar cada mes el año se detiene y se muestra un estado de resultados:
utilidad del mes, camiones-día ociosos y lo que costaron, entregado contra
demandado, deuda en días de flota, tendencia de la temporada y flota confirmada
para el mes siguiente. Concentra las decisiones en doce momentos legibles en vez
de dejar tramos largos donde el jugador mira sin decidir nada.

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
**CAMBIO (2026-09-04): números recalculados.** Los de la primera versión
describían el modelo de un solo flujo con shocks de un día. `CONFIG.seed = 42`
es la semilla de PRUEBAS; la partida usa semilla semanal.

- [ ] Flota fija N=11: balance = **$89,394**, nivel de servicio = **81.7%**,
      backlog final = **33,636** cajas. Es el óptimo entre flotas fijas.
- [ ] Flota fija N=10: balance = **$84,431** (menor que N=11).
- [ ] Flota fija N=12: balance = **$78,419** (menor que N=11). Junto con el
      anterior confirma que el óptimo es INTERIOR y la curva cóncava.
- [ ] Flota fija N=6: balance = **$50,025** (subflota, castigo por deuda
      creciente).
- [ ] Flota fija N=20: balance = **−$34,439** (sobreflota, castigo por
      costo fijo).
- [ ] La invariante de conservación (`demanda - entregado - backlogFinal ≈ 0`)
      se cumple en todos los casos anteriores.
- [ ] La serie de demanda es idéntica para cualquier política: verificado con
      flotas fijas de 4, 11 y 25 y con la adaptativa, **183,769 cajas** en las
      cuatro.
- [ ] Una política adaptativa simple (recalcular `N` cada día como
      `ceil(promedio móvil de los últimos 14 días de demanda / K)`, con
      `N=10` mientras no haya 14 días de historia) da balance = **$108,013**,
      nivel de servicio = **95.6%**, flota promedio ≈ **12.72** camiones.
      Debe ser MAYOR que cualquier flota fija de la lista. Es la prueba de que
      el juego premia adaptarse, no sólo elegir bien una vez.
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
