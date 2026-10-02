package com.octotraiding.app.engine

/** Parámetros del motor (idénticos a la versión validada en Python). */
object Config {
    // Pesos de las familias de indicadores (suman 10).
    const val W_TREND = 3.0
    const val W_MOMENTUM = 2.5
    const val W_VOLUME = 1.5
    const val W_VOLATILITY = 1.5
    const val W_STRUCTURE = 1.5

    // Umbrales de señal (perfil moderado).
    const val BUY = 3.0
    const val STRONG = 6.0

    // Riesgo.
    const val ATR_STOP = 2.0
    const val ATR_TP = 3.0
    const val TRAIL_ATR = 3.0
    const val MIN_RR = 1.5
    const val RISK_PER_TRADE = 0.01

    // Régimen.
    const val ADX_TREND = 25.0
    const val ADX_RANGE = 20.0

    // Ventanas y filtros.
    const val LOOKBACK = 50
    const val ATR_SPIKE = 2.5
    const val CONTEXT_PENALTY = 1.5

    // Señales.
    const val COMPRA_FUERTE = "COMPRA_FUERTE"
    const val COMPRA = "COMPRA"
    const val ESPERAR = "ESPERAR"
    const val VENTA = "VENTA"
    const val VENTA_FUERTE = "VENTA_FUERTE"

    // Textos para el usuario.
    val SIGNAL_PLAIN = mapOf(
        COMPRA_FUERTE to "COMPRA FUERTE",
        COMPRA to "COMPRA (moderada)",
        ESPERAR to "ESPERAR / MANTENER",
        VENTA to "VENTA (moderada)",
        VENTA_FUERTE to "VENTA FUERTE",
    )
}
