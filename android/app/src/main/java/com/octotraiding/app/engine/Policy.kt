package com.octotraiding.app.engine

import kotlin.math.max
import kotlin.math.min

/** Posición abierta (del usuario). El stop sube con el precio; nunca baja. */
data class Position(
    val entry: Double,
    val initialStop: Double,
    var stop: Double,
    val target: Double,
    val positionPct: Double,
    val entryTime: Long,
    var highest: Double,
    var barsHeld: Int = 0,
    var exitSignaled: Boolean = false,
)

/** Evento que se convertirá en notificación. */
data class PolicyEvent(
    val type: String,        // OPEN | TRAIL_STOP_SUBIO | CLOSE
    val time: Long,
    val price: Double,
    val stop: Double = 0.0,
    val target: Double = 0.0,
    val reason: String = "",
    val returnPct: Double = 0.0,
)

object Policy {

    /** ¿Abrir compra con esta señal? (señal fuerte y tendencia diaria no bajista) */
    fun entryOk(prev: ScoredRow): Boolean =
        prev.signal == Config.COMPRA_FUERTE && prev.htfCtx >= 0

    fun openPosition(prev: ScoredRow, row: ScoredRow): Position? {
        val entry = row.open
        val stop = prev.stop
        val target = prev.target
        if (!(stop < entry && entry < target)) return null
        return Position(
            entry = entry,
            initialStop = stop,
            stop = stop,
            target = target,
            positionPct = prev.positionPct,
            entryTime = row.time,
            highest = entry,
        )
    }

    /** Crea la posición cuando el usuario confirma su compra a un precio dado. */
    fun positionFromUser(row: ScoredRow, entryPrice: Double?): Position {
        val entry = entryPrice ?: row.close
        val stop = entry - Config.ATR_STOP * row.atr
        val targetAtra = entry + Config.ATR_TP * row.atr
        val target = if (row.regime == "RANGO" && row.resistance > entry) min(targetAtra, row.resistance) else targetAtra
        val stopPct = (entry - stop) / entry
        val positionPct = if (stopPct <= 0) 0.0 else min(1.0, Config.RISK_PER_TRADE / stopPct)
        return Position(
            entry = entry,
            initialStop = stop,
            stop = stop,
            target = target,
            positionPct = positionPct,
            entryTime = row.time,
            highest = entry,
        )
    }

    private fun checkExit(pos: Position, prev: ScoredRow, row: ScoredRow): Pair<Double, String>? {
        if (prev.signal == Config.VENTA_FUERTE) return Pair(row.open, "SENAL_VENTA")
        if (row.low <= pos.stop) {
            return if (pos.stop > pos.entry) Pair(pos.stop, "STOP_DINAMICO_GANANCIA")
            else Pair(pos.stop, "STOP")
        }
        return null
    }

    private fun updateTrailing(pos: Position, row: ScoredRow): Boolean {
        val old = pos.stop
        pos.highest = max(pos.highest, row.high)
        if (!row.atr.isNaN() && row.atr > 0) {
            val newStop = pos.highest - Config.TRAIL_ATR * row.atr
            pos.stop = max(pos.stop, newStop)
        }
        return pos.stop > old
    }

    /**
     * Avanza una vela. Devuelve (nueva posición, eventos).
     * Misma lógica que la versión validada en Python.
     */
    fun step(prev: ScoredRow, row: ScoredRow, position: Position?): Pair<Position?, List<PolicyEvent>> {
        val events = ArrayList<PolicyEvent>()

        if (position == null) {
            if (entryOk(prev)) {
                val pos = openPosition(prev, row)
                if (pos != null) {
                    events.add(PolicyEvent("OPEN", row.time, pos.entry, pos.stop, pos.target))
                    return Pair(pos, events)
                }
            }
            return Pair(null, events)
        }

        position.barsHeld += 1
        val exit = checkExit(position, prev, row)
        if (exit != null) {
            val (price, reason) = exit
            val ret = price / position.entry - 1.0
            events.add(PolicyEvent("CLOSE", row.time, price, reason = reason, returnPct = ret))
            position.exitSignaled = true
            return Pair(position, events)
        }
        if (updateTrailing(position, row)) {
            events.add(PolicyEvent("TRAIL_STOP_SUBIO", row.time, row.close, stop = position.stop))
        }
        return Pair(position, events)
    }
}
