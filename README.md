# Fleet Sizing — el juego

Juego de simulación económica de un año de reparto de cajas de refresco. El
jugador controla **una sola palanca** —cuántos camiones mantiene en la flota— y
todo lo demás (demanda estacional, shocks, incidentes de ruta, carga suspendida)
es automático.

Inspirado en el explorable [Berlin 8AM](https://www.complexity-explorables.org/),
pero sin mapa ni congestión espacial: la tensión está en el modelo de costos, no
en la geografía.

## Qué se aprende

1. El costo de flota es **fijo y diario**: un camión ocioso cuesta exactamente lo
   mismo que uno que reparte a tope.
2. La carga suspendida es **deuda que se arrastra**, no una pérdida puntual: lo
   que no se entrega hoy compite mañana con la demanda nueva por la misma
   capacidad.
3. **No hay una flota fija ganadora.** Tanto la flota mínima (deuda impagable)
   como la máxima (costo fijo que no se recupera en temporada baja) pierden
   contra una política que ajusta el tamaño según la demanda reciente.

## Cómo jugar

Abre `index.html` en cualquier navegador. No hay build, ni servidor, ni
dependencias: es un solo archivo autocontenido que funciona sin conexión.

- Una partida son 365 días simulados en 5 minutos reales.
- El multiplicador 1x/4x/10x es una **ayuda de prueba**, no una mecánica: no
  cambia ningún número, sólo la velocidad a la que se generan.
- El **modo duro** (opcional, en el menú) agrega costo y tiempo de espera para
  contratar camiones, más dos formas de perder antes de que acabe el año:
  quiebra por caja y pérdida del contrato por deuda acumulada.

## Estructura

| Archivo | Qué es |
|---|---|
| `index.html` | El juego completo. Único entregable. |
| `fleet-sizing-spec.md` | Especificación autoritativa: fórmulas, RNG, criterios de aceptación. |
| `verify_balance.py` | Verificación offline del modelo (sólo stdlib). |
| `embed_portada.py` | Incrusta `portada.jfif` en `index.html` como data URI. |
| `HANDOFF.md` | Bitácora de sesiones de trabajo. |

## Verificación

El modelo es determinista: RNG sembrado (`mulberry32`, semilla en `CONFIG.seed`)
con un orden de llamadas fijo y documentado. Eso permite criterios de aceptación
verificables al dígito.

```bash
python verify_balance.py            # criterios de aceptación
python verify_balance.py --barrido  # barrido de flotas fijas (calibración)
python verify_balance.py --duro     # calibración de las reglas del modo duro
```

El juego también se autoverifica en el navegador: abre `index.html?test=1` y
corre los mismos escenarios con el código que juega el usuario.

Con `CONFIG.seed = 42`, corriendo flotas **fijas** todo el año:

| Escenario | Balance | Nivel de servicio | Deuda final |
|---|---:|---:|---:|
| N=6 | $49,943 | 46.3% | 95,562 |
| N=9 | $76,325 | 70.7% | 51,527 |
| **N=10** | **$83,925** | 78.3% | 38,097 |
| N=11 | $82,504 | 82.7% | 30,755 |
| N=20 | −$50,714 | 99.1% | 1,660 |
| Política adaptativa (media móvil 14d) | **$103,390** | 95.3% | 8,378 |

El óptimo entre flotas fijas es interior (N=10, curva cóncava), y una política
que se adapta le gana a cualquier flota fija. En todas las corridas se cumple la
invariante de conservación `demanda − entregado − deudaFinal ≈ 0`.

## Recalibrar dificultad

Las constantes económicas viven en el objeto `CONFIG` al inicio de
`index.html`. Las que mueven la aguja son `fixedCostPerTruck`, `profitPerBox`,
`incidentP` y `demandAmp`.

Después de tocar cualquiera de ellas hay que correr `verify_balance.py --barrido`
y confirmar que el óptimo entre flotas fijas sigue siendo **interior** y que la
política adaptativa sigue ganando; si no, el juego se convierte en una
calculadora con animación. Los números nuevos se congelan como criterios en el
spec, en `CONFIG.criteriosAceptacion` y en `CRITERIOS` de `verify_balance.py`.

## Nota sobre la portada

`portada.jfif` es una imagen generada para uso personal que incluye marcas
registradas de terceros. El código del juego no reproduce ningún logo ni
wordmark: la flota del plano usa una livería roja genérica.
