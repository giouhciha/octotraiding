"""
Validación cruzada: probar el motor en varios activos y temporalidades.

Si el método es sano, debe funcionar de forma parecida en distintos mercados.
Si solo gana en uno, es frágil (posible sobreajuste).

Uso:
    python validate.py                 # grilla por defecto
"""

from __future__ import annotations

import pandas as pd

from backtest.backtest import run_backtest, split_periods
from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import score_market

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
INTERVALS = {"1h": 26000, "4h": 8000, "1d": 1500}


def evaluate(symbol: str, interval: str, limit: int) -> dict:
    try:
        data = fetch_ohlcv(symbol, interval, limit=limit)
    except Exception as exc:  # noqa: BLE001
        return {"symbol": symbol, "interval": interval, "error": str(exc)[:40]}

    features = build_features(data, DEFAULT_CONFIG)
    scored = score_market(features, DEFAULT_CONFIG).dropna(subset=["score"])
    if len(scored) < 300:
        return {"symbol": symbol, "interval": interval, "error": "datos insuficientes"}

    full = run_backtest(scored, DEFAULT_CONFIG).metrics()
    _, test = split_periods(scored, 0.7)
    oos = run_backtest(test, DEFAULT_CONFIG).metrics()

    return {
        "symbol": symbol,
        "interval": interval,
        "ops": full.get("trades", 0),
        "PF": full.get("profit_factor", 0.0),
        "retorno": full.get("total_return", 0.0),
        "drawdown": full.get("max_drawdown", 0.0),
        "PF_futuro": oos.get("profit_factor", 0.0),
        "ret_futuro": oos.get("total_return", 0.0),
        "buy_hold": full.get("buy_hold_return", 0.0),
    }


def main() -> None:
    rows = []
    for interval, limit in INTERVALS.items():
        for symbol in SYMBOLS:
            print(f"  evaluando {symbol} {interval}...")
            rows.append(evaluate(symbol, interval, limit))

    df = pd.DataFrame(rows)
    if "error" in df.columns:
        errores = df[df["error"].notna()][["symbol", "interval", "error"]]
        if not errores.empty:
            print("\nErrores:")
            print(errores.to_string(index=False))

    for col in ["retorno", "drawdown", "ret_futuro", "buy_hold"]:
        df[col] = (df[col] * 100).round(1)
    df["PF"] = df["PF"].round(2)
    df["PF_futuro"] = df["PF_futuro"].round(2)

    pd.set_option("display.width", 200)
    print("\n" + "=" * 100)
    print("VALIDACIÓN CRUZADA — activos x temporalidades  (%, PF)")
    print("=" * 100)
    print(df.to_string(index=False))

    ok = df[df["PF"].fillna(0) > 1.0]
    validos = df[df["PF"].notna()]
    print(f"\nResumen: {len(ok)} de {len(validos)} combinaciones con Profit Factor > 1.0")
    if len(validos):
        print(f"PF medio: {validos['PF'].mean():.2f}  |  PF futuro medio: {validos['PF_futuro'].mean():.2f}")

    df.to_csv("backtest/out/validacion_cruzada.csv", index=False)


if __name__ == "__main__":
    main()
