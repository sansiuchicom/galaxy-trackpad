package com.galaxytrackpad.app

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.JavascriptInterface
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/**
 * BT lab: Tab listens on RFCOMM.
 * BT-1: line HELLO/ACK/PING/PONG
 * BT-2: MODE FRAME → uint32 BE length + JSON contacts from WebView pad
 */
class BtLabActivity : AppCompatActivity() {

    private val io = Executors.newSingleThreadExecutor()
    private val sendIo = Executors.newSingleThreadExecutor()
    private val latestMove = AtomicReference<String?>(null)
    private val running = AtomicBoolean(false)
    private val acceptLoop = AtomicBoolean(false)
    private val frameMode = AtomicBoolean(false)
    private val writeLock = Any()

    private var adapter: BluetoothAdapter? = null
    private var serverSocket: BluetoothServerSocket? = null
    private var clientSocket: BluetoothSocket? = null
    private var listenChannel: Int = FIXED_CHANNEL
    private var listenAfterPerms: Boolean = false

    private lateinit var status: TextView
    private lateinit var logView: TextView
    private lateinit var logScroll: View
    private lateinit var chrome: View
    private lateinit var padWeb: WebView
    private lateinit var btnListen: Button
    private lateinit var btnHello: Button
    private lateinit var btnPing: Button
    private lateinit var btnStop: Button

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            val ok = result.values.all { it }
            appendLog(if (ok) "Bluetooth permission granted" else "Bluetooth permission denied")
            if (ok) {
                showLocalAddress()
                if (listenAfterPerms) {
                    listenAfterPerms = false
                    startListening()
                }
            } else {
                listenAfterPerms = false
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_bt_lab)

        status = findViewById(R.id.btStatus)
        logView = findViewById(R.id.btLog)
        logScroll = findViewById(R.id.btLogScroll)
        chrome = findViewById(R.id.btChrome)
        padWeb = findViewById(R.id.btPadWeb)
        btnListen = findViewById(R.id.btListen)
        btnHello = findViewById(R.id.btHello)
        btnPing = findViewById(R.id.btPing)
        btnStop = findViewById(R.id.btStop)

        val mgr = getSystemService(BluetoothManager::class.java)
        adapter = mgr?.adapter
        if (adapter == null) {
            setStatus("No Bluetooth adapter")
            return
        }

        setupPadWebView()

        btnListen.setOnClickListener { ensurePermsAndListen() }
        findViewById<Button>(R.id.btConnectPc).setOnClickListener { pickPcAndConnect() }
        btnHello.setOnClickListener { sendLine("HELLO from Tab") }
        btnPing.setOnClickListener { sendLine("PING") }
        btnStop.setOnClickListener { stopAll("User stop") }

