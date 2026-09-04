#!/usr/bin/env python3
"""
Verificación offline de los criterios de aceptación de Fleet Sizing.

Es un puerto byte por byte del núcleo de simulación de `index.html`: mismo PRNG
(`mulberry32`), misma semilla, mismo orden de llamadas a rng() por día y misma
contabilidad de carga suspendida. Si este script y el juego dan números
distintos, uno de los dos tiene un bug: NO se ajustan los números esperados para
que cuadren.

Uso:
    python verify_balance.py            # criterios de aceptación
    python verify_balance.py --barrido  # barrido de flotas fijas (calibración)

Solo usa la librería estándar.
"""

import argparse
import math
import sys

# ---------------------------------------------------------------------------
# CONFIG — debe coincidir con el objeto CONFIG de index.html
# ---------------------------------------------------------------------------
CONFIG = {
    "seed": 42,
    "yearDays": 365,
    "K": 40,
    "incidentP": 0.08,
    "incidentMaxFrac": 0.6,
    "fixedCostPerTruck": 60,
    "profitPerBox": 2.2,
    "demandBase": 480,
    "demandAmp": 300,
    "peakDay": 350,
    "noiseRange": 50,
    # Los shocks son REGIMENES que duran varios dias, no picos de un dia.
    # Con un dia de duracion y 7 de espera para contratar, la respuesta optima
    # a cualquier shock era siempre ignorarlo: no habia decision que tomar.
    "shockStartProb": 0.022,
    "shockMinDays": 3, "shockMaxDays": 12,
    "shockDownMin": 0.3, "shockDownRange": 0.3,
    "shockUpMin": 1.5,   "shockUpRange": 0.7,

    # Flujos de RNG independientes. Antes todo salia de un solo generador, asi
    # que el lazo de incidentes (cuyo numero de llamadas depende del tamano de
    # la flota) corria el ruido y los shocks de todos los dias siguientes: dos
    # jugadores con decisiones distintas enfrentaban AÑOS distintos y el ranking
    # comparaba peras con manzanas. Separados, la serie de demanda depende solo
    # de la semilla.
    "shockSeedXor": 0x9E3779B9,
    "incidentSeedXor": 0x85EBCA6B,
    "adaptiveWindow": 14,
    "adaptiveWarmupFleet": 10,
}

TOL_BALANCE = 1          # dólares, por redondeo de punto flotante
TOL_INVARIANTE = 1e-6    # cajas

MASK32 = 0xFFFFFFFF


# ---------------------------------------------------------------------------
# PRNG
# ---------------------------------------------------------------------------
def mulberry32(seed):
    """Puerto exacto del mulberry32 de JS.

    En JS `a += 0x6D2B79F5` acumula como Number (sin truncar) y son los
    operadores bit a bit los que hacen el módulo 2^32; aquí se replica dejando
    el acumulador como entero de Python y enmascarando dentro de la mezcla.
    """
    state = seed

    def rng():
        nonlocal state
        state = state + 0x6D2B79F5
        t = state & MASK32
        t = ((t ^ (t >> 15)) * (t | 1)) & MASK32
        t = t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & MASK32)) & MASK32)
        return ((t ^ (t >> 14)) & MASK32) / 4294967296

    return rng


def js_round(x):
    """Math.round de JS: los medios van hacia +infinito (Python usa banqueros)."""
    return math.floor(x + 0.5)


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------
def crear_demanda(seed=None, c=CONFIG):
    """Devuelve una funcion demanda(dia) con su propio estado de shock.

    `dia` es indice base 0 (0 = 1 de enero). Consume DOS flujos de RNG que no
    dependen de las decisiones del jugador, asi que la serie de demanda queda
    fijada por la semilla y es identica para todos.

    Orden de consumo, no reordenar:
      rngRuido : 1 llamada por dia.
      rngShock : 1 llamada por dia para el chequeo y, si arranca un regimen,
                 3 mas (direccion, magnitud, duracion).
    """
    seed = c["seed"] if seed is None else seed
    rng_ruido = mulberry32(seed)
    rng_shock = mulberry32(seed ^ c["shockSeedXor"])
    estado = {"restantes": 0, "mult": 1.0}

    def demanda(dia):
        d = c["demandBase"] + c["demandAmp"] * math.cos(
            2 * math.pi * (dia - c["peakDay"]) / c["yearDays"]
        )
        d += (rng_ruido() - 0.5) * c["noiseRange"]

        if estado["restantes"] > 0:
            d *= estado["mult"]
            estado["restantes"] -= 1
        elif rng_shock() < c["shockStartProb"]:
            if rng_shock() < 0.5:
                estado["mult"] = c["shockDownMin"] + rng_shock() * c["shockDownRange"]
            else:
                estado["mult"] = c["shockUpMin"] + rng_shock() * c["shockUpRange"]
            dur = c["shockMinDays"] + int(
                rng_shock() * (c["shockMaxDays"] - c["shockMinDays"] + 1))
            d *= estado["mult"]
            estado["restantes"] = dur - 1

        return max(0, js_round(d))

    return demanda


