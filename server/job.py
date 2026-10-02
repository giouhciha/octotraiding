"""
Job de análisis horario.

Lógica según el estado del USUARIO:

  - SIN posición (no ha comprado): busca el momento de COMPRAR.
      Avisa cuando aparece una COMPRA FUERTE (y la tendencia diaria no es bajista).

  - CON posición (ya compró): busca el momento de VENDER.
      Sube el stop dinámico (y avisa), y avisa cuando toca el stop o aparece
      una VENTA FUERTE.

El usuario confirma sus compras/ventas reales desde la app. El motor y la política
son los mismos que validamos con backtesting.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import COMPRA_FUERTE, score_market
from engine.policy import Position, check_exit, update_trailing_stop
from engine.report import Report, report_from_row

from . import push, storage

INTERVAL_MINUTES = {"1h": 60, "4h": 240, "1d": 1440}
BOOTSTRAP_REPORTS = 48


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _closed_candles(scored: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Descarta la vela en formación: solo analizamos velas cerradas."""
    duration = pd.Timedelta(minutes=INTERVAL_MINUTES.get(interval, 60))
    now = pd.Timestamp(datetime.now(timezone.utc))
    return scored[scored.index + duration <= now]


def _analyze_latest() -> tuple[str, str, pd.DataFrame]:
    """Descarga y calcula; devuelve (symbol, interval, velas cerradas)."""
    settings = storage.get_settings()
    symbol, interval = settings["symbol"], settings["interval"]
    data = fetch_ohlcv(symbol, interval, limit=1000)
    features = build_features(data, DEFAULT_CONFIG)
    scored = score_market(features, DEFAULT_CONFIG).dropna(subset=["score"])
    return symbol, interval, _closed_candles(scored, interval)


def _report_row(rep: Report) -> dict:
    d = rep.to_dict()
    return {
        "ts": d["time_utc"], "symbol": d["symbol"], "price": d["price"],
        "signal": d["signal"], "score": d["score"], "regime": d["regime"],
        "daily_trend": d["daily_trend"], "entry": d["entry"], "stop": d["stop"],
        "target": d["target"], "rr": d["rr"], "position_pct": d["position_pct"],
        "narrative": d["narrative"],
    }


def _in_quiet(hour: int, start: int, end: int) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def _should_notify(ts: pd.Timestamp, settings: dict) -> bool:
    return not _in_quiet(ts.hour, settings["quiet_start"], settings["quiet_end"])


def _push_and_store(ts: str, type_: str, message: str, data: dict, notify: bool, when: pd.Timestamp, settings: dict) -> bool:
    storage.add_event(ts, type_, message, data)
    if notify and _should_notify(when, settings):
        push.send_to_all({
            "title": f"OctoTrading · {data.get('symbol', '')}",
            "body": message,
            "url": "/",
            "tag": f"{data.get('symbol', '')}-{type_}",
        })
        return True
    return False


# ---------------------------------------------------------------------------
# Acciones del usuario (desde la app)
# ---------------------------------------------------------------------------
def register_buy(entry_price: float | None = None) -> dict:
    """El usuario confirma que compró. Se crea su posición y su stop."""
    symbol, interval, closed = _analyze_latest()
    row = closed.iloc[-1]
    entry = float(entry_price) if entry_price else float(row["close"])
    atr = float(row["atr14"])

    stop = entry - DEFAULT_CONFIG.risk.atr_stop_mult * atr
    target_atr = entry + DEFAULT_CONFIG.risk.atr_tp_mult * atr
    resistance = float(row["resistance"])
    if row["regime"] == "RANGO" and resistance > entry:
        target = min(target_atr, resistance)
    else:
        target = target_atr

    stop_pct = (entry - stop) / entry
    position_pct = min(1.0, DEFAULT_CONFIG.risk.risk_per_trade / stop_pct) if stop_pct > 0 else 0.0

    pos = Position(
        entry=entry, initial_stop=stop, stop=stop, target=target,
        position_pct=position_pct, entry_time=str(row.name), highest=entry,
    )
    state = storage.get_state()
    storage.save_state(pos.to_dict(), state["last_processed"])
    storage.add_event(
        str(row.name), "OPEN",
        f"Compra registrada a ${entry:,.2f}. Stop en ${stop:,.2f}, objetivo ${target:,.2f}.",
        {"symbol": symbol, "entry": entry, "stop": stop, "target": target},
    )
    return pos.to_dict()


