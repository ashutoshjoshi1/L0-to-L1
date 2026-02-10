import os
from typing import List, Tuple
import numpy as np
import pandas as pd

from models import L0Record, L1Record
from scodes import SCodeConfig


def _detect_pixel_columns(cols: List[str]) -> List[str]:
    pix = [c for c in cols if c.lower().startswith("pixel_")]
    if pix:
        return pix

    # fallback: columns named p0,p1...
    pix2 = [c for c in cols if c.lower().startswith("p") and c[1:].isdigit()]
    return pix2


def read_l0_csv(path: str) -> List[L0Record]:
    """
    Expected minimum columns:
      - timestamp
      - integration_time_ms
      - pixel_0 ... pixel_n
    Optional:
      - temperature_c
      - dark_0 ... dark_n
    """
    df = pd.read_csv(path)

    needed = {"timestamp", "integration_time_ms"}
    if not needed.issubset(set(df.columns)):
        raise ValueError(
            f"{os.path.basename(path)} missing required columns: {needed}"
        )

    pixel_cols = _detect_pixel_columns(list(df.columns))
    if not pixel_cols:
        raise ValueError(
            f"{os.path.basename(path)} has no pixel columns. Expected pixel_0...pixel_n."
        )

    dark_cols = [c for c in df.columns if c.lower().startswith("dark_")]
    use_dark_cols = len(dark_cols) == len(pixel_cols)

    recs: List[L0Record] = []
    for _, row in df.iterrows():
        spec = row[pixel_cols].to_numpy(dtype=float)

        dark = None
        if use_dark_cols:
            dark = row[dark_cols].to_numpy(dtype=float)

        temp = None
        if "temperature_c" in df.columns:
            t = row["temperature_c"]
            if pd.notna(t):
                temp = float(t)

        recs.append(
            L0Record(
                timestamp=str(row["timestamp"]),
                integration_time_ms=float(row["integration_time_ms"]),
                spectrum_counts=spec,
                dark_counts=dark,
                temperature_c=temp,
                metadata={"source_file": os.path.basename(path)}
            )
        )
    return recs


def build_l1_filename(
    l0_path: str,
    scode: SCodeConfig,
    cal_version: str,
    cal_date: str,
    proc_version: str = "1-0"
) -> str:
    base = os.path.splitext(os.path.basename(l0_path))[0]
    # simplified, Blick-like naming tail
    return f"{base}_L1_s{scode.code}c{cal_version}d{cal_date}p{proc_version}.txt"


def write_l1_text(
    out_path: str,
    l1_records: List[L1Record],
    scode: SCodeConfig,
    cal_version: str,
    cal_date: str,
    software_name: str = "SciGlob Processor",
    software_version: str = "1.0.0"
) -> None:
    if not l1_records:
        raise ValueError("No L1 records to write.")

    n_pix = len(l1_records[0].spectrum)

    with open(out_path, "w", encoding="utf-8") as f:
        # Header
        f.write(f"# {software_name} - L1 file\n")
        f.write(f"# software_version: {software_version}\n")
        f.write(f"# s_code: {scode.code}\n")
        f.write(f"# s_code_description: {scode.description}\n")
        f.write(f"# dark_unc_source: {scode.dark_unc_source}\n")
        f.write(f"# straylight_mode: {scode.straylight_mode}\n")
        f.write(f"# calibration_version: {cal_version}\n")
        f.write(f"# calibration_date: {cal_date}\n")
        f.write(f"# qcode: {scode.qcode}\n")
        f.write(f"# created: {scode.created}\n")
        f.write(f"# author: {scode.author}\n")
        f.write("#\n")
        f.write("# columns:\n")
        f.write("# timestamp,integration_time_ms,processing_flag,dqf,")
        f.write(",".join([f"spec_{i}" for i in range(n_pix)]))
        f.write(",")
        f.write(",".join([f"unc_{i}" for i in range(n_pix)]))
        f.write("\n")

        for r in l1_records:
            left = [
                r.timestamp,
                f"{r.integration_time_ms:.6f}",
                str(r.processing_flag),
                str(r.dqf),
            ]
            spec = [f"{v:.8e}" for v in r.spectrum]
            unc = [f"{u:.8e}" for u in r.uncertainty]
            f.write(",".join(left + spec + unc) + "\n")
