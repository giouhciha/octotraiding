"""
Walk-forward: partir el histórico en varios tramos consecutivos y evaluar cada uno.

Sirve para ver si el método gana de forma CONSISTENTE a lo largo del tiempo, o si
todo su resultado viene de un solo tramo afortunado. Un método sano gana en la
mayoría de los tramos, aunque no en todos.

Uso:
    python walk_forward.py BTCUSDT 1h 26000 8
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from backtest.backtest import run_backtest
from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import score_market


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    interval = sys.argv[2] if len(sys.argv) > 2 else "1h"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 26000
    folds = int(sys.argv[4]) if len(sys.argv) > 4 else 8

    data = fetch_ohlcv(symbol, interval, limit=limit)
    features = build_features(data, DEFAULT_CONFIG)
    scored = score_market(features, DEFAULT_CONFIG).dropna(subset=["score"])

    indices = np.array_split(np.arange(len(scored)), folds)
    rows = []
    for k, idx in enumerate(indices, start=1):
        chunk = scored.iloc[idx]
        m = run_backtest(chunk, DEFAULT_CONFIG).metrics()
        rows.append(
            {
                "tramo": k,
                "desde": str(chunk.index[0].date()),
                "hasta": str(chunk.index[-1].date()),
                "ops": m.get("trades", 0),
                "PF": m.get("profit_factor", 0.0),
                "retorno": m.get("total_return", 0.0),
                "drawdown": m.get("max_drawdown", 0.0),
            }
        )

    df = pd.DataFrame(rows)
    df["retorno"] = (df["retorno"] * 100).round(1)
    df["drawdown"] = (df["drawdown"] * 100).round(1)
    df["PF"] = df["PF"].round(2)

    pd.set_option("display.width", 200)
    print("\n" + "=" * 90)
    print(f"WALK-FORWARD — {symbol} {interval} en {folds} tramos consecutivos")
    print("=" * 90)
    print(df.to_string(index=False))

    con_ops = df[df["ops"] > 0]
    positivos = con_ops[con_ops["retorno"] > 0]
    print(
        f"\nTramos con ganancia: {len(positivos)} de {len(con_ops)} "
        f"({len(positivos) / max(len(con_ops), 1) * 100:.0f}%)"
    )
    print(f"PF medio de los tramos: {con_ops['PF'].mean():.2f}")
    print(f"Retorno medio por tramo: {con_ops['retorno'].mean():.1f}%")


if __name__ == "__main__":
    main()
