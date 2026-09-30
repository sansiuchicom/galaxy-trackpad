package com.galaxytrackpad.app

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
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
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.galaxytrackpad.app.bluetooth.RfcommPadClient
import com.galaxytrackpad.app.databinding.ActivityMainBinding

/**
 * One transport per launch, chosen on this screen: USB or Bluetooth. No mid-session switch.
 * For Bluetooth the user picks a paired PC; the PC engine is always advertising.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val mainHandler = Handler(Looper.getMainLooper())
    private var pageHealthy = false
    private var destroyed = false
    private var mode: String? = null

    private var btClient: RfcommPadClient? = null
    private var btDevice: BluetoothDevice? = null

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            if (mode != MODE_BT) return@registerForActivityResult
            if (result.values.all { it }) {
                pickPc()
            } else {
                Toast.makeText(this, "Bluetooth permission is needed to reach the PC", Toast.LENGTH_LONG).show()
                backToChooser()
            }
        }

    private val watchdogRunnable = object : Runnable {
        override fun run() {
            if (destroyed || mode != MODE_USB || pageHealthy) return
            loadTrackpad()
            mainHandler.postDelayed(this, RELOAD_DELAY_MS)
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

        binding.chooseUsb.setOnClickListener { begin(MODE_USB) }
        binding.chooseBluetooth.setOnClickListener { begin(MODE_BT) }

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
        if (mode == MODE_USB && pageHealthy) {
            binding.webView.evaluateJavascript(JS_RESUME_SYNC, null)
        } else if (mode == MODE_USB) {
            startWatchdog()
        }
    }

    override fun onPause() {
        if (mode != null) {
            binding.webView.evaluateJavascript(JS_RELEASE_ALL, null)
        }
        binding.webView.onPause()
        super.onPause()
    }

    override fun onStop() {
        if (mode != null) {
            binding.webView.evaluateJavascript(JS_RELEASE_ALL, null)
        }
        super.onStop()
    }

    override fun onDestroy() {
        destroyed = true
        mainHandler.removeCallbacks(watchdogRunnable)
        btClient?.shutdown()
        btClient = null
        binding.webView.apply {
            stopLoading()
            loadUrl("about:blank")
            removeAllViews()
            destroy()
        }
        super.onDestroy()
    }

    private fun begin(selected: String) {
        if (mode != null) return
        mode = selected
        binding.chooser.visibility = View.GONE
        binding.webView.visibility = View.VISIBLE
        if (selected == MODE_BT) {
            binding.webView.loadUrl(BT_PAD_URL)
            if (hasBluetoothPermission()) {
                pickPc()
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                permissionLauncher.launch(arrayOf(Manifest.permission.BLUETOOTH_CONNECT))
            }
        } else {
            loadTrackpad()
            startWatchdog()
        }
    }

    /** Only before anything connected: the user backed out of the PC picker. */
    private fun backToChooser() {
        mode = null
        binding.webView.loadUrl("about:blank")
        binding.webView.visibility = View.GONE
        binding.chooser.visibility = View.VISIBLE
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView(webView: WebView) {
        webView.setBackgroundColor(Color.parseColor("#0e1116"))
        webView.isVerticalScrollBarEnabled = false
        webView.isHorizontalScrollBarEnabled = false
        webView.overScrollMode = View.OVER_SCROLL_NEVER
        webView.addJavascriptInterface(PadBridge(), "GalaxyBT")

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
                val isPad = url != null &&
                    (url.startsWith(TRACKPAD_ORIGIN) || url.startsWith(BT_PAD_URL))
                if (isPad) {
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
                if (mode == MODE_BT && btClient?.isLinked() == true) {
                    signalLinked(true)
                }
                if (mode != MODE_USB) return
                if (url != null && url.startsWith(TRACKPAD_ORIGIN)) {
                    pageHealthy = true
                    mainHandler.removeCallbacks(watchdogRunnable)
                }
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?,
            ) {
                if (mode != MODE_USB) return
                if (request?.isForMainFrame != true) return
                pageHealthy = false
                showWaitingPage()
                startWatchdog()
            }
        }
        webView.webChromeClient = WebChromeClient()
    }

    inner class PadBridge {
        @JavascriptInterface
        fun sendPacket(json: String) {
            if (mode != MODE_BT) return
            btClient?.sendPacketJson(json)
        }
    }

    private fun hasBluetoothPermission(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.S ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) ==
            PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission")
    private fun pickPc() {
        val adapter = getSystemService(BluetoothManager::class.java)?.adapter
        if (adapter == null || !adapter.isEnabled) {
            Toast.makeText(this, "Turn Bluetooth on, then choose Bluetooth again", Toast.LENGTH_LONG).show()
            backToChooser()
            return
        }
        val bonded = adapter.bondedDevices.toList()
        val computers = bonded.filter {
            it.bluetoothClass?.majorDeviceClass == BluetoothClass.Device.Major.COMPUTER
        }
        val last = getPreferences(MODE_PRIVATE).getString(PREF_LAST_PC, null)
        val choices = computers.ifEmpty { bonded }.sortedByDescending { it.address == last }
        if (choices.isEmpty()) {
            AlertDialog.Builder(this)
                .setTitle("No paired PC")
                .setMessage("Pair this tablet with the PC in Bluetooth settings first.")
                .setPositiveButton("OK") { _, _ -> backToChooser() }
                .setCancelable(false)
                .show()
            return
        }
        val labels = choices.map { it.name ?: it.address }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle("Connect to which PC?")
            .setItems(labels) { _, which -> connectTo(choices[which]) }
            .setNegativeButton("Cancel") { _, _ -> backToChooser() }
            .setCancelable(false)
            .show()
    }

    @SuppressLint("MissingPermission")
    private fun connectTo(device: BluetoothDevice) {
        val adapter = getSystemService(BluetoothManager::class.java)?.adapter ?: return
        btDevice = device
        getPreferences(MODE_PRIVATE).edit().putString(PREF_LAST_PC, device.address).apply()
        val pcName = device.name ?: device.address
        padLog("Connecting to $pcName…")
        btClient?.shutdown()
        btClient = RfcommPadClient(
            adapter,
            tabletName = adapter.name ?: Build.MODEL,
            onLinked = { runOnUiThread { signalLinked(true) } },
            onMessage = { json ->
                val safe = org.json.JSONObject.quote(json)
                runOnUiThread {
                    binding.webView.evaluateJavascript("window.__gtBtMessage && window.__gtBtMessage($safe)", null)
                }
            },
            onClosed = { reason -> runOnUiThread { onBtClosed(pcName, reason) } },
        ).also { it.connect(device) }
    }

    private fun signalLinked(linked: Boolean) {
        val name = org.json.JSONObject.quote(btDevice?.name ?: btDevice?.address ?: "")
        binding.webView.evaluateJavascript("window.__gtBtLinked && window.__gtBtLinked($linked, $name)", null)
    }

    private fun onBtClosed(pcName: String, reason: String) {
        if (destroyed) return
        signalLinked(false)
        padLog("Not connected to $pcName")
        AlertDialog.Builder(this)
            .setTitle("Not connected to $pcName")
            .setMessage(reason)
            .setPositiveButton("Reconnect") { _, _ -> btDevice?.let(::connectTo) }
            .setNeutralButton("Other PC") { _, _ -> pickPc() }
            .setCancelable(false)
            .show()
    }

    private fun padLog(message: String) {
        val safe = org.json.JSONObject.quote(message)
        binding.webView.evaluateJavascript("window.__gtBtLog && window.__gtBtLog($safe)", null)
    }

    private fun startWatchdog() {
        if (mode != MODE_USB) return
        mainHandler.removeCallbacks(watchdogRunnable)
        mainHandler.postDelayed(watchdogRunnable, RELOAD_DELAY_MS)
    }

    private fun loadTrackpad() {
        if (destroyed || mode != MODE_USB) return
        binding.webView.loadUrl(TRACKPAD_URL)
    }

    private fun showWaitingPage() {
        if (destroyed || mode != MODE_USB) return
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
        private const val MODE_USB = "usb"
        private const val MODE_BT = "bluetooth"
        private const val TRACKPAD_ORIGIN = "http://127.0.0.1:8765"
        const val TRACKPAD_URL = "http://127.0.0.1:8765/touchpad_v04.html?v=094"
        private const val WAITING_URL = "file:///android_asset/waiting.html"
        private const val BT_PAD_URL = "file:///android_asset/touchpad_v04.html"
        private const val RELOAD_DELAY_MS = 2000L
        private const val PREF_LAST_PC = "bt_last_pc"

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
