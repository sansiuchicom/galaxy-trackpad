"""Input engine package."""
from windows.core.pen import PenBridge
from windows.core.sensitivity import GestureScaler
from windows.core.touchpad import ScaledTouchpad, TouchpadBridge

__all__ = [
    "GestureScaler",
    "PenBridge",
    "ScaledTouchpad",
    "TouchpadBridge",
]
