"""
Experimentos: probar variantes de filtrado y comparar resultados.

Sirve para decidir con datos. NO es la app final; es el laboratorio.
Busca reglas con lógica de mercado (no 'ajustar números hasta que salga bien').
"""

from __future__ import annotations

import pandas as pd

from backtest.backtest import run_backtest, split_periods
from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import COMPRA, COMPRA_FUERTE, ESPERAR, VENTA, VENTA_FUERTE, score_market


def apply_buy_filter(scored: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Convierte en ESPERAR todas las compras donde la máscara es falsa."""
    s = scored.copy()
    is_buy = s["signal"].isin([COMPRA, COMPRA_FUERTE])
    s.loc[is_buy & ~mask, "signal"] = ESPERAR
    return s


def compact_metrics(title: str, scored: pd.DataFrame, **bt_kwargs) -> dict:
    full = run_backtest(scored, **bt_kwargs).metrics()
    _, test = split_periods(scored, 0.7)
    oos = run_backtest(test, **bt_kwargs).metrics()
    return {
        "variante": title,
        "ops": full.get("trades", 0),
        "acierto": full.get("win_rate", 0),
        "PF": full.get("profit_factor", 0),
        "retorno": full.get("total_return", 0),
        "drawdown": full.get("max_drawdown", 0),
        "PF_futuro": oos.get("profit_factor", 0),
        "ret_futuro": oos.get("total_return", 0),
    }


def _print_table(rows: list[dict], titulo: str) -> None:
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    df["acierto"] = (df["acierto"] * 100).round(1)
    df["retorno"] = (df["retorno"] * 100).round(1)
    df["drawdown"] = (df["drawdown"] * 100).round(1)
    df["ret_futuro"] = (df["ret_futuro"] * 100).round(1)
    df["PF"] = df["PF"].round(2)
    df["PF_futuro"] = df["PF_futuro"].round(2)
    print("\n" + "=" * 110)
    print(titulo)
    print("=" * 110)
    print(df.to_string(index=False))


def main() -> None:
    data = fetch_ohlcv("BTCUSDT", "1h", limit=26000)
    features = build_features(data, DEFAULT_CONFIG)
    scored = score_market(features, DEFAULT_CONFIG).dropna(subset=["score"])

    htf_up = scored["htf_ctx"] >= 0
    in_trend = scored["regime"] == "TENDENCIA"
    strong_only = scored["signal"] == COMPRA_FUERTE

    variants = {
        "A. Base (sin filtros)": pd.Series(True, index=scored.index),
        "B. No comprar contra tendencia diaria": htf_up,
        "C. Solo en régimen de tendencia": in_trend,
        "D. Tendencia diaria + régimen tendencia": htf_up & in_trend,
        "E. Solo señales fuertes": strong_only,
        "F. Tendencia diaria + solo fuertes": htf_up & strong_only,
        "G. Tendencia diaria + tendencia + fuertes": htf_up & in_trend & strong_only,
    }

    rows = [compact_metrics(name, apply_buy_filter(scored, mask)) for name, mask in variants.items()]
    _print_table(rows, "PARTE 1 — FILTROS DE ENTRADA  (retorno y acierto en %, drawdown en %)")

    # --- Parte 2: con la mejor entrada (tendencia diaria + solo fuertes),
    # qué regla de salida funciona mejor.
    best = apply_buy_filter(scored, htf_up & strong_only)
    exit_variants = {
        "fixed (stop+objetivo) + salir en VENTA": dict(mode="fixed"),
        "fixed + salir solo en VENTA_FUERTE": dict(mode="fixed", exit_signals=(VENTA_FUERTE,)),
        "trail 3xATR + salir en VENTA_FUERTE": dict(mode="trail", trail_mult=3.0, exit_signals=(VENTA_FUERTE,)),
        "trail 2xATR + salir en VENTA_FUERTE": dict(mode="trail", trail_mult=2.0, exit_signals=(VENTA_FUERTE,)),
        "trail 4xATR + salir en VENTA_FUERTE": dict(mode="trail", trail_mult=4.0, exit_signals=(VENTA_FUERTE,)),
    }
    rows2 = [compact_metrics(name, best, **kw) for name, kw in exit_variants.items()]
    _print_table(rows2, "PARTE 2 — REGLAS DE SALIDA  (entrada fija: tendencia diaria + señal fuerte)")

    print("\nLectura: PF = Profit Factor (>1.3 sano). 'Futuro' = 30% final no visto.")


if __name__ == "__main__":
    main()
