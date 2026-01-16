# CT-Segmentation (DICOM → NIfTI → Bone Segmentation GUI)

CT-Segmentation is a lightweight and practical **medical imaging segmentation GUI** built using **PyQt5**.  
It provides an easy end-to-end workflow to:

- ✅ Load a **DICOM folder**
- ✅ Convert it into a **NIfTI (.nii.gz)** volume
- ✅ Run automated segmentation using modern AI tools

This project is useful for **researchers, students, and developers** working on CT imaging pipelines, helping reduce the manual effort of preparing data and running segmentation from the command line.

It supports:

- **Skellytour** *( bone segmentation)*
- **TotalSegmentator** *(bone and organ segmentation tasks)*

---

## Requirements

- **Python 3.10**
- PyQt5
- SimpleITK
- **Skellytour** *(install before running this GUI)*
- **TotalSegmentator** *(install before running this GUI)*

---

## Installation

### 1) Create Conda environment (recommended)

```bash
conda create -y -n ctseg python=3.10
conda activate ctseg
```

### 2) Install GUI dependencies
```bash
pip install PyQt5 SimpleITK
```

### 3) Install Skellytour
```bash
git clone https://github.com/cpwardell/Skellytour.git
cd Skellytour/
python -m pip install .
```

Verify Skellytour:
```bash
skellytour --help
```
### 4) Install TotalSegmentator
```bash
pip install totalsegmentator
```

Verify TotalSegmentator:
```bash
TotalSegmentator --help
```
Run the GUI
```bash
python main.py
```
### How to Use

1. Click Select DICOM Folder

2. Click Select Output Folder

3. Click Convert DICOM → NIfTI

   Creates: ct.nii.gz inside the output folder

4. Select Segmentation Method

  Skellytour

    Model: low / medium / high

    Device: gpu / cpu

  TotalSegmentator

    Select a task from the dropdown

    Click Run Segmentation

### Output
### NIfTI Output
```bash
<output_folder>/ct.nii.gz
```
### Skellytour Output

Saved inside:
```bash
<output_folder>/
```
### TotalSegmentator Output
Saved inside:
```bash
<output_folder>/segmentations_<task_name>/
```
### Notes

- Make sure skellytour and TotalSegmentator commands work in your terminal before using the GUI.
- GPU is recommended for faster segmentation, but CPU also works.
- TotalSegmentator may require a license depending on your usage:
    - A non-commercial license is available.
    - For commercial usage, please check the official TotalSegmentator license terms.
