# OctoTrading

App de seguimiento de criptomonedas que analiza un activo cada hora "como un
experto en trading", genera un reporte en lenguaje simple y avisa cuándo comprar
o vender.

> ⚠️ Análisis técnico automatizado. **No es asesoramiento financiero.** No predice
> el futuro. Su valor es la **disciplina y la gestión de riesgo**.

## Estado actual

**Fase 1 y 2 completadas** (motor validado) + **Fase 3 en marcha: la app PWA
funciona en local.**

- Motor de análisis validado con backtesting, validación cruzada y walk-forward.
- Política de operación compartida entre backtest y app (`engine/policy.py`).
- **Servidor** (`server/`): API + job horario + notificaciones push (VAPID).
- **App PWA** (`web/`): interfaz móvil, cambiar activo, ajustes, historial,
  alertas e ícono propio. Instalable en Android.
- Pendiente: **desplegar en la nube (HTTPS)** para usarla en el teléfono.

Resultados: ver [`docs/BACKTEST_RESULTS.md`](docs/BACKTEST_RESULTS.md).
App: ver [`docs/APP_PWA.md`](docs/APP_PWA.md).

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
server/            Servidor (API + job horario + notificaciones)
  app.py           FastAPI (sirve la app y la API)
  job.py           Ciclo de análisis horario
  storage.py       Base de datos local (SQLite)
  push.py          Notificaciones Web Push (VAPID)
  assets.py        Catálogo de activos
web/               App PWA (interfaz móvil)
backtest/          Simulador histórico
scripts/make_icons.py  Genera el ícono
run_backtest.py    Informe de backtest de un activo
validate.py        Validación cruzada (activos x temporalidades)
walk_forward.py    Consistencia por tramos de tiempo
experiments.py     Comparación de variantes (laboratorio)
run_server.py      Arranca la app + servidor
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

# 6) Levantar la app + servidor (PWA)
.\.venv\Scripts\python.exe run_server.py
#   abrir http://127.0.0.1:8000
```

## Próximos pasos

1. Desplegar en la nube (AWS) con HTTPS para usar la app en el teléfono.
2. Reporte con IA (LLM) sobre el JSON estructurado.
3. Activar notificaciones push reales en el dispositivo.
4. Publicación y disclaimers legales.
