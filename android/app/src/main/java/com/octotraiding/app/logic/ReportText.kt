package com.octotraiding.app.logic

import com.octotraiding.app.engine.Config
import com.octotraiding.app.engine.ScoredRow
import java.util.Locale

/** Genera el texto en lenguaje llano que ve el usuario. */
object ReportText {

    private fun money(v: Double): String = String.format(Locale.US, "%,.0f", v)

    fun dailyTrend(htfCtx: Double): String = when {
        htfCtx > 0 -> "alcista"
        htfCtx < 0 -> "bajista"
        else -> "neutra"
    }

    fun factors(row: ScoredRow): List<String> {
        val out = ArrayList<String>()
        if (row.trend >= 0.5) out.add("La tendencia de fondo es alcista (precio sobre sus medias).")
        else if (row.trend <= -0.5) out.add("La tendencia de fondo es bajista (precio bajo sus medias).")
        if (row.momentum >= 0.4) out.add("El impulso apunta al alza.")
        else if (row.momentum <= -0.4) out.add("El impulso apunta a la baja.")
        if (row.volume >= 0.4) out.add("El volumen está confirmando el movimiento.")
        else if (row.volume <= -0.4) out.add("El volumen no respalda el movimiento.")
        if (row.regime == "TENDENCIA") out.add("El mercado muestra una tendencia clara.")
        else if (row.regime == "RANGO") out.add("El mercado está lateral (sin rumbo marcado).")
        if (row.structure >= 0.4) out.add("El precio está en una zona de compra favorable (soporte).")
        else if (row.structure <= -0.4) out.add("El precio está pegado a una resistencia: poco margen de subida.")
        if (row.htfCtx < 0) out.add("La tendencia diaria es bajista: conviene prudencia.")
        return out
    }

    fun narrative(row: ScoredRow, symbol: String): String {
        val signalPlain = Config.SIGNAL_PLAIN[row.signal] ?: row.signal
        val parts = ArrayList<String>()
        parts.add("$symbol cotiza a \$${money(row.close)}.")
        val reasons = factors(row)
        if (reasons.isNotEmpty()) parts.add(reasons.joinToString(" "))
        parts.add("En conjunto, la lectura del método es: $signalPlain.")
        if (row.signal == Config.COMPRA || row.signal == Config.COMPRA_FUERTE) {
            parts.add(
                "Si decides entrar, el punto de salida de emergencia está en \$${money(row.stop)} " +
                    "y el riesgo/beneficio es 1 : ${"%.1f".format(row.rr)}."
            )
        }
        return parts.joinToString(" ")
    }
}
