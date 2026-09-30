package com.galaxytrackpad.app

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ListView
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
 * BT-1 lab only: connect to the Windows RFCOMM server and exchange HELLO/ACK.
 * Does not talk to the USB WebView touchpad path.
 */
class BtLabActivity : AppCompatActivity() {

    private val io = Executors.newSingleThreadExecutor()
    private val running = AtomicBoolean(false)

    private var adapter: BluetoothAdapter? = null
    private var socket: BluetoothSocket? = null

    private lateinit var status: TextView
    private lateinit var logView: TextView
    private lateinit var list: ListView
    private lateinit var btnRefresh: Button
    private lateinit var btnHello: Button
    private lateinit var btnPing: Button
    private lateinit var btnDisconnect: Button

    private val devices = mutableListOf<BluetoothDevice>()
    private lateinit var listAdapter: ArrayAdapter<String>

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            val ok = result.values.all { it }
            appendLog(if (ok) "Bluetooth permission granted" else "Bluetooth permission denied")
            if (ok) refreshBonded()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_bt_lab)

        status = findViewById(R.id.btStatus)
        logView = findViewById(R.id.btLog)
        list = findViewById(R.id.btDeviceList)
        btnRefresh = findViewById(R.id.btRefresh)
        btnHello = findViewById(R.id.btHello)
        btnPing = findViewById(R.id.btPing)
        btnDisconnect = findViewById(R.id.btDisconnect)

        listAdapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, mutableListOf())
        list.adapter = listAdapter

        val mgr = getSystemService(BluetoothManager::class.java)
        adapter = mgr?.adapter
        if (adapter == null) {
            setStatus("No Bluetooth adapter")
            appendLog("This device has no Bluetooth adapter")
            return
        }

        btnRefresh.setOnClickListener { ensurePermsAndRefresh() }
        btnHello.setOnClickListener { sendLine("HELLO from Tab") }
        btnPing.setOnClickListener { sendLine("PING") }
        btnDisconnect.setOnClickListener { disconnect("User disconnect") }
        list.setOnItemClickListener { _, _, position, _ ->
            if (position in devices.indices) connectTo(devices[position])
        }

        setStatus("Idle — pair PC in system settings first")
        appendLog("BT-1 lab. Windows must run: python -m bluetooth_lab.windows_server")
        appendLog("RFCOMM channel=$RFCOMM_CHANNEL")
        ensurePermsAndRefresh()
    }

    override fun onDestroy() {
        disconnect("Activity destroy")
        io.shutdownNow()
        super.onDestroy()
    }

    private fun ensurePermsAndRefresh() {
        val need = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT)
                != PackageManager.PERMISSION_GRANTED
            ) {
                need += Manifest.permission.BLUETOOTH_CONNECT
            }
        }
        if (need.isNotEmpty()) {
            permissionLauncher.launch(need.toTypedArray())
            return
        }
        refreshBonded()
    }

    @SuppressLint("MissingPermission")
    private fun refreshBonded() {
        val bt = adapter
        if (bt == null) return
        if (!bt.isEnabled) {
            setStatus("Bluetooth OFF — turn it on")
            appendLog("Enable Bluetooth in Android settings")
            return
        }
        devices.clear()
        devices.addAll(bt.bondedDevices.orEmpty())
        listAdapter.clear()
        if (devices.isEmpty()) {
            listAdapter.add("(No paired devices — pair this Tab with the PC first)")
        } else {
            devices.forEach { d ->
                listAdapter.add("${d.name ?: "(no name)"}  ${d.address}")
            }
        }
        listAdapter.notifyDataSetChanged()
        setStatus("Paired devices: ${devices.size}. Tap a PC to connect.")
        appendLog("Refreshed bonded list (${devices.size})")
    }

    @SuppressLint("MissingPermission")
    private fun connectTo(device: BluetoothDevice) {
        disconnect("Reconnect")
        setStatus("Connecting to ${device.name ?: device.address}…")
        appendLog("Connecting ${device.address} channel=$RFCOMM_CHANNEL …")
        io.execute {
            try {
                val sock = createSocket(device)
                sock.connect()
                socket = sock
                running.set(true)
                runOnUiThread {
                    setStatus("CONNECTED to ${device.name ?: device.address}")
                    appendLog("Socket connected")
                    Toast.makeText(this, "BT connected", Toast.LENGTH_SHORT).show()
                }
                // Auto HELLO once connected
                writeRaw("HELLO from Tab\n")
                readLoop(sock)
            } catch (e: Exception) {
                runOnUiThread {
                    setStatus("Connect failed")
                    appendLog("ERROR: ${e.message}")
                }
                disconnect("Connect failed")
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun createSocket(device: BluetoothDevice): BluetoothSocket {
        // Prefer fixed-channel socket so we match the Windows lab server (no SDP).
        return try {
            val m = device.javaClass.getMethod(
                "createInsecureRfcommSocket",
                Integer.TYPE,
            )
            @Suppress("UNCHECKED_CAST")
            m.invoke(device, RFCOMM_CHANNEL) as BluetoothSocket
        } catch (_: Exception) {
            device.createInsecureRfcommSocketToServiceRecord(SERVICE_UUID)
        }
    }

    private fun readLoop(sock: BluetoothSocket) {
        try {
            val reader = BufferedReader(InputStreamReader(sock.inputStream, Charsets.UTF_8))
            while (running.get()) {
                val line = reader.readLine() ?: break
                runOnUiThread { appendLog("RECV << $line") }
            }
        } catch (e: Exception) {
            if (running.get()) {
                runOnUiThread { appendLog("Read ended: ${e.message}") }
            }
        } finally {
            runOnUiThread { setStatus("Disconnected") }
            disconnect("Read loop end")
        }
    }

    private fun sendLine(text: String) {
        io.execute {
            try {
                writeRaw(text.trim() + "\n")
                runOnUiThread { appendLog("SEND >> $text") }
            } catch (e: Exception) {
                runOnUiThread { appendLog("Send failed: ${e.message}") }
            }
        }
    }

    private fun writeRaw(text: String) {
        val sock = socket ?: throw IllegalStateException("Not connected")
        val w = OutputStreamWriter(sock.outputStream, Charsets.UTF_8)
        w.write(text)
        w.flush()
    }

    private fun disconnect(reason: String) {
        running.set(false)
        try {
            socket?.close()
        } catch (_: Exception) {
        }
        socket = null
        runOnUiThread {
            appendLog("Disconnected ($reason)")
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
        private const val RFCOMM_CHANNEL = 5
        private val SERVICE_UUID: UUID =
            UUID.fromString("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    }
}
