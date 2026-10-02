# App OctoTrading (PWA) — Fase 3

> Aplicación web instalable (PWA) que muestra el análisis del motor y recibe
> notificaciones de compra/venta. Se instala en Android como una app normal
> (ícono propio) y no requiere tienda de aplicaciones.

Estado: **funcionando en local**. Pendiente: **desplegar en la nube (HTTPS)** para
usarla desde el teléfono y recibir notificaciones reales.

---

## 1. Qué incluye

- **Interfaz móvil** (dark, pensada para el teléfono):
  - Activo seguido, precio, señal, puntuación y explicación en lenguaje llano.
  - Niveles de riesgo (entrada, stop, objetivo, R/B) y tamaño de posición.
  - Contexto (régimen, tendencia diaria, hora de actualización).
  - Historial de reportes y bandeja de alertas.
- **Cambiar activo**: buscador con las principales criptos (Binance USDT).
- **Ajustes**: capital, riesgo por operación, temporalidad y horario de silencio.
- **Notificaciones push** (Web Push) de entradas, subidas de stop y cierres.
- **Instalable**: se añade a la pantalla de inicio con su ícono (pulpo + velas).

---

## 2. Arquitectura

```
┌────────────────────┐      HTTPS      ┌───────────────────────────────┐
│  App PWA (Android) │ ◄─────────────► │  Servidor FastAPI             │
│  - Interfaz        │                 │  - API REST (/api/...)        │
│  - Service Worker  │ ◄── Web Push ── │  - Job horario (APScheduler)  │
│  - Ícono en inicio │                 │  - Motor de análisis          │
└────────────────────┘                 │  - SQLite (datos locales)     │
                                       └───────────────┬───────────────┘
                                                       │
                                          Binance (velas) · VAPID (push)
```

- **Backend:** Python + FastAPI (`server/`).
- **Datos:** SQLite local (`data/octotraiding.db`) — se migrará a la nube.
- **Job horario:** APScheduler ejecuta `job.run_once()` cada hora (:01) y una vez
  al arrancar. Usa **el mismo motor y la misma política** validados en backtesting.
- **Push:** VAPID (`pywebpush`), suscripciones guardadas en la base.

---

## 3. Cómo se instala en Android (cuando esté desplegada)

1. Abrir la URL de la app en **Chrome para Android**.
2. Menú (⋮) → **"Añadir a pantalla de inicio"** / "Instalar app".
3. Queda el ícono de OctoTrading como una app.
4. Dentro, tocar **🔔 Avisos** y aceptar el permiso de notificaciones.

> **Requisito:** Web Push **solo funciona con HTTPS** (o en `localhost`). Por eso
> el despliegue en la nube es el siguiente paso obligatorio.

---

## 4. Cómo correrla en local

```powershell
# Servidor (API + app + job horario)
.\.venv\Scripts\python.exe run_server.py
# Abrir en el navegador del PC:
#   http://127.0.0.1:8000
```

Ejecutar un ciclo de análisis manualmente (para probar sin esperar la hora):

```powershell
.\.venv\Scripts\python.exe -m server.job
# o vía API:
#   POST http://127.0.0.1:8000/api/run
```

---

## 5. API (resumen)

| Método | Ruta | Para qué |
|--------|------|----------|
| GET | `/api/state` | Estado completo (ajustes, posición, último reporte) |
| GET | `/api/assets?q=` | Buscar activos |
| POST | `/api/track` | Cambiar el activo seguido |
| POST | `/api/settings` | Guardar capital, riesgo, temporalidad, silencio |
| POST | `/api/position/buy` | Registrar que el usuario compró |
| POST | `/api/position/sell` | Registrar que el usuario vendió |
| GET | `/api/reports?limit=` | Historial de reportes |
| GET | `/api/events?limit=` | Alertas emitidas |
| GET | `/api/push/public-key` | Clave pública VAPID para suscribirse |
| POST | `/api/push/subscribe` | Registrar el navegador para push |
| POST | `/api/push/test` | Enviar una notificación de prueba |
| POST | `/api/run` | Ejecutar un ciclo de análisis ahora |

---

## 6. Notificaciones y estado del usuario (compra / venta)

La app **pregunta al usuario si tiene la moneda o no**, y cambia el objetivo
según eso:

| Estado del usuario | Qué hace la app | Mensajes |
|--------------------|-----------------|----------|
| **No tiene** (sin posición) | Busca **cuándo comprar** | "Momento de comprar…" (al aparecer COMPRA FUERTE) |
| **Tiene** (posición abierta) | Busca **cuándo vender** | "Sube tu stop…", "Vender…" |

- El usuario confirma con el botón **"Compré"** (registra su compra) y **"Ya vendí"**
  (cierra la posición). También se puede indicar el precio de compra.
- La insignia de acción cambia: **COMPRAR / VIGILAR / ESPERAR** si no tiene;
  **MANTENER / VENDER** si tiene.
- Al registrar una compra, la app calcula su **stop** y **objetivo** y los vigila
  cada hora (stop dinámico).

**Reglas (sin spam):**

| Evento | Cuándo |
|--------|--------|
| `OPEN` (comprar) | Transición a COMPRA FUERTE sin tener posición |
| `TRAIL_STOP_SUBIO` | El stop sube con el precio (tiene posición) |
| `CLOSE` (vender) | Toca el stop o aparece VENTA FUERTE |

Se respeta el **horario de silencio** (por defecto 23:00–07:00). Las horas se
comparan en **UTC** por ahora; se ajustará a la zona horaria del usuario.

---

## 7. Pendiente / limitaciones actuales

- **HTTPS + despliegue**: imprescindible para push en el teléfono.
- **Un solo usuario** (no hay login todavía) — suficiente para el MVP personal.
- **Zona horaria** del silencio está en UTC.
- **Base de datos** local (SQLite); en la nube se usará algo persistente.
- **Reporte con IA (LLM)**: aún es plantilla; se conectará después.

## 8. Siguiente paso

Desplegar en **AWS** con **HTTPS** (dominio) para:
1. Instalar la app en el teléfono.
2. Activar las notificaciones push reales.
3. Programar el job horario en la nube (EventBridge + Lambda o contenedor).
