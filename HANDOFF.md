# Handoff — Fleet Sizing

Bitácora de sesiones de trabajo. Cada entrada nueva va al final, sin editar
las anteriores. Plantilla:

```
## AAAA-MM-DD — <resumen de una línea>
**Hecho:** qué se completó esta sesión.
**Decisiones:** decisiones de diseño tomadas y por qué (si cambian el spec,
también deben quedar reflejadas ahí, esto es un resumen).
**Pendiente:** qué queda para la próxima sesión.
**Archivos tocados:** lista.
```

---

## 2026-08-13 — Reescritura del spec en formato riguroso + fix de bug de balance

**Hecho:**
- Se identificó que la mecánica de tráfico/congestión espacial de la idea
  original no era necesaria; se simplificó a un modelo puramente económico
  (flota vs. demanda vs. incidentes de ruta).
- Se construyó un prototipo jugable en HTML/Canvas (fuera de esta carpeta,
  en el chat) y se probó: resultó demasiado fácil.
- Se encontró la causa raíz: un bug de contabilidad en el arrastre de
  backlog (la deuda que superaba la capacidad del día se perdía en vez de
  arrastrarse), lo que volvía dominante cualquier flota mínima.
- Se corrigió la fórmula y se validó por simulación offline en Python
  (mismo RNG `mulberry32`, semilla 42, mismo orden de llamadas) que el
  modelo corregido tiene un óptimo interior real (N=10 entre flotas fijas)
  y que una política adaptativa simple supera a cualquier flota fija.
- Se reescribió el spec completo (`fleet-sizing-spec.md`) en un formato
  riguroso (rol, objetivos de aprendizaje, CONFIG, RNG sembrado, máquina de
  estados, criterios de aceptación con números verificados), tomando como
  referencia el estilo de un spec de un juego relacionado de trabajo
  (Stay Time / ruta de reparto KOF).
- Se agregaron dos skills reutilizables: `serious-game-economics` (para
  este tipo de juego en general) y `offline-balance-simulation` (proceso
  de calibración).

**Decisiones:**
- Se descarta el mapa/rutas espaciales definitivamente; la animación
  CEDIS-Ciudad es decorativa (comunica actividad), no una simulación de
  tráfico.
- Se desagregan ingreso, costo y utilidad como números separados en el HUD,
  además del balance acumulado.
- Constantes finales de calibración: `K=40, incidentP=0.08,
  incidentMaxFrac=0.6, fixedCostPerTruck=60, profitPerBox=2.2,
  demandBase=480, demandAmp=300, peakDay=350, shockProb=0.05`.

**Pendiente:**
- Implementar `index.html` final siguiendo el spec (el prototipo del chat
  todavía no tiene el fix de backlog, el RNG sembrado, ni el contrafactual
  de resultados).
- Decidir si el "contrafactual" en la pantalla de resultados se calcula con
  la flota promedio del jugador o con el N óptimo fijo (N=10) como
  referencia — el spec actual pide la primera opción.

**Archivos tocados:** `fleet-sizing-spec.md` (nuevo), `CLAUDE.md` (nuevo),
`skills/serious-game-economics/SKILL.md` (nuevo),
`skills/offline-balance-simulation/SKILL.md` (nuevo), este archivo (nuevo).

---

## 2026-08-13 — Implementación de `index.html` + verificación offline

**Hecho:**
- Se implementó `index.html` completo y autocontenido (sin build, sin CDN,
  sin dependencias): `CONFIG` con todas las constantes, `mulberry32` sembrado,
  máquina de estados `MENU -> JUGANDO -> PAUSA -> RESULTADOS`, franja
  CEDIS-Ciudad animada, HUD con economía desagregada, velocímetro de deuda,
  gráficas en Canvas 2D, pantalla de resultados con contrafactual.
- Se escribió `verify_balance.py` (solo stdlib): puerto byte por byte del
  núcleo, con los criterios de aceptación y un modo `--barrido` para
  recalibración.
- **Los 5 escenarios de flota fija del spec se reprodujeron exactos**
  (N=6 $49,943 · N=9 $76,325 · N=10 $83,925 / 78.3% / 38,097 · N=11 $82,504 ·
  N=20 −$50,714), con invariante de conservación = 0.00e+00 en todos.
