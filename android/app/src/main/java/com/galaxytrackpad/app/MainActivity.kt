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
 * Phase 3C WebView shell: keep screen on, survive USB flaps, clear contacts on pause.
 *
 * Still loads the Windows-served HTML over ADB reverse when available.
 * If HTTP is down, shows a local waiting page and retries automatically.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val mainHandler = Handler(Looper.getMainLooper())
    private var pageHealthy = false
    private var reloadPosted = false
    private var destroyed = false

    private val reloadRunnable = Runnable {
        reloadPosted = false
        if (destroyed || pageHealthy) return@Runnable
        loadTrackpad()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        WindowCompat.setDecorFitsSystemWindows(window, false)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        hideSystemBars()
        setupWebView(binding.webView)

        if (savedInstanceState == null) {
            loadTrackpad()
        } else {
            binding.webView.restoreState(savedInstanceState)
        }

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    // Dedicated input device: ignore back.
                }
            },
        )
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        binding.webView.saveState(outState)
    }

    override fun onResume() {
        super.onResume()
        hideSystemBars()
        binding.webView.onResume()
        if (!pageHealthy) {
            scheduleReload(immediate = true)
        } else {
            // Re-sync after returning from background.
            binding.webView.evaluateJavascript(JS_RESUME_SYNC, null)
        }
    }

    override fun onPause() {
        binding.webView.evaluateJavascript(JS_RELEASE_ALL, null)
        binding.webView.onPause()
        super.onPause()
    }

    override fun onStop() {
        // Extra safety if the process is backgrounded mid-gesture.
        binding.webView.evaluateJavascript(JS_RELEASE_ALL, null)
        super.onStop()
    }

    override fun onDestroy() {
        destroyed = true
        mainHandler.removeCallbacks(reloadRunnable)
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
            // Prefer fresh HTML from Windows after engine updates.
            cacheMode = WebSettings.LOAD_NO_CACHE
            mediaPlaybackRequiresUserGesture = false
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
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
                    pageHealthy = true
                    cancelReload()
                }
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?,
            ) {
                if (request?.isForMainFrame != true) return
                pageHealthy = false
                showWaitingPage()
                scheduleReload(immediate = false)
            }

            @Deprecated("Deprecated in Java")
            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?,
            ) {
                if (failingUrl != null && failingUrl.startsWith(TRACKPAD_ORIGIN)) {
                    pageHealthy = false
                    showWaitingPage()
                    scheduleReload(immediate = false)
                }
            }
        }
        webView.webChromeClient = WebChromeClient()
    }

    private fun loadTrackpad() {
        if (destroyed) return
        binding.webView.loadUrl(TRACKPAD_URL)
    }

    private fun showWaitingPage() {
        if (destroyed) return
        binding.webView.loadUrl(WAITING_URL)
    }

    private fun scheduleReload(immediate: Boolean) {
        if (destroyed || pageHealthy) return
        mainHandler.removeCallbacks(reloadRunnable)
        reloadPosted = true
        val delay = if (immediate) 300L else RELOAD_DELAY_MS
        mainHandler.postDelayed(reloadRunnable, delay)
    }

    private fun cancelReload() {
        reloadPosted = false
        mainHandler.removeCallbacks(reloadRunnable)
    }

    private fun hideSystemBars() {
        val controller = WindowInsetsControllerCompat(window, window.decorView)
        controller.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        controller.hide(WindowInsetsCompat.Type.systemBars())
    }

    companion object {
        private const val TRACKPAD_ORIGIN = "http://127.0.0.1:8765"
        const val TRACKPAD_URL = "http://127.0.0.1:8765/touchpad_v04.html?v=3c"
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
