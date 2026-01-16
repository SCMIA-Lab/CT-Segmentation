import sys
import subprocess
from pathlib import Path

import SimpleITK as sitk
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QTextEdit, QComboBox, QMessageBox
)
from PyQt5.QtCore import QThread, pyqtSignal


# ===============================
# TotalSegmentator Tasks
# ===============================

TOTAL_SEGMENTATOR_TASKS = {
    "CT (default)": [
        "total",
        "lung_vessels",
        "body",
        "cerebral_bleed",
        "hip_implant",
        "pleural_pericard_effusion",
        "head_glands_cavities",
        "head_muscles",
        "headneck_bones_vessels",
        "headneck_muscles",
        "liver_vessels",
        "oculomotor_muscles",
        "lung_nodules",
        "kidney_cysts",
        "breasts",
        "liver_segments",
        "craniofacial_structures",
        "abdominal_muscles",
        "teeth",
        "trunk_cavities",
        "vertebrae_body",
        "brain_structures",
        "coronary_arteries",
        "face",
    ],
    "MR (_mr)": [
        "total_mr",
        "body_mr",
        "vertebrae_mr",
        "liver_segments_mr",
        "appendicular_bones_mr",
        "tissue_types_mr",
        "face_mr",
        "thigh_shoulder_muscles_mr",
    ],
    "Special / Licensed": [
        "heartchambers_highres",
        "appendicular_bones",
        "tissue_types",
        "tissue_4_types",
        "brain_aneurysm",
    ],
}


# ===============================
# Worker: DICOM → NIfTI
# ===============================

class DicomToNiftiWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(Path)

    def __init__(self, dicom_dir, output_dir):
        super().__init__()
        self.dicom_dir = Path(dicom_dir)
        self.output_dir = Path(output_dir)

    def run(self):
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            nifti_path = self.output_dir / "ct.nii.gz"

            self.log.emit("Reading DICOM folder...")

            reader = sitk.ImageSeriesReader()
            series_ids = reader.GetGDCMSeriesIDs(str(self.dicom_dir))

            if not series_ids:
                raise RuntimeError("No DICOM series found")

            best_series = max(
                series_ids,
                key=lambda sid: len(
                    reader.GetGDCMSeriesFileNames(str(self.dicom_dir), sid)
                )
            )

            files = reader.GetGDCMSeriesFileNames(
                str(self.dicom_dir), best_series
            )

            reader.SetFileNames(files)
            image = reader.Execute()

            sitk.WriteImage(image, str(nifti_path))
            self.log.emit(f"NIfTI created: {nifti_path}")

            self.finished.emit(nifti_path)

        except Exception as e:
            self.log.emit(f"ERROR: {e}")
            self.finished.emit(None)


# ===============================
# Worker: Segmentation
# ===============================

class SegmentationWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, nifti_path, output_dir,
                 method, model, device, ts_task):
        super().__init__()
        self.nifti_path = Path(nifti_path)
        self.output_dir = Path(output_dir)
        self.method = method
        self.model = model
        self.device = device
        self.ts_task = ts_task

    def run(self):
        try:
            if self.method == "Skellytour":
                self.run_skellytour()
            else:
                self.run_totalsegmentator()
            self.finished.emit()
        except Exception as e:
            self.log.emit(f"ERROR: {e}")
            self.finished.emit()

    def run_skellytour(self):
        self.log.emit("Running Skellytour...")

        cmd = [
            "skellytour",
            "-i", str(self.nifti_path),
            "-o", str(self.output_dir),
            "-m", self.model,
            "-d", self.device,
            "--overwrite"
        ]

        self._run(cmd)

    def run_totalsegmentator(self):
        self.log.emit(f"Running TotalSegmentator (task: {self.ts_task})")

        out_dir = self.output_dir / f"segmentations_{self.ts_task}"
        out_dir.mkdir(exist_ok=True)

        cmd = [
            "TotalSegmentator",
            "-i", str(self.nifti_path),
            "-o", str(out_dir),
            "-ta", self.ts_task
        ]

        self._run(cmd)

    def _run(self, cmd):
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            self.log.emit(line.rstrip())

        process.wait()
        if process.returncode != 0:
            raise RuntimeError("Segmentation failed")


