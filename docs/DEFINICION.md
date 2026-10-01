# OctoTrading — Definición del producto

> App Android que sigue un activo (crypto en el MVP), lo analiza cada hora
> "como un experto en trading", genera un reporte y notifica cuándo comprar o vender.

Estado: **Definición funcional / técnica (pre-código)**
Fecha: 2026-10-01

---

## 1. Objetivo

1. El usuario selecciona **una crypto** a seguir (cambiable en cualquier momento).
2. Cada hora, el sistema analiza el comportamiento del activo con indicadores
   técnicos, genera un **score de señal** y un **reporte en lenguaje natural**.
3. El sistema **notifica** (push) cuando conviene **comprar** o **vender**.

No es una app de ejecución de órdenes en el MVP: es **seguimiento + señales**.
(La ejecución automática de compra/venta queda como fase futura y requiere
exchange + API keys + consideraciones legales.)

---

## 2. Alcance del MVP

| # | Feature | En MVP |
|---|---------|--------|
| 1 | Elegir 1 activo crypto y persistirlo | ✅ |
| 2 | Precio actual + gráfica básica | ✅ |
| 3 | Análisis automático cada 1 hora | ✅ |
| 4 | Score + señal (BUY / SELL / HOLD) | ✅ |
| 5 | Notificación push al cambiar de señal | ✅ |
| 6 | Reporte en lenguaje natural (IA) | ✅ |
| 7 | Historial de reportes | ✅ |
| 8 | Watchlist multi-activo | ⏳ v2 |
| 9 | Backtesting de la estrategia | ⏳ v2 |
| 10 | Acciones / bolsa | ⏳ v2 |
| 11 | Ejecución real de órdenes | ⏳ v3 |

---

## 3. Arquitectura

```
┌─────────────────┐      ┌───────────────────────────────┐      ┌──────────────┐
│  App Android    │◄────►│  Backend (Python/FastAPI)      │◄────►│  Exchange API │
│  (Flutter)      │ REST │                               │ ccxt │  (Binance)    │
│                 │      │  ┌─────────────────────────┐  │      └──────────────┘
│  - Elegir activo│      │  │ Cron cada hora           │  │
│  - Ver reporte  │      │  │  1. Trae velas (OHLCV)   │  │      ┌──────────────┐
│  - Push (FCM)   │      │  │  2. Calcula indicadores  │  │      │  LLM API      │
└─────────────────┘      │  │  3. Score + niveles      │  │─────►│ (OpenAI/Claude│
        ▲                │  │  4. Genera reporte IA    │  │      │  /Gemini)     │
        │ FCM            │  │  5. Guarda + notifica    │  │      └──────────────┘
        └────────────────│  └─────────────────────────┘  │
                         │  PostgreSQL                       │
                         └───────────────────────────────┘
                                 ▲
                          Firebase Cloud Messaging
```

**Decisión clave:** el análisis corre en el **backend**, no en el teléfono.
Motivos: puntualidad horaria (Android retrasa tareas en background), seguridad
(API keys fuera del dispositivo) y batería.

---

## 4. Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| App | Flutter + Dart |
| Estado (app) | Riverpod |
| Gráficas | fl_chart |
| Push app | firebase_messaging + flutter_local_notifications |
| HTTP app | dio |
| Backend | Python 3.12 + FastAPI + Uvicorn |
| Datos mercado | ccxt (Binance público) |
| Indicadores | pandas + `ta` |
| Backtesting (v2) | backtesting.py |
| Base de datos | PostgreSQL (Supabase / Neon) |
| ORM | SQLAlchemy + Alembic (migraciones) |
| Scheduler | APScheduler o cron del hosting |
| IA | API de LLM (OpenAI / Anthropic / Google) |
| Push backend | firebase-admin (FCM) |
| Auth | Firebase Auth |
| Hosting | Railway / Render / Fly.io (Docker) |

---

## 5. Motor de análisis "experto"

> 📄 **Detalle completo en [`docs/MOTOR_ANALISIS.md`](./MOTOR_ANALISIS.md).**
> Esa es la parte central del proyecto: de ahí salen las recomendaciones.
> Aquí solo va el resumen.

### 5.1 Datos
- Velas OHLCV en **3 temporalidades**: 1h (principal), 4h y 1d (contexto).
- Se descargan ~200 velas por temporalidad.

### 5.2 Indicadores calculados
| Categoría | Indicadores |
|-----------|-------------|
| Tendencia | EMA 20/50/200, MACD (12,26,9), ADX |
| Momentum | RSI(14), Stochastic (14,3,3) |
| Volatilidad | Bandas de Bollinger (20,2), ATR(14) |
| Volumen | OBV, media de volumen (20), picos de volumen |
| Niveles | Soporte/resistencia por pivotes y máximos/mínimos recientes |

### 5.3 Score de señal (-10 a +10)
Cada familia vota con un peso. Ejemplo de pesos iniciales:

| Familia | Rango | Ejemplo de reglas |
|---------|-------|-------------------|
| Tendencia | ±3 | Precio > EMA200 (+1), EMA20 > EMA50 (+1), MACD cruce alcista (+1) |
| Momentum | ±3 | RSI < 30 (+2), RSI > 70 (−2), Stoch cruce alcista (+1) |
| Volatilidad | ±2 | Precio en banda inferior (+1), ATR expandiéndose (−) |
| Volumen | ±2 | OBV subiendo (+1), pico de volumen con vela alcista (+1) |

**Regla de oro: los pesos son configurables y hay que backtestearlos**, no
creerlos a ciegas. El score es una heurística, no una verdad.

