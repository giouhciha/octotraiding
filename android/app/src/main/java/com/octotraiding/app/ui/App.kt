package com.octotraiding.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.octotraiding.app.data.Assets
import com.octotraiding.app.engine.Config
import com.octotraiding.app.power.PowerSetup
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

private val Bg = Color(0xFF0B1220)
private val Card = Color(0xFF121B2E)
private val Card2 = Color(0xFF16213A)
private val Line = Color(0xFF24304A)
private val TextCol = Color(0xFFE6ECF5)
private val Muted = Color(0xFF93A4C0)
private val Teal = Color(0xFF2DD4BF)
private val Green = Color(0xFF22C55E)
private val Red = Color(0xFFEF4444)
private val Amber = Color(0xFFF59E0B)

private val DarkColors = darkColorScheme(
    primary = Teal, background = Bg, surface = Card, onSurface = TextCol,
    onSurfaceVariant = Muted, outline = Line, surfaceVariant = Card2,
)

private fun money(v: Double): String {
    val dec = if (v >= 1000) 0 else 2
    return "$" + String.format(Locale.US, "%,.${dec}f", v)
}

private fun signalPlain(signal: String): String = Config.SIGNAL_PLAIN[signal] ?: signal

private fun actionColor(a: String): Color = when {
    a.contains("COMPRAR") -> Green
    a.contains("VENDER") -> Red
    else -> Muted
}

private val fmt = DateTimeFormatter.ofPattern("dd MMM HH:mm").withZone(ZoneId.systemDefault())
private fun whenText(ms: Long): String = fmt.format(Instant.ofEpochMilli(ms))

@Composable
fun OctoApp(vm: AppViewModel) {
    val state = vm.state
    var showChange by remember { mutableStateOf(false) }
    var showSettings by remember { mutableStateOf(false) }
    val context = LocalContext.current

    MaterialTheme(colorScheme = DarkColors) {
        Box(Modifier.fillMaxSize().background(Bg)) {
            Column(Modifier.fillMaxSize()) {
                TopBar(state)
                LazyColumn(
                    Modifier.weight(1f),
                    contentPadding = PaddingValues(bottom = 104.dp),
                ) {
                    item { HeroCard(state, onBuy = { vm.buy() }, onSell = { vm.sell() }) }
                    item {
                        PriceChart(
                            symbol = state.symbol,
                            candles = state.candles,
                            position = state.position,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                        )
                    }
                    if (state.holding || state.detail?.signal?.contains("COMPRA") == true) {
                        item { LevelsCard(state) }
                    }
                    item { HistoryCard(state) }
                    item { EventsCard(state) }
                }
            }

            BottomBar(
                modifier = Modifier.align(Alignment.BottomCenter),
                onChange = { showChange = true },
                onSettings = { showSettings = true },
            )

            state.message?.let {
                Toast(it, Modifier.align(Alignment.BottomCenter).padding(bottom = 104.dp))
                LaunchedEffect(it) {
                    kotlinx.coroutines.delay(2600)
                    vm.clearMessage()
                }
            }
        }

        if (showChange) {
            ChangeDialog(onPick = { symbol -> vm.selectAsset(symbol); showChange = false }, onClose = { showChange = false })
        }
        if (showSettings) {
            SettingsDialog(
                state,
                onSave = { c, r, qs, qe, in2 -> vm.saveSettings(c, r, qs, qe, in2); showSettings = false },
                onReliability = {
                    PowerSetup.requestExactAlarm(context)
                    PowerSetup.requestBatteryExemption(context)
                },
                onClose = { showSettings = false },
            )
        }
    }
}

@Composable
private fun TopBar(state: AppState) {
    Row(
        Modifier.fillMaxWidth().statusBarsPadding().background(Color(0xE60B1220)).padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column {
            Text("OctoTrading", color = Teal, fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text("tu analista en el bolsillo", color = Muted, fontSize = 12.sp)
        }
        if (state.busy) CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp, color = Teal)
    }
}

