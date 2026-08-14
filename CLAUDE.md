# Fleet Sizing — CLAUDE.md

Proyecto personal de Manuel: juego de simulación económica de un año de
reparto de cajas de refresco, inspirado en el explorable "Berlin 8AM"
(complexity-explorables.org), pero sin mapa ni congestión espacial. El
jugador controla el tamaño de una flota de camiones; todo lo demás
(demanda, incidentes, backlog) es automático.

## Documento autoritativo
`fleet-sizing-spec.md` en esta misma carpeta es la especificación completa
del juego: mecánica, fórmulas exactas, RNG sembrado, HUD, y criterios de
aceptación con números ya verificados por simulación offline. Cualquier
cambio de diseño se discute y se refleja ahí primero, no directo en el
código.

## Arquitectura
- Entregable final: un único `index.html` autocontenido, sin build step,
  sin dependencias externas (sin CDN de fuentes ni librerías: 2D con
  Canvas/SVG/CSS nativos).
- Todas las constantes viven en un objeto `CONFIG` al inicio del archivo.
  Cero números mágicos fuera de él.
- RNG determinista (`mulberry32`, semilla en `CONFIG.seed`) para que los
  criterios de aceptación del spec sean verificables byte por byte.
- Máquina de estados: `MENU -> JUGANDO -> PAUSA -> RESULTADOS`.

## Convenciones
- Comentarios en español, enfocados en la lógica de negocio (por qué existe
  esa regla), no en explicar sintaxis de JS.
- Invariante de conservación (`demanda - entregado - backlogFinal ≈ 0`)
  debe verificarse en cualquier corrida de prueba antes de dar por buena
  una entrega.
- Antes de tocar cualquier constante económica (`fixedCostPerTruck`,
  `profitPerBox`, `incidentP`, parámetros de demanda), usar la skill
  `offline-balance-simulation` y actualizar los números de la sección de
  criterios de aceptación del spec con los nuevos resultados.

## Skills de este proyecto
- `skills/serious-game-economics/` — principios de diseño para este tipo
  de juego (una sola palanca, óptimo interior, contrafactual en
  resultados).
- `skills/offline-balance-simulation/` — proceso para calibrar constantes
  económicas fuera del navegador antes de escribir código final.

## Protocolo de handoff
Al terminar cualquier tarea sobre este proyecto (una sesión de trabajo, un
cambio de calibración, una iteración de UI), agregar una entrada al final
de `HANDOFF.md` siguiendo la plantilla que está ahí, ANTES de cerrar la
tarea. La entrada debe permitir que otra sesión retome el trabajo sin tener
que releer todo el historial de chat.

## Cómo verificar
Abrir `index.html` en el navegador, confirmar que no hay errores en
consola, y correr manualmente (o vía un script de test) los escenarios de
flota fija listados en la sección "Criterios de aceptación" del spec,
comparando contra los números ya calculados ahí.
