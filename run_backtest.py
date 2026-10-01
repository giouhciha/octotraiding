"""
Ejecuta el backtest y muestra un informe legible.

Uso:
    python run_backtest.py                     # BTC/USDT, ~3 años (hora)
    python run_backtest.py BTCUSDT 4h 15000    # otro símbolo/intervalo/rango
"""

from __future__ import annotations

import sys

import pandas as pd

from backtest.backtest import run_backtest, split_periods
from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import score_market


def _fmt_pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def _print_metrics(title: str, metrics: dict) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print(f"{'=' * 62}")
    if metrics.get("trades", 0) == 0:
        print("  No se abrieron operaciones en este periodo.")
        return
    print(f"  Operaciones          : {metrics['trades']}")
    print(f"  Tasa de acierto      : {_fmt_pct(metrics['win_rate'])}")
    print(f"  Profit factor        : {metrics['profit_factor']:.2f}   (>1.3 es sano)")
    print(f"  Ganancia media       : {_fmt_pct(metrics['avg_win'])}")
    print(f"  Pérdida media        : {_fmt_pct(metrics['avg_loss'])}")
    print(f"  R medio por operación: {metrics['avg_r']:.2f}   (>0 es rentable)")
    print(f"  Retorno de la cuenta : {_fmt_pct(metrics['total_return'])}")
    print(f"  Comprar y mantener   : {_fmt_pct(metrics['buy_hold_return'])}")
    print(f"  Peor caída (drawdown): {_fmt_pct(metrics['max_drawdown'])}")
    print(f"  Duración media       : {metrics['avg_bars_held']:.1f} velas")


def _trade_breakdown(trades: pd.DataFrame) -> None:
    if trades.empty:
        return
    print("\n  Salidas por motivo:")
    for reason, group in trades.groupby("reason"):
        avg = group["net_return"].mean()
        print(f"    - {reason:<12}: {len(group):>4} ops  |  retorno medio {_fmt_pct(avg)}")


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    interval = sys.argv[2] if len(sys.argv) > 2 else "1h"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 26000

    print(f"Descargando {symbol} en {interval} (hasta {limit} velas)...")
    data = fetch_ohlcv(symbol, interval, limit=limit)
    print(f"Datos: {len(data)} velas | {data.index.min()} -> {data.index.max()}")

    features = build_features(data, DEFAULT_CONFIG)
    scored = score_market(features, DEFAULT_CONFIG)
    scored = scored.dropna(subset=["score"])

    full = run_backtest(scored)
    _print_metrics(f"PERIODO COMPLETO — {symbol} {interval}", full.metrics())
    _trade_breakdown(full.trades)

    train, test = split_periods(scored, 0.7)
    _print_metrics(f"APRENDIZAJE (70% inicial) — {symbol}", run_backtest(train).metrics())
    _print_metrics(f"VALIDACIÓN (30% final, NO VISTO) — {symbol}", run_backtest(test).metrics())

    # Distribución de señales (da una idea de con qué frecuencia avisaría)
    dist = scored["signal"].value_counts()
    print(f"\n{'=' * 62}")
    print("  Distribución de señales (todas las velas analizadas)")
    print(f"{'=' * 62}")
    for sig, count in dist.items():
        print(f"    {sig:<14}: {count:>6}  ({count / len(scored) * 100:.1f}%)")

    out_dir = "backtest/out"
    import os

    os.makedirs(out_dir, exist_ok=True)
    full.trades.to_csv(f"{out_dir}/{symbol}_{interval}_trades.csv", index=False)
    full.equity_curve.to_csv(f"{out_dir}/{symbol}_{interval}_equity.csv")
    print(f"\nDetalle de operaciones guardado en {out_dir}/")


if __name__ == "__main__":
    main()
