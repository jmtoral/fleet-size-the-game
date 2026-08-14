---
name: serious-game-economics
description: Usa esta skill para construir juegos de simulación económica de un solo archivo (single-file HTML) donde el aprendizaje está en la tensión de un modelo de costos, no en el espectáculo visual. Aplica a juegos tipo "Fleet Sizing" o "Stay Time": el jugador controla una palanca simple (tamaño de flota, elección de vehículo), un modelo determinista con RNG sembrado genera el resto, y el juego se evalúa con un balance final ganable/perdible.
---

# Serious games de economía operativa

## Cuándo aplica
Proyectos donde el objetivo es que el jugador internalice un modelo de
costos real (fijo vs. variable, deuda que se arrastra, riesgo estocástico)
a través de jugar, no de leer. El patrón se repite en varios proyectos
propios: Fleet Sizing (tamaño de flota vs. demanda) y el simulador de
Stay Time / ruta de reparto (KOF).

## Principios de diseño, en orden de prioridad

1. **Una sola palanca real por partida.** Todo lo demás es automático. Si
   el jugador puede tocar dos o tres cosas a la vez, el aprendizaje se
   diluye porque ya no puede atribuir el resultado a una decisión.
2. **El modelo debe tener un óptimo interior, no un extremo dominante.**
   Antes de escribir una sola línea de UI, valida con simulación offline
   (ver skill `offline-balance-simulation`) que ni el mínimo ni el máximo
   de la palanca ganan siempre. Si un extremo domina, el "juego" es en
   realidad una calculadora con animación.
3. **Todo número vive en un objeto `CONFIG`.** Cero números mágicos
   dispersos en el código. Facilita recalibrar y volver a correr la
   simulación offline tras cualquier cambio.
4. **RNG sembrado (`mulberry32` u otro PRNG determinista), nunca
   `Math.random()` crudo.** Sin esto no puedes escribir criterios de
   aceptación verificables ni reproducir un bug que reporte el usuario.
5. **Un "contrafactual" en la pantalla de resultados.** Muestra qué habría
   pasado con la decisión más simple posible (flota fija, vehículo por
   default) usando la misma semilla y el mismo historial de eventos. Es la
   forma más directa de que el jugador vea el valor de su propia decisión,
   en vez de tener que confiar en la afirmación de que "jugó bien".
6. **Invariante de conservación como prueba automática.** En un modelo de
   flujo (cajas, tiempo, dinero), la suma de "lo que entró" menos "lo que
   salió" menos "lo que quedó pendiente" debe dar cero. Impleméntalo como
   assert; detecta bugs de contabilidad (backlog que desaparece, tiempo que
   se duplica) que de otro modo son invisibles a simple vista porque el
   juego sigue siendo "jugable" con el bug adentro.

## Estructura de entrega recomendada
Single-file `index.html`, `CONFIG` al inicio, máquina de estados explícita,
comentarios en español sobre la lógica de negocio (no la sintaxis), sin
dependencias externas si el proyecto es 2D (Canvas/SVG/CSS). Solo usa
Three.js o similar si el juego realmente necesita representar geografía o
rutas espaciales; si la decisión de diseño fue explícitamente "sin mapa",
no lo agregues por defecto.

## Errores ya encontrados en este tipo de proyecto (no repetir)
- Backlog/deuda que se "resetea" en vez de arrastrarse cuando la capacidad
  del día es menor a la deuda acumulada. Vuelve el juego trivialmente fácil
  porque el castigo por subprovisión nunca se acumula de verdad.
