from dataclasses import dataclass
from typing import List
import numpy as np

from models import L0Record, L1Record
from scodes import SCodeConfig
from corrections import (
    CalibrationData,
    dark_correction,
    prnu_correction,
    temperature_correction,
    sensitivity_correction,
    to_count_rate,
    uncertainty_model
)

# Bit mapping for processing_flag
BIT_DARK = 0
BIT_NONLINEARITY = 1
BIT_LATENCY = 2
BIT_PRNU = 3
BIT_COUNT_RATE = 4
BIT_TEMPERATURE = 5
BIT_STRAYLIGHT = 6
BIT_SENSITIVITY = 7
BIT_WAVELENGTH = 8


@dataclass
class ProcessStats:
    total: int = 0
    good: int = 0
    medium: int = 0
    low: int = 0


def _compute_dqf(spec: np.ndarray, unc: np.ndarray) -> int:
    """
    Placeholder DQF:
    0 = good, 1 = medium, 2 = low
    """
    if np.any(~np.isfinite(spec)) or np.any(~np.isfinite(unc)):
        return 2
    if np.max(spec) <= 0:
        return 2

    snr = float(np.mean(spec) / (np.mean(unc) + 1e-12))
    if snr < 5:
        return 2
    if snr < 15:
        return 1
    return 0


def process_l0_to_l1(
    records: List[L0Record],
    scode: SCodeConfig,
    cal: CalibrationData
) -> (List[L1Record], ProcessStats):
    out: List[L1Record] = []
    stats = ProcessStats(total=len(records))

    for rec in records:
        spec = rec.spectrum_counts.astype(float).copy()
        pflag = 0

        # 1) Dark
        if scode.dark:
            spec = dark_correction(spec, rec.dark_counts)
            pflag |= (1 << BIT_DARK)

        # 2) Nonlinearity
        if scode.nonlinearity:
            spec = cal.nonlinearity_inverse(spec)
            pflag |= (1 << BIT_NONLINEARITY)

        # 3) Latency
        if scode.latency:
            spec = cal.latency_correct(spec)
            pflag |= (1 << BIT_LATENCY)

        # 4) PRNU
        if scode.prnu:
            spec = prnu_correction(spec, cal)
            pflag |= (1 << BIT_PRNU)

        # 5) Temperature
        if scode.temperature:
            spec = temperature_correction(spec, rec.temperature_c, cal)
            pflag |= (1 << BIT_TEMPERATURE)

        # 6) Straylight
        if scode.straylight_mode == "MM":
            spec = cal.straylight_mm(spec)
            pflag |= (1 << BIT_STRAYLIGHT)
        elif scode.straylight_mode == "CORRMM":
            spec = cal.straylight_corrmm(spec)
            pflag |= (1 << BIT_STRAYLIGHT)

        # 7) Sensitivity
        if scode.sensitivity:
            spec = sensitivity_correction(spec, cal)
            pflag |= (1 << BIT_SENSITIVITY)

        # 8) Wavelength
        if scode.wavelength:
            spec = cal.wavelength_correct(spec)
            pflag |= (1 << BIT_WAVELENGTH)

        spec = np.clip(spec, 0, None)

        output_is_rate = False
        if scode.count_rate:
            spec_out = to_count_rate(spec, rec.integration_time_ms)
            output_is_rate = True
            pflag |= (1 << BIT_COUNT_RATE)
        else:
            spec_out = spec

        unc = uncertainty_model(
            corrected_counts=spec,
            integration_time_ms=rec.integration_time_ms,
            output_is_rate=output_is_rate,
            floor_counts=1.5
        )

        dqf = _compute_dqf(spec_out, unc)
        if dqf == 0:
            stats.good += 1
        elif dqf == 1:
            stats.medium += 1
        else:
            stats.low += 1

        out.append(
            L1Record(
                timestamp=rec.timestamp,
                integration_time_ms=rec.integration_time_ms,
                spectrum=spec_out,
                uncertainty=unc,
                processing_flag=pflag,
                dqf=dqf,
                metadata=rec.metadata
            )
        )

    return out, stats