@Composable
private fun HeroCard(state: AppState, onBuy: () -> Unit, onSell: () -> Unit) {
    val d = state.detail
    Column(
        Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            .fillMaxWidth().background(Card, RoundedCornerShape(16.dp)).padding(16.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Column {
                Text(state.symbol, color = TextCol, fontWeight = FontWeight.Bold, fontSize = 22.sp)
                Text(state.assetName, color = Muted, fontSize = 13.sp)
            }
            Badge(state.action, actionColor(state.action))
        }
        Text(
            if (d != null) money(d.price) else "—",
            color = TextCol, fontWeight = FontWeight.ExtraBold, fontSize = 40.sp,
        )
        if (d != null) {
            Row(Modifier.fillMaxWidth().padding(top = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Puntuación del método", color = Muted, fontSize = 12.sp)
                Text((if (d.score >= 0) "+" else "") + String.format(Locale.US, "%.2f", d.score), color = TextCol, fontSize = 12.sp)
            }
            val pct = ((d.score + 10) / 20).coerceIn(0.0, 1.0).toFloat()
            Box(Modifier.fillMaxWidth().padding(vertical = 6.dp).height(8.dp).background(Color(0xFF1D2946), RoundedCornerShape(6.dp))) {
                Box(Modifier.fillMaxWidth(pct).height(8.dp).background(
                    brush = androidx.compose.ui.graphics.Brush.horizontalGradient(listOf(Red, Amber, Green)),
                    shape = RoundedCornerShape(6.dp),
                ))
            }
            Text(d.narrative, color = Color(0xFFD7E0EF), fontSize = 14.sp)
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                Chip("Señal: ${signalPlain(d.signal)}")
                Spacer(Modifier.width(8.dp))
                Chip("Régimen: ${d.regime}")
            }
            Spacer(Modifier.height(6.dp))
            Row(Modifier.fillMaxWidth()) {
                Chip("Tendencia diaria: ${d.dailyTrend}")
            }
        }
        Spacer(Modifier.height(14.dp))
        Row(
            Modifier.fillMaxWidth().background(Color(0xFF0F1830), RoundedCornerShape(12.dp)).padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(state.hint, color = Color(0xFFCDD8EA), fontSize = 13.sp, modifier = Modifier.weight(1f))
            Spacer(Modifier.width(10.dp))
            Button(
                onClick = { if (state.holding) onSell() else onBuy() },
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (state.exitSignaled) Red else Teal,
                    contentColor = if (state.exitSignaled) Color.White else Color(0xFF05201C),
                ),
            ) {
                Text(if (state.holding) (if (state.exitSignaled) "Ya vendí ✔" else "Ya vendí") else "Compré")
            }
        }
    }
}

@Composable
private fun LevelsCard(state: AppState) {
    val d = state.detail ?: return
    val p = state.position
    val entry = p?.entry ?: d.entry
    val stop = p?.stop ?: d.stop
    val target = p?.target ?: d.target
    val rr = if (p != null && (p.entry - p.stop) != 0.0) (p.target - p.entry) / (p.entry - p.stop) else d.rr

    Column(
        Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            .fillMaxWidth().background(Card, RoundedCornerShape(16.dp)).padding(16.dp),
    ) {
        Text("SI DECIDES ENTRAR", color = Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(10.dp))
        Row(Modifier.fillMaxWidth()) {
            Metric("Entrada", money(entry), TextCol, Modifier.weight(1f))
            Metric("Stop (salir si falla)", money(stop), Red, Modifier.weight(1f))
        }
        Spacer(Modifier.height(10.dp))
        Row(Modifier.fillMaxWidth()) {
            Metric("Objetivo", money(target), Green, Modifier.weight(1f))
            Metric("Riesgo/Benef.", "1 : " + String.format(Locale.US, "%.2f", rr), TextCol, Modifier.weight(1f))
        }
        Spacer(Modifier.height(10.dp))
        val capital = state.capital
        if (p != null) {
            Text("Tienes posición desde ${money(p.entry)} · stop actual ${money(p.stop)}.", color = Muted, fontSize = 13.sp)
        } else if (capital > 0) {
            Text("Con ${money(capital)} y riesgo ${String.format(Locale.US, "%.1f", state.riskPct * 100)}% → compra sugerida de ${money(capital * d.positionPct)}.", color = Muted, fontSize = 13.sp)
        }
        Spacer(Modifier.height(8.dp))
        Text("Análisis técnico automatizado. No es asesoramiento financiero.", color = Color(0xFF6B7A97), fontSize = 11.sp)
    }
}

@Composable
private fun Metric(label: String, value: String, color: Color, modifier: Modifier) {
    Column(modifier.background(Color(0xFF0F1830), RoundedCornerShape(12.dp)).padding(10.dp)) {
        Text(label, color = Muted, fontSize = 11.sp)
        Text(value, color = color, fontWeight = FontWeight.Bold, fontSize = 18.sp)
    }
}

@Composable
private fun HistoryCard(state: AppState) {
    Column(
        Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            .fillMaxWidth().background(Card, RoundedCornerShape(16.dp)).padding(16.dp),
    ) {
        Text("HISTORIAL RECIENTE", color = Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        if (state.reports.isEmpty()) {
            Text("Sin historial todavía.", color = Muted, fontSize = 13.sp)
        } else {
            state.reports.take(20).forEach { r ->
                Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column {
                        Text(signalPlain(r.signal), color = TextCol, fontSize = 14.sp)
                        Text("${whenText(r.time)} · ${money(r.price)}", color = Muted, fontSize = 12.sp)
                    }
                    Badge((if (r.score >= 0) "+" else "") + String.format(Locale.US, "%.1f", r.score), actionColor(r.signal))
                }
                HorizontalDivider(color = Line, thickness = 1.dp)
            }
        }
    }
}

@Composable
private fun EventsCard(state: AppState) {
    Column(
        Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            .fillMaxWidth().background(Card, RoundedCornerShape(16.dp)).padding(16.dp),
    ) {
        Text("ALERTAS", color = Muted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        if (state.events.isEmpty()) {
            Text("Sin alertas todavía.", color = Muted, fontSize = 13.sp)
        } else {
            state.events.take(20).forEach { e ->
                Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(e.message, color = TextCol, fontSize = 13.sp, modifier = Modifier.weight(1f))
                    Spacer(Modifier.width(8.dp))
                    Text(whenText(e.time), color = Muted, fontSize = 11.sp)
                }
                HorizontalDivider(color = Line, thickness = 1.dp)
            }
        }
    }
}

