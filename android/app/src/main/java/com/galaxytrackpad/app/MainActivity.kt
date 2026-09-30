package com.galaxytrackpad.app

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.view.WindowManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.galaxytrackpad.app.databinding.ActivityMainBinding

/**
 * WebView shell: keep screen on, retry Windows HTML when USB/reverse is down.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val mainHandler = Handler(Looper.getMainLooper())
    private var pageHealthy = false
    private var destroyed = false

    /** Keeps trying Windows HTTP until the pad page loads (survives WAITING stuck state). */
    private val watchdogRunnable = object : Runnable {
        override fun run() {
            if (destroyed) return
            if (!pageHealthy) {
                loadTrackpad()
                mainHandler.postDelayed(this, RELOAD_DELAY_MS)
            }
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

        // Always fetch fresh pad HTML — do not restore a stale WAITING page.
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
        if (!pageHealthy) {
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
        binding.webView.apply {
            stopLoading()
            loadUrl("about:blank")
            removeAllViews()
            destroy()
        }
        super.onDestroy()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView(webView: WebView) {
        webView.setBackgroundColor(Color.parseColor("#0e1116"))
        webView.isVerticalScrollBarEnabled = false
        webView.isHorizontalScrollBarEnabled = false
        webView.overScrollMode = View.OVER_SCROLL_NEVER

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
                markUnhealthy()
                showWaitingPage()
                startWatchdog()
            }
        }
        webView.webChromeClient = WebChromeClient()
    }

    private fun markHealthy() {
        pageHealthy = true
        mainHandler.removeCallbacks(watchdogRunnable)
    }

    private fun markUnhealthy() {
        pageHealthy = false
    }

    private fun startWatchdog() {
        mainHandler.removeCallbacks(watchdogRunnable)
        mainHandler.postDelayed(watchdogRunnable, RELOAD_DELAY_MS)
    }

    private fun loadTrackpad() {
        if (destroyed) return
        binding.webView.loadUrl(TRACKPAD_URL)
    }

    private fun showWaitingPage() {
        if (destroyed) return
        // Avoid clobbering an in-flight successful load with another waiting navigation.
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
        private const val TRACKPAD_ORIGIN = "http://127.0.0.1:8765"
        const val TRACKPAD_URL = "http://127.0.0.1:8765/touchpad_v04.html?v=091"
        private const val WAITING_URL = "file:///android_asset/waiting.html"
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
