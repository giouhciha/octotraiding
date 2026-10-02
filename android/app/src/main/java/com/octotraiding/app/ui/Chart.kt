package com.octotraiding.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.octotraiding.app.engine.Candle
import com.octotraiding.app.engine.Position
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

private val ChartBg = Color(0xFF0F1830)
private val ChartLine = Color(0xFF24304A)
private val ChartMuted = Color(0xFF93A4C0)
private val ChartGreen = Color(0xFF22C55E)
private val ChartRed = Color(0xFFEF4444)

/** Gráfica de velas (candlestick) dibujada a mano, con entrada y stop del usuario. */
@Composable
fun PriceChart(
    symbol: String,
    candles: List<Candle>,
    position: Position?,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier.fillMaxWidth().background(Color(0xFF121B2E), RoundedCornerShape(16.dp)).padding(16.dp),
    ) {
        Text("PRECIO · $symbol", color = ChartMuted, fontSize = 12.sp)
        Spacer(Modifier.height(8.dp))
        if (candles.isEmpty()) {
            Text("Sin datos de gráfica.", color = ChartMuted, fontSize = 13.sp)
            return@Column
        }

        val measurer = rememberTextMeasurer()
        var minP = candles.minOf { it.low }
        var maxP = candles.maxOf { it.high }
        position?.let {
            minP = min(minP, min(it.entry, it.stop))
            maxP = max(maxP, max(it.entry, it.stop))
        }
        val range = (maxP - minP).coerceAtLeast(1e-9)

        Canvas(Modifier.fillMaxWidth().height(200.dp)) {
            val w = size.width
            val h = size.height
            val rightPad = 58.dp.toPx()
            val chartW = w - rightPad
            val step = chartW / candles.size
            val bodyW = (step * 0.6f).coerceAtLeast(1f)

            fun y(price: Double): Float = (h * (1f - ((price - minP) / range))).toFloat()

            // Rejilla + etiquetas de precio
            val lines = 4
            for (i in 0..lines) {
                val price = minP + range * i / lines
                val yy = y(price)
                drawLine(ChartLine, Offset(0f, yy), Offset(chartW, yy), strokeWidth = 1f)
                drawText(
                    textMeasurer = measurer,
                    text = String.format(Locale.US, "%,.0f", price),
                    topLeft = Offset(chartW + 6f, yy - 7f),
                    style = TextStyle(color = ChartMuted, fontSize = 10.sp),
                )
            }

            // Velas
            candles.forEachIndexed { i, c ->
                val cx = i * step + step / 2f
                val color = if (c.close >= c.open) ChartGreen else ChartRed
                drawLine(color, Offset(cx, y(c.high)), Offset(cx, y(c.low)), strokeWidth = 1.5f)
                val top = y(max(c.open, c.close))
                val bot = y(min(c.open, c.close))
                drawRect(
                    color = color,
                    topLeft = Offset(cx - bodyW / 2f, top),
                    size = Size(bodyW, (bot - top).coerceAtLeast(1f)),
                )
            }

            // Entrada y stop del usuario (líneas punteadas)
            position?.let { p ->
                val dash = PathEffect.dashPathEffect(floatArrayOf(10f, 10f), 0f)
                if (p.entry in minP..maxP) {
                    drawLine(ChartGreen, Offset(0f, y(p.entry)), Offset(chartW, y(p.entry)), strokeWidth = 1.5f, pathEffect = dash)
                }
                if (p.stop in minP..maxP) {
                    drawLine(ChartRed, Offset(0f, y(p.stop)), Offset(chartW, y(p.stop)), strokeWidth = 1.5f, pathEffect = dash)
                }
            }
        }

        Spacer(Modifier.height(6.dp))
        Row {
            Text("Últimas ${candles.size} velas", color = ChartMuted, fontSize = 11.sp)
            if (position != null) {
                Spacer(Modifier.width(12.dp))
                Text("— entrada  -- stop", color = ChartMuted, fontSize = 11.sp)
            }
        }
    }
}