- El barrido N=4..24 confirma curva cóncava con óptimo interior en N=10, y que
  la política adaptativa le gana a cualquier flota fija.
- Verificación del archivo entregado, no solo del puerto en Python: se corrió
  `index.html` en Chrome headless y (a) el panel `?test=1` da los mismos 6
  resultados, (b) un driver que recorre el camino interactivo real (click en
  Empezar → 365 ticks → resultados) con la flota en 10 todo el año cierra en
  exactamente $83,925 / 78.3% / 38,097, sin excepciones y con invariante 0.

**Decisiones (cambios deliberados respecto del spec, no bugs):**
1. **Números de la política adaptativa corregidos.** El spec pedía
   $102,250 / 96.3% / flota ≈13.0. La fórmula literal del spec (media móvil de
   14 días, N=10 durante el calentamiento) da **$103,390 / 95.3% / 12.345**.
   No se ajustó el modelo para forzar el número del spec porque los tres
   valores del spec son **mutuamente inconsistentes**: implican 175,886 cajas
   entregadas sobre 182,644 demandadas, y con ~13 camiones este modelo genera
   ~178,000 cajas de demanda total (la serie de demanda depende de N, porque el
   lazo de incidentes consume rng()). Se barrieron ventanas de 5 a 30 días,
   calentamientos, pisos de flota, lookahead y variantes con backlog: ninguna
   reproduce la tripleta. Dado que los 5 escenarios fijos y la invariante sí
   coinciden al dígito, el núcleo es correcto y lo que estaba mal era el
   fixture. **Falta reflejarlo en `fleet-sizing-spec.md`.** El criterio de
   fondo (adaptativa > mejor flota fija) sí se cumple: $103,390 > $83,925.
2. **Índice de día fijado a base 0** (0 = 1 de enero). El spec no lo definía y
   sólo base 0 reproduce los números de aceptación; quedó documentado en el
   código y en el script.
3. **`diaSimulado` se partió en `demandaDelDia` + `ejecutarDia`**, más un
   `avanzarDia(acc, ...)` que comparten el bucle jugado en vivo y las corridas
   headless de verificación. Motivo: en el diseño original el juego y el
   verificador habrían tenido dos contabilidades paralelas que pueden
   desincronizarse. El orden de llamadas a `rng()` no cambia.
4. **Contrafactual re-juega la serie de demanda registrada**, no una nueva.
   Como un N distinto despacha un número distinto de camiones, volver a correr
   el año desde la semilla produciría otra serie de demanda y la comparación no
   sería contra el mismo año. Los incidentes se sortean con un flujo propio
   (`CONFIG.contrafactualSeed`); se avisa en pantalla.
5. **La gráfica en vivo son tres paneles apilados** (cajas/día, deuda, $/día)
   en lugar de una sola con 4 series: demanda (~500), deuda (~95,000) y $/día
   no comparten escala y en un solo eje la deuda aplasta todo lo demás.
6. **La flota se grafica como capacidad (N×K)** en resultados, para que
   comparta eje con la demanda y se vea directo dónde quedó corta o sobrada.
7. **El velocímetro mide la deuda en "días de flota completa"**, no en cajas:
   es la lectura que dice qué tan lejos está el jugador de poder pagarla con la
   flota que tiene hoy. El número crudo de cajas se muestra al lado.
8. **Veredicto** con vara en `CONFIG.balanceObjetivo = 83925` (la mejor flota
   fija con la semilla por defecto): Quebraste (<0) / Sobreviviste / Ganaste.

**Pendiente:**
- Actualizar `fleet-sizing-spec.md` con los números corregidos de la política
  adaptativa (punto 1 de arriba) y con el índice de día base 0.
- Revisar a ojo el layout en 375px. El CSS es responsivo y los objetivos de tap
  son de 44px+ (56px en la palanca de flota), y renderiza sin errores, pero
  **no se hizo una revisión visual**; sólo se generaron capturas headless.
- Queda abierta la duda del handoff anterior (contrafactual contra flota
  promedio del jugador vs. contra N=10): se implementó la primera opción, que
  es lo que pide el spec.

