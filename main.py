import os
import sys
import traceback
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, QVBoxLayout,
    QHBoxLayout, QProgressBar, QTextEdit, QMessageBox, QComboBox, QLineEdit,
    QCheckBox, QGroupBox, QFormLayout
)

from scodes import get_scode_configs
from io_utils import read_l0_csv, write_l1_text, build_l1_filename
from corrections import CalibrationData
from processor import process_l0_to_l1
from gpu_backend import get_backend


APP_NAME = "SciGlob Processor"
APP_VERSION = "1.0.0"


class SciGlobProcessorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - L0 to L1")
        self.resize(1100, 760)

        self.l0_files: List[str] = []
        self.output_dir: str = ""
        self.scodes = get_scode_configs()

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout()

        title = QLabel(f"{APP_NAME} (L0 → L1)")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel("S-code driven processing (cs00/cs01/cs02/cs03/cs04/mca0/mca1)")
        subtitle.setStyleSheet("color: #555;")
        root.addWidget(subtitle)

        # File block
        files_box = QGroupBox("Input / Output")
        files_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        self.btn_files = QPushButton("Select L0 Files")
        self.btn_files.clicked.connect(self.select_files)
        row1.addWidget(self.btn_files)

        self.lbl_files = QLabel("No files selected")
        self.lbl_files.setWordWrap(True)
        row1.addWidget(self.lbl_files, 1)
        files_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_out = QPushButton("Select Output Folder")
        self.btn_out.clicked.connect(self.select_output_dir)
        row2.addWidget(self.btn_out)

        self.lbl_out = QLabel("No output folder selected")
        self.lbl_out.setWordWrap(True)
        row2.addWidget(self.lbl_out, 1)
        files_layout.addLayout(row2)

        files_box.setLayout(files_layout)
        root.addWidget(files_box)

        # S-code config block
        cfg_box = QGroupBox("Processing Configuration")
        cfg_form = QFormLayout()

        self.cmb_scode = QComboBox()
        for k in self.scodes.keys():
            self.cmb_scode.addItem(k)
        self.cmb_scode.currentTextChanged.connect(self.update_scode_description)
        cfg_form.addRow("S-code:", self.cmb_scode)

        self.lbl_sdesc = QLabel("")
        self.lbl_sdesc.setWordWrap(True)
        self.lbl_sdesc.setStyleSheet("color:#333;")
        cfg_form.addRow("Description:", self.lbl_sdesc)

        self.in_cal_ver = QLineEdit("1")
        cfg_form.addRow("Calibration version (c):", self.in_cal_ver)

        self.in_cal_date = QLineEdit("20260101")
        cfg_form.addRow("Calibration date (d):", self.in_cal_date)

        self.chk_gpu = QCheckBox("Use GPU if available (CuPy)")
        self.chk_gpu.setChecked(False)
        cfg_form.addRow("Backend:", self.chk_gpu)

        cfg_box.setLayout(cfg_form)
        root.addWidget(cfg_box)

        # Run block
        run_row = QHBoxLayout()
        self.btn_run = QPushButton("Run L0 → L1")
        self.btn_run.clicked.connect(self.run_conversion)
        run_row.addWidget(self.btn_run)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        run_row.addWidget(self.progress, 1)
        root.addLayout(run_row)

        # Logs
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)

        self.setLayout(root)
        self.update_scode_description(self.cmb_scode.currentText())

    def append_log(self, msg: str):
        self.log.append(msg)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select L0 files",
            "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        if files:
            self.l0_files = files
            self.lbl_files.setText(f"{len(files)} file(s) selected")
            self.append_log(f"[INFO] Selected {len(files)} input file(s).")

    def select_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select output folder")
        if d:
            self.output_dir = d
            self.lbl_out.setText(d)
            self.append_log(f"[INFO] Output directory: {d}")

    def update_scode_description(self, code: str):
        sc = self.scodes.get(code)
        if not sc:
            self.lbl_sdesc.setText("Unknown s-code")
            return

        text = (
            f"{sc.description}\n"
            f"dark_unc_source={sc.dark_unc_source}, "
            f"straylight={sc.straylight_mode}, "
            f"sensitivity={'YES' if sc.sensitivity else 'NO'}, "
            f"wavelength={'YES' if sc.wavelength else 'NO'}"
        )
        self.lbl_sdesc.setText(text)

    def _validate_inputs(self) -> bool:
        if not self.l0_files:
            QMessageBox.warning(self, "Missing input", "Please select L0 files.")
            return False
        if not self.output_dir:
            QMessageBox.warning(self, "Missing output", "Please select output folder.")
            return False

        cal_ver = self.in_cal_ver.text().strip()
        cal_date = self.in_cal_date.text().strip()

        if not cal_ver:
            QMessageBox.warning(self, "Invalid calibration", "Calibration version cannot be empty.")
            return False
        if not (cal_date.isdigit() and len(cal_date) == 8):
            QMessageBox.warning(self, "Invalid calibration date", "Calibration date must be YYYYMMDD.")
            return False

        return True

    def run_conversion(self):
        if not self._validate_inputs():
            return

        code = self.cmb_scode.currentText().strip()
        scode = self.scodes[code]
        cal_ver = self.in_cal_ver.text().strip()
        cal_date = self.in_cal_date.text().strip()

        backend = get_backend(self.chk_gpu.isChecked())
        self.append_log(f"[INFO] Backend selected: {backend.name}")

        total = len(self.l0_files)
        done = 0

        self.progress.setValue(0)
        self.btn_run.setEnabled(False)

        try:
            for idx, path in enumerate(self.l0_files, start=1):
                self.append_log(f"\n[INFO] Processing file: {os.path.basename(path)}")
                l0 = read_l0_csv(path)
                if len(l0) == 0:
                    self.append_log("[WARN] No records found, skipping.")
                    continue

                n_pix = len(l0[0].spectrum_counts)
                cal = CalibrationData(n_pixels=n_pix)

                # Process
                l1_records, stats = process_l0_to_l1(l0, scode, cal)

                # Write
                out_name = build_l1_filename(
                    l0_path=path,
                    scode=scode,
                    cal_version=cal_ver,
                    cal_date=cal_date,
                    proc_version="1-0"
                )
                out_path = os.path.join(self.output_dir, out_name)

                # Extract instrument and spectrometer numbers from L0 filename
                l0_basename = os.path.basename(path)
                # Expected format: Pandora209s1_Izana_*
                instrument_num = "209"
                spectrometer_num = "s1"
                if "Pandora" in l0_basename:
                    parts = l0_basename.split("_")
                    if parts:
                        prefix = parts[0]  # e.g., "Pandora209s1"
                        if prefix.startswith("Pandora"):
                            after_pandora = prefix[7:]  # Remove "Pandora"
                            for i, c in enumerate(after_pandora):
                                if c.isalpha():
                                    instrument_num = after_pandora[:i]
                                    spectrometer_num = after_pandora[i:]
                                    break

                write_l1_text(
                    out_path=out_path,
                    l1_records=l1_records,
                    scode=scode,
                    cal_version=cal_ver,
                    cal_date=cal_date,
                    l0_filename=l0_basename,
                    instrument_number=instrument_num,
                    spectrometer_number=spectrometer_num,
                    wavelengths=cal.wavelength_nm,
                    software_name=APP_NAME,
                    software_version=APP_VERSION,
                    proc_version="1-0"
                )

                self.append_log(
                    f"[OK] Wrote: {out_path}\n"
                    f"      Records={stats.total}, DQ0={stats.good}, DQ1={stats.medium}, DQ2={stats.low}"
                )

                done += 1
                self.progress.setValue(int(idx * 100 / total))
                QApplication.processEvents()

            QMessageBox.information(self, "Done", f"Completed {done}/{total} file(s).")
            self.append_log(f"\n[DONE] Completed {done}/{total} file(s).")

        except Exception as e:
            self.append_log("[ERROR] Processing failed.")
            self.append_log(str(e))
            self.append_log(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Processing failed:\n{e}")
        finally:
            self.btn_run.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SciGlobProcessorGUI()
    w.show()
    sys.exit(app.exec_())
