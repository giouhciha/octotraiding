"""
Backtesting: ¿qué habría pasado si usáramos estas señales en el pasado?

Simulación realista (solo largos, spot):
- Se entra en la apertura de la vela SIGUIENTE a la señal (sin mirar el futuro).
- Se sale por stop, por objetivo, o por señal de venta.
- Se descuentan comisiones (0.1% por lado, típico de Binance spot).

Métricas honestas: no basta con 'acertar'; importa el riesgo.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from engine.config import DEFAULT_CONFIG, EngineConfig
from engine.policy import step

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
    cfg: EngineConfig = DEFAULT_CONFIG,
    fee: float = FEE_PER_SIDE,
) -> BacktestResult:
    """
    Simula el histórico usando EXACTAMENTE la misma política que la app en vivo
    (engine.policy.step). Así el backtest y la producción no se pueden separar.
    """
    trades: list[dict] = []
    position = None
    equity = 1.0
    equity_points = []

    for i in range(1, len(scored)):
        row = scored.iloc[i]
        prev = scored.iloc[i - 1]

        closed = position
        new_position, events = step(prev, row, position, cfg)

        for ev in events:
            if ev["type"] == "CLOSE" and closed is not None:
                net = ev["return"] - 2 * fee
                risk = closed.entry - closed.initial_stop
                r_mult = (ev["price"] - closed.entry) / risk if risk > 0 else 0.0
                equity *= 1 + closed.position_pct * net
                trades.append(
                    {
                        "entry_time": closed.entry_time,
                        "exit_time": ev["time"],
                        "entry": closed.entry,
                        "exit": ev["price"],
                        "reason": ev["reason"],
                        "gross_return": ev["return"],
                        "net_return": net,
                        "r_multiple": r_mult,
                        "bars_held": closed.bars_held,
                    }
                )

        position = new_position
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