**Cómo recalibrar dificultad:** tocar `fixedCostPerTruck` (castigo por
sobreflota), `profitPerBox` (premio por servicio), `incidentP` /
`incidentMaxFrac` (riesgo) y `demandAmp` (qué tanto se mueve la estacionalidad,
o sea qué tanto paga adaptarse). Después de cualquiera de esos cambios, correr
`python verify_balance.py --barrido` y confirmar que el óptimo entre flotas
fijas sigue siendo interior y que la adaptativa sigue ganando; luego congelar
los nuevos números como criterios en el spec, en `CONFIG.criteriosAceptacion`
de `index.html` y en `CRITERIOS` de `verify_balance.py`.

**Archivos tocados:** `index.html` (nuevo), `verify_balance.py` (nuevo),
este archivo.

---

## 2026-08-13 — Modo duro (el juego era demasiado fácil) + ciudad en pixel art

Manuel reportó dos cosas: el juego salía demasiado fácil, y la animación de
camiones era pobre. También dejó `portada.jfif` como referencia visual.

**Hecho — dificultad:**
- Diagnóstico: el juego era pasivo. Con dejar la flota en ~10-13 y no volver a
  tocarla, se ganaba. No había forma de perder durante la partida, sólo un
  número al final.
- **No se tocó ninguna constante económica.** Se agregó una capa de reglas de
  juego (`CONFIG.duro`) por encima del modelo: la economía por día
  (`ejecutarDia`) es exactamente la misma que verifican los criterios de
  aceptación, que siguen pasando los 6 sin cambios.
- Mecánicas nuevas:
  - `leadTimeDays: 7` — los camiones contratados tardan una semana en llegar.
    Obliga a anticipar la estacionalidad en vez de reaccionar a ella.
  - `hireCost: 600` / `fireCost: 300` — mover la palanca cuesta, así que
    manosearla todo el tiempo se castiga.
  - `pisoCaja: -25000` — si el balance acumulado cae de ahí, **quiebras** y se
    acaba la partida.
  - `deudaMaxDias: 30` / `graciaDias: 5` — si la carga suspendida pasa de 30
    días de tu capacidad durante 5 días seguidos, **pierdes el contrato**.
- Calibrado offline con `python verify_balance.py --duro` (semilla 42):

  | Forma de jugar | Balance | Fin |
  |---|---|---|
  | fija N=6 | $1,168 | contrato día 17 |
  | fija N=10 | $8,749 | contrato día 38 |
  | fija N=14 | $43,933 | contrato día 363 |
  | fija N=16 | $11,386 | completó el año |
  | fija N=18 | −$25,367 | quiebra día 186 |
  | fija N=20 | −$25,619 | quiebra día 155 |
  | jugador adaptativo | **$58,542** | completó el año |

  De todas las flotas fijas **sólo N=16 sobrevive el año**, y rinde 5 veces
  menos que un jugador que se adapta. El objetivo de aprendizaje #3 ("no existe
  una flota fija ganadora") pasó de ser una afirmación del spec a una regla que
  el juego hace cumplir. La vara para ganar quedó en $50,000.
- Verificado end-to-end en Chrome headless sobre el `index.html` entregado:
  pasivo → pierde el contrato día 39; N=20 → quiebra día 156; adaptativo →
  $62,086 y gana.
- Se puede volver al juego anterior con la casilla **"Modo clásico"** del menú
  (`CONFIG.duro.activo = false`): lead time y costos a cero, sin fin
  anticipado, y la vara vuelve a $83,925.

**Hecho — ciudad en pixel art:**
- Se eliminó la franja de `<div>`s con SVG y se reemplazó por un canvas de
  **320×96 "pixeles de arte"** estirado al ancho con `image-rendering:
  pixelated` e `imageSmoothingEnabled = false`. Todo se dibuja con `fillRect`
  en coordenadas enteras: es pixel art de verdad, no vectores chiquitos.
- Escena procedural: cielo en bandas sólidas, skyline lejano en silueta,
  edificios cercanos con ventanas encendidas (algunas parpadean), nubes que se
  desplazan, sol/luna, calle de 3 carriles con rayas que corren, y el CEDIS a
  la izquierda con letrero rojo.
