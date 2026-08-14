---
name: offline-balance-simulation
description: Usa esta skill antes de fijar o cambiar cualquier constante económica (costos, probabilidades, capacidades) en un juego de simulación tipo Fleet Sizing o Stay Time. Corre un puerto de las fórmulas exactas del juego en Python (mismo RNG sembrado, mismo orden de llamadas) fuera del navegador, para encontrar el balance de dificultad antes de escribir una sola línea de HTML/JS final.
---

# Calibración offline antes de tocar CONFIG

## Por qué
Probar el balance de un juego económico jugándolo manualmente en el
navegador es lento y no concluyente: una sola corrida no te dice si el
óptimo está en un extremo (juego trivial) o en el interior del rango
(juego con tensión real). Portar el modelo a un script corto y correr un
barrido de la palanca principal contra una semilla fija toma minutos y da
una respuesta numérica, no una impresión.

## Proceso
1. Implementa en Python (o Node) el mismo PRNG sembrado que usará el juego
   (`mulberry32` si el juego es JS), byte por byte igual, incluyendo el
   mismo orden exacto de llamadas a `rng()` por tick/día. Un orden distinto
   produce números distintos aunque la semilla sea la misma.
2. Porta las fórmulas de demanda/costos/eventos tal cual están en el spec,
   sin simplificar.
3. Corre un barrido de la palanca principal (p. ej. tamaño de flota de 6 a
   24) con semilla fija y registra: métrica de resultado (balance), y al
   menos una métrica de calidad de servicio (nivel de servicio, backlog
   final).
4. Verifica que la curva de resultado contra la palanca tenga un máximo
   interior, no en los extremos del rango jugable. Si un extremo domina,
   ajusta el parámetro que genera esa asimetría (costo fijo, margen por
   unidad, severidad de incidentes) y vuelve a correr el barrido. No
   ajustes a ojo dentro del navegador: cada iteración del barrido offline
   cuesta segundos, cada iteración jugando manualmente cuesta minutos.
5. Simula también una política simple *reactiva* (p. ej. ajustar la
   palanca según un promedio móvil de la demanda reciente) y confirma que
   supera a la mejor política fija encontrada en el paso 3. Si una política
   fija sigue ganando, el juego no está premiando la habilidad que se
   supone que enseña.
6. Verifica la invariante de conservación del modelo (lo que entra menos lo
   que sale menos lo que queda pendiente = 0) en cada corrida del barrido.
   Una invariante que falla revela un bug de contabilidad antes de que
   llegue a la versión jugable.
7. Congela los números de al menos 3-4 corridas del barrido (semilla fija)
   como criterios de aceptación literales en el spec, para que quien
   implemente el juego tenga un resultado exacto contra el cual validar su
   puerto a JS.

## Señales de que hace falta repetir el barrido
- Cambiaste `fixedCostPerTruck`, `profitPerBox`, cualquier probabilidad de
  evento, o los parámetros de la curva de demanda.
- Un usuario reporta que el juego "se resuelve solo" con una estrategia
  fija, o que ninguna estrategia parece ganable.
- Cambiaste la fórmula de arrastre de deuda/backlog o cualquier lógica de
  acumulación entre ticks; ese tipo de cambio suele alterar el óptimo sin
  que sea obvio con solo leer el diff del código.
