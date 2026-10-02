"""
Política de operación: el 'cómo se gestiona una operación hora a hora'.

Es la MISMA lógica que usarán:
  - el backtest (para simular el pasado), y
  - la app en vivo (para decidir y notificar cada hora).

Así garantizamos que lo que probamos es exactamente lo que ejecutará la app.

Modelo de estado:
  - FLAT (sin posición): espera una señal de entrada.
  - OPEN (con posición): actualiza el stop dinámico y espera una salida.

Eventos que produce (lo que se convertirá en notificaciones):
  - OPEN            : se abrió una compra
  - TRAIL_STOP_SUBIO: el stop subió (protege más ganancia)
  - CLOSE           : se cerró la posición (por stop, stop dinámico o venta fuerte)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd

from .config import DEFAULT_CONFIG, EngineConfig


@dataclass
class Position:
    """Una operación abierta."""

    entry: float
    initial_stop: float
    stop: float           # stop vigente (sube con el precio)
    target: float
    position_pct: float   # fracción del capital sugerida
    entry_time: Any
    highest: float        # máximo alcanzado desde la entrada
    bars_held: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["entry_time"] = str(d["entry_time"])
        return d


def entry_ok(prev_row: pd.Series, cfg: EngineConfig) -> bool:
    """
    ¿Se debe abrir una compra con esta señal?
    Regla validada: señal FUERTE de compra y tendencia diaria no bajista.
    """
    if prev_row["signal"] not in cfg.policy.entry_signals:
        return False
    if cfg.policy.require_htf_up and float(prev_row["htf_ctx"]) < 0:
        return False
    return True


def open_position(prev_row: pd.Series, row: pd.Series, cfg: EngineConfig) -> Position | None:
    """Abre la posición en la apertura de la vela actual, usando niveles de la anterior."""
    entry = float(row["open"])
    stop = float(prev_row["stop"])
    target = float(prev_row["target"])
    if not (stop < entry < target):
        return None
    return Position(
        entry=entry,
        initial_stop=stop,
        stop=stop,
        target=target,
        position_pct=float(prev_row["position_pct"]),
        entry_time=row.name,
        highest=entry,
    )


def check_exit(
    position: Position, prev_row: pd.Series, row: pd.Series, cfg: EngineConfig
) -> tuple[float, str] | None:
    """Decide si hay que cerrar. Prioridad: señal de venta -> stop -> objetivo."""
    if prev_row["signal"] in cfg.policy.exit_signals:
        return float(row["open"]), "SENAL_VENTA"
    if float(row["low"]) <= position.stop:
        if position.stop > position.entry:
            return position.stop, "STOP_DINAMICO_GANANCIA"
        return position.stop, "STOP"
    if cfg.policy.mode == "fixed" and float(row["high"]) >= position.target:
        return position.target, "OBJETIVO"
    return None


def update_trailing_stop(position: Position, row: pd.Series, cfg: EngineConfig) -> bool:
    """
    Sube el stop si el precio marcó un nuevo máximo. Nunca baja.
    Devuelve True si el stop subió (para notificar).
    """
    if cfg.policy.mode != "trail":
        return False
    old_stop = position.stop
    position.highest = max(position.highest, float(row["high"]))
    atr = float(row["atr14"])
    if pd.notna(atr) and atr > 0:
        new_stop = position.highest - cfg.risk.trail_atr_mult * atr
        position.stop = max(position.stop, new_stop)
    return position.stop > old_stop


def step(
    prev_row: pd.Series,
    row: pd.Series,
    position: Position | None,
    cfg: EngineConfig = DEFAULT_CONFIG,
) -> tuple[Position | None, list[dict]]:
    """
    Avanza una vela. Devuelve (nueva_posición, eventos).
    Esta es la función que la app llamará cada hora.
    """
    events: list[dict] = []

    if position is None:
        if entry_ok(prev_row, cfg):
            pos = open_position(prev_row, row, cfg)
            if pos is not None:
                events.append(
                    {
                        "type": "OPEN",
                        "time": str(row.name),
                        "price": pos.entry,
                        "stop": pos.stop,
                        "target": pos.target,
                        "position_pct": pos.position_pct,
                    }
                )
                return pos, events
        return None, events

    # --- Hay posición: gestionarla ---
    position.bars_held += 1
    exit_result = check_exit(position, prev_row, row, cfg)
    if exit_result is not None:
        exit_price, reason = exit_result
        events.append(
            {
                "type": "CLOSE",
                "time": str(row.name),
                "price": exit_price,
                "reason": reason,
                "entry": position.entry,
                "return": exit_price / position.entry - 1,
            }
        )
        return None, events

    if update_trailing_stop(position, row, cfg):
        events.append(
            {
                "type": "TRAIL_STOP_SUBIO",
                "time": str(row.name),
                "new_stop": position.stop,
                "price": float(row["close"]),
            }
        )
    return position, events
