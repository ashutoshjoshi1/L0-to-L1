from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SCodeConfig:
    code: str
    description: str
    dark: bool
    dark_unc_source: str   # "MEAS" / "MAPSIGMA"
    nonlinearity: bool
    latency: bool
    prnu: bool
    count_rate: bool
    temperature: bool
    straylight_mode: str   # "NO" / "MM" / "CORRMM"
    sensitivity: bool
    wavelength: bool
    qcode: str
    created: str
    author: str


def get_scode_configs() -> Dict[str, SCodeConfig]:
    """
    Aligned with the s_codes provided by user.
    """
    return {
        "cs00": SCodeConfig(
            code="cs00",
            description="Dark correction only",
            dark=True, dark_unc_source="MEAS",
            nonlinearity=False, latency=False, prnu=False, count_rate=False,
            temperature=False, straylight_mode="NO", sensitivity=False, wavelength=False,
            qcode="nlim", created="1-Dec-2016", author="Alexander Cede"
        ),
        "cs01": SCodeConfig(
            code="cs01",
            description="Dark, linearity, latency, PRNU and conversion to count rates",
            dark=True, dark_unc_source="MEAS",
            nonlinearity=True, latency=True, prnu=True, count_rate=True,
            temperature=False, straylight_mode="NO", sensitivity=False, wavelength=False,
            qcode="nlim", created="1-Dec-2016", author="Alexander Cede"
        ),
        "cs02": SCodeConfig(
            code="cs02",
            description="Dark, linearity, latency, PRNU, count rates, temperature correction",
            dark=True, dark_unc_source="MEAS",
            nonlinearity=True, latency=True, prnu=True, count_rate=True,
            temperature=True, straylight_mode="NO", sensitivity=False, wavelength=False,
            qcode="nlim", created="22-Feb-2017", author="Alexander Cede"
        ),
        "cs03": SCodeConfig(
            code="cs03",
            description="cs02 + MM stray light correction",
            dark=True, dark_unc_source="MEAS",
            nonlinearity=True, latency=True, prnu=True, count_rate=True,
            temperature=True, straylight_mode="MM", sensitivity=False, wavelength=False,
            qcode="nlim", created="19-Jul-2017", author="Alexander Cede"
        ),
        "cs04": SCodeConfig(
            code="cs04",
            description="cs03 + sensitivity correction",
            dark=True, dark_unc_source="MEAS",
            nonlinearity=True, latency=True, prnu=True, count_rate=True,
            temperature=True, straylight_mode="MM", sensitivity=True, wavelength=False,
            qcode="nlim", created="8-Nov-2017", author="Alexander Cede"
        ),
        "mca0": SCodeConfig(
            code="mca0",
            description="All corrections applied",
            dark=True, dark_unc_source="MAPSIGMA",
            nonlinearity=True, latency=True, prnu=True, count_rate=True,
            temperature=True, straylight_mode="CORRMM", sensitivity=True, wavelength=True,
            qcode="st00", created="20-Jan-2017", author="Alexander Cede"
        ),
        "mca1": SCodeConfig(
            code="mca1",
            description="All corrections except wavelength correction",
            dark=True, dark_unc_source="MAPSIGMA",
            nonlinearity=True, latency=True, prnu=True, count_rate=True,
            temperature=True, straylight_mode="CORRMM", sensitivity=True, wavelength=False,
            qcode="st00", created="20-Jan-2017", author="Alexander Cede"
        ),
    }
