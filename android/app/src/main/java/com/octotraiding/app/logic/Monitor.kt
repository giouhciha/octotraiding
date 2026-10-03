package com.octotraiding.app.logic

import android.content.Context
import com.octotraiding.app.data.BinanceApi
import com.octotraiding.app.data.Detail
import com.octotraiding.app.data.EventItem
import com.octotraiding.app.data.ReportItem
import com.octotraiding.app.data.Store
import com.octotraiding.app.engine.Config
import com.octotraiding.app.engine.Engine
import com.octotraiding.app.engine.Policy
import com.octotraiding.app.engine.PolicyEvent
import com.octotraiding.app.notif.Notifier
import java.time.Instant
import java.time.ZoneId
import java.util.Locale

data class MonitorResult(val status: String, val notifications: Int, val positionOpen: Boolean)

/** Ejecuta un ciclo de análisis en el propio teléfono. */
object Monitor {

    fun intervalMillis(interval: String): Long = when (interval) {
        "4h" -> 4 * 3_600_000L
        "1d" -> 86_400_000L
        else -> 3_600_000L
    }

    private fun fmt(v: Double): String = String.format(Locale.US, "%,.0f", v)

    private fun reasonText(reason: String): String = when (reason) {
        "STOP" -> "tocó el stop"
        "STOP_DINAMICO_GANANCIA" -> "stop de ganancia"
        "SENAL_VENTA" -> "señal de venta fuerte"
        else -> reason
    }

    private fun eventMessage(ev: PolicyEvent, symbol: String): String = when (ev.type) {
        "OPEN" -> "Momento de comprar $symbol: entrada $${fmt(ev.price)} · stop $${fmt(ev.stop)} · objetivo $${fmt(ev.target)}"
        "TRAIL_STOP_SUBIO" -> "Sube tu stop a $${fmt(ev.stop)}. Estás protegiendo ganancia."
        "CLOSE" -> "Vender $symbol cerca de $${fmt(ev.price)} (${"%.1f".format(ev.returnPct * 100)}%). Motivo: ${reasonText(ev.reason)}"
        else -> ev.type
    }

    private fun shouldNotify(time: Long, quietStart: Int, quietEnd: Int): Boolean {
        val hour = Instant.ofEpochMilli(time).atZone(ZoneId.systemDefault()).hour
        if (quietStart == quietEnd) return true
        return if (quietStart < quietEnd) {
            !(hour in quietStart until quietEnd)
        } else {
            !(hour >= quietStart || hour < quietEnd)
        }
    }

