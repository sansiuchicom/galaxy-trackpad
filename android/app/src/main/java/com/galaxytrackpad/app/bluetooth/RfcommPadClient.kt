package com.galaxytrackpad.app.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
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
 * Dials the Galaxy Trackpad service on a paired PC (the PC engine advertises it).
 * After connect the PC drives HELLO/PING/MODE FRAME; then pad packets flow Tab → PC
 * as uint32 BE length + JSON.
 */
class RfcommPadClient(
    private val adapter: BluetoothAdapter,
    private val tabletName: String,
    private val onLinked: () -> Unit,
    private val onClosed: (reason: String) -> Unit,
) {
    private val io = Executors.newSingleThreadExecutor()
    private val sendIo = Executors.newSingleThreadExecutor()
    private val latestMove = AtomicReference<String?>(null)
    private val frameMode = AtomicBoolean(false)
    private val closing = AtomicBoolean(false)
    private val writeLock = Any()

    @Volatile
    private var socket: BluetoothSocket? = null

    @SuppressLint("MissingPermission")
    fun connect(device: BluetoothDevice) {
        closing.set(false)
        io.execute {
            val sock = try {
                // Needs BLUETOOTH_SCAN, which we do not request; we never start discovery anyway.
                runCatching { adapter.cancelDiscovery() }
                device.createRfcommSocketToServiceRecord(SERVICE_UUID).also { it.connect() }
            } catch (e: Exception) {
                onClosed("Could not reach the PC. Is Galaxy Trackpad running there? (${e.message})")
                return@execute
            }
            socket = sock
            val reason = try {
                serve(sock)
                "PC closed the connection"
            } catch (e: Exception) {
                e.message ?: "connection lost"
            } finally {
                frameMode.set(false)
                socket = null
                runCatching { sock.close() }
            }
            if (!closing.get()) onClosed(reason)
        }
    }

    fun isLinked(): Boolean = frameMode.get()

    fun close() {
        closing.set(true)
        frameMode.set(false)
        runCatching { socket?.close() }
    }

    fun shutdown() {
        close()
        io.shutdownNow()
        sendIo.shutdownNow()
    }

    /**
     * Never block the WebView on the radio. If the link falls behind, stale moves
     * are replaced by the newest one; down/up are always delivered in order.
     */
    fun sendPacketJson(json: String) {
        if (!frameMode.get()) return
        if (json.contains("\"event\":\"move\"")) {
            if (latestMove.getAndSet(json) == null) {
                sendIo.execute { latestMove.getAndSet(null)?.let(::writePacket) }
            }
        } else {
            sendIo.execute { writePacket(json) }
        }
    }

    private fun writePacket(json: String) {
        val sock = socket ?: return
        runCatching {
            synchronized(writeLock) { writeFrame(sock.outputStream, json.toByteArray(Charsets.UTF_8)) }
        }
    }

    private fun serve(sock: BluetoothSocket) {
        val input = sock.inputStream
        val output = sock.outputStream
        while (!frameMode.get()) {
            val line = readLineRaw(input) ?: return
            val upper = line.trim().uppercase()
            when {
                upper.startsWith("HELLO") -> writeLine(output, "ACK name=$tabletName")
                upper.startsWith("PING") -> writeLine(output, "PONG ${System.currentTimeMillis()}")
                upper == "MODE FRAME" -> {
                    writeLine(output, "ACK FRAME")
                    frameMode.set(true)
                    onLinked()
                }
                else -> writeLine(output, "ACK echo:$line")
            }
        }
        // PC → Tab frames (state, acks) are not used by the Bluetooth pad yet.
        while (frameMode.get()) readFrame(input)
    }

    private fun writeLine(output: OutputStream, text: String) {
        synchronized(writeLock) {
            output.write((text + "\n").toByteArray(Charsets.UTF_8))
            output.flush()
        }
    }

    companion object {
        /** Must match SERVICE_UUID in windows/transport/winrt_rfcomm.py. */
        val SERVICE_UUID: UUID = UUID.fromString("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        private const val MAX_FRAME = 1_000_000

        private fun readLineRaw(input: InputStream): String? {
            val buf = ByteArrayOutputStream()
            while (true) {
                val b = input.read()
                if (b < 0) return if (buf.size() == 0) null else buf.toString(Charsets.UTF_8.name())
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
                if (r < 0) throw java.io.EOFException("PC closed the connection")
                off += r
            }
            return out
        }

        private fun readFrame(input: InputStream): ByteArray {
            val header = readExact(input, 4)
            val length = ByteBuffer.wrap(header).order(ByteOrder.BIG_ENDIAN).int
            if (length < 0 || length > MAX_FRAME) throw IllegalArgumentException("bad frame length $length")
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
