package com.galaxytrackpad.app.bluetooth

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.content.ContextCompat
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Production RFCOMM pad server (Tab listens). Same wire format as BT lab:
 * line HELLO/PING then MODE FRAME → uint32 BE + JSON.
 */
class RfcommPadServer(
    private val context: Context,
    private val onLog: (String) -> Unit = {},
    private val onClient: (Boolean) -> Unit = {},
    private val onFramed: (Boolean) -> Unit = {},
) {
    private val io = Executors.newSingleThreadExecutor()
    private val acceptLoop = AtomicBoolean(false)
    private val running = AtomicBoolean(false)
    private val frameMode = AtomicBoolean(false)
    private val writeLock = Any()

    private var serverSocket: BluetoothServerSocket? = null
    private var clientSocket: BluetoothSocket? = null
    private var listenChannel: Int = FIXED_CHANNEL

    fun hasBluetoothPermission(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return true
        return ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_CONNECT) ==
            PackageManager.PERMISSION_GRANTED &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_ADVERTISE) ==
            PackageManager.PERMISSION_GRANTED
    }

    fun isListening(): Boolean = acceptLoop.get()

    @SuppressLint("MissingPermission")
    fun start() {
        if (acceptLoop.get()) return
        val mgr = context.getSystemService(BluetoothManager::class.java)
        val bt = mgr?.adapter
        if (bt == null || !bt.isEnabled) {
            onLog("Bluetooth unavailable")
            return
        }
        if (!hasBluetoothPermission()) {
            onLog("Bluetooth permission needed")
            return
        }
        stop()
        acceptLoop.set(true)
        io.execute {
            try {
                val server = openServerSocket(bt)
                serverSocket = server
                onLog("BT listening on channel $listenChannel")
                while (acceptLoop.get()) {
                    val sock = try {
                        server.accept()
                    } catch (e: Exception) {
                        if (acceptLoop.get()) onLog("accept ended: ${e.message}")
                        break
                    } ?: break
                    onLog("BT client accepted")
                    onClient(true)
                    clientSocket = sock
                    running.set(true)
                    frameMode.set(false)
                    handleClient(sock)
                    running.set(false)
                    frameMode.set(false)
                    clientSocket = null
                    onClient(false)
                    onFramed(false)
                    onLog("BT client gone — still listening")
                }
            } catch (e: Exception) {
                onLog("BT listen failed: ${e.message}")
            }
        }
    }

    fun stop() {
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

    fun sendPacketJson(json: String) {
        val sock = clientSocket
        if (sock == null || !frameMode.get()) return
        try {
            synchronized(writeLock) {
                writeFrame(sock.outputStream, json.toByteArray(Charsets.UTF_8))
            }
        } catch (e: Exception) {
            onLog("BT frame send failed: ${e.message}")
        }
    }

    @SuppressLint("MissingPermission")
    private fun openServerSocket(bt: BluetoothAdapter): BluetoothServerSocket {
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
                return sock
            } catch (e: Exception) {
                Log.i(TAG, "Fixed channel via $name failed: ${e.message}")
            }
        }
        val sock = bt.listenUsingInsecureRfcommWithServiceRecord(SERVICE_NAME, SERVICE_UUID)
        listenChannel = peekServerChannel(sock) ?: -1
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
            val mSocketField = server.javaClass.getDeclaredField("mSocket")
            mSocketField.isAccessible = true
            val mSocket = mSocketField.get(server) ?: return null
            for (name in listOf("mPort", "mChannel")) {
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
                    drainFrames(input)
                    break
                }
                val line = readLineRaw(input) ?: break
                val upper = line.trim().uppercase()
                when {
                    upper == "MODE FRAME" -> {
                        writeRaw(output, "ACK FRAME\n")
                        frameMode.set(true)
                        onLog("BT framed pad mode ON")
                        onFramed(true)
                    }
                    upper.startsWith("HELLO") -> {
                        writeRaw(
                            output,
                            "ACK Tab RFCOMM lab ch=$listenChannel uuid=$SERVICE_UUID\n",
                        )
                    }
                    upper.startsWith("PING") -> {
                        writeRaw(output, "PONG ${System.currentTimeMillis()}\n")
                    }
                    else -> writeRaw(output, "ACK echo:$line\n")
                }
            }
        } catch (e: Exception) {
            if (running.get()) onLog("BT session: ${e.message}")
        } finally {
            try {
                sock.close()
            } catch (_: Exception) {
            }
        }
    }

    private fun drainFrames(input: InputStream) {
        while (running.get() && frameMode.get()) {
            try {
                readFrame(input)
            } catch (e: Exception) {
                if (running.get()) onLog("BT frame read ended: ${e.message}")
                break
            }
        }
    }

    private fun writeRaw(output: OutputStream, text: String) {
        synchronized(writeLock) {
            output.write(text.toByteArray(Charsets.UTF_8))
            output.flush()
        }
    }

    companion object {
        private const val TAG = "RfcommPadServer"
        private const val SERVICE_NAME = "GalaxyTrackpadLab"
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
            val header = ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putInt(body.size).array()
            output.write(header)
            output.write(body)
            output.flush()
        }
    }
}