### 5.4 Interpretación del score
| Score | Señal |
|-------|-------|
| ≥ +6 | COMPRA FUERTE |
| +3 a +5 | COMPRA |
| −2 a +2 | NEUTRO / ESPERAR |
| −5 a −3 | VENTA |
| ≤ −6 | VENTA FUERTE |

> Nota de diseño: los umbrales y pesos se ajustarán con backtesting (v2).

### 5.5 Niveles sugeridos
- **Zona de entrada**: calculada desde soportes y ATR.
- **Stop loss**: entrada − k·ATR (ej. k=2).
- **Take profit**: entrada + m·ATR (ej. m=3), o resistencia próxima.
- **Ratio riesgo/beneficio** mostrado siempre.

### 5.6 Reporte con IA
Se envía al LLM un JSON estructurado (precio, indicadores, score, niveles) y
este devuelve 3–5 frases tipo analista:

> *"BTC/USDT cotiza a $61.450. El RSI en 28.4 indica sobreventa y el precio
> toca la banda inferior de Bollinger ($60.900). El soporte clave está en
> $60.200 y el stop sugerido en $59.800 (riesgo 1.6%). El volumen no confirma
> aún, por lo que se recomienda entrada escalonada. Señal: COMPRA moderada."*

Reglas del prompt: **nunca prometer rentabilidad**, siempre indicar el riesgo,
y aclarar que no es asesoría financiera.

---

## 6. Reglas de notificación (anti-spam)

Notificar **solo** cuando:
1. La señal **cambia de estado** (NEUTRO → COMPRA, etc.), o
2. El score **cruza un umbral extremo** (±6), o
3. Se **activa un stop / se alcanza el take profit** de una señal previa.

Límites:
- Máximo 1 notificación por activo por hora.
- Silencio configurable (horario nocturno).
- Si no hay cambio, **no se notifica** (aunque se guarde el reporte).

Esto es vital: si se notifica cada hora sin cambios, el usuario desinstala.

---

## 7. Modelo de datos (borrador)

```sql
users (
  id uuid pk,
  email text,
  created_at timestamptz
)

devices (
  id uuid pk,
  user_id uuid fk,
  fcm_token text,
  platform text,        -- 'android'
  created_at timestamptz
)

tracked_assets (
  id uuid pk,
  user_id uuid fk,
  symbol text,          -- 'BTC/USDT'
  exchange text,        -- 'binance'
  timeframe text,       -- '1h'
  active bool,
  updated_at timestamptz
)

reports (
  id uuid pk,
  user_id uuid fk,
  symbol text,
  price numeric,
  score int,
  signal text,          -- 'COMPRA_FUERTE' | ...
  indicators jsonb,
  levels jsonb,         -- entrada, stop, take profit, R:R
  narrative text,       -- reporte IA
  created_at timestamptz
)

signals_history (
  id uuid pk,
  report_id uuid fk,
  previous_signal text,
  new_signal text,
  notified bool,
  created_at timestamptz
)
```

---

## 8. API REST (borrador)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/login` | Login Firebase (o anónimo) |
| GET | `/assets/search?q=btc` | Buscar crypto |
| GET | `/me/tracking` | Activo(s) seguido(s) |
| PUT | `/me/tracking` | Cambiar activo seguido |
| GET | `/me/reports?limit=48` | Historial de reportes |
| GET | `/reports/latest/{symbol}` | Último reporte de un activo |
| POST | `/me/devices` | Registrar token FCM |
| DELETE | `/me/devices/{id}` | Desregistrar token |

El **cron interno** (no expuesto) ejecuta el pipeline de análisis cada hora.

---

## 9. Flujo de usuario

1. Abre la app → login (anónimo o email).
2. Busca y selecciona una crypto (ej. BTC/USDT).
3. Ve el precio actual, la gráfica y el **último reporte**.
4. Cada hora el backend analiza y, si hay cambio relevante, llega la **push**.
5. Al tocar la notificación → se abre el reporte correspondiente.
6. Puede consultar el **historial** de reportes y señales.

---

## 10. Roadmap por fases

| Fase | Entregable |
|------|-----------|
| **0** | Repo, esqueleto backend, obtener precio de BTC con ccxt |
| **1** | Pipeline de indicadores + score (validado en notebook) |
| **2** | Job horario, persistencia de reportes en Postgres |
| **3** | App Flutter: login, elegir activo, ver reporte |
| **4** | FCM + notificaciones locales + deep link |
| **5** | Reporte con IA (LLM) |
| **6** | (v2) Backtesting, watchlist multi-activo |
| **7** | (v2) Publicación en Play Store + disclaimers |

---

## 11. Riesgos y advertencias

- **No es asesoría financiera.** Toda salida debe incluir disclaimer.
- **Google Play** es estricto con apps financieras: prohibido prometer
  rentabilidad o dar consejos de inversión. Comunicar como "herramienta
  educativa de análisis técnico".
- **APIs de mercado**: Binance público es fiable; los límites de tasa hay que
  respetarlos. Para acciones se necesitará API de pago.
- **LLM**: costo por uso y posible latencia; cachear/limitar.
- **Seguridad**: API keys solo en el backend; nunca en la app.
- **Backtesting obligatorio** antes de confiar en los pesos del score.

---

## 12. Costos estimados (inicio)

| Servicio | Plan inicial |
|----------|--------------|
| Backend hosting | Free tier (Railway/Render) o ~$5/mes |
| PostgreSQL | Free tier (Supabase/Neon) |
| Firebase (FCM/Auth) | Gratis |
| LLM | Pago por uso (~centavos por reporte) |
| ccxt / datos crypto | Gratis |
