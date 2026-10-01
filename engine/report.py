"""
Reporte para el usuario: convierte el estado del motor en un mensaje en
lenguaje llano (el 'experto en el bolsillo').

Versión 1: narrativa por plantilla (determinista, gratis, sin IA externa).
Versión futura: la misma estructura JSON se enviará a un LLM para redactar
de forma más natural, pero SIN poder cambiar la señal ni los niveles.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

from .config import DEFAULT_CONFIG, EngineConfig
from .data import fetch_ohlcv
from .features import build_features
from .model import (
    COMPRA,
    COMPRA_FUERTE,
    ESPERAR,
    VENTA,
    VENTA_FUERTE,
    score_market,
)

SIGNAL_PLAIN = {
    COMPRA_FUERTE: "COMPRA FUERTE",
    COMPRA: "COMPRA (moderada)",
    ESPERAR: "ESPERAR / MANTENER",
    VENTA: "VENTA (moderada)",
    VENTA_FUERTE: "VENTA FUERTE",
}

SIGNAL_ACTION = {
    COMPRA_FUERTE: "Comprar",
    COMPRA: "Considerar compra, con cautela",
    ESPERAR: "No hacer nada por ahora",
    VENTA: "Considerar reducir",
    VENTA_FUERTE: "Vender / salir",
}


@dataclass
class Report:
    symbol: str
    time_utc: str
    price: float
    signal: str
    action: str
    score: float
    regime: str
    daily_trend: str
    entry: float
    stop: float
    target: float
    rr: float
    position_pct: float
    narrative: str
    reasons: list[str]
    disclaimer: str = (
        "Análisis técnico automatizado. No es asesoramiento financiero. "
        "Los mercados pueden moverse en contra; nunca arriesgues lo que no puedas perder."
    )

    def to_dict(self) -> dict:
        return asdict(self)


def _explain_factors(row: pd.Series) -> list[str]:
    """Traduce los factores más fuertes a frases simples."""
    reasons: list[str] = []
    if row["trend"] >= 0.5:
        reasons.append("La tendencia de fondo es alcista (precio sobre sus medias).")
    elif row["trend"] <= -0.5:
        reasons.append("La tendencia de fondo es bajista (precio bajo sus medias).")

    if row["momentum"] >= 0.4:
        reasons.append("El impulso apunta al alza.")
    elif row["momentum"] <= -0.4:
        reasons.append("El impulso apunta a la baja.")

    if row["volume"] >= 0.4:
        reasons.append("El volumen está confirmando el movimiento.")
    elif row["volume"] <= -0.4:
        reasons.append("El volumen no respalda el movimiento.")

    if row["regime"] == "TENDENCIA":
        reasons.append("El mercado muestra una tendencia clara.")
    elif row["regime"] == "RANGO":
        reasons.append("El mercado está lateral (sin rumbo marcado).")

    if row["structure"] >= 0.4:
        reasons.append("El precio está en una zona de compra favorable (soporte).")
    elif row["structure"] <= -0.4:
        reasons.append("El precio está pegado a una resistencia: poco margen de subida.")

    if row["htf_ctx"] < 0:
        reasons.append("La tendencia diaria es bajista: conviene prudencia.")
    return reasons


def _build_narrative(row: pd.Series, symbol: str) -> str:
    signal = SIGNAL_PLAIN[row["signal"]]
    price = row["close"]
    parts = [f"{symbol} cotiza a ${price:,.0f}."]
    reasons = _explain_factors(row)
    if reasons:
        parts.append(" ".join(reasons))
    parts.append(f"En conjunto, la lectura del método es: {signal}.")
    if row["signal"] in (COMPRA, COMPRA_FUERTE):
        parts.append(
            f"Si decides entrar, el punto de salida de emergencia está en "
            f"${row['stop']:,.0f} y el riesgo/beneficio es 1 : {row['rr']:.1f}."
        )
    return " ".join(parts)


def latest_report(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    cfg: EngineConfig = DEFAULT_CONFIG,
    limit: int = 2000,
) -> Report:
    data = fetch_ohlcv(symbol, interval, limit=limit)
    features = build_features(data, cfg)
    scored = score_market(features, cfg)
    row = scored.iloc[-1]

    daily = "alcista" if row["htf_ctx"] > 0 else ("bajista" if row["htf_ctx"] < 0 else "neutra")

    return Report(
        symbol=symbol,
        time_utc=str(row.name),
        price=float(row["close"]),
        signal=SIGNAL_PLAIN[row["signal"]],
        action=SIGNAL_ACTION[row["signal"]],
        score=round(float(row["score"]), 2),
        regime=str(row["regime"]),
        daily_trend=daily,
        entry=round(float(row["entry"]), 2),
        stop=round(float(row["stop"]), 2),
        target=round(float(row["target"]), 2),
        rr=round(float(row["rr"]), 2),
        position_pct=round(float(row["position_pct"]), 3),
        narrative=_build_narrative(row, symbol),
        reasons=_explain_factors(row),
    )


if __name__ == "__main__":
    rep = latest_report("BTCUSDT")
    print("=" * 62)
    print(f"  REPORTE — {rep.symbol}   ({rep.time_utc})")
    print("=" * 62)
    print(f"  Precio        : ${rep.price:,.0f}")
    print(f"  Señal         : {rep.signal}   (score {rep.score:+.2f})")
    print(f"  Acción        : {rep.action}")
    print(f"  Régimen       : {rep.regime}   |   Tendencia diaria: {rep.daily_trend}")
    print(f"  Entrada       : ${rep.entry:,.0f}")
    print(f"  Stop loss     : ${rep.stop:,.0f}")
    print(f"  Objetivo      : ${rep.target:,.0f}")
    print(f"  Riesgo/Benef. : 1 : {rep.rr:.2f}")
    print(f"  Posición sug. : {rep.position_pct * 100:.0f}% del capital")
    print("-" * 62)
    print(f"  {rep.narrative}")
    print("-" * 62)
    print(f"  {rep.disclaimer}")
