"""
Genera un 'fixture' para verificar que el motor en Kotlin da el mismo resultado
que el motor en Python (la referencia validada).

Escribe:
  android/app/src/test/resources/btc_1h.csv     (velas reales)
  android/app/src/test/resources/expected.properties (resultado esperado)

Nota: se usa una ventana corta (~2000 velas) para que el contexto diario sea 0
en ambas implementaciones y así comparar el núcleo del motor.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import DEFAULT_CONFIG
from engine.data import fetch_ohlcv
from engine.features import build_features
from engine.model import score_market

OUT = Path(__file__).resolve().parent.parent / "android" / "app" / "src" / "test" / "resources"
OUT.mkdir(parents=True, exist_ok=True)

data = fetch_ohlcv("BTCUSDT", "1h", limit=2000)
features = build_features(data, DEFAULT_CONFIG)
scored = score_market(features, DEFAULT_CONFIG)
last = scored.iloc[-1]

# CSV de velas
df = data.reset_index()
df.columns = ["time", "open", "high", "low", "close", "volume"]
df["time"] = (df["time"].astype("int64") // 1_000_000)  # a milisegundos
df.to_csv(OUT / "btc_1h.csv", index=False)

# Resultado esperado (última vela)
expected = {
    "signal": str(last["signal"]),
    "score": f"{float(last['score']):.4f}",
    "atr": f"{float(last['atr14']):.6f}",
    "entry": f"{float(last['entry']):.2f}",
    "stop": f"{float(last['stop']):.2f}",
    "target": f"{float(last['target']):.2f}",
    "rr": f"{float(last['rr']):.4f}",
    "regime": str(last["regime"]),
    "htf_ctx": f"{float(last['htf_ctx']):.1f}",
    "support": f"{float(last['support']):.2f}",
    "resistance": f"{float(last['resistance']):.2f}",
    "trend": f"{float(last['trend']):.4f}",
    "momentum": f"{float(last['momentum']):.4f}",
    "volume": f"{float(last['volume']):.4f}",
    "volatility": f"{float(last['volatility']):.4f}",
    "structure": f"{float(last['structure']):.4f}",
}
with open(OUT / "expected.properties", "w", encoding="utf-8") as f:
    for k, v in expected.items():
        f.write(f"{k}={v}\n")

print(f"Fixture escrito en {OUT}")
print("Esperado:", expected)
