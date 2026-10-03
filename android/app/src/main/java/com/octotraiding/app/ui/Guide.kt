package com.octotraiding.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.Locale

private val GBg = Color(0xFF0B1220)
private val GCard = Color(0xFF121B2E)
private val GLine = Color(0xFF24304A)
private val GText = Color(0xFFE6ECF5)
private val GMuted = Color(0xFF93A4C0)
private val GGreen = Color(0xFF22C55E)
private val GTeal = Color(0xFF2DD4BF)
private val GRed = Color(0xFFEF4444)
private val GAmber = Color(0xFFF59E0B)

/** Pantalla de ayuda: explica cada señal y muestra un 'termómetro' del score actual. */
@Composable
fun GuideScreen(score: Double?, action: String, hint: String, onBack: () -> Unit) {
    Column(
        Modifier.fillMaxSize().background(GBg).statusBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver", tint = GText)
            }
            Text("Cómo leer las señales", color = GText, fontWeight = FontWeight.Bold, fontSize = 20.sp)
        }

        Spacer(Modifier.height(8.dp))

        // Termómetro del score
        Column(
            Modifier.fillMaxWidth().background(GCard, RoundedCornerShape(16.dp)).padding(16.dp),
        ) {
            Text("TERMÓMETRO DEL MERCADO", color = GMuted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(10.dp))
            val s = score ?: 0.0
            Text(
                "Puntuación actual: " + (if (s >= 0) "+" else "") + String.format(Locale.US, "%.2f", s),
                color = GText, fontWeight = FontWeight.Bold, fontSize = 16.sp,
            )
            Spacer(Modifier.height(8.dp))
            Thermometer(s)
            Spacer(Modifier.height(8.dp))
            Text(
                "El marcador blanco muestra dónde está el mercado hoy. Mientras más a la derecha, más favorable comprar; más a la izquierda, más favorable vender.",
                color = GMuted, fontSize = 12.sp,
            )
        }

        Spacer(Modifier.height(12.dp))

        // Estado actual
        Column(
            Modifier.fillMaxWidth().background(GCard, RoundedCornerShape(16.dp)).padding(16.dp),
        ) {
            Text("AHORA MISMO", color = GMuted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(6.dp))
            Text(action, color = guideActionColor(action), fontWeight = FontWeight.Bold, fontSize = 22.sp)
            Text(hint, color = GText, fontSize = 13.sp)
        }

        Spacer(Modifier.height(12.dp))

        Text("LAS 5 SEÑALES", color = GMuted, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))

        SignalRow(
            range = "+6 a +10", name = "COMPRA FUERTE", color = GGreen,
            action = "COMPRAR",
            detail = "Todo apunta a favor y la tendencia diaria acompaña. Es la única señal pensada para entrar. Con stop definido.",
        )
        SignalRow(
            range = "+3 a +6", name = "COMPRA (moderada)", color = GTeal,
            action = "VIGILAR (no entrar aún)",
            detail = "El mercado se pone interesante, pero aún no hay ventaja clara. Es información, no orden de compra. Espera la señal fuerte.",
        )
        SignalRow(
            range = "-3 a +3", name = "ESPERAR / MANTENER", color = GMuted,
            action = "NO HACER NADA",
            detail = "Sin ventaja clara. Si no tienes la moneda: espera. Si ya la tienes: mantén; tu salida es el stop o una venta fuerte.",
        )
        SignalRow(
            range = "-6 a -3", name = "VENTA (moderada)", color = GAmber,
            action = "PRECAUCIÓN",
            detail = "El mercado se debilita. Si tienes posición, vigila tu stop. No es aún una orden de venta.",
        )
        SignalRow(
            range = "-10 a -6", name = "VENTA FUERTE", color = GRed,
            action = "VENDER",
            detail = "El conjunto se gira a la baja. Es señal para salir y proteger el capital.",
        )

        Spacer(Modifier.height(16.dp))

        // Regla de oro
        Column(
            Modifier.fillMaxWidth().background(Color(0xFF0F1830), RoundedCornerShape(16.dp)).padding(16.dp),
        ) {
            Text("LA REGLA DE ORO", color = GTeal, fontSize = 12.sp, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(6.dp))
            Text(
                "• Si NO tienes la moneda: solo compras en COMPRA FUERTE.\n" +
                    "• Si YA la tienes: no vendes por señales moderadas; sales por el STOP o por VENTA FUERTE.\n" +
                    "• Una compra moderada no es una orden de compra.",
                color = GText, fontSize = 13.sp,
            )
        }

        Spacer(Modifier.height(16.dp))
        Text(
            "Análisis técnico automatizado. No es asesoramiento financiero. El pasado no garantiza el futuro.",
            color = Color(0xFF6B7A97), fontSize = 11.sp,
        )
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun Thermometer(score: Double) {
    val pct = ((score + 10) / 20).coerceIn(0.0, 1.0).toFloat()
    Canvas(Modifier.fillMaxWidth().height(40.dp)) {
        val barH = 16.dp.toPx()
        val cy = size.height / 2f
        drawRoundRect(
            brush = Brush.horizontalGradient(listOf(GRed, GAmber, GGreen)),
            topLeft = Offset(0f, cy - barH / 2f),
            size = Size(size.width, barH),
            cornerRadius = CornerRadius(barH / 2f),
        )
        val x = size.width * pct
        drawCircle(Color.White, radius = 9.dp.toPx(), center = Offset(x, cy))
        drawCircle(colorForScore(score), radius = 6.dp.toPx(), center = Offset(x, cy))
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text("−10", color = GMuted, fontSize = 10.sp)
        Text("−6", color = GMuted, fontSize = 10.sp)
        Text("0", color = GMuted, fontSize = 10.sp)
        Text("+6", color = GMuted, fontSize = 10.sp)
        Text("+10", color = GMuted, fontSize = 10.sp)
    }
}

@Composable
private fun SignalRow(range: String, name: String, color: Color, action: String, detail: String) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 6.dp)
            .background(GCard, RoundedCornerShape(14.dp)).padding(14.dp),
    ) {
        Box(
            Modifier.size(10.dp).padding(top = 4.dp)
                .background(color, RoundedCornerShape(50)),
        )
        Spacer(Modifier.width(12.dp))
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(name, color = color, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Spacer(Modifier.width(8.dp))
                Text(range, color = GMuted, fontSize = 11.sp)
            }
            Text(action, color = GText, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            Spacer(Modifier.height(2.dp))
            Text(detail, color = GMuted, fontSize = 12.sp)
        }
    }
}

private fun colorForScore(score: Double): Color = when {
    score >= 6 -> GGreen
    score >= 3 -> GTeal
    score <= -6 -> GRed
    score <= -3 -> GAmber
    else -> GMuted
}

private fun guideActionColor(a: String): Color = when {
    a.contains("COMPRAR") -> GGreen
    a.contains("VENDER") -> GRed
    else -> GMuted
}
