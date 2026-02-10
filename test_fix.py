#!/usr/bin/env python3
from io_utils import read_l0_csv
from corrections import CalibrationData
from processor import process_l0_to_l1
from scodes import get_scode_configs

# Load L0 data
l0_path = "/Users/ashu/Desktop/Github/L0-to-L1/Pandora209s1_Izana_20250911_L0.txt"
print("[INFO] Reading L0 file...")
l0 = read_l0_csv(l0_path)
print(f"[INFO] Read {len(l0)} L0 records")

if len(l0) > 0:
    first_spec = l0[0].spectrum_counts
    print(f"[INFO] First spectrum has {len(first_spec)} pixels")
    
    # Create calibration data
    n_pix = len(first_spec)
    cal = CalibrationData(n_pixels=n_pix)
    print(f"[INFO] CalibrationData created with {n_pix} pixels")
    print(f"[INFO] PRNU array has {len(cal.prnu)} pixels")
    
    # Try processing
    print("[INFO] Processing L0 to L1...")
    scode = get_scode_configs()[0]  # Use first s-code
    try:
        l1_records, stats = process_l0_to_l1(l0, scode, cal)
        print(f"[SUCCESS] Processed {len(l1_records)} L1 records")
        print(f"[SUCCESS] Stats: {stats}")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
else:
    print("[ERROR] No L0 records found!")
