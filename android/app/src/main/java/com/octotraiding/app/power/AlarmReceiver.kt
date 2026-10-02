package com.octotraiding.app.power

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.octotraiding.app.work.MonitorWorker

/** Se dispara cada hora con la alarma exacta. */
class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        MonitorWorker.runNow(context)
        AlarmScheduler.scheduleNext(context)
    }
}

/** Al reiniciar el teléfono, vuelve a programar todo. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            MonitorWorker.schedule(context)
            AlarmScheduler.scheduleNext(context)
        }
    }
}
