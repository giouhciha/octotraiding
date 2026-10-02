"""
Modelo: convierte las features en un SCORE, una SEÑAL y NIVELES de riesgo.

Este es el 'cerebro'. Los números deciden; el texto (LLM) solo explicará después.
Regla de oro: el score va de -10 (muy bajista) a +10 (muy alcista).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DEFAULT_CONFIG, EngineConfig

# Etiquetas de señal (lo que verá el usuario)
COMPRA_FUERTE = "COMPRA_FUERTE"
COMPRA = "COMPRA"
ESPERAR = "ESPERAR"
VENTA = "VENTA"
VENTA_FUERTE = "VENTA_FUERTE"


def _sign(s: pd.Series) -> pd.Series:
    return np.sign(s.fillna(0.0))


def compute_factors(f: pd.DataFrame, cfg: EngineConfig) -> pd.DataFrame:
    """Calcula cada familia de indicadores como un valor entre -1 y +1."""
    out = pd.DataFrame(index=f.index)
    close = f["close"]

    # --- Tendencia: dirección de fondo (4 señales que votan) ---
    out["trend"] = (
        _sign(close - f["ema200"])
        + _sign(f["ema20"] - f["ema50"])
        + _sign(f["macd_hist"])
        + _sign(f["ema50_slope5"])
    ) / 4.0

    # --- Momentum: ganas de moverse. Cambia según el régimen ---
    rsi_norm = ((f["rsi14"] - 50) / 25).clip(-1, 1)
    stoch_norm = ((f["stoch_k"] - 50) / 50).clip(-1, 1)
    macd_mom = _sign(f["macd_hist_slope"])
    momentum_trend = 0.5 * rsi_norm + 0.3 * stoch_norm + 0.2 * macd_mom

    # En rango, la lógica se invierte: sobreventa = oportunidad de compra.
    rsi_rev = ((50 - f["rsi14"]) / 25).clip(-1, 1)
    stoch_rev = ((50 - f["stoch_k"]) / 50).clip(-1, 1)
    momentum_range = 0.5 * rsi_rev + 0.3 * stoch_rev - 0.2 * macd_mom

    out["momentum"] = np.where(
        f["regime"] == "RANGO", momentum_range, momentum_trend
    )

    # --- Volumen: ¿confirma el movimiento? ---
    obv_dir = _sign(f["obv_slope10"])
    confirm = np.where(
        (f["price_change"] > 0) & (f["vol_ratio"] > 1.3), 1.0,
        np.where((f["price_change"] < 0) & (f["vol_ratio"] > 1.3), -1.0, 0.0),
    )
    out["volume"] = 0.6 * obv_dir + 0.4 * confirm

    # --- Volatilidad: dónde está el precio dentro de su zona normal ---
    pctb = f["bb_pctb"].clip(0, 1)
    vol_range = ((0.5 - pctb) * 2).clip(-1, 1)     # barato abajo, caro arriba
    vol_trend = ((pctb - 0.5) * 2).clip(-1, 1)     # en tendencia, arriba manda
    out["volatility"] = np.where(f["regime"] == "RANGO", vol_range, 0.4 * vol_trend)

    # --- Estructura: depende del régimen ---
    # En RANGO: cerca de soporte = bueno comprar; cerca de resistencia = malo.
    # En TENDENCIA: lo que importa es que siga haciendo máximos y mínimos
    #   crecientes (estructura de subida). Estar cerca del máximo NO es malo:
    #   significa fuerza / posible ruptura.
    span = (f["resistance"] - f["support"]).replace(0.0, np.nan)
    range_pos = ((close - f["support"]) / span).clip(0, 1)
    struct_range = ((0.5 - range_pos) * 2).clip(-1, 1)
    near_support = (close - f["support"]) < 1.0 * f["atr14"]
    near_resistance = (f["resistance"] - close) < 1.0 * f["atr14"]
    struct_range = np.where(near_support, np.maximum(struct_range, 0.5), struct_range)
    struct_range = np.where(near_resistance, np.minimum(struct_range, -0.5), struct_range)

    higher_high = (f["resistance"] > f["resistance"].shift(20)).astype(float)
    higher_low = (f["support"] > f["support"].shift(20)).astype(float)
    struct_trend = (higher_high + higher_low) - 1.0          # -1..1
    struct_trend = struct_trend + np.where(close > f["ema50"], 0.3, -0.3)
    struct_trend = np.clip(struct_trend, -1, 1)

    out["structure"] = np.where(
        f["regime"] == "RANGO",
        struct_range,
        np.where(f["regime"] == "TENDENCIA", struct_trend, 0.5 * struct_range + 0.5 * struct_trend),
    )

    return out


def compute_score(factors: pd.DataFrame, cfg: EngineConfig) -> pd.Series:
    """Suma ponderada de los factores -> score de -10 a +10."""
    w = cfg.weights
    score = (
        w.trend * factors["trend"]
        + w.momentum * factors["momentum"]
        + w.volume * factors["volume"]
        + w.volatility * factors["volatility"]
        + w.structure * factors["structure"]
    )
    return score.clip(-10, 10)


def signal_from_score(score: pd.Series, cfg: EngineConfig) -> pd.Series:
    """Traduce el score a una señal legible."""
    t = cfg.thresholds
    sig = pd.Series(ESPERAR, index=score.index, dtype="object")
    sig[score >= t.buy] = COMPRA
    sig[score >= t.strong] = COMPRA_FUERTE
    sig[score <= -t.buy] = VENTA
    sig[score <= -t.strong] = VENTA_FUERTE
    return sig


def compute_levels(f: pd.DataFrame, cfg: EngineConfig) -> pd.DataFrame:
    """
    Calcula entrada, stop loss, objetivo y Riesgo/Beneficio para una COMPRA.
    El stop usa el ATR (margen adaptado a la volatilidad real del activo).
    El objetivo se recorta en la resistencia más cercana: no se compra pegado a un techo.
    """
    r = cfg.risk
    entry = f["close"]
    stop = entry - r.atr_stop_mult * f["atr14"]

    target_atr = entry + r.atr_tp_mult * f["atr14"]
    resistance = f["resistance"]
    # En RANGO el techo frena el objetivo; en TENDENCIA se deja correr
    # (el precio puede romper el máximo, no se recorta la ganancia potencial).
    cap_by_resistance = (f["regime"] == "RANGO") & (resistance > entry)
    target = np.where(cap_by_resistance, np.minimum(target_atr, resistance), target_atr)

    risk_dist = (entry - stop).replace(0.0, np.nan)
    rr = (target - entry) / risk_dist
    stop_pct = risk_dist / entry
    position_pct = (r.risk_per_trade / stop_pct).clip(0, 1)

    return pd.DataFrame(
        {
            "entry": entry,
            "stop": stop,
            "target": target,
            "rr": rr,
            "stop_pct": stop_pct,
            "position_pct": position_pct,
        },
        index=f.index,
    )


def score_market(features: pd.DataFrame, cfg: EngineConfig = DEFAULT_CONFIG) -> pd.DataFrame:
    """
    Pipeline completo: features -> factores -> score -> señal -> niveles.
    Devuelve la tabla 'scored' con todo lo necesario para decidir y notificar.
    """
    factors = compute_factors(features, cfg)
    score = compute_score(factors, cfg)

    # Ajuste por contexto: si el largo plazo contradice, se penaliza.
    htf = features["htf_ctx"]
    score = score.where(~((htf < 0) & (score > 0)), score - cfg.context_penalty)
    score = score.where(~((htf > 0) & (score < 0)), score + cfg.context_penalty)
    score = score.clip(-10, 10)

    signal = signal_from_score(score, cfg)

    # Filtro de pánico: si la volatilidad se dispara, se espera.
    atr_spike = features["atr14"] > cfg.atr_spike_mult * features["atr_ma20"]

    levels = compute_levels(features, cfg)

    # Filtro de R:R: un COMPRA solo vale si el beneficio compensa el riesgo.
    buy_ok = levels["rr"] >= cfg.risk.min_rr
    signal = signal.where(~(signal.isin([COMPRA, COMPRA_FUERTE]) & ~buy_ok), ESPERAR)
    signal = signal.where(~atr_spike, ESPERAR)

    out = features[
        ["close", "open", "high", "low", "atr14", "regime", "htf_ctx", "resistance", "support"]
    ].copy()
    out = out.join(factors)
    out["score"] = score
    out["signal"] = signal
    out = out.join(levels)
    out["atr_spike"] = atr_spike
    return out


if __name__ == "__main__":
    from .data import fetch_ohlcv
    from .features import build_features

    data = fetch_ohlcv("BTCUSDT", "1h", limit=2000)
    feats = build_features(data, DEFAULT_CONFIG)
    scored = score_market(feats)
    print(scored.tail(5)[["close", "score", "signal", "regime", "rr"]])