- Camiones de 24×11 con livería roja y blanca inspirada en la portada, ruedas
  de dos cuadros, carga visible en la caja al salir (regresan vacíos), salidas
  escalonadas para que se vea un convoy. Los que tuvieron incidente se quedan
  tirados a media ruta con intermitentes ámbar y humo; los ociosos quedan
  estacionados en el patio.
- **El cielo comunica el estado del negocio:** cambia de tono con la estación
  (el año arranca y acaba en temporada alta) y se ensucia de rojo conforme
  crece la deuda. Cuando estás a punto de perder, el marco de la ciudad
  parpadea en rojo y aparece un aviso con la cuenta regresiva.
- El skyline se genera con **su propio PRNG** (`CONFIG.pixel.seed`), nunca con
  el `rng` de la partida: si la decoración consumiera del flujo de la partida
  cambiaría los números del juego.

**Decisiones:**
- **La portada usa marca registrada de Coca-Cola** (logo, disco rojo, camiones
  con la marca). El juego toma sólo la dirección visual — livería roja y blanca
  genérica de refresquera, ciudad, estética de caja de videojuego — sin
  reproducir el logo ni el wordmark.
- Los criterios de aceptación describen el **modelo económico**, no el modo
  duro. Por eso `?test=1` y `verify_balance.py` (sin flags) siguen corriendo el
  modelo base: es lo que garantiza que la capa de reglas no contaminó la
  economía. El modo duro se calibra aparte con `--duro`.
- El contrafactual sigue corriendo el modelo base, sin costos de contratación.
  Es lo correcto: una flota que nunca se mueve no paga contrataciones. La
  única idealización es que tampoco paga la rampa inicial desde 10 camiones.
- `resumen()` ahora promedia la flota sobre los **días efectivamente jugados**,
  no sobre 365, porque una partida puede terminar el día 38.

**Pendiente:**
- Sigue pendiente del handoff anterior: actualizar `fleet-sizing-spec.md` con
  los números corregidos de la política adaptativa, el índice de día base 0 y
  ahora también la sección de modo duro y la ciudad en pixel art.
- Revisión visual en 375px del layout con la ciudad nueva (se revisó a 1000px).
- Posible ajuste fino: la flota pasiva pierde el contrato el día 39 (~32 s de
  partida). Es una lección instantánea, pero si resulta demasiado brusco para
  alguien que juega por primera vez, subir `deudaMaxDias` de 30 a 40 le da
  cerca de dos semanas simuladas más de margen.

**Archivos tocados:** `index.html`, `verify_balance.py` (nuevo modo `--duro`),
este archivo.

---

## 2026-08-14 — La animación de camiones se desacopla del reloj del juego

Manuel reportó que los camiones iban demasiado rápido para apreciarlos, que
sólo "topaban con el límite" y que se veían muy grandes.

**Hecho:**
- **Causa raíz de la velocidad:** el spec pedía sincronizar el viaje de ida y
  vuelta con la duración del tick del día (`gameMs / yearDays / velocidad`).
  Eso da 822 ms por viaje completo a 1x y sólo 82 ms a 10x: a esa velocidad los
  camiones son un borrón. **Cambio de diseño deliberado respecto del spec:** el
  viaje ahora corre en tiempo real con `CONFIG.pixel.viajeMs = 11000`, en un
  reloj propio (`P.animMs`) que **no** se multiplica por la velocidad de
  testing. Los camiones se ven igual de legibles a 1x que a 10x, y el
  multiplicador sigue sin afectar ningún número.
- **Causa raíz del apilamiento:** la fase del viaje se calculaba con un desfase
  por camión y luego se recortaba con `clamp(0,1)`. Los que todavía no salían
  quedaban pegados en el extremo del CEDIS y los que ya habían vuelto se
  amontonaban ahí también. Ahora la fase es continua y cada camión arranca
  desfasado un tramo igual (`i / total`) del recorrido: siempre hay camiones
  repartidos a lo largo de toda la ruta y nadie topa con nada.
- **Camiones más chicos:** de 24×11 a 16×7 píxeles de arte, y la calle pasó de
  3 a 4 carriles. Caben más y se distinguen mejor.
