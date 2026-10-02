package com.octotraiding.app.power

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build

/** Programa una alarma exacta cada hora para revisar el mercado a tiempo. */
object AlarmScheduler {

    private const val REQUEST_CODE = 1001
    private const val MINUTE_OFFSET = 2 * 60_000L // 2 min después de la hora

    fun scheduleNext(context: Context) {
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pi = pendingIntent(context)
        val now = System.currentTimeMillis()
        val nextHour = ((now / 3_600_000L) + 1) * 3_600_000L
        val triggerAt = nextHour + MINUTE_OFFSET

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !am.canScheduleExactAlarms()) {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi)
            } else {
                am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi)
            }
        } catch (_: SecurityException) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pi)
        }
    }

    fun cancel(context: Context) {
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        am.cancel(pendingIntent(context))
    }

    private fun pendingIntent(context: Context): PendingIntent {
        val intent = Intent(context, AlarmReceiver::class.java)
        return PendingIntent.getBroadcast(
            context,
            REQUEST_CODE,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
}
