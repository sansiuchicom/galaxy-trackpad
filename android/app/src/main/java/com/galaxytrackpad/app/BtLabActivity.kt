package com.galaxytrackpad.app

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * BT-1 lab: Tab listens on RFCOMM; Windows client dials in.
 * USB Galaxy Trackpad / WebView path is unused here.
 */
class BtLabActivity : AppCompatActivity() {

    private val io = Executors.newSingleThreadExecutor()
    private val running = AtomicBoolean(false)
    private val acceptLoop = AtomicBoolean(false)

    private var adapter: BluetoothAdapter? = null
    private var serverSocket: BluetoothServerSocket? = null
    private var clientSocket: BluetoothSocket? = null

    private lateinit var status: TextView
    private lateinit var logView: TextView
    private lateinit var btnListen: Button
    private lateinit var btnHello: Button
    private lateinit var btnPing: Button
    private lateinit var btnStop: Button

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            val ok = result.values.all { it }
            appendLog(if (ok) "Bluetooth permission granted" else "Bluetooth permission denied")
            if (ok) showLocalAddress()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_bt_lab)

        status = findViewById(R.id.btStatus)
        logView = findViewById(R.id.btLog)
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

        btnListen.setOnClickListener { ensurePermsAndListen() }
        btnHello.setOnClickListener { sendLine("HELLO from Tab") }
        btnPing.setOnClickListener { sendLine("PING") }
        btnStop.setOnClickListener { stopAll("User stop") }

        setStatus("Idle — pair PC, then tap Listen")
        appendLog("BT-1: Tab = server, Windows = client")
        appendLog("Do NOT need GalaxyTrackpad.exe for this test")
        appendLog("Windows: python -m bluetooth_lab.windows_client <TAB_MAC>")
        ensurePerms()
    }

    override fun onDestroy() {
        stopAll("Activity destroy")
        io.shutdownNow()
        super.onDestroy()
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
        appendLog("Tab Bluetooth name=${bt.name}  MAC=$addr")
        appendLog("Give that MAC to Windows client if asked")
        setStatus("Ready — MAC $addr — tap Listen")
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
        stopAll("Restart listen")
        setStatus("Listening… start Windows client now")
        appendLog("listenUsingInsecureRfcommWithServiceRecord($SERVICE_NAME)")
        acceptLoop.set(true)
        io.execute {
            try {
                val server = bt.listenUsingInsecureRfcommWithServiceRecord(
                    SERVICE_NAME,
                    SERVICE_UUID,
                )
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
                    // Handle one client; then continue listening if still wanted
                    handleClient(sock)
                    running.set(false)
                    clientSocket = null
                    runOnUiThread { setStatus("Client gone — still listening") }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    setStatus("Listen failed")
                    appendLog("ERROR: ${e.message}")
                }
            }
        }
    }

    private fun handleClient(sock: BluetoothSocket) {
        try {
            val reader = BufferedReader(InputStreamReader(sock.inputStream, Charsets.UTF_8))
            while (running.get()) {
                val line = reader.readLine() ?: break
                runOnUiThread { appendLog("RECV << $line") }
                val upper = line.trim().uppercase()
                val reply = when {
                    upper.startsWith("HELLO") ->
                        "ACK Tab RFCOMM lab uuid=$SERVICE_UUID"
                    upper.startsWith("PING") ->
                        "PONG ${System.currentTimeMillis()}"
                    else -> "ACK echo:$line"
                }
                writeRaw(sock, reply + "\n")
                runOnUiThread { appendLog("SEND >> $reply") }
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

    private fun sendLine(text: String) {
        io.execute {
            val sock = clientSocket
            if (sock == null) {
                runOnUiThread { appendLog("Not connected — Wait for Windows client") }
                return@execute
            }
            try {
                writeRaw(sock, text.trim() + "\n")
                runOnUiThread { appendLog("SEND >> $text") }
            } catch (e: Exception) {
                runOnUiThread { appendLog("Send failed: ${e.message}") }
            }
        }
    }

    private fun writeRaw(sock: BluetoothSocket, text: String) {
        val w = OutputStreamWriter(sock.outputStream, Charsets.UTF_8)
        w.write(text)
        w.flush()
    }

    private fun stopAll(reason: String) {
        acceptLoop.set(false)
        running.set(false)
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
        runOnUiThread {
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
        private val SERVICE_UUID: UUID =
            UUID.fromString("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    }
}
