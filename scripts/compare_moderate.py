"""
Compara entrar en señales FUERTES vs MODERADAS, con la política validada.

Sirve para responder con datos: ¿conviene comprar en una compra moderada?
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtest.backtest import run_backtest, split_periods
from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import score_market


def evaluate(symbol: str, interval: str, limit: int, entries, label: str) -> None:
    data = fetch_ohlcv(symbol, interval, limit=limit)
    scored = score_market(build_features(data, DEFAULT_CONFIG), DEFAULT_CONFIG).dropna(subset=["score"])
    cfg = replace(
        DEFAULT_CONFIG,
        policy=replace(DEFAULT_CONFIG.policy, entry_signals=entries, require_htf_up=True),
    )
    full = run_backtest(scored, cfg).metrics()
    _, test = split_periods(scored, 0.7)
    oos = run_backtest(test, cfg).metrics()
    print(
        f"  {label:<26} {full.get('trades', 0):>4} ops | "
        f"PF {full.get('profit_factor', 0):.2f} | ret {full.get('total_return', 0) * 100:6.1f}% | "
        f"DD {full.get('max_drawdown', 0) * 100:5.1f}% | futuro PF {oos.get('profit_factor', 0):.2f} "
        f"ret {oos.get('total_return', 0) * 100:6.1f}%"
    )


def main() -> None:
    variantes = [
        (("COMPRA_FUERTE",), "Solo FUERTES (actual)"),
        (("COMPRA", "COMPRA_FUERTE"), "Fuertes + moderadas"),
        (("COMPRA",), "Solo moderadas"),
    ]
    for symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        print(f"\n== {symbol} 1h (3 años) ==")
        for entries, label in variantes:
            evaluate(symbol, "1h", 26000, entries, label)


if __name__ == "__main__":
    main()
