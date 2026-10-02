package com.octotraiding.app.logic

import com.octotraiding.app.data.Detail
import com.octotraiding.app.engine.Position

/** Traduce el estado (detalle + posición) a la acción que ve el usuario. */
object Actions {

    fun compute(detail: Detail?, position: Position?): Pair<String, String> {
        if (position != null) {
            return when {
                position.exitSignaled ->
                    "VENDER" to "Tienes posición y hay señal de SALIR. Vende y confírmalo."
                detail?.signal == "VENTA" || detail?.signal == "VENTA_FUERTE" ->
                    "VENDER" to "Tienes posición y el método pide salir."
                else ->
                    "MANTENER" to "Tienes posición. Mantén según el plan; el stop sube solo."
            }
        }
        return when (detail?.signal) {
            "COMPRA_FUERTE" -> "COMPRAR" to "No tienes posición y hay una oportunidad de COMPRA."
            "COMPRA" -> "VIGILAR" to "No tienes posición. Señal tibia: aún no es momento claro."
            else -> "ESPERAR" to "No tienes posición. No hay ventaja clara por ahora."
        }
    }
}