@Composable
private fun Badge(text: String, color: Color) {
    Box(Modifier.background(color.copy(alpha = 0.18f), RoundedCornerShape(50)).padding(horizontal = 12.dp, vertical = 5.dp)) {
        Text(text, color = color, fontSize = 12.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun Chip(text: String) {
    Box(Modifier.background(Color(0xFF1A2540), RoundedCornerShape(50)).padding(horizontal = 10.dp, vertical = 5.dp)) {
        Text(text, color = Muted, fontSize = 12.sp)
    }
}

@Composable
private fun BottomBar(modifier: Modifier, onChange: () -> Unit, onSettings: () -> Unit) {
    Row(
        modifier.fillMaxWidth().navigationBarsPadding().background(Color(0xF20B1220)).padding(12.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Button(onClick = onChange, modifier = Modifier.weight(1f),
            colors = ButtonDefaults.buttonColors(containerColor = Teal, contentColor = Color(0xFF05201C))) {
            Text("Cambiar activo")
        }
        OutlinedButton(onClick = onSettings, modifier = Modifier.weight(1f)) {
            Text("Ajustes")
        }
    }
}

@Composable
private fun Toast(text: String, modifier: Modifier = Modifier) {
    Box(modifier.background(Color(0xFF17324F), RoundedCornerShape(12.dp)).padding(12.dp)) {
        Text(text, color = TextCol, fontSize = 14.sp)
    }
}

@Composable
private fun ChangeDialog(onPick: (String) -> Unit, onClose: () -> Unit) {
    var query by remember { mutableStateOf("") }
    val results = remember(query) { Assets.search(query) }
    AlertDialog(
        onDismissRequest = onClose,
        confirmButton = {},
        dismissButton = { TextButton(onClick = onClose) { Text("Cerrar") } },
        title = { Text("Elegir activo") },
        text = {
            Column {
                OutlinedTextField(
                    value = query, onValueChange = { query = it },
                    placeholder = { Text("Buscar (BTC, solana…)") },
                    singleLine = true, modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                LazyColumn(Modifier.heightIn(max = 360.dp)) {
                    items(results) { (symbol, name) ->
                        Row(
                            Modifier.fillMaxWidth().padding(vertical = 12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(name, color = TextCol)
                            TextButton(onClick = { onPick(symbol) }) { Text(symbol, color = Teal) }
                        }
                    }
                }
            }
        },
    )
}

@Composable
private fun SettingsDialog(
    state: AppState,
    onSave: (Double, Double, Int, Int, String) -> Unit,
    onReliability: () -> Unit,
    onClose: () -> Unit,
) {
    var capital by remember { mutableStateOf(state.capital.toInt().toString()) }
    var risk by remember { mutableStateOf(String.format(Locale.US, "%.1f", state.riskPct * 100)) }
    var qs by remember { mutableStateOf(state.quietStart.toString()) }
    var qe by remember { mutableStateOf(state.quietEnd.toString()) }
    var interval by remember { mutableStateOf(state.interval) }

    AlertDialog(
        onDismissRequest = onClose,
        confirmButton = {
            Button(onClick = {
                onSave(
                    capital.toDoubleOrNull() ?: 1000.0,
                    (risk.toDoubleOrNull() ?: 1.0) / 100.0,
                    qs.toIntOrNull() ?: 23,
                    qe.toIntOrNull() ?: 7,
                    interval,
                )
            }) { Text("Guardar") }
        },
        dismissButton = { TextButton(onClick = onClose) { Text("Cancelar") } },
        title = { Text("Ajustes") },
        text = {
            Column {
                OutlinedTextField(capital, { capital = it }, label = { Text("Capital de referencia (USD)") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(risk, { risk = it }, label = { Text("Riesgo por operación (%)") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(qs, { qs = it }, label = { Text("Silencio desde") }, singleLine = true, modifier = Modifier.weight(1f))
                    OutlinedTextField(qe, { qe = it }, label = { Text("hasta") }, singleLine = true, modifier = Modifier.weight(1f))
                }
                Spacer(Modifier.height(12.dp))
                Text("Temporalidad", color = Muted, fontSize = 12.sp)
                Assets.INTERVALS.forEach { (key, label) ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = interval == key, onClick = { interval = key })
                        Text(label, color = TextCol)
                    }
                }
                Spacer(Modifier.height(8.dp))
                OutlinedButton(onClick = onReliability, modifier = Modifier.fillMaxWidth()) {
                    Text("Mejorar fiabilidad de avisos")
                }
                Text(
                    "Permite alarmas exactas y quitar la optimización de batería, para que los avisos lleguen a tiempo.",
                    color = Muted, fontSize = 11.sp,
                )
            }
        },
    )
}
