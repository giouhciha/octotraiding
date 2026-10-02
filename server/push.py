"""
Notificaciones push web (Web Push / VAPID).

Genera (una sola vez) un par de claves VAPID y las guarda en data/. La clave
pública se entrega al navegador para suscribirse; la privada firma los envíos.

Esta es la vía por la que la app PWA recibe avisos de compra/venta.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from pywebpush import WebPushException, webpush
from py_vapid import Vapid

from . import storage

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRIVATE_PEM = DATA_DIR / "vapid_private.pem"
PUBLIC_TXT = DATA_DIR / "vapid_public.txt"

VAPID_SUBJECT = "mailto:admin@octotraiding.app"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def ensure_keys() -> None:
    """Crea el par de claves VAPID si no existe."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if PRIVATE_PEM.exists() and PUBLIC_TXT.exists():
        return
    vapid = Vapid()
    vapid.generate_keys()
    vapid.save_key(str(PRIVATE_PEM))
    # Clave pública en formato base64url (la que usa el navegador).
    from cryptography.hazmat.primitives import serialization

    public_bytes = vapid.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    PUBLIC_TXT.write_text(_b64url(public_bytes), encoding="ascii")


def public_key() -> str:
    ensure_keys()
    return PUBLIC_TXT.read_text(encoding="ascii").strip()


def send_to_all(payload: dict) -> int:
    """Envía una notificación a todas las suscripciones. Devuelve cuántas salieron."""
    ensure_keys()
    sent = 0
    for sub in storage.list_subscriptions():
        info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=info,
                data=json.dumps(payload),
                vapid_private_key=str(PRIVATE_PEM),
                vapid_claims={"sub": VAPID_SUBJECT},
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                storage.remove_subscription(sub["endpoint"])
        except Exception:  # noqa: BLE001
            continue
    return sent


if __name__ == "__main__":
    ensure_keys()
    print("Clave pública VAPID:", public_key())