- Los camiones descompuestos se detienen en un punto distinto cada uno
  (determinista por índice, sin consumir el `rng` de la partida) en vez de
  amontonarse todos en el mismo lugar de la ruta.
- Verificado: los 6 criterios de aceptación siguen pasando en el `index.html`
  entregado.

**Pendiente:** lo mismo que la entrada anterior. Se agrega que el spec
(`fleet-sizing-spec.md`, sección "Animación CEDIS-Ciudad") todavía describe la
animación atada al tick del día, que ya no es lo que hace el código.

**Archivos tocados:** `index.html`, este archivo.

---

## 2026-08-14 — Ciudad en vista aérea, flota roja y paleta nueva

Manuel pidió tres cosas: los camiones deben ser rojos, no le gustó que
corrieran en una "banda infinita", y dio una paleta fija.

**Hecho:**
- **Paleta nueva** `["#273043","#9197ae","#eff6ee","#f02d3a","#dd0426"]`, con el
  más claro como superficie principal. El juego pasó de tema oscuro a **tema
  claro**: `#eff6ee` en tarjetas, `#273043` para texto y estructura, `#9197ae`
  para lo apagado, y los dos rojos como acento (flota, costo, deuda, peligro).
  Se actualizaron variables CSS, colores de Canvas y del velocímetro. Las
  únicas variaciones fuera de la lista son dos tintes del propio `#eff6ee`
  para separar el fondo de página de las tarjetas.
- **La ciudad pasó de vista lateral a vista aérea (plano de la ciudad).** El
  problema de fondo de la banda lateral era que los camiones no iban a ningún
  lado: entraban y salían de cuadro sin destino. Ahora el canvas muestra un
  plano con el CEDIS a la izquierda y **18 colonias** (6×3) separadas por
  avenidas. Cada camión tiene **una colonia asignada**: sale del CEDIS, recorre
  su avenida, **se detiene a descargar** y regresa. El viaje tiene tres tramos
  (ida / descarga / regreso) en vez de un ir y venir sin pausa.
- **Los camiones son rojos** (`#f02d3a` con cabina `#dd0426`), vistos desde
  arriba, de 9×5 píxeles de arte.
- **El plano comunica la deuda:** las colonias surtidas se ven claras y las que
  están esperando se pintan de rojo, y el rojo se oscurece conforme la deuda se
  vuelve estructural. La fracción de ciudad en rojo es
  `min(1, díasDeDeuda / CONFIG.pixel.deudaCiudadMax)`. Con la flota pasiva a los
  200 días la ciudad entera está roja; con un jugador que se adapta, sólo se
  enrojecen las colonias más lejanas. Es la misma lectura del velocímetro pero
  entendible de un vistazo.
- Los camiones descompuestos ya no llegan a su colonia: se quedan tirados en el
  camino con intermitentes.

**Decisiones:**
- **El plano NO contradice la decisión de "sin mapa" del spec.** Esa decisión
  era sobre la *mecánica*: no hay geografía, ni rutas, ni congestión espacial en
  la economía, y eso sigue igual — `ejecutarDia` no sabe que existen colonias.
  El plano es una *lectura de los agregados del día* (qué fracción de la ciudad
  alcanzaste a surtir) puesta en forma de mapa. Está anotado así en el código
  para que nadie lo confunda con una simulación espacial.
- El trazado de colonias se genera con el PRNG propio de la decoración
  (`CONFIG.pixel.seed`), nunca con el `rng` de la partida.
- El tamaño del lienzo ahora se fija desde `CONFIG.pixel` en JS y no desde los
  atributos del `<canvas>`: al subir el alto del arte se me quedó el atributo
  viejo en 96 y la ciudad salía recortada. Atarlo a `CONFIG` evita que el
  lienzo y las coordenadas de arte se desincronicen al recalibrar la escena.
- Verificado: los 6 criterios de aceptación siguen pasando sin cambios.

**Pendiente:** lo de las entradas anteriores. Se agrega que la sección
"Animación CEDIS-Ciudad" del spec describe una franja lateral que ya no existe.

**Archivos tocados:** `index.html`, este archivo.

---

## 2026-08-14 — La portada entra al juego

Manuel señaló que `portada.jfif` sólo se había usado como referencia visual y
no estaba en el juego.

