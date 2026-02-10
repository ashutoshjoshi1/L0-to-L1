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
    Reads Blick L0 format files with space-delimited measurement records.
    Blick format: Each data record starts with a record type (e.g., MO for measurement)
    followed by timestamp, integration time, and spectra data.
    """
    # Try to read with UTF-8, fallback to latin-1 if encoding issues occur
    try:
        with open(path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
    except UnicodeDecodeError:
        with open(path, 'r', encoding='latin-1') as f:
            all_lines = f.readlines()
    
    recs: List[L0Record] = []
    
    # Process lines looking for measurement records (starting with "MO" for Measurement]
    for line in all_lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is a measurement record (starts with MO)
        if line.startswith('MO '):
            try:
                parts = line.split()
                if len(parts) < 3:
                    continue
                
                # Parse the record:
                # parts[0] = Record type ("MO")
                # parts[1] = Timestamp (ISO 8601 format)
                # parts[2] onwards = numerical data
                
                timestamp = parts[1]
                
                # The third field is typically routine count
                # Fourth field is repetition count  
                # Fifth field onwards contains spectrum data
                # Integration time is typically in one of the early numeric fields
                # For now, use a placeholder value from the numeric fields
                
                numeric_fields = []
                for p in parts[2:]:
                    try:
                        numeric_fields.append(float(p))
                    except ValueError:
                        break
                
                if len(numeric_fields) < 10:
                    continue
                
                # Extract integration time (usually 5th numeric field = index 4)
                integration_time_ms = numeric_fields[4]
                
                # Spectrum data starts after the metadata fields
                # Based on Blick format: 4120 numeric fields total, spectrum is 4109 elements
                # Metadata: 11 fields (indices 0-10), Spectrum starts at index 11
                spectrum_data = numeric_fields[11:]
                
                if len(spectrum_data) == 0:
                    continue
                
                spec = np.array(spectrum_data, dtype=float)
                
                recs.append(
                    L0Record(
                        timestamp=timestamp,
                        integration_time_ms=float(integration_time_ms),
                        spectrum_counts=spec,
                        dark_counts=None,
                        temperature_c=None,
                        metadata={"source_file": os.path.basename(path)}
                    )
                )
            except (ValueError, IndexError):
                # Skip malformed lines
                continue
    
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


def _fmt_generation_date_utc(date_str: str) -> str:
    """Format generation date for header."""
    # Convert YYYYMMDD format to readable date
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def write_l1_text(
    out_path: str,
    l1_records: List[L1Record],
    scode: SCodeConfig,
    cal_version: str,
    cal_date: str,
    l0_filename: str = "",
    instrument_number: str = "209",
    spectrometer_number: str = "s1",
    wavelengths: np.ndarray = None,
    software_name: str = "SciGlob Processor",
    software_version: str = "1.0.0",
    proc_version: str = "1-0",
    generation_date_utc: str = ""
) -> None:
    if not l1_records:
        raise ValueError("No L1 records to write.")

    n_pix = len(l1_records[0].spectrum)

    # Use current date if not provided
    if not generation_date_utc:
        from datetime import datetime
        generation_date_utc = datetime.utcnow().strftime("%Y%m%d")

    # Extract output filename
    output_filename = os.path.basename(out_path)

    # Format wavelengths
    if wavelengths is None:
        wavelengths = np.linspace(280, 530, n_pix)
    
    waves_str = ", ".join([f"{w:.2f}" for w in wavelengths])

    with open(out_path, "w", encoding="utf-8") as f:
        # Build header lines
        lines = [
            f"File name: {output_filename}",
            f"File generation date: {_fmt_generation_date_utc(generation_date_utc)}",
            "Data description: Level 1 file (corrected signals)",
            f"Data file version: {proc_version}",
            "Local principal investigator: Alberto Redondas",
            "Network principal investigator: Alexander Cede",
            "Instrument type: Pandora",
            f"Instrument number: {instrument_number}",
            f"Spectrometer number: {spectrometer_number}",
            f"Processing software version used: {software_name} v{software_version}",
            "Instrument operation file used: Pandora209_OF_v3d20210806.txt",
            f"Instrument calibration file used: Pandora209s1_CF_v8d20230220.txt",
            f"Level 0 file used: {l0_filename}",
            "Full location name: Izana Atmospheric Research Center",
            "Short location name: Izana",
            "Country of location: Spain",
            "Location latitude [deg]: 28.3090",
            "Location longitude [deg]: -16.4994",
            "Location altitude [m]: 2360",
            "Local noon date: 20250911",
            "Notes on s-number (L1 configuration): Corrections NOT applied although requested by the s-number are blind pixel subtraction, dark map for dark correction (replaced by immediate dark method), latency correction, matrix method stray light correction (replaced by simple method)",
            "Data caveats: None",
            f"Nominal wavelengths [nm]: {waves_str}",
            "",
        ]

        # Write header
        for line in lines:
            f.write(f"{line}\n")

        # Write column definitions
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


