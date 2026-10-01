"""
Indicadores técnicos estándar, calculados con pandas/numpy.

Todos son "causales": el valor en la hora X usa SOLO información hasta esa hora.
Esto es imprescindible para que el backtest no haga trampa (mirar el futuro).

Cada indicador se explica en una línea en lenguaje llano, porque el usuario
final no es experto y la app debe poder explicarse.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Medias móviles
# ---------------------------------------------------------------------------
def ema(series: pd.Series, span: int) -> pd.Series:
    """Media móvil exponencial: promedio que da más peso a lo reciente."""
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """Media móvil simple: promedio de las últimas `window` velas."""
    return series.rolling(window).mean()


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------
def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI: mide si el activo está 'caro' (cerca de 100) o 'barato' (cerca de 0).
    Por encima de 70 = sobrecompra; por debajo de 30 = sobreventa.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100 - (100 / (1 + rs))
    # Si no hubo pérdidas en la ventana, el RSI es 100 (todo subidas).
    return out.fillna(100.0).where(avg_gain.notna(), np.nan)


def macd(
    close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD: compara dos medias (rápida y lenta) para detectar cambios de impulso.
    - macd: la diferencia de medias.
    - signal: media del macd.
    - hist: macd - signal (si es positivo, el impulso es alcista).
    """
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k: int = 14,
    slowing: int = 3,
    d: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """
    Stochastic: ubicación del precio dentro del rango reciente (0-100).
    %K > 80 = sobrecompra; %K < 20 = sobreventa. %D es su media (más suave).
    """
    lowest = low.rolling(k).min()
    highest = high.rolling(k).max()
    span = (highest - lowest).replace(0.0, np.nan)
    raw_k = 100 * (close - lowest) / span
    slow_k = raw_k.rolling(slowing).mean()
    slow_d = slow_k.rolling(d).mean()
    return slow_k, slow_d


# ---------------------------------------------------------------------------
# Volatilidad
# ---------------------------------------------------------------------------
def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    ATR: cuánto se mueve el precio, en promedio, en una vela.
    Es la base para calcular el stop loss (cuánto margen de error hay).
    """
    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def bollinger(
    close: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bandas de Bollinger: una 'zona normal' alrededor del precio.
    Si el precio toca la banda inferior suele estar barato; la superior, caro.
    """
    mid = sma(close, window)
    std = close.rolling(window).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower


# ---------------------------------------------------------------------------
# Fuerza de tendencia
# ---------------------------------------------------------------------------
def adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    ADX: mide la FUERZA de la tendencia (no la dirección).
    - ADX >= 25 -> hay tendencia clara.
    - ADX < 20  -> mercado lateral (sin rumbo).
    +DI y -DI indican la dirección (alcista / bajista).
    """
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    atr_s = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_dm_s = pd.Series(plus_dm, index=high.index).ewm(
        alpha=1 / period, adjust=False, min_periods=period
    ).mean()
    minus_dm_s = pd.Series(minus_dm, index=high.index).ewm(
        alpha=1 / period, adjust=False, min_periods=period
    ).mean()

    plus_di = 100 * plus_dm_s / atr_s.replace(0.0, np.nan)
    minus_di = 100 * minus_dm_s / atr_s.replace(0.0, np.nan)

    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx_s = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return adx_s, plus_di, minus_di


# ---------------------------------------------------------------------------
# Volumen
# ---------------------------------------------------------------------------
def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    OBV (On-Balance Volume): acumula volumen según si el precio sube o baja.
    Si sube, el volumen está respaldando la subida (señal sana).
    """
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).cumsum()
