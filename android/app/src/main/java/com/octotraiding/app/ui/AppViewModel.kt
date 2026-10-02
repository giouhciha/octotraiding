package com.octotraiding.app.ui

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.octotraiding.app.data.Assets
import com.octotraiding.app.data.Detail
import com.octotraiding.app.data.EventItem
import com.octotraiding.app.data.ReportItem
import com.octotraiding.app.data.Settings
import com.octotraiding.app.data.Store
import com.octotraiding.app.engine.Position
import com.octotraiding.app.logic.Monitor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class AppState(
    val symbol: String = "BTCUSDT",
    val assetName: String = "Bitcoin",
    val capital: Double = 1000.0,
    val riskPct: Double = 0.01,
    val interval: String = "1h",
    val quietStart: Int = 23,
    val quietEnd: Int = 7,
    val detail: Detail? = null,
    val position: Position? = null,
    val action: String = "ESPERAR",
    val hint: String = "",
    val holding: Boolean = false,
    val exitSignaled: Boolean = false,
    val reports: List<ReportItem> = emptyList(),
    val events: List<EventItem> = emptyList(),
    val busy: Boolean = false,
    val message: String? = null,
)

class AppViewModel(app: Application) : AndroidViewModel(app) {

    var state by mutableStateOf(AppState())
        private set

    init {
        viewModelScope.launch { load() }
        refresh(runMonitor = true)
    }

    fun refresh(runMonitor: Boolean = true) {
        viewModelScope.launch {
            state = state.copy(busy = true, message = if (runMonitor) "Analizando el mercado…" else null)
            val ok = withContext(Dispatchers.IO) {
                if (!runMonitor) true
                else runCatching { Monitor.runOnce(getApplication(), allowNotify = true) }.isSuccess
            }
            load()
            state = state.copy(
                busy = false,
                message = if (!ok) "No se pudo conectar. Revisa tu internet." else null,
            )
        }
    }

    private suspend fun load() {
        val app = getApplication<Application>()
        val data = withContext(Dispatchers.IO) {
            Triple(Store.settings(app), Store.detail(app), Store.position(app))
        }
        val reports = withContext(Dispatchers.IO) { Store.reports(app) }
        val events = withContext(Dispatchers.IO) { Store.events(app) }
        val settings = data.first
        val detail = data.second
        val position = data.third
        val (action, hint) = computeAction(detail, position)
        state = state.copy(
            symbol = settings.symbol,
            assetName = Assets.name(settings.symbol),
            capital = settings.capital,
            riskPct = settings.riskPct,
            interval = settings.interval,
            quietStart = settings.quietStart,
            quietEnd = settings.quietEnd,
            detail = detail,
            position = position,
            action = action,
            hint = hint,
            holding = position != null,
            exitSignaled = position?.exitSignaled == true,
            reports = reports,
            events = events,
        )
    }

    private fun computeAction(detail: Detail?, position: Position?): Pair<String, String> {
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

    fun selectAsset(symbol: String, interval: String? = null) {
        viewModelScope.launch {
            val app = getApplication<Application>()
            withContext(Dispatchers.IO) {
                val s = Store.settings(app)
                Store.saveSettings(app, s.copy(symbol = symbol, interval = interval ?: s.interval))
                Store.clearForNewAsset(app)
            }
            refresh(runMonitor = true)
        }
    }

    fun buy() {
        viewModelScope.launch {
            val app = getApplication<Application>()
            val ok = withContext(Dispatchers.IO) { runCatching { Monitor.registerBuy(app, null) }.getOrDefault(false) }
            load()
            state = state.copy(message = if (ok) "Compra registrada. Vigilaremos tu salida." else "No se pudo registrar.")
        }
    }

    fun sell() {
        viewModelScope.launch {
            val app = getApplication<Application>()
            withContext(Dispatchers.IO) { Monitor.registerSell(app) }
            load()
            state = state.copy(message = "Venta registrada. Estás fuera del mercado.")
        }
    }

    fun saveSettings(capital: Double, riskPct: Double, quietStart: Int, quietEnd: Int, interval: String) {
        viewModelScope.launch {
            val app = getApplication<Application>()
            withContext(Dispatchers.IO) {
                val s = Store.settings(app)
                Store.saveSettings(
                    app,
                    Settings(
                        symbol = s.symbol,
                        interval = interval,
                        capital = capital,
                        riskPct = riskPct,
                        quietStart = quietStart,
                        quietEnd = quietEnd,
                    ),
                )
            }
            load()
            state = state.copy(message = "Ajustes guardados.")
        }
    }

    fun clearMessage() {
        state = state.copy(message = null)
    }
}
