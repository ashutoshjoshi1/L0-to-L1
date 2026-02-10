"""
Simple backend selector.
If CuPy is available and user wants GPU, use it.
Else fallback to NumPy.
"""

from dataclasses import dataclass


@dataclass
class Backend:
    xp: object
    name: str


def get_backend(use_gpu: bool) -> Backend:
    if use_gpu:
        try:
            import cupy as cp  # optional
            return Backend(xp=cp, name="cupy")
        except Exception:
            pass

    import numpy as np
    return Backend(xp=np, name="numpy")