        setStatus("Idle — pair PC, then tap Listen")
        appendLog("BT-2: Listen, then on PC:")
        appendLog("  python -m bluetooth_lab.windows_pad_client")
        appendLog("BT-1 only: python -m bluetooth_lab.windows_client")
        ensurePerms()
    }

    override fun onDestroy() {
        stopAll("Activity destroy")
        io.shutdownNow()
        sendIo.shutdownNow()
        super.onDestroy()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupPadWebView() {
        padWeb.settings.javaScriptEnabled = true
        padWeb.settings.domStorageEnabled = true
        padWeb.settings.cacheMode = WebSettings.LOAD_NO_CACHE
        // file:// asset + binder thread; do not queue on the RFCOMM reader executor.
        padWeb.addJavascriptInterface(PadBridge(), "GalaxyBT")
        padWeb.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                if (frameMode.get()) {
                    view.evaluateJavascript("window.__gtBtLinked && window.__gtBtLinked(true)", null)
                }
            }
        }
    }

    inner class PadBridge {
        /**
         * Never block the WebView on the radio. If the link falls behind, stale
         * moves are replaced by the newest one; down/up are always delivered in order.
         */
        @JavascriptInterface
        fun sendPacket(json: String) {
            if (clientSocket == null || !frameMode.get()) return
            if (json.contains("\"event\":\"move\"")) {
                if (latestMove.getAndSet(json) == null) {
                    sendIo.execute { latestMove.getAndSet(null)?.let(::writePacket) }
                }
            } else {
                sendIo.execute { writePacket(json) }
            }
        }
    }

    private fun writePacket(json: String) {
        val sock = clientSocket ?: return
        try {
            synchronized(writeLock) {
                writeFrame(sock.outputStream, json.toByteArray(Charsets.UTF_8))
            }
        } catch (e: Exception) {
            runOnUiThread { appendLog("frame send failed: ${e.message}") }
        }
    }

    private fun showPad(show: Boolean) {
        padWeb.visibility = if (show) View.VISIBLE else View.GONE
        logScroll.visibility = if (show) View.GONE else View.VISIBLE
        if (show) {
            padWeb.loadUrl("file:///android_asset/touchpad_bt.html")
            setStatus("PAD MODE — touch the pad")
        }
    }

    private fun ensurePerms() {
        val need = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED
            ) {
                need += Manifest.permission.BLUETOOTH_CONNECT
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_ADVERTISE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                need += Manifest.permission.BLUETOOTH_ADVERTISE
            }
        }
        if (need.isNotEmpty()) {
            permissionLauncher.launch(need.toTypedArray())
        } else {
            showLocalAddress()
        }
    }

    private fun ensurePermsAndListen() {
        val need = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED
            ) {
                need += Manifest.permission.BLUETOOTH_CONNECT
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_ADVERTISE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                need += Manifest.permission.BLUETOOTH_ADVERTISE
            }
        }
        if (need.isNotEmpty()) {
            listenAfterPerms = true
            permissionLauncher.launch(need.toTypedArray())
            return
        }
        startListening()
    }

    @SuppressLint("MissingPermission", "HardwareIds")
    private fun showLocalAddress() {
        val bt = adapter ?: return
        val addr = try {
            bt.address
        } catch (_: SecurityException) {
            "(permission needed)"
        }
        appendLog("Tab Bluetooth name=${bt.name}")
        if (addr == null || addr.startsWith("02:00:00") || addr == "00:00:00:00:00:00") {
            appendLog("MAC hidden by Android ($addr) — use Windows paired list")
            setStatus("Ready — tap Listen (MAC from Windows)")
        } else {
            appendLog("MAC=$addr")
            setStatus("Ready — MAC $addr — tap Listen")
        }
    }

    @SuppressLint("MissingPermission")
    private fun startListening() {
        val bt = adapter
        if (bt == null) return
        if (!bt.isEnabled) {
            setStatus("Bluetooth OFF")
            appendLog("Turn Bluetooth on")
            return
        }
        stopAllQuiet()
        runOnUiThread { showPad(false) }
        setStatus("Listening… start Windows pad client now")
        acceptLoop.set(true)
        io.execute {
            try {
                val server = openServerSocket(bt)
                serverSocket = server
                runOnUiThread {
                    appendLog("Server socket open — waiting for Windows…")
                    Toast.makeText(this, "Listening", Toast.LENGTH_SHORT).show()
                }
                while (acceptLoop.get()) {
                    val sock = try {
                        server.accept()
                    } catch (e: Exception) {
                        if (acceptLoop.get()) {
                            runOnUiThread { appendLog("accept ended: ${e.message}") }
                        }
                        break
                    } ?: break
                    runOnUiThread {
                        setStatus("CONNECTED from Windows")
                        appendLog("Client accepted")
                    }
                    clientSocket = sock
                    running.set(true)
                    frameMode.set(false)
                    // Wait for peer HELLO first — sending READY into a half-open
                    // probe socket caused Broken pipe when Windows timed out connect.
                    handleClient(sock)
                    running.set(false)
                    frameMode.set(false)
                    clientSocket = null
                    runOnUiThread {
                        showPad(false)
                        setStatus("Client gone — still listening")
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    setStatus("Listen failed")
                    appendLog("ERROR: ${e.message}")
                }
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun pickPcAndConnect() {
        val bt = adapter ?: return
        if (!bt.isEnabled) {
            setStatus("Bluetooth OFF")
            return
        }
        val bonded = try {
            bt.bondedDevices.toList()
        } catch (e: SecurityException) {
            appendLog("Need Bluetooth permission: ${e.message}")
            ensurePerms()
            return
        }
        val computers = bonded.filter {
            it.bluetoothClass?.majorDeviceClass == BluetoothClass.Device.Major.COMPUTER
        }
        val choices = computers.ifEmpty { bonded }
        if (choices.isEmpty()) {
            setStatus("No paired devices — pair the PC in Settings first")
            return
        }
        val labels = choices.map { "${it.name ?: "Unknown"}  (${it.address})" }.toTypedArray()
        AlertDialog.Builder(this)
            .setTitle("Connect to which PC?")
            .setItems(labels) { _, which -> connectToPc(choices[which]) }
            .setNegativeButton("Cancel", null)
            .show()
    }

    @SuppressLint("MissingPermission")
    private fun connectToPc(device: BluetoothDevice) {
        stopAllQuiet()
        runOnUiThread { showPad(false) }
        val name = device.name ?: device.address
        setStatus("Connecting to $name…")
        appendLog("Dial PC $name via SDP UUID (PC must run windows_pad_server)")
        io.execute {
            val sock = try {
                // Needs BLUETOOTH_SCAN, which we do not request; we never start discovery anyway.
                runCatching { adapter?.cancelDiscovery() }
                device.createRfcommSocketToServiceRecord(SERVICE_UUID).also { it.connect() }
            } catch (e: Exception) {
                runOnUiThread {
                    setStatus("Could not reach $name")
                    appendLog("connect failed: ${e.message}")
                }
                return@execute
            }
            runOnUiThread {
                setStatus("CONNECTED to $name")
                appendLog("Connected to PC $name")
            }
            clientSocket = sock
            running.set(true)
            frameMode.set(false)
            handleClient(sock)
            running.set(false)
            frameMode.set(false)
            clientSocket = null
            runOnUiThread {
                showPad(false)
                setStatus("Disconnected from $name")
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun openServerSocket(bt: BluetoothAdapter): BluetoothServerSocket {
        // Hidden API — must use getDeclaredMethod (getMethod fails on Tab S7).
        for (name in listOf(
            "listenUsingInsecureRfcommOnChannel",
            "listenUsingRfcommOnChannel",
        )) {
            try {
                val method = bt.javaClass.getDeclaredMethod(
                    name,
                    Int::class.javaPrimitiveType,
                )
                method.isAccessible = true
                val sock = method.invoke(bt, FIXED_CHANNEL) as BluetoothServerSocket
                listenChannel = FIXED_CHANNEL
                runOnUiThread {
                    appendLog("Listening on FIXED channel $FIXED_CHANNEL via $name")
                    setStatus("Listening on channel $FIXED_CHANNEL — start PC client")
                }
                return sock
            } catch (e: Exception) {
                runOnUiThread {
                    appendLog("Fixed channel via $name failed: ${e.javaClass.simpleName}: ${e.message}")
                }
            }
        }
        val sock = bt.listenUsingInsecureRfcommWithServiceRecord(SERVICE_NAME, SERVICE_UUID)
        listenChannel = peekServerChannel(sock) ?: -1
        runOnUiThread {
            appendLog("UUID service record open (channel=$listenChannel)")
            setStatus(
                if (listenChannel > 0) {
                    "Listening on channel $listenChannel — start PC client"
                } else {
                    "Listening (UUID, channel unknown) — start PC client"
                },
            )
        }
        return sock
    }

    private fun peekServerChannel(server: BluetoothServerSocket): Int? {
        try {
            val f = server.javaClass.getDeclaredField("mChannel")
            f.isAccessible = true
            val ch = f.getInt(server)
            if (ch > 0) return ch
        } catch (_: Exception) {
        }
        try {
            val m = server.javaClass.getDeclaredMethod("getChannel")
            m.isAccessible = true
            val ch = m.invoke(server) as Int
            if (ch > 0) return ch
        } catch (_: Exception) {
        }
        try {
            val mSocketField = server.javaClass.getDeclaredField("mSocket")
            mSocketField.isAccessible = true
            val mSocket = mSocketField.get(server) ?: return null
            for (name in listOf("mPort", "mChannel", "port", "channel")) {
                try {
                    val pf = mSocket.javaClass.getDeclaredField(name)
                    pf.isAccessible = true
                    val ch = pf.getInt(mSocket)
                    if (ch > 0) return ch
                } catch (_: Exception) {
                }
            }
        } catch (_: Exception) {
        }
        return null
    }

    private fun handleClient(sock: BluetoothSocket) {
        try {
            val input = sock.inputStream
            val output = sock.outputStream
            while (running.get()) {
                if (frameMode.get()) {
                    handleFramed(input, output)
                    break
                }
                val line = readLineRaw(input) ?: break
                runOnUiThread { appendLog("RECV << $line") }
                val upper = line.trim().uppercase()
                when {
                    upper == "MODE FRAME" -> {
                        writeRaw(output, "ACK FRAME\n")
                        runOnUiThread {
                            appendLog("SEND >> ACK FRAME")
                            appendLog("Framed pad mode ON")
                            showPad(true)
                        }
                        frameMode.set(true)
                    }
                    upper.startsWith("HELLO") -> {
                        val reply =
                            "ACK Tab RFCOMM lab ch=$listenChannel uuid=$SERVICE_UUID"
                        writeRaw(output, reply + "\n")
                        runOnUiThread { appendLog("SEND >> $reply") }
                    }
                    upper.startsWith("PING") -> {
                        val reply = "PONG ${System.currentTimeMillis()}"
                        writeRaw(output, reply + "\n")
                        runOnUiThread { appendLog("SEND >> $reply") }
                    }
                    else -> {
                        val reply = "ACK echo:$line"
                        writeRaw(output, reply + "\n")
                        runOnUiThread { appendLog("SEND >> $reply") }
                    }
                }
            }
        } catch (e: Exception) {
            if (running.get()) {
                runOnUiThread { appendLog("Session error: ${e.message}") }
            }
        } finally {
            try {
                sock.close()
            } catch (_: Exception) {
            }
        }
    }

    private fun handleFramed(input: InputStream, output: OutputStream) {
        while (running.get() && frameMode.get()) {
            val body = try {
                readFrame(input)
            } catch (e: Exception) {
                if (running.get()) {
                    runOnUiThread { appendLog("frame read ended: ${e.message}") }
                }
                break
            }
            // PC may push state; we only log type for now.
            val preview = body.toString(Charsets.UTF_8).take(80)
            runOnUiThread { appendLog("RECV frame ${body.size}B $preview") }
            // Contacts are Tab → PC; ignore PC→Tab input packets.
        }
    }

    private fun sendLine(text: String) {
        io.execute {
            val sock = clientSocket
            if (sock == null) {
                runOnUiThread { appendLog("Not connected — Wait for Windows client") }
                return@execute
            }
            if (frameMode.get()) {
                runOnUiThread { appendLog("In FRAME mode — use the pad, not HELLO/PING") }
                return@execute
            }
            try {
                writeRaw(sock.outputStream, text.trim() + "\n")
                runOnUiThread { appendLog("SEND >> $text") }
            } catch (e: Exception) {
                runOnUiThread { appendLog("Send failed: ${e.message}") }
            }
        }
    }

    private fun writeRaw(output: OutputStream, text: String) {
        synchronized(writeLock) {
            output.write(text.toByteArray(Charsets.UTF_8))
            output.flush()
        }
    }

    private fun stopAllQuiet() {
        acceptLoop.set(false)
        running.set(false)
        frameMode.set(false)
        try {
            clientSocket?.close()
        } catch (_: Exception) {
        }
        clientSocket = null
        try {
            serverSocket?.close()
        } catch (_: Exception) {
        }
        serverSocket = null
    }

    private fun stopAll(reason: String) {
        stopAllQuiet()
        runOnUiThread {
            showPad(false)
            appendLog("Stopped ($reason)")
            setStatus("Stopped — tap Listen to wait again")
        }
    }

    private fun setStatus(text: String) {
        status.text = text
    }

    private fun appendLog(line: String) {
        val next = (logView.text?.toString().orEmpty() + "\n" + line).trim()
        logView.text = next.takeLast(4000)
    }

    companion object {
        private const val SERVICE_NAME = "GalaxyTrackpadLab"
        /** Keep in sync with bluetooth_lab/constants.py RFCOMM_CHANNEL. */
        private const val FIXED_CHANNEL = 5
        private val SERVICE_UUID: UUID =
            UUID.fromString("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        private const val MAX_FRAME = 1_000_000

        private fun readLineRaw(input: InputStream): String? {
            val buf = ByteArrayOutputStream()
            while (true) {
                val b = input.read()
                if (b < 0) {
                    return if (buf.size() == 0) null else buf.toString(Charsets.UTF_8.name())
                }
                if (b == '\n'.code) break
                if (b != '\r'.code) buf.write(b)
            }
            return buf.toString(Charsets.UTF_8.name())
        }

        private fun readExact(input: InputStream, n: Int): ByteArray {
            val out = ByteArray(n)
            var off = 0
            while (off < n) {
                val r = input.read(out, off, n - off)
                if (r < 0) throw java.io.EOFException("closed")
                off += r
            }
            return out
        }

        private fun readFrame(input: InputStream): ByteArray {
            val header = readExact(input, 4)
            val length = ByteBuffer.wrap(header).order(ByteOrder.BIG_ENDIAN).int
            if (length < 0 || length > MAX_FRAME) {
                throw IllegalArgumentException("bad frame length $length")
            }
            return readExact(input, length)
        }

        private fun writeFrame(output: OutputStream, body: ByteArray) {
            if (body.size > MAX_FRAME) throw IllegalArgumentException("frame too large")
            val frame = ByteBuffer.allocate(4 + body.size).order(ByteOrder.BIG_ENDIAN)
                .putInt(body.size).put(body).array()
            output.write(frame)
            output.flush()
        }
    }
}
