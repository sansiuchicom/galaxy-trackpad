package com.galaxytrackpad.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.View
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.galaxytrackpad.app.bluetooth.RfcommPadServer
import com.galaxytrackpad.app.databinding.ActivityMainBinding

/**
 * WebView shell: USB pad when Windows HTTP/WS is up; Bluetooth fallback on USB loss.
 *
 * Cable unplug is detected via USB_STATE (WebSocket often stays half-open).
 * GalaxyShell is a backup when WS closes cleanly.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val mainHandler = Handler(Looper.getMainLooper())
    private var pageHealthy = false
    private var destroyed = false
    private var btMode = false
    private var unhealthySince = 0L
    private var usbReceiverRegistered = false

    private var btServer: RfcommPadServer? = null

    private val enterBtAfterUsbLost = Runnable {
        if (destroyed || btMode) return@Runnable
        enterBluetoothPad("USB unplugged")
    }

    private val usbReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != ACTION_USB_STATE) return
            val connected = intent.getBooleanExtra("connected", true)
            if (!connected) {
                scheduleEnterBluetooth()
            }
        }
    }

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            if (result.values.all { it }) {
                enterBluetoothPad("permission granted")
            } else {
                Toast.makeText(this, "Bluetooth permission denied", Toast.LENGTH_SHORT).show()
            }
        }

    private val watchdogRunnable = object : Runnable {
        override fun run() {
            if (destroyed || btMode || pageHealthy) return
            if (unhealthySince == 0L) {
                unhealthySince = SystemClock.elapsedRealtime()
            } else if (SystemClock.elapsedRealtime() - unhealthySince >= BT_FALLBACK_AFTER_MS) {
                enterBluetoothPad("USB page unavailable")
                return
            }
            loadTrackpad()
            mainHandler.postDelayed(this, RELOAD_DELAY_MS)
        }
    }

    private val btUsbProbeRunnable = object : Runnable {
        override fun run() {
            if (destroyed || !btMode) return
            probeUsbOnce()
            mainHandler.postDelayed(this, BT_USB_PROBE_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        WindowCompat.setDecorFitsSystemWindows(window, false)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        hideSystemBars()
        setupWebView(binding.webView)
        registerUsbReceiver()

        loadTrackpad()
        startWatchdog()

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    // Dedicated input device: ignore back.
                }
            },
        )
    }

    override fun onResume() {
        super.onResume()
        hideSystemBars()
        binding.webView.onResume()
        if (btMode) {
            ensureBtServer()
            probeUsbOnce()
            startBtUsbProbe()
        } else if (!pageHealthy) {
            startWatchdog()
            loadTrackpad()
        } else {
            binding.webView.evaluateJavascript(JS_RESUME_SYNC, null)
        }
    }

    override fun onPause() {
        binding.webView.evaluateJavascript(JS_RELEASE_ALL, null)
        binding.webView.onPause()
        super.onPause()
    }

    override fun onStop() {
        binding.webView.evaluateJavascript(JS_RELEASE_ALL, null)
        super.onStop()
    }

    override fun onDestroy() {
        destroyed = true
        mainHandler.removeCallbacks(watchdogRunnable)
        mainHandler.removeCallbacks(enterBtAfterUsbLost)
        mainHandler.removeCallbacks(btUsbProbeRunnable)
        unregisterUsbReceiver()
        btServer?.stop()
        btServer = null
        binding.webView.apply {
            stopLoading()
            loadUrl("about:blank")
            removeAllViews()
            destroy()
        }
        super.onDestroy()
    }

    private fun registerUsbReceiver() {
        if (usbReceiverRegistered) return
        val filter = IntentFilter(ACTION_USB_STATE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(usbReceiver, filter, Context.RECEIVER_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(usbReceiver, filter)
        }
        usbReceiverRegistered = true
    }

    private fun unregisterUsbReceiver() {
        if (!usbReceiverRegistered) return
        try {
            unregisterReceiver(usbReceiver)
        } catch (_: Exception) {
        }
        usbReceiverRegistered = false
    }

    private fun scheduleEnterBluetooth() {
        if (destroyed || btMode) return
        markUnhealthy()
        mainHandler.removeCallbacks(enterBtAfterUsbLost)
        mainHandler.postDelayed(enterBtAfterUsbLost, USB_LOST_GRACE_MS)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView(webView: WebView) {
        webView.setBackgroundColor(Color.parseColor("#0e1116"))
        webView.isVerticalScrollBarEnabled = false
        webView.isHorizontalScrollBarEnabled = false
        webView.overScrollMode = View.OVER_SCROLL_NEVER
        webView.addJavascriptInterface(PadBridge(), "GalaxyBT")
        webView.addJavascriptInterface(ShellBridge(), "GalaxyShell")

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_NO_CACHE
            mediaPlaybackRequiresUserGesture = false
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            allowFileAccess = true
            allowContentAccess = true
            setSupportZoom(false)
            builtInZoomControls = false
            displayZoomControls = false
            useWideViewPort = true
            loadWithOverviewMode = true
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                if (url != null && url.startsWith(TRACKPAD_ORIGIN)) {
                    leaveBluetoothPad("USB pad ready")
                    markHealthy()
                    val ver = BuildConfig.VERSION_NAME
                    view?.evaluateJavascript(
                        """
                        (function(){
                          var el = document.getElementById('settingsVersion');
                          if (el) el.textContent = 'App version: $ver';
                        })();
                        """.trimIndent(),
                        null,
                    )
                }
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?,
            ) {
                if (request?.isForMainFrame != true) return
                if (btMode) return
                markUnhealthy()
                showWaitingPage()
                startWatchdog()
            }
        }
        webView.webChromeClient = WebChromeClient()
    }

    inner class PadBridge {
        @JavascriptInterface
        fun sendPacket(json: String) {
            btServer?.sendPacketJson(json)
        }
    }

    inner class ShellBridge {
        @JavascriptInterface
        fun onUsbLost() {
            runOnUiThread { scheduleEnterBluetooth() }
        }

        @JavascriptInterface
        fun onUsbRestored() {
            runOnUiThread {
                if (destroyed) return@runOnUiThread
                mainHandler.removeCallbacks(enterBtAfterUsbLost)
                if (!btMode) markHealthy()
            }
        }
    }

    private fun ensureBtServer() {
        if (btServer == null) {
            btServer = RfcommPadServer(
                this,
                onFramed = { linked ->
                    runOnUiThread {
                        binding.webView.evaluateJavascript(
                            "window.__gtBtLinked && window.__gtBtLinked(${linked})",
                            null,
                        )
                    }
                },
            )
        }
        if (btServer?.hasBluetoothPermission() != true) {
            requestBtPerms()
            return
        }
        btServer?.start()
    }

    private fun requestBtPerms() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            enterBluetoothPad("legacy BT")
            return
        }
        permissionLauncher.launch(
            arrayOf(
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.BLUETOOTH_ADVERTISE,
            ),
        )
    }

    private fun enterBluetoothPad(reason: String) {
        if (destroyed) return
        if (btMode) {
            ensureBtServer()
            return
        }
        btMode = true
        pageHealthy = false
        mainHandler.removeCallbacks(watchdogRunnable)
        mainHandler.removeCallbacks(enterBtAfterUsbLost)
        ensureBtServer()
        binding.webView.loadUrl(BT_PAD_URL)
        Toast.makeText(this, "Bluetooth pad ($reason)", Toast.LENGTH_SHORT).show()
        startBtUsbProbe()
    }

    private fun leaveBluetoothPad(reason: String) {
        if (!btMode) return
        btMode = false
        btServer?.stop()
        unhealthySince = 0L
        mainHandler.removeCallbacks(btUsbProbeRunnable)
    }

    private fun startBtUsbProbe() {
        mainHandler.removeCallbacks(btUsbProbeRunnable)
        mainHandler.postDelayed(btUsbProbeRunnable, BT_USB_PROBE_MS)
    }

    private fun probeUsbOnce() {
        Thread {
            val ok = try {
                val url = java.net.URL(TRACKPAD_ORIGIN + "/")
                val conn = url.openConnection() as java.net.HttpURLConnection
                conn.connectTimeout = 700
                conn.readTimeout = 700
                conn.requestMethod = "GET"
                val code = conn.responseCode
                conn.disconnect()
                code in 200..399
            } catch (_: Exception) {
                false
            }
            if (!ok) return@Thread
            runOnUiThread {
                if (destroyed || !btMode) return@runOnUiThread
                leaveBluetoothPad("USB healthy")
                loadTrackpad()
                startWatchdog()
            }
        }.start()
    }

    private fun markHealthy() {
        pageHealthy = true
        unhealthySince = 0L
        mainHandler.removeCallbacks(watchdogRunnable)
        mainHandler.removeCallbacks(enterBtAfterUsbLost)
    }

    private fun markUnhealthy() {
        pageHealthy = false
        if (unhealthySince == 0L) {
            unhealthySince = SystemClock.elapsedRealtime()
        }
    }

    private fun startWatchdog() {
        mainHandler.removeCallbacks(watchdogRunnable)
        mainHandler.postDelayed(watchdogRunnable, RELOAD_DELAY_MS)
    }

    private fun loadTrackpad() {
        if (destroyed || btMode) return
        binding.webView.loadUrl(TRACKPAD_URL)
    }

    private fun showWaitingPage() {
        if (destroyed || btMode) return
        val current = binding.webView.url.orEmpty()
        if (current.startsWith(TRACKPAD_ORIGIN)) return
        if (current == WAITING_URL || current.endsWith("waiting.html")) return
        binding.webView.loadUrl(WAITING_URL)
    }

    private fun hideSystemBars() {
        val controller = WindowInsetsControllerCompat(window, window.decorView)
        controller.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        controller.hide(WindowInsetsCompat.Type.systemBars())
    }

    companion object {
        private const val ACTION_USB_STATE = "android.hardware.usb.action.USB_STATE"
        private const val TRACKPAD_ORIGIN = "http://127.0.0.1:8765"
        const val TRACKPAD_URL = "http://127.0.0.1:8765/touchpad_v04.html?v=093"
        private const val WAITING_URL = "file:///android_asset/waiting.html"
        private const val BT_PAD_URL = "file:///android_asset/touchpad_bt.html"
        private const val RELOAD_DELAY_MS = 2000L
        private const val BT_FALLBACK_AFTER_MS = 8000L
        private const val USB_LOST_GRACE_MS = 1500L
        private const val BT_USB_PROBE_MS = 15_000L

        private const val JS_RELEASE_ALL = """
            (function () {
              try {
                if (typeof releaseAllContacts === 'function') {
                  releaseAllContacts();
                } else if (typeof pointers !== 'undefined') {
                  pointers.clear();
                  if (typeof send === 'function') send('up');
                }
              } catch (e) {}
            })();
        """

        private const val JS_RESUME_SYNC = """
            (function () {
              try {
                if (typeof releaseAllContacts === 'function') {
                  releaseAllContacts();
                }
                if (typeof connect === 'function') {
                  connect();
                }
                if (socket && socket.readyState === 1 && typeof socket.send === 'function') {
                  socket.send(JSON.stringify({ type: 'hello' }));
                }
              } catch (e) {}
            })();
        """
    }
}
