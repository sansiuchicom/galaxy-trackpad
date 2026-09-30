package com.galaxytrackpad.app

import android.Manifest
import android.annotation.SuppressLint
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
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.galaxytrackpad.app.bluetooth.RfcommPadServer
import com.galaxytrackpad.app.databinding.ActivityMainBinding

/**
 * One transport per launch: USB or Bluetooth. No mid-session switch.
 * PC engine must be started in the same mode.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val mainHandler = Handler(Looper.getMainLooper())
    private var pageHealthy = false
    private var destroyed = false
    private var mode: String? = null

    private var btServer: RfcommPadServer? = null

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            if (mode != MODE_BT) return@registerForActivityResult
            if (result.values.all { it }) {
                btServer?.start()
            } else {
                Toast.makeText(this, "Bluetooth permission denied", Toast.LENGTH_SHORT).show()
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
        } else if (mode == MODE_BT) {
            ensureBtServer()
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

    private fun begin(selected: String) {
        if (mode != null) return
        mode = selected
        binding.chooser.visibility = View.GONE
        binding.webView.visibility = View.VISIBLE
        if (selected == MODE_BT) {
            binding.webView.loadUrl(BT_PAD_URL)
            ensureBtServer()
            Toast.makeText(this, "Bluetooth — PC must be in Bluetooth mode", Toast.LENGTH_LONG).show()
        } else {
            loadTrackpad()
            startWatchdog()
            Toast.makeText(this, "USB — PC must be in USB mode", Toast.LENGTH_SHORT).show()
        }
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
                if (mode != MODE_USB) return
                if (url != null && url.startsWith(TRACKPAD_ORIGIN)) {
                    pageHealthy = true
                    mainHandler.removeCallbacks(watchdogRunnable)
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
            btServer?.sendPacketJson(json)
        }
    }

    private fun ensureBtServer() {
        if (btServer == null) {
            btServer = RfcommPadServer(
                this,
                onLog = { msg ->
                    runOnUiThread {
                        val safe = org.json.JSONObject.quote(msg)
                        binding.webView.evaluateJavascript(
                            "window.__gtBtLog && window.__gtBtLog($safe)",
                            null,
                        )
                    }
                },
                onFramed = { linked ->
                    runOnUiThread {
                        binding.webView.evaluateJavascript(
                            "window.__gtBtLinked && window.__gtBtLinked($linked)",
                            null,
                        )
                    }
                },
            )
        }
        if (btServer?.hasBluetoothPermission() != true) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                permissionLauncher.launch(
                    arrayOf(
                        Manifest.permission.BLUETOOTH_CONNECT,
                        Manifest.permission.BLUETOOTH_ADVERTISE,
                    ),
                )
            }
            return
        }
        btServer?.start()
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
        private const val BT_PAD_URL = "file:///android_asset/touchpad_bt.html"
        private const val RELOAD_DELAY_MS = 2000L

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
