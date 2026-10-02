# App nativa Android — OctoTrading

> App Android escrita en **Kotlin (Jetpack Compose)** que hace **todo en el
> teléfono**: descarga los datos, analiza con el mismo motor validado y muestra
> las notificaciones. **Sin servidor, sin AWS, sin dominio.** Costo: $0.

Estado: **compila y genera APK** (`octotraiding-debug.apk`).

---

## 1. Qué hace

- Elige un activo (30 criptos) y una temporalidad (1h / 4h / 1d).
- Cada hora revisa el mercado **en el propio teléfono**.
- Muestra: precio, señal, puntuación, narrativa y niveles (entrada, stop, objetivo, R/B).
- El usuario dice **"Compré"** / **"Ya vendí"**, y la app cambia sus avisos:
  - **Sin posición** → busca **cuándo comprar**.
  - **Con posición** → vigila el **stop dinámico** y avisa **cuándo vender**.
- Notificaciones locales de: oportunidad de compra, subida de stop y venta.

---

## 2. Arquitectura (todo local)

```
┌──────────────────────────── App Android ────────────────────────────┐
│  UI (Compose)                                                       │
│  ViewModel ── Refresh / Compré / Ya vendí / Ajustes                 │
│  Monitor.runOnce()  ── orquesta el ciclo                            │
│     ├─ BinanceApi   → velas (1h + 1d)                               │
│     ├─ Engine       → indicadores, score, señal, niveles            │
│     ├─ Policy       → entrada, stop dinámico, salida                │
│     ├─ Store        → SharedPreferences (ajustes, posición, historial)│
│     └─ Notifier     → notificaciones locales                        │
│  WorkManager        → dispara el ciclo cada hora                    │
└─────────────────────────────────────────────────────────────────────┘
```

- **Sin backend.** La app habla directo con la API pública de Binance.
- **Motor portado** de Python a Kotlin (`engine/`), verificado contra la
  referencia (ver §4).

---

## 3. Estructura del código

```
android/app/src/main/java/com/octotraiding/app/
  MainActivity.kt          Pantalla (permiso de notificaciones, agenda el job)
  engine/
    Indicators.kt          EMA, RSI, MACD, ATR, ADX, Bollinger, Stochastic, OBV
    Config.kt              Pesos, umbrales y riesgo (igual que Python)
    Engine.kt              Features + score + señal + niveles
    Policy.kt              Posición, stop dinámico, entrada/salida
  data/
    BinanceApi.kt          Descarga de velas (HTTP)
    Store.kt               Almacenamiento local (SharedPreferences)
    Models.kt / Assets.kt  Modelos y catálogo de activos
  logic/
    Monitor.kt             Ciclo horario + acciones Compré/Ya vendí
    ReportText.kt          Narrativa en lenguaje llano
  notif/Notifier.kt        Notificaciones
  work/MonitorWorker.kt    Job periódico (WorkManager)
  ui/App.kt, AppViewModel.kt   Interfaz (Compose)
```

---

## 4. Verificación: ¿el motor del teléfono da lo mismo que el de Python?

Sí. Se genera un "fixture" con datos reales (`scripts/make_engine_fixture.py`)
y un **test** compara ambos motores:

```
Kotlin   -> signal=COMPRA score=4.60654
Python   -> signal=COMPRA score=4.6065
```

Test: `EngineParityTest`. Ejecutar con:

```powershell
$env:JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"
& "$env:USERPROFILE\.gradle\wrapper\dists\gradle-8.13-bin\5xuhj0ry160q40clulazy9h7d\gradle-8.13\bin\gradle.bat" `
   -p android testDebugUnitTest --tests "com.octotraiding.app.EngineParityTest"
```

---

## 5. Cómo compilar el APK

```powershell
$env:JAVA_HOME="C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME="$env:LOCALAPPDATA\Android\Sdk"
& "$env:USERPROFILE\.gradle\wrapper\dists\gradle-8.13-bin\5xuhj0ry160q40clulazy9h7d\gradle-8.13\bin\gradle.bat" `
   -p android assembleDebug
```

Resultado: `android/app/build/outputs/apk/debug/app-debug.apk`
(también copiado a `octotraiding-debug.apk` en la raíz del proyecto).

---

## 6. Cómo instalarlo en el teléfono

1. Pasa el archivo `octotraiding-debug.apk` al teléfono (USB, Google Drive, etc.).
2. En el teléfono, ábrelo. Android pedirá permitir "instalar apps de orígenes
   desconocidos" → **Permitir**.
3. Instalar → abrir. Acepta el permiso de **notificaciones**.
4. (Recomendado) En Ajustes de Android → Batería → **excluir OctoTrading de la
   optimización de batería**, para que los avisos lleguen puntuales.
5. En la app, deja el activo que quieras (por defecto BTC) y toca **"Compré"**
   si ya tienes la moneda.

> El APK de depuración (debug) sirve para uso personal. Para publicar en Play
> Store habría que firmarlo en "release" y generar un AAB.

---

## 7. Fiabilidad de las notificaciones (importante)

Como todo corre en el teléfono, Android puede **retrasar** las tareas de fondo
para ahorrar batería. Mitigaciones incluidas y recomendadas:

- **Alarma exacta** (`AlarmManager.setExactAndAllowWhileIdle`) cada hora a los
  ~2 minutos. Es el disparador principal.
- **WorkManager** periódico (cada hora) como respaldo.
- Al abrir la app, se ejecuta un ciclo inmediato.
- **Exclusión de optimización de batería**: se pide la primera vez y hay un botón
  en **Ajustes → "Mejorar fiabilidad de avisos"**.
- Reprogramación al **reiniciar** el teléfono (`BootReceiver`).

> Aun así, si el teléfono está apagado, en modo avión o sin internet, no hay
> revisión en ese rato. Y algunos fabricantes muy agresivos pueden limitarlo:
> si notas retrasos, revisa que la app tenga permiso de "inicio automático".
>
> La solución 100% garantizada es mover el análisis a un **servidor + push (FCM)**.
> Todo el motor ya está listo para reutilizarse.

---

## 8. Limitaciones actuales

- Notificaciones locales (dependen del teléfono), no push de servidor.
- Una sola cuenta/dispositivo (sin login).
- El APK es de **depuración** (no para Play Store todavía).
- Sin gráficas por ahora (solo textos y niveles).

## 9. Próximos pasos

1. Instalar y probar en el teléfono (feedback de UX).
2. (Opcional) Gráfica de precio.
3. (Opcional) Servidor + FCM si se necesita máxima fiabilidad.
4. (Opcional) Firma de release y publicación.
