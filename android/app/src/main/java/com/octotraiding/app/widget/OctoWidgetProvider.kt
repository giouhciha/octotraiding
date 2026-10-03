package com.octotraiding.app.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.widget.RemoteViews
import com.octotraiding.app.MainActivity
import com.octotraiding.app.R
import com.octotraiding.app.data.Store
import com.octotraiding.app.engine.Config
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
            if (detail != null) {
                views.setTextViewText(R.id.widget_price, money(detail.price))
                val plain = Config.SIGNAL_PLAIN[detail.signal] ?: detail.signal
                views.setTextViewText(R.id.widget_action, "● $plain")
                views.setTextColor(R.id.widget_action, signalColor(detail.signal))
            } else {
                views.setTextViewText(R.id.widget_price, "—")
                views.setTextViewText(R.id.widget_action, "Sin datos")
                views.setTextColor(R.id.widget_action, 0xFFE6ECF5.toInt())
            }

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

        private fun signalColor(signal: String): Int = when (signal) {
            "COMPRA_FUERTE" -> 0xFF22C55E.toInt()
            "COMPRA" -> 0xFF2DD4BF.toInt()
            "VENTA" -> 0xFFF59E0B.toInt()
            "VENTA_FUERTE" -> 0xFFEF4444.toInt()
            else -> 0xFFE6ECF5.toInt()
        }
    }
}
