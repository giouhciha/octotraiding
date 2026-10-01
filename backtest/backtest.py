"""
Backtesting: ¿qué habría pasado si usáramos estas señales en el pasado?

Simulación realista (solo largos, spot):
- Se entra en la apertura de la vela SIGUIENTE a la señal (sin mirar el futuro).
- Se sale por stop, por objetivo, o por señal de venta.
- Se descuentan comisiones (0.1% por lado, típico de Binance spot).

Métricas honestas: no basta con 'acertar'; importa el riesgo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from engine.model import COMPRA_FUERTE, VENTA_FUERTE

FEE_PER_SIDE = 0.001  # 0.1%


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.Series
    start_price: float
    end_price: float

    @property
    def buy_hold_return(self) -> float:
        return self.end_price / self.start_price - 1

    def metrics(self) -> dict:
        if self.trades.empty:
            return {"trades": 0}
        t = self.trades
        wins = t[t["net_return"] > 0]["net_return"]
        losses = t[t["net_return"] <= 0]["net_return"]
        gross_win = wins.sum()
        gross_loss = abs(losses.sum())
        drawdown = self._max_drawdown(self.equity_curve)

        return {
            "trades": int(len(t)),
            "win_rate": len(wins) / len(t),
            "total_return": float(self.equity_curve.iloc[-1] - 1),
            "buy_hold_return": float(self.buy_hold_return),
            "profit_factor": float(gross_win / gross_loss) if gross_loss > 0 else float("inf"),
            "avg_win": float(wins.mean()) if len(wins) else 0.0,
            "avg_loss": float(losses.mean()) if len(losses) else 0.0,
            "avg_r": float(t["r_multiple"].mean()),
            "expectancy": float(t["net_return"].mean()),
            "max_drawdown": float(drawdown),
            "avg_bars_held": float(t["bars_held"].mean()),
        }

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        return abs(drawdown.min())


def run_backtest(
    scored: pd.DataFrame,
    fee: float = FEE_PER_SIDE,
    exit_signals: tuple[str, ...] = (VENTA_FUERTE,),
    mode: str = "trail",
    trail_mult: float = 3.0,
    entry_signals: tuple[str, ...] = (COMPRA_FUERTE,),
    require_htf_up: bool = True,
) -> BacktestResult:
    """
    Recorre las velas y simula las operaciones.

    Estrategia validada por backtesting (perfil moderado):
    - Entrar solo con señal FUERTE de compra, y solo si la tendencia diaria no
      es bajista (no se compra 'contra corriente').
    - Salir con stop dinámico que sube con el precio, o con señal de venta fuerte.

    mode='fixed' : sale por stop, por objetivo o por señal de venta.
    mode='trail' : stop dinámico que sube con el precio (deja correr ganancias).
    """
    trades: list[dict] = []
    position = None
    equity = 1.0
    equity_points = []

    for i in range(1, len(scored)):
        row = scored.iloc[i]
        prev = scored.iloc[i - 1]

        if position is None:
            # Entrar en la apertura de esta vela si la vela ANTERIOR cumplió.
            htf_ok = (not require_htf_up) or float(prev["htf_ctx"]) >= 0
            if prev["signal"] in entry_signals and htf_ok:
                entry = float(row["open"])
                stop = float(prev["stop"])
                target = float(prev["target"])
                if np.isfinite(entry) and np.isfinite(stop) and np.isfinite(target):
                    if stop < entry and (mode == "trail" or entry < target):
                        position = {
                            "entry_time": row.name,
                            "entry": entry,
                            "stop": stop,
                            "initial_stop": stop,
                            "target": target,
                            "position_pct": float(prev["position_pct"]),
                            "bars": 0,
                            "high_since": entry,
                        }
        else:
            position["bars"] += 1
            exit_price, reason = None, None

            # 1) Señal de venta en la vela anterior -> salir en la apertura.
            if prev["signal"] in exit_signals:
                exit_price, reason = float(row["open"]), "SENAL_VENTA"
            # 2) Stop (con el valor vigente ANTES de actualizarlo con esta vela).
            elif float(row["low"]) <= position["stop"]:
                exit_price = position["stop"]
                if mode == "trail" and exit_price > position["entry"]:
                    reason = "STOP_DINAMICO_GANANCIA"
                else:
                    reason = "STOP"
            # 3) Objetivo (solo en modo 'fixed').
            elif mode == "fixed" and float(row["high"]) >= position["target"]:
                exit_price, reason = position["target"], "OBJETIVO"

            if exit_price is not None:
                gross = exit_price / position["entry"] - 1
                net = gross - 2 * fee
                risk = position["entry"] - position["initial_stop"]
                r_mult = (exit_price - position["entry"]) / risk if risk > 0 else 0.0
                equity *= 1 + position["position_pct"] * net
                trades.append(
                    {
                        "entry_time": position["entry_time"],
                        "exit_time": row.name,
                        "entry": position["entry"],
                        "exit": exit_price,
                        "reason": reason,
                        "gross_return": gross,
                        "net_return": net,
                        "r_multiple": r_mult,
                        "bars_held": position["bars"],
                    }
                )
                position = None
            else:
                # Actualizar stop dinámico SOLO al final de la vela (sin mirar el futuro).
                position["high_since"] = max(position["high_since"], float(row["high"]))
                if mode == "trail":
                    atr = float(row["atr14"])
                    if np.isfinite(atr):
                        new_stop = position["high_since"] - trail_mult * atr
                        position["stop"] = max(position["stop"], new_stop)

        equity_points.append((row.name, equity))

    equity_curve = pd.Series(
        [p[1] for p in equity_points],
        index=[p[0] for p in equity_points],
        name="equity",
    )
    trades_df = pd.DataFrame(trades)
    return BacktestResult(
        trades=trades_df,
        equity_curve=equity_curve,
        start_price=float(scored["close"].iloc[0]),
        end_price=float(scored["close"].iloc[-1]),
    )


def split_periods(scored: pd.DataFrame, train_frac: float = 0.7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide el histórico en 'aprendizaje' (pasado) y 'validación' (futuro, no visto)."""
    cut = int(len(scored) * train_frac)
    return scored.iloc[:cut], scored.iloc[cut:]