# ===============================
# Main UI
# ===============================

class SegmentationUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CT Segmentation Pipeline")
        self.resize(780, 560)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "DICOM → NIfTI → Segmentation\n"
            "Supports Skellytour and TotalSegmentator"
        ))

        self.btn_dicom = QPushButton("Select DICOM Folder")
        self.btn_dicom.clicked.connect(self.select_dicom)
        layout.addWidget(self.btn_dicom)

        self.btn_output = QPushButton("Select Output Folder")
        self.btn_output.clicked.connect(self.select_output)
        layout.addWidget(self.btn_output)

        self.btn_convert = QPushButton("Convert DICOM → NIfTI")
        self.btn_convert.clicked.connect(self.convert_dicom)
        layout.addWidget(self.btn_convert)

        layout.addWidget(QLabel("Segmentation Method"))
        self.method_box = QComboBox()
        self.method_box.addItems(["Skellytour", "TotalSegmentator"])
        self.method_box.currentTextChanged.connect(self.on_method_changed)
        layout.addWidget(self.method_box)

        layout.addWidget(QLabel("Skellytour Model"))
        self.model_box = QComboBox()
        self.model_box.addItems(["low", "medium", "high"])
        layout.addWidget(self.model_box)

        layout.addWidget(QLabel("Skellytour Device"))
        self.device_box = QComboBox()
        self.device_box.addItems(["gpu", "cpu"])
        layout.addWidget(self.device_box)

        layout.addWidget(QLabel("TotalSegmentator Task"))
        self.ts_task_box = QComboBox()
        for group, tasks in TOTAL_SEGMENTATOR_TASKS.items():
            self.ts_task_box.addItem(f"--- {group} ---")
            for task in tasks:
                self.ts_task_box.addItem(task)
        layout.addWidget(self.ts_task_box)

        self.run_btn = QPushButton("Run Segmentation")
        self.run_btn.clicked.connect(self.run_segmentation)
        layout.addWidget(self.run_btn)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box, 1)

        self.dicom_dir = None
        self.output_dir = None
        self.nifti_path = None

        self.on_method_changed(self.method_box.currentText())

    def log(self, text):
        self.log_box.append(text)

    def on_method_changed(self, method):
        skel = method == "Skellytour"
        self.model_box.setEnabled(skel)
        self.device_box.setEnabled(skel)
        self.ts_task_box.setEnabled(not skel)

    def select_dicom(self):
        path = QFileDialog.getExistingDirectory(self, "Select DICOM Folder")
        if path:
            self.dicom_dir = path
            self.log(f"DICOM: {path}")

    def select_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_dir = path
            self.log(f"Output: {path}")

    def convert_dicom(self):
        if not self.dicom_dir or not self.output_dir:
            QMessageBox.warning(self, "Missing Input",
                                "Select DICOM and output folders")
            return

        self.log("Converting DICOM → NIfTI...\n")
        self.btn_convert.setEnabled(False)

        self.worker = DicomToNiftiWorker(self.dicom_dir, self.output_dir)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_nifti_done)
        self.worker.start()

    def on_nifti_done(self, nifti):
        self.btn_convert.setEnabled(True)
        if nifti:
            self.nifti_path = nifti
            self.log("\nNIfTI conversion done.\n")
        else:
            self.log("\nNIfTI conversion failed.\n")

    def run_segmentation(self):
        if not self.nifti_path:
            QMessageBox.warning(self, "Missing NIfTI",
                                "Run DICOM → NIfTI first")
            return

        task = self.ts_task_box.currentText()
        if task.startswith("---"):
            QMessageBox.warning(self, "Invalid Task",
                                "Select a valid TotalSegmentator task")
            return

        if task.endswith("_mr"):
            self.log("⚠ WARNING: MR task selected. Ensure MR input.\n")

        self.log("Starting segmentation...\n")
        self.run_btn.setEnabled(False)

        self.worker = SegmentationWorker(
            self.nifti_path,
            self.output_dir,
            self.method_box.currentText(),
            self.model_box.currentText(),
            self.device_box.currentText(),
            task
        )

        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self):
        self.run_btn.setEnabled(True)
        self.log("\nDone.\n")


# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = SegmentationUI()
    ui.show()
    sys.exit(app.exec_())