def ejecutar_dia(demanda, N, backlog, rng, c=CONFIG):
    """Un día de operación. La deuda vieja se atiende antes que la demanda
    nueva, y la parte de la deuda que no cabe en la capacidad de hoy SE
    ARRASTRA (`backlog_viejo_no_atendido`): borrarla es el bug que vuelve
    trivial el juego."""
    K = c["K"]
    capacidad = N * K
    backlog_asignado = min(backlog, capacidad)
    restante = capacidad - backlog_asignado
    demanda_asignada = min(demanda, restante)
    no_atendido_estructural = demanda - demanda_asignada
    backlog_viejo_no_atendido = backlog - backlog_asignado
    total_asignado = backlog_asignado + demanda_asignada
    camiones_usados = min(N, math.ceil(total_asignado / K)) if total_asignado > 0 else 0

    carga_restante = total_asignado
    entregado = 0.0
    perdido = 0.0
    for i in range(N):
        if i < camiones_usados:
            carga = min(K, carga_restante)
            carga_restante -= carga
            if rng() < c["incidentP"]:
                fraccion = rng() * c["incidentMaxFrac"]
                entregado += carga * fraccion
                perdido += carga * (1 - fraccion)
            else:
                entregado += carga
        # else: camión ocioso — cuesta igual que uno que repartió lleno

    return {
        "entregado": entregado,
        "camiones_usados": camiones_usados,
        "backlog_manana": backlog_viejo_no_atendido + no_atendido_estructural + perdido,
        "ingreso": entregado * c["profitPerBox"],
        "costo": N * c["fixedCostPerTruck"],
    }


def simular_anio(politica, seed=None, c=CONFIG):
    """`politica(dia, historial_demanda, backlog) -> N`."""
    seed = c["seed"] if seed is None else seed
    demanda_del_dia = crear_demanda(seed, c)
    rng = mulberry32(seed ^ c["incidentSeedXor"])   # flujo propio de incidentes
    backlog = 0.0
    ingreso = costo = 0.0
    total_demanda = total_entregado = 0.0
    camion_dias = 0
    suma_flota = 0
    dems = []

    for dia in range(c["yearDays"]):
        N = politica(dia, dems, backlog)
        demanda = demanda_del_dia(dia)
        r = ejecutar_dia(demanda, N, backlog, rng, c)

        backlog = r["backlog_manana"]
        ingreso += r["ingreso"]
        costo += r["costo"]
        total_demanda += demanda
        total_entregado += r["entregado"]
        camion_dias += r["camiones_usados"]
        suma_flota += N
        dems.append(demanda)

    return {
        "balance": ingreso - costo,
        "servicio": 100 * total_entregado / total_demanda if total_demanda else 100.0,
        "backlog_final": backlog,
        "flota_promedio": suma_flota / c["yearDays"],
        "eficiencia": total_entregado / camion_dias if camion_dias else 0.0,
        # Invariante: lo que entró - lo que salió - lo que quedó pendiente = 0
        "invariante": total_demanda - total_entregado - backlog,
    }


def politica_fija(N):
    return lambda dia, dems, backlog: N


