"""Shared BT-1 lab constants (keep in sync with Android BtLabActivity)."""

# Fixed RFCOMM channel for the lab (avoids SDP on Windows Python).
RFCOMM_CHANNEL = 5

# Reserved for later SDP / service-record experiments (BT-2+).
SERVICE_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
SERVICE_NAME = "GalaxyTrackpadLab"

# Line protocol for BT-1 only (length-prefix comes in BT-2).
MSG_HELLO = "HELLO"
MSG_ACK = "ACK"
MSG_PING = "PING"
MSG_PONG = "PONG"
