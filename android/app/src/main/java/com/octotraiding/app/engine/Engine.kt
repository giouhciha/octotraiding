package com.octotraiding.app.engine

import kotlin.math.max
import kotlin.math.min

/** Una vela OHLCV. */
data class Candle(
    val time: Long,          // epoch millis (apertura)
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val volume: Double,
)

/** Resultado del motor para una vela: puntuación, señal y niveles. */
data class ScoredRow(
    val time: Long,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val trend: Double,
    val momentum: Double,
    val volume: Double,
    val volatility: Double,
    val structure: Double,
    val score: Double,
    val signal: String,
    val regime: String,
    val htfCtx: Double,
    val atr: Double,
    val entry: Double,
    val stop: Double,
    val target: Double,
    val rr: Double,
    val positionPct: Double,
    val support: Double,
    val resistance: Double,
    val atrSpike: Boolean,
)

object Engine {

    private fun sign(x: Double): Double = when {
        x.isNaN() -> 0.0
        x > 0 -> 1.0
        x < 0 -> -1.0
        else -> 0.0
    }

    private fun clamp(x: Double, lo: Double, hi: Double): Double = max(lo, min(hi, x))

    /** Contexto diario (+1 / -1) proyectado a cada vela horaria. */
    private fun dailyContext(daily: List<Candle>, times: LongArray): DoubleArray {
        val n = times.size
        val out = DoubleArray(n)
        if (daily.size < 200) return out
        val dClose = DoubleArray(daily.size) { daily[it].close }
        val dEma = Indicators.ema(dClose, 200)
        var j = -1
        for (i in 0 until n) {
            while (j + 1 < daily.size && daily[j + 1].time <= times[i]) j++
            out[i] = if (j < 0) 0.0 else sign(dClose[j] - dEma[j])
        }
        return out
    }

