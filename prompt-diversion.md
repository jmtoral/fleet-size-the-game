# Prompt para consultar cómo hacer Fleet Sizing más divertido

> Copia todo lo que sigue a partir de la línea divisoria y pégalo como un solo
> mensaje. Está escrito para que el modelo pueda razonar sin ver el código.

---

Actúa como diseñador senior de juegos, especializado en *serious games* y en
simulaciones económicas. Has diseñado juegos de gestión donde la diversión sale
de la tensión del modelo, no de los efectos visuales. Sé concreto y opinado: no
quiero un menú de ideas genéricas, quiero criterio.

## Lo que tengo

Un juego web de un solo archivo HTML. El jugador dirige el reparto de cajas de
refresco durante **un año simulado (365 días) en 5 minutos reales** (0.82 s por
día). Controla **una sola palanca**: cuántos camiones tiene en la flota (1 a 30,
arranca en 10). Todo lo demás es automático.

### Objetivos de aprendizaje (esto NO se negocia)

1. El costo de flota es **fijo y diario**: un camión ocioso cuesta exactamente
   lo mismo que uno que reparte a tope.
2. La carga suspendida es **deuda que se arrastra**, no una pérdida puntual: lo
   que no entregas hoy compite mañana con la demanda nueva por la misma
   capacidad.
3. **No existe una flota fija ganadora.** Gana quien ajusta el tamaño según la
   demanda reciente.

Si una propuesta hace el juego más divertido pero diluye alguno de estos tres
puntos, prefiero no hacerla. Dímelo explícitamente cuando detectes ese conflicto.

### El modelo económico exacto

```
capacidad        = N * 40                       # 40 cajas por camión al día
demanda(día)     = 480 + 300*cos(2π*(día-350)/365) + ruido(±25)
                   # 5% de los días hay shock: ×[0.3,0.6] o ×[1.5,2.2]

# La deuda vieja se atiende ANTES que la demanda nueva
backlogAsignado  = min(backlog, capacidad)
demandaAsignada  = min(demanda, capacidad - backlogAsignado)
# Lo que no cupo (demanda nueva + deuda vieja) se arrastra al día siguiente

# Por cada camión despachado: 8% de incidente.
# Si hay incidente, entrega sólo una fracción aleatoria (0 a 0.6) de su carga;
# el resto se vuelve deuda.

ingreso = entregado * 2.20
costo   = N * 60                                # por día, se use o no
```

Punto de equilibrio: un camión se paga si mueve **28 cajas al día** de las 40
que puede.

### Números verificados (semilla fija 42, flota FIJA todo el año)

| Flota | Balance final | Nivel de servicio | Deuda final |
|---|---:|---:|---:|
| 6  | $49,943 | 46.3% | 95,562 |
| 9  | $76,325 | 70.7% | 51,527 |
| **10** | **$83,925** | 78.3% | 38,097 |
| 11 | $82,504 | 82.7% | 30,755 |
| 20 | −$50,714 | 99.1% | 1,660 |

Óptimo interior real en N=10, curva cóncava. Una política adaptativa simple
(media móvil de 14 días ÷ 40) da **$103,390** con flota promedio 12.35: adaptarse
gana.

### Qué existe ya

- **Ciudad en pixel art, vista aérea.** Camiones rojos salen del CEDIS a
  colonias concretas, descargan y vuelven. Las colonias se pintan de rojo
  conforme crece la deuda: el mapa entero se enrojece si te hundes.
- **HUD**: balance grande, ingreso/costo/utilidad por separado, nivel de
  servicio, demanda y entregado del día, camiones en ruta e incidentes.
- **Velocímetro de deuda** medido en "días de tu flota completa" (no en cajas).
- **Lectura marginal en vivo** junto a la palanca: "+1 camión = +40 cajas/día y
  −$60/día, se paga si mueve 28 cajas", más un diagnóstico del día
  ("no cupieron 245 cajas, te faltan 7 camiones para dejar de atrasarte" /
  "15 camiones sin salir hoy y aun así te costaron $900").
- **Gráficas** por día: demanda vs. capacidad vs. entregado, deuda, y $/día.
- **Modo duro opcional**: contratar cuesta $600 y **tarda 7 días en llegar**,
  despedir cuesta $300, quiebras si la caja baja de −$25,000, y pierdes el
  contrato si la deuda supera 30 días de tu capacidad durante 5 días seguidos.
  Con esas reglas, dejar la flota quieta en 10 **pierde el contrato el día 38**,
  y una flota de 20 **quiebra el día 155**.
- **Contrafactual al cerrar**: recalcula qué habrías ganado con tu flota
  promedio fija todo el año, sobre la misma serie de demanda.
- **Ranking global** con backend propio.

### Restricciones técnicas duras

- Un solo `index.html` autocontenido. Sin build, sin npm, sin frameworks.
- Sin dependencias externas en tiempo de ejecución. 2D con Canvas/SVG/CSS.
- RNG determinista sembrado (`mulberry32`), con orden de llamadas fijo y
  documentado. Hay criterios de aceptación verificados al dígito contra ese
  orden: cualquier mecánica que consuma números aleatorios en otro punto los
  rompe. Dime si tu propuesta lo hace y cómo lo aislarías.
- Todas las constantes viven en un objeto `CONFIG`.
- Tiene que funcionar con tap en 375 px de ancho.

## El problema

**No estoy seguro de que sea divertido.** Mis sospechas, que puedes contradecir:

1. Son 5 minutos en los que sobre todo *miras*. La única interacción es mover un
   número, y el resultado de moverlo tarda en verse.
2. Una vez que entiendes "sigue la media móvil", está resuelto. La habilidad
   tiene techo bajo y se alcanza rápido.
3. **La semilla es fija**: el año es idéntico en cada partida. A la segunda o
   tercera vuelta te sabes dónde caen los shocks. Sospecho que esto mata la
   rejugabilidad, pero la semilla fija es lo que hace verificable el modelo y
   comparable el ranking.
4. Hay tramos largos donde no pasa nada y el jugador no tiene nada que decidir.
5. No hay sonido.

## Lo que quiero de ti

1. **Diagnóstico primero.** ¿Cuál es el problema real de diversión aquí? Si
   crees que mis cinco sospechas están mal enfocadas, dilo y explica por qué.
   ¿Qué género de juego es esto realmente, y contra qué debería compararse?
2. **De 3 a 5 cambios concretos**, ordenados por relación impacto/esfuerzo. Para
   cada uno: qué se implementa, por qué hace el juego más divertido, qué
   objetivo de aprendizaje refuerza o pone en riesgo, y qué constante de
   `CONFIG` habría que recalibrar.
3. **Resuelve explícitamente la tensión de la semilla fija** (punto 3). Quiero
   rejugabilidad *y* un ranking justo. ¿Semillas por temporada? ¿Semilla diaria
   compartida por todos, tipo Wordle? ¿Ranking por semilla? Dame la opción que
   elegirías y por qué.
4. **Dime qué NO hacer.** Qué de lo que ya existe sobra, distrae o da la
   respuesta demasiado pronto. Estoy dispuesto a quitar cosas.
5. **El momento a momento.** Diséñame qué debería hacer, sentir o decidir el
   jugador en los segundos 0-30, 30-90 y en el último minuto. Si la respuesta es
   que la estructura de 5 minutos está mal, dímelo y propón otra.

Prioriza el criterio sobre la exhaustividad: prefiero tres ideas peleadas y
justificadas que quince en lista. Si necesitas algo que no te di, pregúntalo
antes de responder.
