package com.octotraiding.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import com.octotraiding.app.data.Store
import com.octotraiding.app.notif.Notifier
import com.octotraiding.app.power.AlarmScheduler
import com.octotraiding.app.power.PowerSetup
import com.octotraiding.app.ui.AppViewModel
import com.octotraiding.app.ui.OctoApp
import com.octotraiding.app.work.MonitorWorker

class MainActivity : ComponentActivity() {

    private val vm: AppViewModel by viewModels()

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        Notifier.ensureChannel(this)
        MonitorWorker.schedule(this)
        AlarmScheduler.scheduleNext(this)
        requestNotificationPermission()
        setupReliability()

        setContent { OctoApp(vm) }
    }

    override fun onResume() {
        super.onResume()
        // Al volver a la app, refrescamos: así se refleja lo que pasó en segundo plano.
        vm.onResume()
    }

    /** Pide (una vez) que Android no duerma la app, para que los avisos lleguen a tiempo. */
    private fun setupReliability() {
        if (!Store.reliabilityAsked(this)) {
            PowerSetup.requestExactAlarm(this)
            PowerSetup.requestBatteryExemption(this)
            Store.setReliabilityAsked(this, true)
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (!granted) permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
