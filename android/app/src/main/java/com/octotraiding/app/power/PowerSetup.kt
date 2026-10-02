package com.octotraiding.app.power

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import android.app.AlarmManager

/** Ayuda a que Android no duerma la app: alarma exacta y batería sin optimizar. */
object PowerSetup {

    // --- Batería ---
    fun isBatteryOptimized(context: Context): Boolean {
        val pm = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        return !pm.isIgnoringBatteryOptimizations(context.packageName)
    }

    fun requestBatteryExemption(context: Context) {
        if (!isBatteryOptimized(context)) return
        try {
            val intent = Intent(
                Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                Uri.parse("package:${context.packageName}"),
            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
        } catch (_: Exception) {
            try {
                context.startActivity(
                    Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                )
            } catch (_: Exception) {
            }
        }
    }

    // --- Alarmas exactas ---
    fun canScheduleExact(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return true
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        return am.canScheduleExactAlarms()
    }

    fun requestExactAlarm(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !canScheduleExact(context)) {
            try {
                context.startActivity(
                    Intent(
                        Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,
                        Uri.parse("package:${context.packageName}"),
                    ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                )
            } catch (_: Exception) {
            }
        }
    }
}
