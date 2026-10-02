package com.octotraiding.app

import com.octotraiding.app.engine.Candle
import com.octotraiding.app.engine.Engine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Properties
import kotlin.math.abs

/**
 * Verifica que el motor en Kotlin reproduce el motor en Python (la referencia
 * validada con backtesting). Los datos y el resultado esperado los genera
 * scripts/make_engine_fixture.py.
 */
class EngineParityTest {

    private fun loadCandles(): List<Candle> {
        val lines = javaClass.classLoader!!
            .getResourceAsStream("btc_1h.csv")!!
            .bufferedReader().readLines()
        return lines.drop(1).filter { it.isNotBlank() }.map { line ->
            val p = line.split(",")
            Candle(
                time = p[0].trim().toLong(),
                open = p[1].toDouble(),
                high = p[2].toDouble(),
                low = p[3].toDouble(),
                close = p[4].toDouble(),
                volume = p[5].toDouble(),
            )
        }
    }

    private fun loadExpected(): Properties {
        val props = Properties()
        javaClass.classLoader!!.getResourceAsStream("expected.properties")!!.use { props.load(it) }
        return props
    }

    @Test
    fun kotlin_engine_matches_python_reference() {
        val candles = loadCandles()
        val expected = loadExpected()
        val rows = Engine.analyze(candles, emptyList())
        assertTrue("El motor no produjo filas", rows.isNotEmpty())

        val last = rows.last()
        println("Kotlin   -> signal=${last.signal} score=${last.score} regime=${last.regime}")
        println("Python   -> signal=${expected.getProperty("signal")} score=${expected.getProperty("score")} regime=${expected.getProperty("regime")}")

        // La señal debe coincidir exactamente (es lo que le importa al usuario).
        assertEquals("La señal no coincide", expected.getProperty("signal"), last.signal)

        val expScore = expected.getProperty("score").toDouble()
        assertTrue("El score se desvía demasiado: ${last.score} vs $expScore",
            abs(last.score - expScore) < 0.75)

        val expAtr = expected.getProperty("atr").toDouble()
        assertTrue("El ATR se desvía demasiado", abs(last.atr - expAtr) / expAtr < 0.02)

        val expStop = expected.getProperty("stop").toDouble()
        assertTrue("El stop se desvía demasiado", abs(last.stop - expStop) / expStop < 0.01)

        val expTarget = expected.getProperty("target").toDouble()
        assertTrue("El objetivo se desvía demasiado", abs(last.target - expTarget) / expTarget < 0.01)

        assertEquals("El régimen no coincide", expected.getProperty("regime"), last.regime)
    }
}
