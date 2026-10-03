package com.octotraiding.app.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Shader
import android.widget.RemoteViews
import com.octotraiding.app.MainActivity
import com.octotraiding.app.R
import com.octotraiding.app.data.Store
import com.octotraiding.app.logic.Actions
import java.util.Locale

/** Widget de pantalla de inicio: activo, precio y acción; fondo de color y opacidad configurables. */
class OctoWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        ids.forEach { render(context, manager, it) }
    }

    override fun onAppWidgetOptionsChanged(
        context: Context,
        manager: AppWidgetManager,
        id: Int,
        newOptions: android.os.Bundle,
    ) {
        render(context, manager, id)
    }

    companion object {

        fun refresh(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, OctoWidgetProvider::class.java))
            ids.forEach { render(context, manager, it) }
        }

        private fun render(context: Context, manager: AppWidgetManager, id: Int) {
            val views = RemoteViews(context.packageName, R.layout.widget_octo)

            val settings = Store.settings(context)
            val detail = Store.detail(context)
            val position = Store.position(context)
            val (action, _) = Actions.compute(detail, position)

            // Fondo: color elegido + porcentaje de opacidad.
            val base = try {
                android.graphics.Color.parseColor(Store.widgetColor(context))
            } catch (_: Exception) {
                android.graphics.Color.parseColor("#121B2E")
            }
            val alpha = (Store.widgetOpacity(context) * 255 / 100)
            val argb = (base and 0x00FFFFFF) or (alpha shl 24)

            val (wPx, hPx) = widgetSizePx(context, manager, id)
            views.setImageViewBitmap(R.id.widget_bg_image, roundedRect(wPx, hPx, argb, context))

            views.setTextViewText(R.id.widget_symbol, settings.symbol)
            val score = detail?.score ?: 0.0
            if (detail != null) {
                views.setTextViewText(R.id.widget_price, money(detail.price))
                views.setTextViewText(R.id.widget_action, action)
            } else {
                views.setTextViewText(R.id.widget_price, "—")
                views.setTextViewText(R.id.widget_action, "Sin datos")
            }
            views.setTextColor(R.id.widget_action, actionColor(action))

            val thermoH = (16 * context.resources.displayMetrics.density).toInt().coerceAtLeast(12)
            views.setImageViewBitmap(R.id.widget_thermo, thermoBitmap(wPx, thermoH, score, context))

            val intent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP
            }
            val pi = PendingIntent.getActivity(
                context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            views.setOnClickPendingIntent(R.id.widget_root, pi)

            manager.updateAppWidget(id, views)
        }

        private fun widgetSizePx(context: Context, manager: AppWidgetManager, id: Int): Pair<Int, Int> {
            val density = context.resources.displayMetrics.density
            val opts = manager.getAppWidgetOptions(id)
            val wDp = opts.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH).takeIf { it > 0 } ?: 200
            val hDp = opts.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT).takeIf { it > 0 } ?: 120
            return Pair((wDp * density).toInt().coerceAtLeast(60), (hDp * density).toInt().coerceAtLeast(60))
        }

        private fun roundedRect(w: Int, h: Int, color: Int, context: Context): Bitmap {
            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bmp)
            val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color }
            val radius = 20f * context.resources.displayMetrics.density
            canvas.drawRoundRect(RectF(0f, 0f, w.toFloat(), h.toFloat()), radius, radius, paint)
            return bmp
        }

        private fun money(v: Double): String {
            val dec = if (v >= 1000) 0 else 2
            return "$" + String.format(Locale.US, "%,.${dec}f", v)
        }

        private fun actionColor(action: String): Int = when {
            action.contains("COMPRAR") -> 0xFF22C55E.toInt()
            action.contains("VIGILAR") -> 0xFF2DD4BF.toInt()
            action.contains("VENDER") -> 0xFFEF4444.toInt()
            else -> 0xFFE6ECF5.toInt()
        }

        private fun scoreColor(score: Double): Int = when {
            score >= 6 -> 0xFF22C55E.toInt()
            score >= 3 -> 0xFF2DD4BF.toInt()
            score <= -6 -> 0xFFEF4444.toInt()
            score <= -3 -> 0xFFF59E0B.toInt()
            else -> 0xFF93A4C0.toInt()
        }

        /** Barra tipo termómetro (rojo→ámbar→verde) con un marcador en el score. */
        private fun thermoBitmap(w: Int, h: Int, score: Double, context: Context): Bitmap {
            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bmp)
            val paint = Paint(Paint.ANTI_ALIAS_FLAG)
            val density = context.resources.displayMetrics.density
            val barH = 6f * density
            val cy = h / 2f
            val radius = (h / 2f - 1f).coerceAtLeast(3f)

            paint.shader = LinearGradient(
                0f, 0f, w.toFloat(), 0f,
                intArrayOf(0xFFEF4444.toInt(), 0xFFF59E0B.toInt(), 0xFF22C55E.toInt()),
                null, Shader.TileMode.CLAMP,
            )
            canvas.drawRoundRect(
                RectF(0f, cy - barH / 2f, w.toFloat(), cy + barH / 2f),
                barH / 2f, barH / 2f, paint,
            )

            val pct = ((score + 10.0) / 20.0).coerceIn(0.0, 1.0).toFloat()
            val x = radius + (w - 2f * radius) * pct
            paint.shader = null
            paint.color = 0xFFFFFFFF.toInt()
            canvas.drawCircle(x, cy, radius, paint)
            paint.color = scoreColor(score)
            canvas.drawCircle(x, cy, radius * 0.66f, paint)
            return bmp
        }
    }
}