    /**
     * Calcula todas las filas puntuadas. Devuelve desde una vela mínima de
     * calentamiento para que los indicadores largos sean fiables.
     */
    fun analyze(candles: List<Candle>, daily: List<Candle> = emptyList()): List<ScoredRow> {
        val n = candles.size
        if (n < 210) return emptyList()

        val close = DoubleArray(n) { candles[it].close }
        val high = DoubleArray(n) { candles[it].high }
        val low = DoubleArray(n) { candles[it].low }
        val open = DoubleArray(n) { candles[it].open }
        val volume = DoubleArray(n) { candles[it].volume }
        val times = LongArray(n) { candles[it].time }

        val ema20 = Indicators.ema(close, 20)
        val ema50 = Indicators.ema(close, 50)
        val ema200 = Indicators.ema(close, 200)
        val rsi = Indicators.rsi(close, 14)
        val (macdLine, _, macdHist) = Indicators.macd(close)
        val (stochK, _) = Indicators.stochastic(high, low, close)
        val atr = Indicators.atr(high, low, close, 14)
        val atrMa20 = Indicators.sma(atr, 20)
        val (bbMid, bbUp, bbLow) = Indicators.bollinger(close, 20, 2.0)
        val (adx, _, _) = Indicators.adx(high, low, close, 14)
        val obv = Indicators.obv(close, volume)
        val volMa20 = Indicators.sma(volume, 20)
        val support = Indicators.rollingMin(low, Config.LOOKBACK)
        val resistance = Indicators.rollingMax(high, Config.LOOKBACK)
        val htfCtx = dailyContext(daily, times)

        val rows = ArrayList<ScoredRow>()
        val start = 200
        for (i in start until n) {
            if (atr[i].isNaN() || ema200[i].isNaN() || bbMid[i].isNaN() || resistance[i].isNaN()) continue

            val regime = when {
                adx[i].isNaN() -> "TRANSICION"
                adx[i] >= Config.ADX_TREND -> "TENDENCIA"
                adx[i] < Config.ADX_RANGE -> "RANGO"
                else -> "TRANSICION"
            }

            // --- Tendencia ---
            val trend = (
                sign(close[i] - ema200[i]) +
                    sign(ema20[i] - ema50[i]) +
                    sign(macdHist[i]) +
                    sign(ema50[i] - ema50[i - 5])
                ) / 4.0

            // --- Momentum ---
            val rsiNorm = clamp((rsi[i] - 50) / 25.0, -1.0, 1.0)
            val stochNorm = clamp((stochK[i] - 50) / 50.0, -1.0, 1.0)
            val macdMom = sign(macdHist[i] - macdHist[i - 1])
            val momentumTrend = 0.5 * rsiNorm + 0.3 * stochNorm + 0.2 * macdMom
            val rsiRev = clamp((50 - rsi[i]) / 25.0, -1.0, 1.0)
            val stochRev = clamp((50 - stochK[i]) / 50.0, -1.0, 1.0)
            val momentumRange = 0.5 * rsiRev + 0.3 * stochRev - 0.2 * macdMom
            val momentum = if (regime == "RANGO") momentumRange else momentumTrend

            // --- Volumen ---
            val obvDir = sign(obv[i] - obv[i - 10])
            val priceChange = close[i] - close[i - 1]
            val volRatio = if (volMa20[i].isNaN() || volMa20[i] == 0.0) Double.NaN else volume[i] / volMa20[i]
            val confirm = when {
                priceChange > 0 && !volRatio.isNaN() && volRatio > 1.3 -> 1.0
                priceChange < 0 && !volRatio.isNaN() && volRatio > 1.3 -> -1.0
                else -> 0.0
            }
            val volumeF = 0.6 * obvDir + 0.4 * confirm

            // --- Volatilidad ---
            val bbSpan = bbUp[i] - bbLow[i]
            val pctb = if (bbSpan == 0.0) 0.5 else clamp((close[i] - bbLow[i]) / bbSpan, 0.0, 1.0)
            val volRange = clamp((0.5 - pctb) * 2, -1.0, 1.0)
            val volTrend = clamp((pctb - 0.5) * 2, -1.0, 1.0)
            val volatility = if (regime == "RANGO") volRange else 0.4 * volTrend

            // --- Estructura ---
            val span = resistance[i] - support[i]
            val rangePos = if (span == 0.0) 0.5 else clamp((close[i] - support[i]) / span, 0.0, 1.0)
            var structRange = clamp((0.5 - rangePos) * 2, -1.0, 1.0)
            val nearSupport = (close[i] - support[i]) < atr[i]
            val nearResistance = (resistance[i] - close[i]) < atr[i]
            if (nearSupport) structRange = max(structRange, 0.5)
            if (nearResistance) structRange = min(structRange, -0.5)

            val higherHigh = if (resistance[i] > resistance[i - 20]) 1.0 else 0.0
            val higherLow = if (support[i] > support[i - 20]) 1.0 else 0.0
            var structTrend = (higherHigh + higherLow) - 1.0
            structTrend += if (close[i] > ema50[i]) 0.3 else -0.3
            structTrend = clamp(structTrend, -1.0, 1.0)

            val structure = when (regime) {
                "RANGO" -> structRange
                "TENDENCIA" -> structTrend
                else -> 0.5 * structRange + 0.5 * structTrend
            }

            // --- Score ---
            var score = Config.W_TREND * trend +
                Config.W_MOMENTUM * momentum +
                Config.W_VOLUME * volumeF +
                Config.W_VOLATILITY * volatility +
                Config.W_STRUCTURE * structure
            score = clamp(score, -10.0, 10.0)

            if (htfCtx[i] < 0 && score > 0) score -= Config.CONTEXT_PENALTY
            if (htfCtx[i] > 0 && score < 0) score += Config.CONTEXT_PENALTY
            score = clamp(score, -10.0, 10.0)

            var signal = when {
                score >= Config.STRONG -> Config.COMPRA_FUERTE
                score >= Config.BUY -> Config.COMPRA
                score <= -Config.STRONG -> Config.VENTA_FUERTE
                score <= -Config.BUY -> Config.VENTA
                else -> Config.ESPERAR
            }

            // --- Niveles ---
            val entry = close[i]
            val stop = entry - Config.ATR_STOP * atr[i]
            val targetAtra = entry + Config.ATR_TP * atr[i]
            val target = if (regime == "RANGO" && resistance[i] > entry) min(targetAtra, resistance[i]) else targetAtra
            val riskDist = entry - stop
            val rr = if (riskDist <= 0) 0.0 else (target - entry) / riskDist
            val stopPct = riskDist / entry
            val positionPct = if (stopPct <= 0) 0.0 else clamp(Config.RISK_PER_TRADE / stopPct, 0.0, 1.0)

            val atrSpike = !atrMa20[i].isNaN() && atr[i] > Config.ATR_SPIKE * atrMa20[i]

            // --- Filtros de seguridad ---
            val buyOk = rr >= Config.MIN_RR
            if ((signal == Config.COMPRA || signal == Config.COMPRA_FUERTE) && !buyOk) signal = Config.ESPERAR
            if (atrSpike) signal = Config.ESPERAR

            rows.add(
                ScoredRow(
                    time = times[i],
                    open = open[i], high = high[i], low = low[i], close = close[i],
                    trend = trend, momentum = momentum, volume = volumeF,
                    volatility = volatility, structure = structure,
                    score = score, signal = signal, regime = regime, htfCtx = htfCtx[i],
                    atr = atr[i], entry = entry, stop = stop, target = target,
                    rr = rr, positionPct = positionPct, support = support[i], resistance = resistance[i],
                    atrSpike = atrSpike,
                )
            )
        }
        return rows
    }
}