**Hecho:**
- La portada es ahora la imagen principal del menú, arriba de la explicación de
  la mecánica. El `<h1>` de texto se quedó en el DOM pero oculto visualmente
  (`.solo-lectores`), porque el título ya viene dentro de la imagen; se
  conserva para lectores de pantalla, y la imagen lleva `alt`.
- Va **incrustada como data URI**, no como archivo aparte, para no romper el
  requisito de que el entregable sea un solo `index.html` que funcione sin
  conexión.
- Se agregó `embed_portada.py`: recomprime la portada (900 px de ancho,
  JPEG calidad 82, progresivo) y la escribe dentro del `<img id="portada">`.
  Hay que volver a correrlo cada vez que cambie `portada.jfif`.
  El original de 502 KB queda en 189 KB (252 KB ya en base64), y con eso
  `index.html` pasó de ~65 KB a **317 KB**.

**Decisiones:**
- **Desviación deliberada del spec.** La sección "STACK Y ENTREGA" dice
  "Geometría/visuales 100% procedurales. Prohibido cargar imágenes". Esa regla
  existe para que el archivo funcione sin conexión y sin dependencias externas,
  y el data URI cumple las dos cosas: no hay fetch de red ni archivos sueltos.
  El costo real es el peso del archivo, que quedó anotado arriba. Todo lo demás
  (la ciudad, los camiones, el velocímetro, las gráficas) sigue siendo 100%
  procedural.
- La portada usa marca registrada de Coca-Cola. Es la imagen de Manuel en un
  proyecto personal y es su decisión usarla; lo que se mantiene es que **el
  código no reproduce el logo ni el wordmark**: la livería de la flota en el
  plano es roja genérica.
- Verificado: los 6 criterios de aceptación siguen pasando.

**Archivos tocados:** `index.html`, `embed_portada.py` (nuevo), este archivo.

---

## 2026-08-14 — Clásico por defecto, efecto marginal visible y leyendas por panel

**Hecho:**
- **El modo clásico pasa a ser el modo por defecto** (`CONFIG.duro.activo =
  false`). Es el modelo económico puro, el mismo que verifican los criterios de
  aceptación. El modo duro sigue completo pero ahora es una casilla opcional
  en el menú (`#chk-duro`), junto a la lista de sus reglas extra.
- **Se hace visible qué compra un camión más.** Bajo la palanca hay dos
  renglones nuevos:
  - Fijo: "Un camión más: +40 cajas/día de capacidad y −$60/día de costo fijo.
    Se paga solo si mueve 28 cajas o más al día" (el punto de equilibrio sale
    de `fixedCostPerTruck / profitPerBox`, no está escrito a mano). En modo
    duro añade el costo y los días de contratación.
  - Diagnóstico del día, que cambia según en cuál de los tres regímenes estás:
    - falta capacidad → "Hoy la demanda nueva no cupo: 682 cajas se fueron a la
      deuda. Te faltan 18 camiones sólo para dejar de atrasarte."
    - vas pagando deuda → "Cubriste la demanda de hoy y además bajaste 24 cajas
      de deuda vieja. Cada camión de más saca hasta 40 cajas de deuda al día."
    - sobra flota → "15 camiones sin salir hoy, y aun así te costaron $900."
  - Para esto `ejecutarDia` ahora devuelve `demandaNoAtendida`, `deudaAtendida`
    y `camionesOciosos`. **No cambia ningún número**, sólo expone lo que ya
    calculaba.
- **Leyendas de las gráficas, una por panel, dibujadas dentro del Canvas.**
  Antes había una sola leyenda global con las 6 series, y como los paneles
  reusan la paleta (el rojo es "entregado" en el panel de cajas y "costo" en el
  de dinero), esa leyenda hacía ver como si fueran la misma serie. Ahora cada
  panel declara las suyas junto al título, con la muestra dibujada con el mismo
  trazo (sólido o punteado) que usa la línea.

**Decisiones:**
- El primer intento del diagnóstico marginal sumaba la demanda no atendida y
  toda la deuda vieja que no cupo, y salían mensajes inútiles del tipo "te
  faltan 187 camiones" (lo que costaría liquidar la deuda entera en un día).
  Se separaron: el mensaje de "te faltan N camiones" se calcula **sólo contra
  la demanda del día**, que es la decisión que el jugador puede tomar hoy.
