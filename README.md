# OctoTrading

App de seguimiento de criptomonedas que analiza un activo cada hora "como un
experto en trading", genera un reporte en lenguaje simple y avisa cuándo comprar
o vender.

> ⚠️ Análisis técnico automatizado. **No es asesoramiento financiero.** No predice
> el futuro. Su valor es la **disciplina y la gestión de riesgo**.

## Estado actual

**Fases 1-2** (motor validado) + **Fase 3**: app **nativa Android** que hace todo
en el teléfono (sin servidor).

- Motor de análisis validado con backtesting, validación cruzada y walk-forward.
- Política de operación compartida entre backtest y app (`engine/policy.py`).
- **App Android nativa** (Kotlin + Compose) con el motor **portado y verificado**
  contra Python; descarga datos de Binance, analiza cada hora y notifica.
  Genera `octotraiding-debug.apk`.
- (Alternativa web PWA en `server/` + `web/`, por si se retoma.)

Docs: [motor](docs/MOTOR_ANALISIS.md) · [resultados](docs/BACKTEST_RESULTS.md) ·
[app nativa](docs/APP_NATIVA.md) · [PWA](docs/APP_PWA.md).

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [`docs/DEFINICION.md`](docs/DEFINICION.md) | Qué es la app, arquitectura, stack, roadmap |
| [`docs/MOTOR_ANALISIS.md`](docs/MOTOR_ANALISIS.md) | Cómo piensa el "experto" |
| [`docs/BACKTEST_RESULTS.md`](docs/BACKTEST_RESULTS.md) | Evidencia y estrategia validada |

## Estructura del código

```
engine/            Motor de análisis (Python, referencia validada)
server/  web/      App web PWA (alternativa; requiere backend)
android/           App Android NATIVA (Kotlin + Compose, todo en el teléfono)
  app/src/main/java/com/octotraiding/app/
    engine/        Motor portado a Kotlin
    data/          Binance API + almacenamiento local
    logic/         Ciclo horario + acciones
    notif/ work/   Notificaciones y job periódico
    ui/            Interfaz (Compose)
backtest/          Simulador histórico
scripts/make_icons.py           Genera el ícono
scripts/make_engine_fixture.py  Fixture para verificar el motor Kotlin
run_backtest.py · validate.py · walk_forward.py · experiments.py
run_server.py      Arranca la app web (alternativa)
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

# 6) Compilar la app Android nativa (APK)
$env:JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME="$env:LOCALAPPDATA\Android\Sdk"
& "$env:USERPROFILE\.gradle\wrapper\dists\gradle-8.13-bin\5xuhj0ry160q40clulazy9h7d\gradle-8.13\bin\gradle.bat" -p android assembleDebug
#   resultado: android/app/build/outputs/apk/debug/app-debug.apk

# (Alternativa web PWA)
.\.venv\Scripts\python.exe run_server.py   # http://127.0.0.1:8000
```

## Próximos pasos

1. Instalar el APK en el teléfono y probarlo.
2. (Opcional) Gráfica de precio y mejoras de interfaz.
3. (Opcional) Servidor + FCM si se necesita máxima fiabilidad de avisos.
4. (Opcional) Firma de release y publicación.
