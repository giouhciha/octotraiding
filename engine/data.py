"""
Descarga de datos de mercado (velas OHLCV) desde Binance.

Binance es público y gratuito. Descargamos por páginas (su límite es 1000 velas
por petición) y guardamos en caché local para no repetir descargas.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import requests

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data_cache"

# Binance usa sus propios nombres de intervalo.
INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "6h": "6h",
    "12h": "12h", "1d": "1d", "1w": "1w",
}

_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_base", "taker_quote", "ignore",
]


def _fetch_page(symbol: str, interval: str, end_time_ms: int | None, limit: int = 1000) -> list:
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    resp = requests.get(BINANCE_KLINES, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def fetch_ohlcv(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 2000,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Devuelve un DataFrame con columnas: open, high, low, close, volume
    e índice temporal (UTC). Descarga hacia atrás desde ahora.
    """
    if interval not in INTERVAL_MAP:
        raise ValueError(f"Intervalo no soportado: {interval}")

    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{symbol}_{interval}_{limit}.csv"

    if use_cache and cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < 1:  # la caché dura 1 hora
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)

    rows: list = []
    end_time_ms: int | None = None
    remaining = limit

    while remaining > 0:
        page_size = min(1000, remaining)
        page = _fetch_page(symbol, interval, end_time_ms, page_size)
        if not page:
            break
        rows = page + rows
        end_time_ms = page[0][0] - 1  # pedir antes de la primera vela recibida
        remaining -= len(page)
        if len(page) < page_size:
            break
        time.sleep(0.15)  # respetar los límites de Binance

    if not rows:
        raise RuntimeError(f"Binance no devolvió datos para {symbol} {interval}")

    df = pd.DataFrame(rows, columns=_COLUMNS)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("open_time")[["open", "high", "low", "close", "volume"]]
    df = df[~df.index.duplicated(keep="first")].sort_index()

    if use_cache:
        df.to_csv(cache_file)

    return df


if __name__ == "__main__":
    data = fetch_ohlcv("BTCUSDT", "1h", limit=500)
    print(data.tail())
    print(f"\n{len(data)} velas | desde {data.index.min()} hasta {data.index.max()}")
