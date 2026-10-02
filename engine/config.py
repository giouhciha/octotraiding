"""
Parámetros del motor. Aquí está TODO lo ajustable en un solo lugar.

Estos valores son hipótesis de partida (perfil 'moderado'); el backtesting
los validará o los corregirá. No se toca código para ajustarlos: se tocan aquí.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoringWeights:
    """Peso de cada familia de indicadores. Suman 10.0 (score va de -10 a +10)."""

    trend: float = 3.0       # Dirección y fuerza de fondo
    momentum: float = 2.5    # Ganas de moverse (RSI, Stoch, MACD)
    volume: float = 1.5      # ¿El volumen respalda el movimiento?
    volatility: float = 1.5  # Posición dentro de la zona normal + ATR
    structure: float = 1.5   # Cercanía a soportes/resistencias

    def total(self) -> float:
        return self.trend + self.momentum + self.volume + self.volatility + self.structure


@dataclass(frozen=True)
class Thresholds:
    """Umbrales que traducen el score a una señal (perfil moderado)."""

    buy: float = 3.0          # score >= 3  -> COMPRA
    strong: float = 6.0       # score >= 6  -> COMPRA FUERTE
    # Para venta se usan los negativos simétricos.


@dataclass(frozen=True)
class RiskConfig:
    """Gestión de riesgo. Es lo que protege al usuario de una señal equivocada."""

    atr_stop_mult: float = 2.0   # stop inicial = entrada - 2 x ATR (para compras)
    atr_tp_mult: float = 3.0     # objetivo  = entrada + 3 x ATR
    trail_atr_mult: float = 3.0  # stop dinámico: sigue al precio a 3 x ATR
    min_rr: float = 1.5          # no se compra si el Riesgo/Beneficio < 1.5
    risk_per_trade: float = 0.01 # arriesgar 1% del capital por operación


@dataclass(frozen=True)
class RegimeConfig:
    """Cómo se decide si el mercado está en tendencia o lateral."""

    adx_trend: float = 25.0    # ADX >= 25 -> TENDENCIA
    adx_range: float = 20.0    # ADX < 20  -> RANGO


@dataclass(frozen=True)
class PolicyConfig:
    """Cómo se opera: cuándo entrar, cuándo salir, cómo gestionar el stop."""

    entry_signals: tuple[str, ...] = ("COMPRA_FUERTE",)
    exit_signals: tuple[str, ...] = ("VENTA_FUERTE",)
    require_htf_up: bool = True   # no comprar contra la tendencia diaria
    mode: str = "trail"           # 'trail' (stop dinámico) o 'fixed' (objetivo)


@dataclass(frozen=True)
class EngineConfig:
    """Configuración completa del motor."""

    weights: ScoringWeights = field(default_factory=ScoringWeights)
    thresholds: Thresholds = field(default_factory=Thresholds)
    risk: RiskConfig = field(default_factory=RiskConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)

    # Ventana de contexto
    lookback_support: int = 50   # velas para calcular soporte/resistencia
    higher_timeframe: str = "1D" # contexto de largo plazo

    # Filtros de seguridad
    atr_spike_mult: float = 2.5  # si ATR > 2.5x su media -> pánico, se espera
    context_penalty: float = 1.5 # cuánto resta que 1d contradiga a 1h


DEFAULT_CONFIG = EngineConfig()