def register_sell() -> dict:
    """El usuario confirma que vendió. Se cierra su posición."""
    state = storage.get_state()
    pos = state["position"]
    if pos:
        storage.add_event(
            str(pd.Timestamp.now(tz="UTC")), "CLOSE",
            f"Venta registrada. Operación cerrada (entrada ${pos['entry']:,.2f}).",
            {"symbol": storage.get_settings()["symbol"], "entry": pos["entry"]},
        )
    storage.save_state(None, state["last_processed"])
    return {"position": None}


# ---------------------------------------------------------------------------
# Ciclo horario
# ---------------------------------------------------------------------------
def run_once(notify: bool = True) -> dict:
    settings = storage.get_settings()
    symbol, interval, closed = _analyze_latest()
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

    index_list = list(closed.index)
    position = state["position"]
    sent = 0

    for ts in new.index:
        i = index_list.index(ts)
        prev_row, row = closed.iloc[i - 1], closed.iloc[i]

        if position is None:
            # Sin compra: buscamos el momento de COMPRAR (transición a señal fuerte).
            is_new_buy = (
                row["signal"] == COMPRA_FUERTE
                and prev_row["signal"] != COMPRA_FUERTE
                and float(row["htf_ctx"]) >= 0
            )
            if is_new_buy:
                msg = (
                    f"Momento de comprar {symbol}: entrada ${row['close']:,.0f} · "
                    f"stop ${row['stop']:,.0f} · objetivo ${row['target']:,.0f}."
                )
                if _push_and_store(str(row.name), "OPEN", msg,
                                   {"symbol": symbol, "price": float(row["close"]),
                                    "stop": float(row["stop"]), "target": float(row["target"])},
                                   notify, row.name, settings):
                    sent += 1

        else:
            # Con compra: buscamos el momento de VENDER.
            pos = Position(**position)
            pos.bars_held += 1
            exit_result = check_exit(pos, prev_row, row, DEFAULT_CONFIG)

            if exit_result and not pos.exit_signaled:
                price, reason = exit_result
                ret = price / pos.entry - 1
                motivo = {"STOP": "tocó el stop",
                          "STOP_DINAMICO_GANANCIA": "stop de ganancia",
                          "SENAL_VENTA": "señal de venta fuerte"}.get(reason, reason)
                msg = f"Vender {symbol} cerca de ${price:,.0f} ({ret * 100:+.1f}%). Motivo: {motivo}."
                pos.exit_signaled = True
                if _push_and_store(str(row.name), "CLOSE", msg,
                                   {"symbol": symbol, "price": price, "return": ret, "reason": reason},
                                   notify, row.name, settings):
                    sent += 1
            elif not pos.exit_signaled:
                if update_trailing_stop(pos, row, DEFAULT_CONFIG):
                    msg = f"Sube tu stop a ${pos.stop:,.0f}. Estás protegiendo ganancia."
                    if _push_and_store(str(row.name), "TRAIL_STOP_SUBIO", msg,
                                       {"symbol": symbol, "new_stop": pos.stop, "price": float(row["close"])},
                                       notify, row.name, settings):
                        sent += 1

            position = pos.to_dict()

        storage.add_report(_report_row(report_from_row(symbol, row)))

    storage.save_state(position, str(new.index[-1]))
    return {"status": "ok", "procesadas": len(new), "avisos": sent,
            "posicion": "abierta" if position else "cerrada"}


if __name__ == "__main__":
    storage.init_db()
    print(run_once(notify=False))
