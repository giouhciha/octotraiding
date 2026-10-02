# OctoTrading

App de seguimiento de criptomonedas que analiza un activo cada hora "como un
experto en trading", genera un reporte en lenguaje simple y avisa cuándo comprar
o vender.

> ⚠️ Análisis técnico automatizado. **No es asesoramiento financiero.** No predice
> el futuro. Su valor es la **disciplina y la gestión de riesgo**.

## Estado actual

**Fase 1 y Fase 2 completadas — el motor de análisis ("el cerebro") está
construido, validado y con política de operación.**

- Indicadores técnicos (EMA, RSI, MACD, ADX, Bollinger, ATR, Stochastic, OBV).
- Detección de **régimen** (tendencia vs lateral).
- **Score** de −10 a +10 → señal COMPRA / MANTENER / VENDER.
- **Niveles de riesgo** (entrada, stop dinámico, objetivo, R:R, tamaño de posición).
- **Reporte** en lenguaje llano.
- **Backtesting** con 3 años de datos reales (BTC, ETH, SOL, BNB).
- **Validación cruzada** (4 activos × 3 temporalidades) y **walk-forward**.
- **Política de operación** compartida entre backtest y app (`engine/policy.py`).

Resultados: ver [`docs/BACKTEST_RESULTS.md`](docs/BACKTEST_RESULTS.md).

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [`docs/DEFINICION.md`](docs/DEFINICION.md) | Qué es la app, arquitectura, stack, roadmap |
| [`docs/MOTOR_ANALISIS.md`](docs/MOTOR_ANALISIS.md) | Cómo piensa el "experto" |
| [`docs/BACKTEST_RESULTS.md`](docs/BACKTEST_RESULTS.md) | Evidencia y estrategia validada |

## Estructura del código

```
engine/            Motor de análisis
  config.py        Parámetros (pesos, umbrales, riesgo, política) en un solo lugar
  data.py          Descarga de velas desde Binance
  indicators.py    Indicadores técnicos
  features.py      Features + régimen + contexto diario
  model.py         Score, señal y niveles de riesgo
  policy.py        Política de operación (entrada, stop dinámico, salida)
  report.py        Reporte para el usuario (lenguaje llano)
backtest/          Simulador histórico
run_backtest.py    Informe de backtest de un activo
validate.py        Validación cruzada (activos x temporalidades)
walk_forward.py    Consistencia por tramos de tiempo
experiments.py     Comparación de variantes (laboratorio)
```

## Cómo ejecutarlo

```powershell
# 1) Entorno (una sola vez)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2) Reporte actual de BTC
.\.venv\Scripts\python.exe -m engine.report

# 3) Backtest (BTC y ETH, 3 años, velas de 1h)
.\.venv\Scripts\python.exe run_backtest.py BTCUSDT 1h 26000
.\.venv\Scripts\python.exe run_backtest.py ETHUSDT 1h 26000

# 4) Validación cruzada y walk-forward
.\.venv\Scripts\python.exe validate.py
.\.venv\Scripts\python.exe walk_forward.py BTCUSDT 1h 26000 8

# 5) Comparar variantes del motor
.\.venv\Scripts\python.exe experiments.py
```

## Próximos pasos

1. App Android (Flutter) + notificaciones push (FCM).
2. Reporte con IA (LLM) sobre el JSON estructurado.
3. Nube (serverless en AWS) con el job horario.
4. Publicación y disclaimers legales.