- Verificado: los 6 criterios de aceptación siguen pasando.

**Archivos tocados:** `index.html`, este archivo.

---

## 2026-08-14 — Layout que no saltaba ni desbordaba, y publicación en GitHub

Manuel reportó que el texto nuevo "hace un movimiento mal que mueve las
gráficas" y que "el juego no se ve completo en la pantalla".

**Hecho — layout:**
- **Salto de layout.** El diagnóstico marginal cambia de largo cada día
  simulado, y como la caja crecía y se encogía, empujaba las gráficas varias
  veces por segundo. Ahora `.marginal-hoy` tiene **alto fijo** (56 px) con el
  espacio del mensaje más largo ya reservado, y los mensajes se acortaron para
  caber.
- **Bug encontrado al arreglar lo anterior:** puse `display:flex` en esa caja
  para centrar vertical, y eso convirtió cada `<b>` del mensaje en un ítem
  flex, desarmando la frase en columnas ("No cupieron | 245 | cajas | de hoy").
  El texto ahora va dentro de un `<span>` propio y las clases de estado
  (`falta`/`sobra`) se aplican a la caja, no al span.
- **El juego no cabía.** La pantalla de juego medía ~1,180 px de alto. Tres
  cambios: (1) la retícula `.paneles` sube las gráficas a una **tercera
  columna** a partir de 1180 px de ancho en vez de dejarlas hasta abajo;
  (2) la ciudad tiene tope de ancho (660 px → 198 px de alto, por la
  proporción 320:96), antes se comía media pantalla; (3) las gráficas bajaron
  de 360 a 300 px y las de resultados de 260 a 240. A 1440×900 ya entra
  completo.

**Hecho — publicación:**
- `README.md` nuevo: qué se aprende, cómo jugar, estructura de archivos, cómo
  verificar (con la tabla de criterios) y cómo recalibrar.
- Repo inicializado y publicado en
  **https://github.com/jmtoral/fleet-size-the-game** (público).
- **GitHub Pages** activado desde `main` en la raíz:
  **https://jmtoral.github.io/fleet-size-the-game/**. Funciona sin
  configuración extra porque el entregable es un `index.html` autocontenido.
- `.claude/settings.local.json` queda fuera del control de versiones (config
  local de sesión, con rutas de la máquina). Sí se versionan las dos skills
  del proyecto.

**Incidentes de esta sesión (para no repetirlos):**
- **Rompí la codificación de `index.html`.** Usé
  `Get-Content index.html -Raw | ... | Set-Content -Encoding utf8` para un
  reemplazo. En PowerShell 5.1 `Get-Content` lee con la codepage ANSI cuando el
  archivo no tiene BOM, así que leyó UTF-8 como cp1252 y lo reescribió como
  UTF-8: doble codificación en todo el archivo (`camiÃ³n`, `DÃA POR DÃA`). Se
  reparó aplicando el inverso exacto (encode cp1252 → decode utf-8), con un
  manejador para los bytes que .NET mapea a controles C1 y Python rechaza.
  **Regla: en este proyecto no se editan archivos con `Set-Content`**; usar las
  herramientas de edición o Python con `encoding='utf-8'`.
- **Force-push en el primer commit.** El push inicial arrastró un archivo
  temporal (`settings.local.json.tmp.…`) que Claude Code había creado. Se sacó
  del historial con `--amend` + `--force-with-lease`; era seguro porque el repo
  tenía un solo commit y nadie lo había clonado.

**Pendiente:**
- Sigue pendiente de sesiones anteriores: actualizar `fleet-sizing-spec.md` con
  (1) los números corregidos de la política adaptativa, (2) el índice de día
  base 0, (3) la sección de modo duro, (4) la ciudad en vista aérea (la sección
  "Animación CEDIS-Ciudad" describe una franja lateral que ya no existe) y
  (5) que la animación corre en tiempo real y no atada al tick del día.
- Revisión visual en 375 px del layout nuevo (se verificó a 1440×900).

**Archivos tocados:** `index.html`, `README.md` (nuevo), `.gitignore` (nuevo),
este archivo.
