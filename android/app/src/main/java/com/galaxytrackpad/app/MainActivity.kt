package com.galaxytrackpad.app

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.webkit.WebChromeClient
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
 * Phase 3A: thin WebView shell over the existing Windows-served HTML.
 *
 * Loads http://127.0.0.1:8765/touchpad_v04.html after ADB reverse.
 * Does not embed assets yet — that comes after input parity is verified.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        WindowCompat.setDecorFitsSystemWindows(window, false)

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        hideSystemBars()
        setupWebView(binding.webView)

        if (savedInstanceState == null) {
            binding.webView.loadUrl(TRACKPAD_URL)
        } else {
            binding.webView.restoreState(savedInstanceState)
        }

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    // Dedicated input device: ignore back (no Chrome history UX).
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
    }

    override fun onPause() {
        // Drop any active contacts before the page / WS may stall.
        binding.webView.evaluateJavascript(JS_RELEASE_ALL, null)
        binding.webView.onPause()
        super.onPause()
    }

    override fun onDestroy() {
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
        webView.setBackgroundColor(Color.parseColor("#15191F"))
        webView.isVerticalScrollBarEnabled = false
        webView.isHorizontalScrollBarEnabled = false
        webView.overScrollMode = View.OVER_SCROLL_NEVER

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            mediaPlaybackRequiresUserGesture = false
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            // Allow ws://127.0.0.1 from the HTTP page origin.
            allowFileAccess = false
            allowContentAccess = false
            setSupportZoom(false)
            builtInZoomControls = false
            displayZoomControls = false
            useWideViewPort = true
            loadWithOverviewMode = true
        }

        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()
    }

    private fun hideSystemBars() {
        val controller = WindowInsetsControllerCompat(window, window.decorView)
        controller.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        controller.hide(WindowInsetsCompat.Type.systemBars())
    }

    companion object {
        /** Same page Chrome used; served by Windows HTTP on 8765 via ADB reverse. */
        const val TRACKPAD_URL = "http://127.0.0.1:8765/touchpad_v04.html?v=3b2"

        /**
         * Best-effort clear of active pointers + empty contacts send.
         * Matches HTML globals from touchpad_v04.html.
         */
        private const val JS_RELEASE_ALL = """
            (function () {
              try {
                if (typeof pointers !== 'undefined') {
                  pointers.clear();
                }
                if (typeof send === 'function') {
                  send('up');
                }
              } catch (e) {}
            })();
        """
    }
}