    fun runOnce(context: Context, allowNotify: Boolean = true): MonitorResult {
        val settings = Store.settings(context)
        val candles = BinanceApi.fetchKlines(settings.symbol, settings.interval, 1000)
        val daily = try {
            BinanceApi.fetchKlines(settings.symbol, "1d", 400)
        } catch (_: Exception) {
            emptyList()
        }
        val rows = Engine.analyze(candles, daily)
        if (rows.size < 2) return MonitorResult("Datos insuficientes", 0, false)

        val dur = intervalMillis(settings.interval)
        val now = System.currentTimeMillis()
        val closed = rows.filter { it.time + dur <= now }
        if (closed.size < 2) return MonitorResult("Sin velas cerradas", 0, false)

        val last = Store.lastProcessed(context)
        if (last == null) {
            closed.takeLast(48).forEach {
                Store.addReport(context, ReportItem(it.time, it.close, it.signal, it.score))
            }
            Store.setLastProcessed(context, closed.last().time)
            saveDetail(context, closed.last(), settings.symbol)
            return MonitorResult("Inicio (historial cargado)", 0, false)
        }

        val startIdx = closed.indexOfFirst { it.time > last }
        if (startIdx <= 0) return MonitorResult("Sin velas nuevas", 0, Store.position(context) != null)

        var position = Store.position(context)
        var sent = 0

        for (idx in startIdx until closed.size) {
            val row = closed[idx]
            val prev = closed[idx - 1]

            if (position == null) {
                val isBuy = { s: String -> s == Config.COMPRA || s == Config.COMPRA_FUERTE }
                val strongBuy = row.signal == Config.COMPRA_FUERTE && prev.signal != Config.COMPRA_FUERTE
                val moderateBuy = Store.notifyModerate(context) &&
                    row.signal == Config.COMPRA && !isBuy(prev.signal)
                val shouldAlert = (strongBuy || moderateBuy) && row.htfCtx >= 0
                if (shouldAlert) {
                    val moderada = row.signal == Config.COMPRA
                    val msg = (if (moderada) "Señal moderada. " else "") +
                        "Momento de comprar ${settings.symbol}: entrada $${fmt(row.close)} · " +
                        "stop $${fmt(row.stop)} · objetivo $${fmt(row.target)}"
                    Store.addEvent(context, EventItem(row.time, "OPEN", msg))
                    if (allowNotify && shouldNotify(row.time, settings.quietStart, settings.quietEnd)) {
                        Notifier.notify(context, "OctoTrading · ${settings.symbol}", msg, row.time.hashCode())
                        sent++
                    }
                }
            } else {
                val (newPos, events) = Policy.step(prev, row, position)
                position = newPos
                events.forEach { ev ->
                    val msg = eventMessage(ev, settings.symbol)
                    Store.addEvent(context, EventItem(ev.time, ev.type, msg))
                    if (allowNotify && shouldNotify(ev.time, settings.quietStart, settings.quietEnd)) {
                        Notifier.notify(context, "OctoTrading · ${settings.symbol}", msg,
                            ("${ev.time}-${ev.type}").hashCode())
                        sent++
                    }
                }
            }
            Store.addReport(context, ReportItem(row.time, row.close, row.signal, row.score))
        }

        Store.savePosition(context, position)
        Store.setLastProcessed(context, closed.last().time)
        saveDetail(context, closed.last(), settings.symbol)
        return MonitorResult("${closed.size - startIdx} velas procesadas, $sent avisos", sent, position != null)
    }

    private fun saveDetail(context: Context, row: com.octotraiding.app.engine.ScoredRow, symbol: String) {
        Store.saveDetail(
            context,
            Detail(
                time = row.time,
                price = row.close,
                signal = row.signal,
                score = row.score,
                regime = row.regime,
                dailyTrend = ReportText.dailyTrend(row.htfCtx),
                entry = row.entry,
                stop = row.stop,
                target = row.target,
                rr = row.rr,
                positionPct = row.positionPct,
                narrative = ReportText.narrative(row, symbol),
            ),
        )
    }

    private fun latestClosedRow(context: Context): com.octotraiding.app.engine.ScoredRow? {
        val settings = Store.settings(context)
        val candles = BinanceApi.fetchKlines(settings.symbol, settings.interval, 1000)
        val daily = try {
            BinanceApi.fetchKlines(settings.symbol, "1d", 400)
        } catch (_: Exception) {
            emptyList()
        }
        val rows = Engine.analyze(candles, daily)
        val dur = intervalMillis(settings.interval)
        val now = System.currentTimeMillis()
        return rows.filter { it.time + dur <= now }.lastOrNull()
    }

    /** El usuario confirma que compró: se crea su posición y su stop. */
    fun registerBuy(context: Context, entryPrice: Double?): Boolean {
        val row = latestClosedRow(context) ?: return false
        val pos = Policy.positionFromUser(row, entryPrice)
        Store.savePosition(context, pos)
        Store.addEvent(
            context,
            EventItem(
                row.time, "OPEN",
                "Compra registrada a $${fmt(pos.entry)}. Stop $${fmt(pos.stop)}, objetivo $${fmt(pos.target)}.",
            ),
        )
        return true
    }

    /** El usuario confirma que vendió: se cierra la posición. */
    fun registerSell(context: Context) {
        val p = Store.position(context)
        if (p != null) {
            Store.addEvent(
                context,
                EventItem(
                    System.currentTimeMillis(), "CLOSE",
                    "Venta registrada. Operación cerrada (entrada $${fmt(p.entry)}).",
                ),
            )
        }
        Store.savePosition(context, null)
    }
}