def politica_adaptativa(c=CONFIG):
    """N = ceil(media móvil de los últimos 14 días de demanda / K); mientras no
    hay ventana completa, flota de arranque."""
    def pol(dia, dems, backlog):
        if len(dems) < c["adaptiveWindow"]:
            return c["adaptiveWarmupFleet"]
        v = dems[-c["adaptiveWindow"]:]
        return math.ceil(sum(v) / c["adaptiveWindow"] / c["K"])
    return pol


# ---------------------------------------------------------------------------
# Criterios de aceptación del spec
# ---------------------------------------------------------------------------
# Números recalculados tras separar los flujos de RNG y dar duración a los
# shocks (2026-09-04). Los del spec original ya no aplican: describían el modelo
# de un solo flujo con shocks de un día. El óptimo entre flotas fijas se movió
# de N=10 a N=11 y sigue siendo interior, con la curva cóncava a ambos lados
# (N=10 y N=12 rinden menos), que es la propiedad que hace que el juego tenga
# tensión. Ver HANDOFF.md.
CRITERIOS = [
    {"etiqueta": "Flota fija N=6",  "N": 6,  "balance": 50025},
    {"etiqueta": "Flota fija N=10", "N": 10, "balance": 84431},
    {"etiqueta": "Flota fija N=11", "N": 11, "balance": 89394,
     "servicio": 81.7, "backlog": 33636},
    {"etiqueta": "Flota fija N=12", "N": 12, "balance": 78419},
    {"etiqueta": "Flota fija N=20", "N": 20, "balance": -34439},
]
CRITERIO_ADAPTATIVO = {
    "etiqueta": "Política adaptativa (media móvil 14d)",
    "balance": 108013, "servicio": 95.6, "flota": 12.718,
}


def correr_criterios():
    filas = []
    ok_global = True

    for cr in CRITERIOS:
        r = simular_anio(politica_fija(cr["N"]))
        ok = abs(round(r["balance"]) - cr["balance"]) <= TOL_BALANCE
        if "servicio" in cr:
            ok = ok and abs(round(r["servicio"], 1) - cr["servicio"]) <= 0.05
        if "backlog" in cr:
            ok = ok and abs(round(r["backlog_final"]) - cr["backlog"]) <= 1
        inv_ok = abs(r["invariante"]) < TOL_INVARIANTE
        ok = ok and inv_ok
        ok_global = ok_global and ok
        filas.append((cr["etiqueta"], cr["balance"], r, ok))

    ra = simular_anio(politica_adaptativa())
    mejor_fija = max(round(f[2]["balance"]) for f in filas)
    ad = CRITERIO_ADAPTATIVO
    ok_ad = (
        abs(round(ra["balance"]) - ad["balance"]) <= TOL_BALANCE
        and abs(round(ra["servicio"], 1) - ad["servicio"]) <= 0.05
        and abs(ra["flota_promedio"] - ad["flota"]) <= 0.01
        and abs(ra["invariante"]) < TOL_INVARIANTE
        # La razón de ser del criterio: adaptarse debe ganarle a cualquier flota fija.
        and round(ra["balance"]) > mejor_fija
    )
    ok_global = ok_global and ok_ad
    filas.append((ad["etiqueta"], ad["balance"], ra, ok_ad))

    print(f"Semilla {CONFIG['seed']} · {CONFIG['yearDays']} días · "
          f"K={CONFIG['K']} incidentP={CONFIG['incidentP']} "
          f"costo/camión={CONFIG['fixedCostPerTruck']} margen/caja={CONFIG['profitPerBox']}\n")
    cab = f"{'Escenario':<40}{'Esperado':>12}{'Obtenido':>12}{'Servicio':>10}{'Deuda fin':>12}{'Invariante':>13}   "
    print(cab)
    print("-" * (len(cab) + 6))
    for etiqueta, esperado, r, ok in filas:
        print(f"{etiqueta:<40}{esperado:>12,}{round(r['balance']):>12,}"
              f"{r['servicio']:>9.1f}%{round(r['backlog_final']):>12,}"
              f"{r['invariante']:>13.2e}   {'PASA' if ok else 'FALLA'}")

    print(f"\nFlota promedio de la política adaptativa: {ra['flota_promedio']:.3f} camiones")
    print(f"Mejor flota fija de la lista: ${mejor_fija:,} · "
          f"adaptativa: ${round(ra['balance']):,} "
          f"({'gana' if round(ra['balance']) > mejor_fija else 'NO gana'})")
    print("\n" + ("TODOS LOS CRITERIOS PASAN" if ok_global else "HAY CRITERIOS QUE FALLAN"))
    return ok_global


