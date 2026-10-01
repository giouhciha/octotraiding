"""
Construcción de 'features': todas las medidas calculadas para cada vela.

Aquí se juntan los indicadores, se detecta el RÉGIMEN del mercado (tendencia
o lateral) y se añade el contexto de largo plazo (tendencia diaria). El motor
de puntuación (model.py) consume estas columnas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DEFAULT_CONFIG, EngineConfig
from .indicators import adx, atr, bollinger, ema, macd, obv, rsi, stochastic


def _regime(adx_val: pd.Series, close: pd.Series, ema200: pd.Series, cfg: EngineConfig) -> pd.Series:
    """
    Decide el régimen de cada vela:
    - TENDENCIA: hay fuerza (ADX alto) y precio alineado con la media larga.
    - RANGO: poca fuerza (ADX bajo).
    - TRANSICION: zona intermedia.
    """
    r = pd.Series("TRANSICION", index=close.index, dtype="object")
    trending = adx_val >= cfg.regime.adx_trend
    ranging = adx_val < cfg.regime.adx_range
    r[trending] = "TENDENCIA"
    r[ranging] = "RANGO"
    r[adx_val.isna()] = "TRANSICION"
    return r


def _daily_context(df: pd.DataFrame) -> pd.Series:
    """
    Contexto de largo plazo: ¿el precio diario está por encima de su media de 200
    días? +1 = sí (contexto alcista), -1 = no (contexto bajista).
    Se proyecta a cada vela horaria (se usa el último dato diario conocido).
    """
    daily = df["close"].resample("1D").last().dropna()
    if len(daily) < 200:
        return pd.Series(0.0, index=df.index)
    daily_ema200 = ema(daily, 200)
    ctx = np.sign(daily - daily_ema200).fillna(0.0)
    return ctx.reindex(df.index).ffill().fillna(0.0)


def build_features(df: pd.DataFrame, cfg: EngineConfig) -> pd.DataFrame:
    """Devuelve una tabla con todas las features, lista para puntuar."""
    out = pd.DataFrame(index=df.index)
    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]

    # --- Tendencia ---
    out["ema20"] = ema(close, 20)
    out["ema50"] = ema(close, 50)
    out["ema200"] = ema(close, 200)
    out["ema50_slope5"] = out["ema50"] - out["ema50"].shift(5)

    # --- Momentum ---
    out["rsi14"] = rsi(close, 14)
    macd_line, macd_sig, macd_hist = macd(close)
    out["macd"] = macd_line
    out["macd_signal"] = macd_sig
    out["macd_hist"] = macd_hist
    out["macd_hist_slope"] = macd_hist - macd_hist.shift(1)
    out["stoch_k"], out["stoch_d"] = stochastic(high, low, close)

    # --- Volatilidad ---
    out["atr14"] = atr(high, low, close, 14)
    out["atr_ma20"] = out["atr14"].rolling(20).mean()
    bb_mid, bb_up, bb_low = bollinger(close, 20, 2.0)
    out["bb_mid"], out["bb_up"], out["bb_low"] = bb_mid, bb_up, bb_low
    bb_span = (bb_up - bb_low).replace(0.0, np.nan)
    out["bb_pctb"] = (close - bb_low) / bb_span  # 0 = banda inferior, 1 = superior

    # --- Fuerza de tendencia ---
    out["adx14"], out["plus_di"], out["minus_di"] = adx(high, low, close, 14)

    # --- Volumen ---
    out["obv"] = obv(close, vol)
    out["obv_slope10"] = out["obv"] - out["obv"].shift(10)
    out["vol_ma20"] = vol.rolling(20).mean()
    out["vol_ratio"] = vol / out["vol_ma20"].replace(0.0, np.nan)

    # --- Estructura: soporte / resistencia recientes ---
    out["support"] = low.rolling(cfg.lookback_support).min()
    out["resistance"] = high.rolling(cfg.lookback_support).max()

    # --- Precio y cambio ---
    out["open"] = df["open"]
    out["close"] = close
    out["high"] = high
    out["low"] = low
    out["price_change"] = close - close.shift(1)

    # --- Régimen y contexto ---
    out["regime"] = _regime(out["adx14"], close, out["ema200"], cfg)
    out["htf_ctx"] = _daily_context(df)

    return out


if __name__ == "__main__":
    from .data import fetch_ohlcv

    data = fetch_ohlcv("BTCUSDT", "1h", limit=1000)
    feats = build_features(data, DEFAULT_CONFIG)
    print(feats.tail(3)[["close", "rsi14", "adx14", "regime", "htf_ctx"]])
