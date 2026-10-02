package com.octotraiding.app.engine

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Indicadores técnicos en Kotlin puro (mismos que el motor en Python).
 * Trabajan sobre DoubleArray; usan Double.NaN cuando aún no hay datos.
 */
object Indicators {

    fun ema(values: DoubleArray, span: Int): DoubleArray {
        val out = DoubleArray(values.size)
        if (values.isEmpty()) return out
        val a = 2.0 / (span + 1)
        var prev = values[0]
        out[0] = prev
        for (i in 1 until values.size) {
            prev = a * values[i] + (1 - a) * prev
            out[i] = prev
        }
        return out
    }

    fun sma(values: DoubleArray, window: Int): DoubleArray {
        val out = DoubleArray(values.size) { Double.NaN }
        if (values.size < window) return out
        var sum = 0.0
        for (i in values.indices) {
            sum += values[i]
            if (i >= window) sum -= values[i - window]
            if (i >= window - 1) out[i] = sum / window
        }
        return out
    }

    fun rollingMin(values: DoubleArray, window: Int): DoubleArray {
        val out = DoubleArray(values.size) { Double.NaN }
        for (i in values.indices) {
            if (i >= window - 1) {
                var m = Double.POSITIVE_INFINITY
                for (j in i - window + 1..i) m = min(m, values[j])
                out[i] = m
            }
        }
        return out
    }

    fun rollingMax(values: DoubleArray, window: Int): DoubleArray {
        val out = DoubleArray(values.size) { Double.NaN }
        for (i in values.indices) {
            if (i >= window - 1) {
                var m = Double.NEGATIVE_INFINITY
                for (j in i - window + 1..i) m = max(m, values[j])
                out[i] = m
            }
        }
        return out
    }

    fun rsi(close: DoubleArray, period: Int = 14): DoubleArray {
        val n = close.size
        val out = DoubleArray(n) { Double.NaN }
        if (n <= period) return out
        var gainSum = 0.0
        var lossSum = 0.0
        for (i in 1..period) {
            val d = close[i] - close[i - 1]
            if (d >= 0) gainSum += d else lossSum += -d
        }
        var avgGain = gainSum / period
        var avgLoss = lossSum / period
        out[period] = rsiValue(avgGain, avgLoss)
        for (i in period + 1 until n) {
            val d = close[i] - close[i - 1]
            val g = if (d > 0) d else 0.0
            val l = if (d < 0) -d else 0.0
            avgGain = (avgGain * (period - 1) + g) / period
            avgLoss = (avgLoss * (period - 1) + l) / period
            out[i] = rsiValue(avgGain, avgLoss)
        }
        return out
    }

    private fun rsiValue(avgGain: Double, avgLoss: Double): Double {
        if (avgLoss == 0.0) return 100.0
        val rs = avgGain / avgLoss
        return 100.0 - (100.0 / (1.0 + rs))
    }

    fun macd(close: DoubleArray, fast: Int = 12, slow: Int = 26, signal: Int = 9): Triple<DoubleArray, DoubleArray, DoubleArray> {
        val emaFast = ema(close, fast)
        val emaSlow = ema(close, slow)
        val macdLine = DoubleArray(close.size) { emaFast[it] - emaSlow[it] }
        val signalLine = ema(macdLine, signal)
        val hist = DoubleArray(close.size) { macdLine[it] - signalLine[it] }
        return Triple(macdLine, signalLine, hist)
    }

    fun stochastic(high: DoubleArray, low: DoubleArray, close: DoubleArray, k: Int = 14, slowing: Int = 3, d: Int = 3): Pair<DoubleArray, DoubleArray> {
        val n = close.size
        val lowest = rollingMin(low, k)
        val highest = rollingMax(high, k)
        val rawK = DoubleArray(n) { i ->
            val span = highest[i] - lowest[i]
            if (span.isNaN() || span == 0.0) Double.NaN else 100.0 * (close[i] - lowest[i]) / span
        }
        val slowK = smaNaN(rawK, slowing)
        val slowD = smaNaN(slowK, d)
        return Pair(slowK, slowD)
    }

    /** SMA que propaga NaN mientras falten datos (para encadenar suavizados). */
    private fun smaNaN(values: DoubleArray, window: Int): DoubleArray {
        val out = DoubleArray(values.size) { Double.NaN }
        for (i in values.indices) {
            if (i >= window - 1) {
                var sum = 0.0
                var ok = true
                for (j in i - window + 1..i) {
                    if (values[j].isNaN()) { ok = false; break }
                    sum += values[j]
                }
                if (ok) out[i] = sum / window
            }
        }
        return out
    }