def correr_barrido(lo=4, hi=24):
    """Barrido de flotas fijas: sirve para confirmar que el óptimo es interior
    (no en un extremo) después de tocar cualquier constante económica."""
    print(f"{'N':>4}{'Balance':>12}{'Servicio':>10}{'Deuda final':>14}{'Cajas/camión-día':>18}")
    print("-" * 58)
    mejor = (None, float("-inf"))
    for N in range(lo, hi + 1):
        r = simular_anio(politica_fija(N))
        if r["balance"] > mejor[1]:
            mejor = (N, r["balance"])
        assert abs(r["invariante"]) < TOL_INVARIANTE, f"invariante rota en N={N}"
        print(f"{N:>4}{round(r['balance']):>12,}{r['servicio']:>9.1f}%"
              f"{round(r['backlog_final']):>14,}{r['eficiencia']:>18.1f}")
    ra = simular_anio(politica_adaptativa())
    print(f"\nÓptimo entre flotas fijas: N={mejor[0]} (${round(mejor[1]):,})")
    if mejor[0] in (lo, hi):
        print("  AVISO: el óptimo cayó en un extremo del barrido. El juego no tiene "
              "tensión real: recalibra antes de tocar el código.")
    print(f"Política adaptativa: ${round(ra['balance']):,} "
          f"(flota promedio {ra['flota_promedio']:.2f}, servicio {ra['servicio']:.1f}%)")


# ---------------------------------------------------------------------------
# MODO DURO — capa de reglas de juego sobre el mismo modelo económico
# ---------------------------------------------------------------------------
DURO = {
    "leadTimeDays": 7,
    # Recalibrado tras los shocks con duración: con 600/300 los regímenes
    # obligaban a mover tanto la flota que el costo de mover se comía la
    # ventaja de adaptarse, y el jugador adaptativo apenas empataba con la
    # mejor flota fija. `graciaDias` resultó irrelevante en todo el barrido
    # (nadie ronda el umbral tantos días seguidos), así que se dejó en 5.
    "hireCost": 400,
    "fireCost": 200,
    "pisoCaja": -25000,
    "deudaMaxDias": 30,
    "graciaDias": 5,
    "balanceObjetivo": 50000,
}


def simular_duro(politica, d=DURO, c=CONFIG):
    """Mismo `ejecutar_dia` que el modo base; lo que cambia es que mover la
    palanca cuesta y tarda, y que la partida puede terminar antes de tiempo."""
    demanda_del_dia = crear_demanda(c["seed"], c)
    rng = mulberry32(c["seed"] ^ c["incidentSeedXor"])
    activos = c["adaptiveWarmupFleet"]
    pedidos = {}
    backlog = 0.0
    ingreso = costo = 0.0
    total_demanda = total_entregado = 0.0
    suma_flota = 0
    min_caja = float("inf")
    max_deuda_dias = 0.0
    racha = 0
    fin = motivo = None
    gasto_flota = 0.0
    dems = []

    for dia in range(c["yearDays"]):
        objetivo = politica(dia, dems, backlog, activos)
        en_camino = sum(pedidos.values())
        if objetivo > activos + en_camino:
            faltan = objetivo - activos - en_camino
            llegada = dia + d["leadTimeDays"]
            pedidos[llegada] = pedidos.get(llegada, 0) + faltan
            costo += faltan * d["hireCost"]
            gasto_flota += faltan * d["hireCost"]
        elif objetivo < activos:
            sobran = activos - objetivo
            activos -= sobran
            costo += sobran * d["fireCost"]
            gasto_flota += sobran * d["fireCost"]
        # Las llegadas se aplican después de la orden del día
        activos += pedidos.pop(dia, 0)

        demanda = demanda_del_dia(dia)
        r = ejecutar_dia(demanda, activos, backlog, rng, c)
        backlog = r["backlog_manana"]
        ingreso += r["ingreso"]
        costo += r["costo"]
        total_demanda += demanda
        total_entregado += r["entregado"]
        suma_flota += activos
        dems.append(demanda)

        balance = ingreso - costo
        min_caja = min(min_caja, balance)
        dias_deuda = backlog / (activos * c["K"]) if activos else float("inf")
        max_deuda_dias = max(max_deuda_dias, dias_deuda)

        if fin is None:
            if balance < d["pisoCaja"]:
                fin, motivo = dia, "caja"
            else:
                racha = racha + 1 if dias_deuda > d["deudaMaxDias"] else 0
                if racha >= d["graciaDias"]:
                    fin, motivo = dia, "contrato"
        if fin is not None:
            break

    dias = len(dems)
    return {
        "balance": ingreso - costo,
        "servicio": 100 * total_entregado / total_demanda if total_demanda else 100.0,
        "min_caja": min_caja,
        "max_deuda_dias": max_deuda_dias,
        "fin": fin, "motivo": motivo,
        "flota_promedio": suma_flota / dias if dias else 0,
        "gasto_flota": gasto_flota,
        "dias": dias,
    }


