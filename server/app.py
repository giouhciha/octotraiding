"""
Servidor FastAPI de OctoTrading.

- Sirve la app PWA (carpeta web/).
- Expone la API para la app (estado, activos, reportes, ajustes, push).
- Arranca el job de análisis cada hora (APScheduler) y hace un primer ciclo al iniciar.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import assets, job, push, storage

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
scheduler = BackgroundScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    # Primer ciclo en segundo plano (para no bloquear el arranque).
    scheduler.add_job(lambda: job.run_once(notify=True), "cron", minute=1, id="hourly")
    scheduler.start()
    scheduler.add_job(lambda: job.run_once(notify=False), id="startup", replace_existing=True)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="OctoTrading", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Modelos de entrada
# ---------------------------------------------------------------------------
class TrackIn(BaseModel):
    symbol: str
    interval: str | None = None


class SettingsIn(BaseModel):
    capital: float | None = None
    risk_pct: float | None = None
    quiet_start: int | None = None
    quiet_end: int | None = None
    notify_strong_only: int | None = None
    interval: str | None = None


class SubscribeIn(BaseModel):
    endpoint: str
    keys: dict


class BuyIn(BaseModel):
    entry_price: float | None = None


def _compute_action(latest: dict | None, position: dict | None) -> dict:
    """Traduce el estado a una acción clara para el usuario."""
    signal = (latest or {}).get("signal", "")
    if position:
        if position.get("exit_signaled"):
            return {"action": "VENDER", "holding": True, "exit_signaled": True,
                    "hint": "Tienes posición abierta y hay señal de SALIR. Considera vender y confírmalo."}
        if signal in ("VENTA", "VENTA FUERTE"):
            return {"action": "VENDER", "holding": True, "exit_signaled": False,
                    "hint": "Tienes posición abierta y el método pide salir."}
        return {"action": "MANTENER", "holding": True, "exit_signaled": False,
                "hint": "Tienes posición abierta. Mantén según el plan; el stop sube solo."}
    # Sin posición: nos importa CUÁNDO comprar
    if signal == "COMPRA FUERTE":
        return {"action": "COMPRAR", "holding": False, "exit_signaled": False,
                "hint": "No tienes posición y el método marca una oportunidad de COMPRA."}
    if signal == "COMPRA":
        return {"action": "VIGILAR", "holding": False, "exit_signaled": False,
                "hint": "No tienes posición. Señal tibia: aún no es momento claro."}
    return {"action": "ESPERAR", "holding": False, "exit_signaled": False,
            "hint": "No tienes posición. No hay ventaja clara por ahora."}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/state")
def get_state() -> dict:
    settings = storage.get_settings()
    state = storage.get_state()
    latest = storage.latest_report()
    action = _compute_action(latest, state["position"])
    return {
        "settings": settings,
        "position": state["position"],
        "latest": latest,
        "action": action["action"],
        "holding": action["holding"],
        "exit_signaled": action["exit_signaled"],
        "action_hint": action["hint"],
        "intervals": assets.INTERVALS,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/assets")
def list_assets(q: str = "") -> dict:
    return {"assets": assets.search(q), "intervals": assets.INTERVALS}


@app.post("/api/track")
def track(payload: TrackIn) -> dict:
    if not assets.is_valid(payload.symbol):
        raise HTTPException(status_code=400, detail="Activo no soportado")
    fields = {"symbol": payload.symbol}
    if payload.interval:
        fields["interval"] = payload.interval
    settings = storage.update_settings(**fields)
    # Reiniciar seguimiento: nueva línea base para el nuevo activo.
    storage.save_state(None, None)
    job.run_once(notify=False)
    return {"ok": True, "settings": settings}


@app.post("/api/settings")
def update_settings(payload: SettingsIn) -> dict:
    return {"ok": True, "settings": storage.update_settings(**payload.model_dump())}


@app.post("/api/position/buy")
def position_buy(payload: BuyIn) -> dict:
    """El usuario confirma que compró la moneda."""
    position = job.register_buy(payload.entry_price)
    return {"ok": True, "position": position}


@app.post("/api/position/sell")
def position_sell() -> dict:
    """El usuario confirma que vendió la moneda."""
    return {"ok": True, **job.register_sell()}


@app.get("/api/reports")
def reports(limit: int = 48) -> dict:
    return {"reports": storage.recent_reports(limit)}


@app.get("/api/events")
def events(limit: int = 50) -> dict:
    return {"events": storage.recent_events(limit)}


@app.post("/api/push/subscribe")
def subscribe(payload: SubscribeIn) -> dict:
    keys = payload.keys or {}
    if "p256dh" not in keys or "auth" not in keys:
        raise HTTPException(status_code=400, detail="Suscripción inválida")
    storage.add_subscription(payload.endpoint, keys["p256dh"], keys["auth"])
    return {"ok": True}


@app.get("/api/push/public-key")
def push_public_key() -> dict:
    return {"publicKey": push.public_key()}


@app.post("/api/push/test")
def push_test() -> dict:
    sent = push.send_to_all(
        {
            "title": "OctoTrading",
            "body": "Prueba de notificación. ¡Las alertas funcionan!",
            "url": "/",
            "tag": "test",
        }
    )
    return {"ok": True, "sent": sent}


@app.post("/api/run")
def run_now(notify: bool = False) -> dict:
    return job.run_once(notify=notify)


# La app PWA (se monta al final para no tapar la API).
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
