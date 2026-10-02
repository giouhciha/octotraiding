package com.octotraiding.app.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import com.octotraiding.app.MainActivity
import com.octotraiding.app.R
import com.octotraiding.app.data.Store
import com.octotraiding.app.logic.Actions
import java.util.Locale

/** Widget de pantalla de inicio: muestra el activo, su precio y la acción. */
class OctoWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        ids.forEach { render(context, manager, it) }
    }

    companion object {

        /** Actualiza todos los widgets colocados. Se llama al refrescar datos. */
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

            views.setTextViewText(R.id.widget_symbol, settings.symbol)
            if (detail != null) {
                views.setTextViewText(R.id.widget_price, money(detail.price))
                views.setTextViewText(R.id.widget_action, action)
                views.setTextViewText(R.id.widget_hint, "Señal: ${detail.signal.replace('_', ' ').lowercase().replaceFirstChar { it.titlecase() }}")
            } else {
                views.setTextViewText(R.id.widget_price, "—")
                views.setTextViewText(R.id.widget_action, "Sin datos")
                views.setTextViewText(R.id.widget_hint, "Abre la app para analizar")
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

        private fun money(v: Double): String {
            val dec = if (v >= 1000) 0 else 2
            return "$" + String.format(Locale.US, "%,.${dec}f", v)
        }
    }
}