def politica_duro_fija(N):
    return lambda dia, dems, backlog, activos: N


def politica_duro_adaptativa(ventana=14, c=CONFIG):
    """Jugador competente: media móvil de la demanda MÁS la parte de la deuda
    que quiere amortizar en la ventana. Es la política mínima que sobrevive las
    dos formas de perder."""
    def pol(dia, dems, backlog, activos):
        if len(dems) < ventana:
            return c["adaptiveWarmupFleet"]
        media = sum(dems[-ventana:]) / ventana
        return max(1, math.ceil((media + backlog / ventana) / c["K"]))
    return pol


def correr_duro():
    print("MODO DURO · " + " · ".join(f"{k}={v}" for k, v in DURO.items()) + "\n")
    print(f"{'Forma de jugar':<34}{'Balance':>11}{'Fin':>22}{'Serv':>7}"
          f"{'MinCaja':>11}{'MaxDeudaD':>11}{'Flota':>7}")
    print("-" * 103)

    filas = []
    for N in (6, 8, 10, 12, 14, 16, 18, 20):
        r = simular_duro(politica_duro_fija(N))
        filas.append((f"flota fija N={N}", r))
    filas.append(("jugador adaptativo", simular_duro(politica_duro_adaptativa())))

    for etiqueta, r in filas:
        fin = "completó el año" if r["fin"] is None else f"{r['motivo']} día {r['fin']}"
        print(f"{etiqueta:<34}{round(r['balance']):>11,}{fin:>22}{r['servicio']:>6.1f}%"
              f"{round(r['min_caja']):>11,}{r['max_deuda_dias']:>11.1f}{r['flota_promedio']:>7.1f}")

    sobrevive_fija = [(e, r) for e, r in filas[:-1] if r["fin"] is None]
    adapt = filas[-1][1]
    print()
    if sobrevive_fija:
        mejor = max(sobrevive_fija, key=lambda t: t[1]["balance"])
        print(f"Mejor flota fija que sobrevive el año: {mejor[0]} (${round(mejor[1]['balance']):,})")
    else:
        print("Ninguna flota fija sobrevive el año completo.")
    print(f"Jugador adaptativo: ${round(adapt['balance']):,} "
          f"(vara para ganar: ${DURO['balanceObjetivo']:,} → "
          f"{'GANA' if adapt['balance'] >= DURO['balanceObjetivo'] and adapt['fin'] is None else 'NO GANA'})")
    print("\nEl modo duro es correcto si: (a) la flota pasiva pierde el contrato, "
          "(b) la flota grande quiebra,\n(c) el jugador adaptativo termina el año "
          "por encima de la vara.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--barrido", action="store_true",
                    help="barrido de flotas fijas en vez de los criterios")
    ap.add_argument("--duro", action="store_true",
                    help="calibración de las reglas del modo duro")
    args = ap.parse_args()
    if args.barrido:
        correr_barrido()
    elif args.duro:
        correr_duro()
    else:
        sys.exit(0 if correr_criterios() else 1)
