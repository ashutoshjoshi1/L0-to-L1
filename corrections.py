from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class CalibrationData:
    n_pixels: int
    ref_temp_c: float = 20.0

    def __post_init__(self):
        # Placeholder arrays; replace with real calibration data.
        self.prnu = np.ones(self.n_pixels, dtype=float)
        self.temp_coeff = np.zeros(self.n_pixels, dtype=float)     # fractional / °C
        self.sensitivity = np.ones(self.n_pixels, dtype=float)     # relative sensitivity
        self.wavelength_nm = np.linspace(280, 530, self.n_pixels)  # placeholder grid

    def nonlinearity_inverse(self, arr: np.ndarray) -> np.ndarray:
        # placeholder inverse response model
        return arr - 1e-6 * arr**2

    def latency_correct(self, arr: np.ndarray) -> np.ndarray:
        # placeholder latency model (very light smoothing)
        if arr.size < 3:
            return arr
        kernel = np.array([0.05, 0.90, 0.05], dtype=float)
        return np.convolve(arr, kernel, mode="same")

    def straylight_mm(self, arr: np.ndarray) -> np.ndarray:
        # placeholder MM correction
        kernel = np.array([0.02, 0.96, 0.02], dtype=float)
        return np.convolve(arr, kernel, mode="same")

    def straylight_corrmm(self, arr: np.ndarray) -> np.ndarray:
        # placeholder stronger correction model
        kernel = np.array([0.03, 0.94, 0.03], dtype=float)
        return np.convolve(arr, kernel, mode="same")

    def wavelength_correct(self, arr: np.ndarray) -> np.ndarray:
        # placeholder wavelength correction (identity for now)
        # later: interpolate to corrected wavelength grid
        return arr


def dark_correction(spec: np.ndarray, dark: Optional[np.ndarray]) -> np.ndarray:
    if dark is None:
        return spec
    return spec - dark


def prnu_correction(spec: np.ndarray, cal: CalibrationData) -> np.ndarray:
    denom = np.where(cal.prnu == 0.0, 1.0, cal.prnu)
    return spec / denom


def temperature_correction(spec: np.ndarray, temp_c: Optional[float], cal: CalibrationData) -> np.ndarray:
    if temp_c is None:
        return spec
    dt = temp_c - cal.ref_temp_c
    f = 1.0 + cal.temp_coeff * dt
    f = np.where(f == 0.0, 1.0, f)
    return spec / f


def sensitivity_correction(spec: np.ndarray, cal: CalibrationData) -> np.ndarray:
    denom = np.where(cal.sensitivity == 0.0, 1.0, cal.sensitivity)
    return spec / denom


def to_count_rate(spec_counts: np.ndarray, integration_time_ms: float) -> np.ndarray:
    sec = max(integration_time_ms, 1e-9) / 1000.0
    return spec_counts / sec


def uncertainty_model(
    corrected_counts: np.ndarray,
    integration_time_ms: float,
    output_is_rate: bool,
    floor_counts: float = 1.5
) -> np.ndarray:
    # sigma_counts
    counts = np.clip(corrected_counts, 0, None)
    sigma_counts = np.sqrt(counts + floor_counts**2)

    if output_is_rate:
        sec = max(integration_time_ms, 1e-9) / 1000.0
        return sigma_counts / sec

    return sigma_counts