    fun atr(high: DoubleArray, low: DoubleArray, close: DoubleArray, period: Int = 14): DoubleArray {
        val n = close.size
        val tr = DoubleArray(n) { Double.NaN }
        for (i in 1 until n) {
            val hl = high[i] - low[i]
            val hc = abs(high[i] - close[i - 1])
            val lc = abs(low[i] - close[i - 1])
            tr[i] = max(hl, max(hc, lc))
        }
        val out = DoubleArray(n) { Double.NaN }
        if (n <= period) return out
        var sum = 0.0
        for (i in 1..period) sum += tr[i]
        var prev = sum / period
        out[period] = prev
        for (i in period + 1 until n) {
            prev = (prev * (period - 1) + tr[i]) / period
            out[i] = prev
        }
        return out
    }

    fun bollinger(close: DoubleArray, window: Int = 20, mult: Double = 2.0): Triple<DoubleArray, DoubleArray, DoubleArray> {
        val n = close.size
        val mid = sma(close, window)
        val upper = DoubleArray(n) { Double.NaN }
        val lower = DoubleArray(n) { Double.NaN }
        for (i in close.indices) {
            if (i >= window - 1 && !mid[i].isNaN()) {
                var sumSq = 0.0
                for (j in i - window + 1..i) {
                    val diff = close[j] - mid[i]
                    sumSq += diff * diff
                }
                val std = sqrt(sumSq / window)
                upper[i] = mid[i] + mult * std
                lower[i] = mid[i] - mult * std
            }
        }
        return Triple(mid, upper, lower)
    }

    /** Devuelve (adx, +DI, -DI). */
    fun adx(high: DoubleArray, low: DoubleArray, close: DoubleArray, period: Int = 14): Triple<DoubleArray, DoubleArray, DoubleArray> {
        val n = close.size
        val plusDM = DoubleArray(n)
        val minusDM = DoubleArray(n)
        val tr = DoubleArray(n)
        for (i in 1 until n) {
            val up = high[i] - high[i - 1]
            val down = low[i - 1] - low[i]
            plusDM[i] = if (up > down && up > 0) up else 0.0
            minusDM[i] = if (down > up && down > 0) down else 0.0
            tr[i] = max(high[i] - low[i], max(abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1])))
        }
        val adxOut = DoubleArray(n) { Double.NaN }
        val plusDI = DoubleArray(n) { Double.NaN }
        val minusDI = DoubleArray(n) { Double.NaN }
        if (n <= period * 2) return Triple(adxOut, plusDI, minusDI)

        var trS = 0.0; var plusS = 0.0; var minusS = 0.0
        for (i in 1..period) { trS += tr[i]; plusS += plusDM[i]; minusS += minusDM[i] }
        var dxSum = 0.0
        val dx = DoubleArray(n) { Double.NaN }
        for (i in period until n) {
            if (i > period) {
                trS = trS - trS / period + tr[i]
                plusS = plusS - plusS / period + plusDM[i]
                minusS = minusS - minusS / period + minusDM[i]
            }
            val pdi = if (trS == 0.0) 0.0 else 100.0 * plusS / trS
            val mdi = if (trS == 0.0) 0.0 else 100.0 * minusS / trS
            plusDI[i] = pdi; minusDI[i] = mdi
            val sum = pdi + mdi
            dx[i] = if (sum == 0.0) 0.0 else 100.0 * abs(pdi - mdi) / sum
        }
        // ADX = media (Wilder) de DX
        var adxPrev = 0.0
        for (i in period until n) {
            if (i == period) { adxPrev = dx[i]; adxOut[i] = dx[i]; continue }
            adxPrev = (adxPrev * (period - 1) + dx[i]) / period
            adxOut[i] = adxPrev
        }
        return Triple(adxOut, plusDI, minusDI)
    }

    fun obv(close: DoubleArray, volume: DoubleArray): DoubleArray {
        val out = DoubleArray(close.size)
        for (i in 1 until close.size) {
            val dir = when {
                close[i] > close[i - 1] -> 1.0
                close[i] < close[i - 1] -> -1.0
                else -> 0.0
            }
            out[i] = out[i - 1] + dir * volume[i]
        }
        return out
    }
}
