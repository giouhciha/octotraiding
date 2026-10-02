"""
Job de análisis horario.

Cada vez que se ejecuta:
  1. Descarga las velas del activo seguido.
  2. Calcula el score/señal (motor) y detecta solo las velas YA CERRADAS.
  3. Procesa las velas nuevas con la política de operación (entrada/stop/salida).
  4. Guarda el reporte, registra eventos y envía notificaciones push.

Es el mismo motor y la misma política que validamos con backtesting.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import score_market
from engine.policy import Position, step
from engine.report import Report, report_from_row

from . import push, storage

INTERVAL_MINUTES = {"1h": 60, "4h": 240, "1d": 1440}
BOOTSTRAP_REPORTS = 48  # reportes de historia para mostrar en la app


def _closed_candles(scored: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Descarta la vela en formación: solo analizamos velas cerradas."""
    duration = pd.Timedelta(minutes=INTERVAL_MINUTES.get(interval, 60))
    now = pd.Timestamp(datetime.now(timezone.utc))
    return scored[scored.index + duration <= now]


def _report_row(rep: Report) -> dict:
    d = rep.to_dict()
    return {
        "ts": d["time_utc"],
        "symbol": d["symbol"],
        "price": d["price"],
        "signal": d["signal"],
        "score": d["score"],
        "regime": d["regime"],
        "daily_trend": d["daily_trend"],
        "entry": d["entry"],
        "stop": d["stop"],
        "target": d["target"],
        "rr": d["rr"],
        "position_pct": d["position_pct"],
        "narrative": d["narrative"],
    }


def _in_quiet(hour: int, start: int, end: int) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end  # rango que cruza medianoche


def _should_notify(ts: pd.Timestamp, settings: dict) -> bool:
    return not _in_quiet(ts.hour, settings["quiet_start"], settings["quiet_end"])


def _event_message(ev: dict, symbol: str) -> str:
    if ev["type"] == "OPEN":
        return (
            f"Comprar {symbol}: entrada ${ev['price']:,.0f} · "
            f"stop ${ev['stop']:,.0f} · objetivo ${ev['target']:,.0f}"
        )
    if ev["type"] == "TRAIL_STOP_SUBIO":
        return f"Stop subido a ${ev['new_stop']:,.0f}. Estás protegiendo ganancia."
    if ev["type"] == "CLOSE":
        return (
            f"Salir {symbol} en ${ev['price']:,.0f} "
            f"({ev['return'] * 100:+.1f}%). Motivo: {ev['reason']}."
        )
    return ev["type"]


def run_once(notify: bool = True) -> dict:
    """Ejecuta un ciclo de análisis. Devuelve un resumen."""
    settings = storage.get_settings()
    symbol = settings["symbol"]
    interval = settings["interval"]

    data = fetch_ohlcv(symbol, interval, limit=1000)
    features = build_features(data, DEFAULT_CONFIG)
    scored = score_market(features, DEFAULT_CONFIG).dropna(subset=["score"])
    closed = _closed_candles(scored, interval)
    if len(closed) < 2:
        return {"status": "sin datos suficientes"}

    state = storage.get_state()
    last = pd.Timestamp(state["last_processed"]) if state["last_processed"] else None

    # --- Primera ejecución: guardar historia y fijar punto de partida ---
    if last is None:
        for _, row in closed.tail(BOOTSTRAP_REPORTS).iterrows():
            storage.add_report(_report_row(report_from_row(symbol, row)))
        storage.save_state(None, str(closed.index[-1]))
        return {"status": "bootstrap", "reports": min(len(closed), BOOTSTRAP_REPORTS)}

    new = closed[closed.index > last]
    if len(new) == 0:
        return {"status": "sin velas nuevas"}

    # Reconstruir la posición abierta (si la hay)
    position = Position(**state["position"]) if state["position"] else None

    index_list = list(closed.index)
    events_sent = 0
    for ts in new.index:
        i = index_list.index(ts)
        prev_row = closed.iloc[i - 1]
        row = closed.iloc[i]
        position, events = step(prev_row, row, position, DEFAULT_CONFIG)

        storage.add_report(_report_row(report_from_row(symbol, row)))

        for ev in events:
            storage.add_event(str(row.name), ev["type"], _event_message(ev, symbol), ev)
            if notify and _should_notify(row.name, settings):
                push.send_to_all(
                    {
                        "title": f"OctoTrading · {symbol}",
                        "body": _event_message(ev, symbol),
                        "url": "/",
                        "tag": f"{symbol}-{ev['type']}",
                    }
                )
                events_sent += 1

    storage.save_state(position.to_dict() if position else None, str(new.index[-1]))
    return {
        "status": "ok",
        "processadas": len(new),
        "eventos": events_sent,
        "posicion": "abierta" if position else "cerrada",
    }


if __name__ == "__main__":
    storage.init_db()
    print(run_once(notify=False))
