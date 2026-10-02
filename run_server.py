"""
Arranca el servidor de OctoTrading (API + app PWA + job horario).

Uso:
    .\.venv\Scripts\python.exe run_server.py
Luego abre:  http://127.0.0.1:8000
"""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("server.app:app", host="127.0.0.1", port=8000, reload=False)
